# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Exposes deterministic campaign submission, manual fallback review, protected editing, and approved launch.

"""REST endpoints for Phase 1B campaign approval."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
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
from .campaign_review_models import CampaignReview
from .models import CampaignEvent, DemandCampaign
from .serializers import CampaignSerializer


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
    """Add approval state and actor capabilities to the existing campaign contract."""

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
    return payload


def _error(exc: Exception) -> Response:
    """Preserve permission semantics separately from lifecycle conflicts."""

    response_status = (
        status.HTTP_403_FORBIDDEN
        if isinstance(exc, CampaignApprovalPermissionError)
        else status.HTTP_409_CONFLICT
    )
    return Response({"detail": str(exc)}, status=response_status)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def campaign_collection(request):
    """Provide enriched public listing and authenticated campaign creation."""

    if request.method == "GET":
        campaigns = DemandCampaign.objects.select_related("owner").all()
        return Response([_campaign_payload(campaign, request) for campaign in campaigns])

    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication is required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = CampaignSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    campaign = serializer.save(owner=request.user)
    CampaignEvent.objects.create(
        campaign=campaign,
        event_type="campaign.created",
        payload={"actor_id": request.user.id},
    )
    return Response(
        _campaign_payload(campaign, request),
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def campaign_detail(request, slug: str):
    """Provide public retrieval while limiting edits and deletion to draft/rejected owners."""

    campaign = get_object_or_404(
        DemandCampaign.objects.select_related("owner"),
        slug=slug,
    )
    if request.method == "GET":
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
    if campaign.status not in [DRAFT, REJECTED]:
        return Response(
            {"detail": "Campaign content can be changed only while draft or rejected."},
            status=status.HTTP_409_CONFLICT,
        )

    if request.method == "DELETE":
        campaign.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CampaignSerializer(
        campaign,
        data=request.data,
        partial=request.method == "PATCH",
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    campaign = serializer.save()
    CampaignEvent.objects.create(
        campaign=campaign,
        event_type="campaign.updated",
        payload={"actor_id": request.user.id, "status": campaign.status},
    )
    return Response(_campaign_payload(campaign, request))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def campaign_submit_review(request, slug: str):
    """Run automatic checks and approve or route the campaign to administrators."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    try:
        campaign, review = submit_campaign_for_review(campaign.id, request.user)
    except CampaignApprovalError as exc:
        return _error(exc)
    return Response(_campaign_payload(campaign, request, review))


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
    except (CampaignApprovalError, ValueError) as exc:
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
