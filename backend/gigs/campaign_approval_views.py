# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Exposes deterministic campaign review, owner-safe editing, approved launch, and Phase 2 option-enriched payloads.

"""REST endpoints for campaign approval and enriched campaign details."""

from __future__ import annotations

import logging
from uuid import uuid4

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .campaign_approval import (
    DRAFT,
    PENDING_REVIEW,
    REJECTED,
    CampaignApprovalError,
    CampaignApprovalPermissionError,
    approve_campaign_manually,
    can_review_campaigns,
    launch_approved_campaign,
    reject_campaign_manually,
    submit_campaign_for_review,
)
from .campaign_preference_serializers import (
    CampaignDateOptionSerializer,
    CampaignPriceOptionSerializer,
    SupporterPreferenceSerializer,
)
from .campaign_preferences import (
    PUBLIC_CAMPAIGN_STATUSES,
    CampaignPreferenceError,
    build_preference_summary,
    create_date_option,
    create_price_option,
    current_user_preference,
    deactivate_date_option,
    deactivate_price_option,
    replace_campaign_options,
    update_date_option,
    update_price_option,
)
from .campaign_review_models import CampaignReview
from .models import CampaignEvent, DemandCampaign
from .serializers import CampaignSerializer


logger = logging.getLogger(__name__)


def _can_view_private_campaign(campaign: DemandCampaign, user) -> bool:
    """Allow owners and trusted reviewers to see nonpublic lifecycle states."""

    return bool(
        getattr(user, "is_authenticated", False)
        and (
            campaign.owner_id == user.id
            or can_review_campaigns(user)
        )
    )


def _visible_campaigns_for(user):
    """Return public campaigns plus the authenticated owner's private records."""

    queryset = DemandCampaign.objects.select_related("owner")
    if can_review_campaigns(user):
        return queryset.all()
    if getattr(user, "is_authenticated", False):
        return queryset.filter(
            Q(status__in=PUBLIC_CAMPAIGN_STATUSES) | Q(owner_id=user.id)
        )
    return queryset.filter(status__in=PUBLIC_CAMPAIGN_STATUSES)


def _review_payload(review: CampaignReview | None) -> dict | None:
    """Serialize review evidence without exposing the full reviewer account."""

    if review is None:
        return None
    return {
        "id": review.id,
        "decision": review.decision,
        "reviewer_id": review.reviewer_id,
        "notes": review.notes,
        "checks": review.checks,
        "reviewed_at": review.reviewed_at,
        "previous_status": review.previous_status,
        "resulting_status": review.resulting_status,
    }


def _campaign_payload(campaign: DemandCampaign, request, review=None) -> dict:
    """Add approval, option, aggregate, and actor-capability data."""

    payload = CampaignSerializer(campaign, context={"request": request}).data
    payload["latest_review"] = _review_payload(
        review
        or campaign.reviews.select_related("reviewer")
        .order_by("-reviewed_at", "-id")
        .first()
    )
    payload["can_manage"] = bool(
        request.user.is_authenticated
        and (campaign.owner_id == request.user.id or request.user.is_staff)
    )
    payload["can_review_campaign"] = can_review_campaigns(request.user)
    payload["date_options"] = CampaignDateOptionSerializer(
        campaign.date_options.filter(active=True),
        many=True,
    ).data
    payload["price_options"] = CampaignPriceOptionSerializer(
        campaign.price_options.filter(active=True),
        many=True,
    ).data
    payload["preference_summary"] = build_preference_summary(campaign)

    own_preference = current_user_preference(campaign, request.user)
    payload["my_preference"] = (
        SupporterPreferenceSerializer(own_preference).data
        if own_preference is not None
        else None
    )
    return payload


def _error(exc: CampaignApprovalError) -> Response:
    """Return static public messages so internal exception details are never exposed."""

    if isinstance(exc, CampaignApprovalPermissionError):
        return Response(
            {"detail": "You do not have permission to perform this campaign action."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response(
        {"detail": "The campaign cannot complete this transition in its current state."},
        status=status.HTTP_409_CONFLICT,
    )


def _unexpected_approval_error(
    *,
    action: str,
    campaign: DemandCampaign,
    user,
) -> Response:
    """Log an unexpected approval failure and return an opaque support reference."""

    reference_id = uuid4().hex[:16]
    logger.exception(
        "Unexpected campaign approval failure "
        "reference_id=%s action=%s campaign_id=%s campaign_slug=%s "
        "campaign_status=%s actor_id=%s",
        reference_id,
        action,
        campaign.id,
        campaign.slug,
        campaign.status,
        getattr(user, "id", None),
    )
    response = Response(
        {
            "detail": (
                "Approval checks could not be completed because of a server error. "
                f"Reference: {reference_id}."
            ),
            "error_code": "campaign_approval_internal_error",
            "reference_id": reference_id,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    response["X-Error-Reference"] = reference_id
    return response


def _split_campaign_input(request) -> tuple[dict, object, object]:
    """Separate nested Phase 2 options from legacy campaign scalar fields."""

    campaign_data = {
        key: value
        for key, value in request.data.items()
        if key not in {"date_options", "price_options"}
    }
    return (
        campaign_data,
        request.data.get("date_options"),
        request.data.get("price_options"),
    )


def _validate_option_input(date_input, price_input) -> tuple[list | None, list | None]:
    """Validate optional nested option lists before initial campaign creation."""

    validated_dates = None
    validated_prices = None

    if date_input is not None:
        if not isinstance(date_input, list):
            raise TypeError("date_options must be a list")
        serializer = CampaignDateOptionSerializer(data=date_input, many=True)
        serializer.is_valid(raise_exception=True)
        validated_dates = [dict(item) for item in serializer.validated_data]

    if price_input is not None:
        if not isinstance(price_input, list):
            raise TypeError("price_options must be a list")
        serializer = CampaignPriceOptionSerializer(data=price_input, many=True)
        serializer.is_valid(raise_exception=True)
        validated_prices = [dict(item) for item in serializer.validated_data]

    return validated_dates, validated_prices


def _option_rows(value, field_name: str) -> list[dict]:
    """Require a nonempty list of option objects for a full-seed edit."""

    if not isinstance(value, list) or not value:
        raise serializers.ValidationError(
            {field_name: "Provide at least one option."}
        )
    if any(not isinstance(item, dict) for item in value):
        raise serializers.ValidationError(
            {field_name: "Every option must be a JSON object."}
        )
    return [dict(item) for item in value]


def _sync_date_options(campaign: DemandCampaign, user, raw_options) -> None:
    """Create, update, or safely deactivate dates through covered services."""

    existing = {option.id: option for option in campaign.date_options.all()}
    retained: set[int] = set()

    for row in _option_rows(raw_options, "date_options"):
        option_id = row.pop("id", None)
        if option_id is None:
            serializer = CampaignDateOptionSerializer(data=row)
            serializer.is_valid(raise_exception=True)
            option = create_date_option(campaign.id, user, dict(serializer.validated_data))
        else:
            try:
                option_id = int(option_id)
                option = existing[option_id]
            except (KeyError, TypeError, ValueError) as exc:
                raise serializers.ValidationError(
                    {"date_options": "A date option does not belong to this campaign."}
                ) from exc
            serializer = CampaignDateOptionSerializer(option, data=row)
            serializer.is_valid(raise_exception=True)
            option = update_date_option(
                campaign.id,
                option_id,
                user,
                dict(serializer.validated_data),
            )
        retained.add(option.id)

    for option in existing.values():
        if option.active and option.id not in retained:
            deactivate_date_option(campaign.id, option.id, user)


def _sync_price_options(campaign: DemandCampaign, user, raw_options) -> None:
    """Create, update, or safely deactivate prices through covered services."""

    existing = {option.id: option for option in campaign.price_options.all()}
    retained: set[int] = set()

    for row in _option_rows(raw_options, "price_options"):
        option_id = row.pop("id", None)
        if option_id is None:
            serializer = CampaignPriceOptionSerializer(data=row)
            serializer.is_valid(raise_exception=True)
            option = create_price_option(campaign.id, user, dict(serializer.validated_data))
        else:
            try:
                option_id = int(option_id)
                option = existing[option_id]
            except (KeyError, TypeError, ValueError) as exc:
                raise serializers.ValidationError(
                    {"price_options": "A price option does not belong to this campaign."}
                ) from exc
            serializer = CampaignPriceOptionSerializer(option, data=row)
            serializer.is_valid(raise_exception=True)
            option = update_price_option(
                campaign.id,
                option_id,
                user,
                dict(serializer.validated_data),
            )
        retained.add(option.id)

    for option in existing.values():
        if option.active and option.id not in retained:
            deactivate_price_option(campaign.id, option.id, user)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def campaign_collection(request):
    """Provide enriched public listing and authenticated nested campaign creation."""

    if request.method == "GET":
        campaigns = _visible_campaigns_for(request.user)
        return Response([_campaign_payload(campaign, request) for campaign in campaigns])

    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication is required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    campaign_data, date_input, price_input = _split_campaign_input(request)
    try:
        validated_dates, validated_prices = _validate_option_input(
            date_input,
            price_input,
        )
    except TypeError:
        return Response(
            {"detail": "Campaign date and price options must be JSON lists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = CampaignSerializer(
        data=campaign_data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    with transaction.atomic():
        campaign = serializer.save(owner=request.user)
        CampaignEvent.objects.create(
            campaign=campaign,
            event_type="campaign.created",
            payload={"actor_id": request.user.id},
        )
        if validated_dates is not None or validated_prices is not None:
            replace_campaign_options(
                campaign.id,
                request.user,
                date_options=validated_dates,
                price_options=validated_prices,
            )

    return Response(
        _campaign_payload(campaign, request),
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def campaign_detail(request, slug: str):
    """Allow owner seed edits at any status while protecting lifecycle state."""

    campaign = get_object_or_404(
        DemandCampaign.objects.select_related("owner"),
        slug=slug,
    )
    if request.method == "GET":
        if (
            campaign.status not in PUBLIC_CAMPAIGN_STATUSES
            and not _can_view_private_campaign(campaign, request.user)
        ):
            return Response(
                {"detail": "Campaign not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(_campaign_payload(campaign, request))

    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication is required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if campaign.owner_id != request.user.id and not request.user.is_staff:
        return Response(
            {"detail": "Only the campaign owner or an administrator may modify it."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "DELETE":
        if campaign.status not in [DRAFT, REJECTED]:
            return Response(
                {
                    "detail": (
                        "An active campaign cannot be deleted. Edit its seed or use "
                        "the lifecycle controls instead."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        campaign.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    campaign_data, date_input, price_input = _split_campaign_input(request)
    serializer = CampaignSerializer(
        campaign,
        data=campaign_data,
        partial=request.method == "PATCH",
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    before = {
        field: getattr(campaign, field)
        for field in campaign_data
        if hasattr(campaign, field)
    }

    try:
        with transaction.atomic():
            campaign = serializer.save()
            if date_input is not None:
                _sync_date_options(campaign, request.user, date_input)
            if price_input is not None:
                _sync_price_options(campaign, request.user, price_input)
            changed_fields = [
                field
                for field, previous_value in before.items()
                if getattr(campaign, field) != previous_value
            ]
            CampaignEvent.objects.create(
                campaign=campaign,
                event_type="campaign.owner_edited",
                payload={
                    "actor_id": request.user.id,
                    "status": campaign.status,
                    "changed_fields": changed_fields,
                    "date_options_edited": date_input is not None,
                    "price_options_edited": price_input is not None,
                    "protected_fields_unchanged": [
                        "owner",
                        "slug",
                        "status",
                        "artist_confirmed",
                        "venue_confirmed",
                        "confirmed_artist_details",
                        "confirmed_venue_details",
                        "event_id",
                    ],
                },
            )
    except CampaignPreferenceError:
        return Response(
            {
                "detail": (
                    "A date or price with supporter votes cannot be removed. "
                    "Edit it or add another option instead."
                )
            },
            status=status.HTTP_409_CONFLICT,
        )

    return Response(_campaign_payload(campaign, request))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def campaign_submit_review(request, slug: str):
    """Run automatic checks and approve or route the campaign to administrators."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    try:
        campaign, review = submit_campaign_for_review(campaign.id, request.user)
        return Response(_campaign_payload(campaign, request, review))
    except CampaignApprovalError as exc:
        return _error(exc)
    except Exception:
        return _unexpected_approval_error(
            action="submit_review",
            campaign=campaign,
            user=request.user,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def campaign_approve(request, slug: str):
    """Apply an administrator approval after automatic checks requested manual review."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    notes = str(request.data.get("notes", "")).strip()
    try:
        campaign, review = approve_campaign_manually(
            campaign.id,
            request.user,
            notes,
        )
    except CampaignApprovalError as exc:
        return _error(exc)
    return Response(_campaign_payload(campaign, request, review))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def campaign_reject(request, slug: str):
    """Reject a pending campaign and return written correction notes to its owner."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    notes = str(request.data.get("notes", "")).strip()
    try:
        campaign, review = reject_campaign_manually(
            campaign.id,
            request.user,
            notes,
        )
    except CampaignApprovalError as exc:
        return _error(exc)
    return Response(_campaign_payload(campaign, request, review))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def campaign_launch(request, slug: str):
    """Run deterministic review for legacy launch calls, then launch only approval-passing campaigns."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    try:
        review = None
        if campaign.status in [DRAFT, REJECTED]:
            campaign, review = submit_campaign_for_review(campaign.id, request.user)
        if campaign.status == PENDING_REVIEW:
            payload = _campaign_payload(campaign, request, review)
            payload["detail"] = (
                "Automatic checks require administrator review before launch."
            )
            return Response(payload, status=status.HTTP_409_CONFLICT)
        campaign = launch_approved_campaign(campaign.id, request.user)
    except CampaignApprovalError as exc:
        return _error(exc)
    return Response(_campaign_payload(campaign, request))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def campaign_review_queue(request):
    """Return pending campaigns only to trusted campaign reviewers."""

    if not can_review_campaigns(request.user):
        return Response(
            {"detail": "Administrator campaign-review permission is required."},
            status=status.HTTP_403_FORBIDDEN,
        )
    campaigns = (
        DemandCampaign.objects.filter(status=PENDING_REVIEW)
        .select_related("owner")
        .order_by("created_at")
    )
    return Response([_campaign_payload(campaign, request) for campaign in campaigns])
