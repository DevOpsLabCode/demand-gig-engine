# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Allows owners to edit campaign seed content and options at any lifecycle stage while preserving protected state, votes, and audit history.

"""Owner-safe campaign and option editing with restricted destructive actions."""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .campaign_approval import DRAFT, REJECTED, can_review_campaigns
from .campaign_approval_views import (
    _campaign_payload,
    _can_view_private_campaign,
    _split_campaign_input,
)
from .campaign_preference_models import CampaignDateOption, CampaignPriceOption
from .campaign_preference_serializers import (
    CampaignDateOptionSerializer,
    CampaignPriceOptionSerializer,
)
from .campaign_preferences import PUBLIC_CAMPAIGN_STATUSES
from .models import CampaignEvent, DemandCampaign
from .serializers import CampaignSerializer


def _may_manage(campaign: DemandCampaign, user) -> bool:
    """Return whether the actor may edit campaign seed information."""

    return bool(
        getattr(user, "is_authenticated", False)
        and (
            campaign.owner_id == user.id
            or user.is_staff
            or can_review_campaigns(user)
        )
    )


def _permission_error() -> Response:
    return Response(
        {"detail": "Only the campaign owner or an administrator may modify it."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _private_response(campaign: DemandCampaign, user):
    if (
        campaign.status not in PUBLIC_CAMPAIGN_STATUSES
        and not _can_view_private_campaign(campaign, user)
    ):
        return Response(
            {"detail": "Campaign not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return None


def _record_event(campaign: DemandCampaign, event_type: str, user, **payload) -> None:
    CampaignEvent.objects.create(
        campaign=campaign,
        event_type=event_type,
        payload={"actor_id": user.id, "campaign_status": campaign.status, **payload},
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def campaign_owner_edit_detail(request, slug: str):
    """Retrieve a campaign and allow its owner to edit seed content at any status."""

    campaign = get_object_or_404(
        DemandCampaign.objects.select_related("owner"),
        slug=slug,
    )

    if request.method == "GET":
        hidden = _private_response(campaign, request.user)
        return hidden or Response(_campaign_payload(campaign, request))

    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication is required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not _may_manage(campaign, request.user):
        return _permission_error()

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
    if date_input is not None or price_input is not None:
        return Response(
            {
                "detail": (
                    "Edit campaign date and price choices through their dedicated "
                    "option controls so existing supporter votes remain protected."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

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

    with transaction.atomic():
        campaign = serializer.save()
        changed_fields = [
            field
            for field, previous_value in before.items()
            if getattr(campaign, field) != previous_value
        ]
        _record_event(
            campaign,
            "campaign.owner_edited",
            request.user,
            changed_fields=changed_fields,
            protected_fields_unchanged=[
                "owner",
                "slug",
                "status",
                "artist_confirmed",
                "venue_confirmed",
                "confirmed_artist_details",
                "confirmed_venue_details",
                "event_id",
            ],
        )

    return Response(_campaign_payload(campaign, request))


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def campaign_owner_date_options(request, slug: str):
    """List active dates and allow owner-managed additions at every status."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    if request.method == "GET":
        hidden = _private_response(campaign, request.user)
        if hidden is not None:
            return hidden
        return Response(
            CampaignDateOptionSerializer(
                campaign.date_options.filter(active=True),
                many=True,
            ).data
        )

    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication is required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if not _may_manage(campaign, request.user):
        return _permission_error()

    serializer = CampaignDateOptionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        option = CampaignDateOption.objects.create(
            campaign=campaign,
            **serializer.validated_data,
        )
        _record_event(
            campaign,
            "campaign.date_option.created",
            request.user,
            option_id=option.id,
        )
    return Response(
        CampaignDateOptionSerializer(option).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def campaign_owner_date_option_detail(request, slug: str, option_id: int):
    """Update a date at any status and prevent removal after supporter selection."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    option = get_object_or_404(
        CampaignDateOption,
        pk=option_id,
        campaign=campaign,
    )
    if not _may_manage(campaign, request.user):
        return _permission_error()

    if request.method == "DELETE":
        if option.preferences.exists():
            return Response(
                {
                    "detail": (
                        "This date already has supporter votes and cannot be removed. "
                        "Edit it or add another date instead."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        with transaction.atomic():
            option.active = False
            option.save(update_fields=["active"])
            _record_event(
                campaign,
                "campaign.date_option.deactivated",
                request.user,
                option_id=option.id,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CampaignDateOptionSerializer(
        option,
        data=request.data,
        partial=request.method == "PATCH",
    )
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        for field, value in serializer.validated_data.items():
            setattr(option, field, value)
        option.full_clean()
        option.save()
        _record_event(
            campaign,
            "campaign.date_option.updated",
            request.user,
            option_id=option.id,
            changed_fields=list(serializer.validated_data),
        )
    return Response(CampaignDateOptionSerializer(option).data)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def campaign_owner_price_options(request, slug: str):
    """List active prices and allow owner-managed additions at every status."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    if request.method == "GET":
        hidden = _private_response(campaign, request.user)
        if hidden is not None:
            return hidden
        return Response(
            CampaignPriceOptionSerializer(
                campaign.price_options.filter(active=True),
                many=True,
            ).data
        )

    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication is required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if not _may_manage(campaign, request.user):
        return _permission_error()

    serializer = CampaignPriceOptionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        option = CampaignPriceOption.objects.create(
            campaign=campaign,
            **serializer.validated_data,
        )
        _record_event(
            campaign,
            "campaign.price_option.created",
            request.user,
            option_id=option.id,
        )
    return Response(
        CampaignPriceOptionSerializer(option).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def campaign_owner_price_option_detail(request, slug: str, option_id: int):
    """Update a price at any status and prevent removal after supporter selection."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    option = get_object_or_404(
        CampaignPriceOption,
        pk=option_id,
        campaign=campaign,
    )
    if not _may_manage(campaign, request.user):
        return _permission_error()

    if request.method == "DELETE":
        if option.preferences.exists():
            return Response(
                {
                    "detail": (
                        "This price already has supporter votes and cannot be removed. "
                        "Edit it or add another price instead."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        with transaction.atomic():
            option.active = False
            option.save(update_fields=["active"])
            _record_event(
                campaign,
                "campaign.price_option.deactivated",
                request.user,
                option_id=option.id,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CampaignPriceOptionSerializer(
        option,
        data=request.data,
        partial=request.method == "PATCH",
    )
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        for field, value in serializer.validated_data.items():
            setattr(option, field, value)
        option.full_clean()
        option.save()
        _record_event(
            campaign,
            "campaign.price_option.updated",
            request.user,
            option_id=option.id,
            changed_fields=list(serializer.validated_data),
        )
    return Response(CampaignPriceOptionSerializer(option).data)
