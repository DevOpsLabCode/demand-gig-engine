# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Exposes privacy-safe date, price, attendance-vote, and aggregate campaign APIs.

"""Phase 2 REST endpoints."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .campaign_approval import can_review_campaigns
from .campaign_preference_models import (
    CampaignDateOption,
    CampaignPriceOption,
)
from .campaign_preference_serializers import (
    CampaignDateOptionSerializer,
    CampaignPriceOptionSerializer,
    SupporterPreferenceSerializer,
)
from .campaign_preferences import (
    PUBLIC_CAMPAIGN_STATUSES,
    CampaignPreferenceError,
    CampaignPreferencePermissionError,
    build_preference_summary,
    create_date_option,
    create_price_option,
    current_user_preference,
    deactivate_date_option,
    deactivate_price_option,
    update_date_option,
    update_price_option,
    upsert_supporter_preference,
)
from .models import DemandCampaign


def _can_view_campaign(campaign: DemandCampaign, user) -> bool:
    """Allow public active campaigns plus owner or administrator access."""

    if campaign.status in PUBLIC_CAMPAIGN_STATUSES:
        return True
    return bool(
        getattr(user, "is_authenticated", False)
        and (
            campaign.owner_id == user.id
            or can_review_campaigns(user)
        )
    )


def _not_found_if_private(campaign: DemandCampaign, user):
    """Return a privacy-preserving 404 response for a private campaign."""

    if _can_view_campaign(campaign, user):
        return None
    return Response(
        {"detail": "Campaign not found."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _error(exc: CampaignPreferenceError) -> Response:
    """Map domain failures to static public messages."""

    if isinstance(exc, CampaignPreferencePermissionError):
        return Response(
            {"detail": "You do not have permission to manage these campaign options."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response(
        {"detail": "The campaign cannot accept this option or preference now."},
        status=status.HTTP_409_CONFLICT,
    )


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def campaign_date_options(request, slug: str):
    """List active dates publicly and let an owner or administrator add dates."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    if request.method == "GET":
        private_response = _not_found_if_private(campaign, request.user)
        if private_response is not None:
            return private_response
        options = campaign.date_options.filter(active=True)
        return Response(CampaignDateOptionSerializer(options, many=True).data)

    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication is required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    serializer = CampaignDateOptionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        option = create_date_option(
            campaign.id,
            request.user,
            dict(serializer.validated_data),
        )
    except CampaignPreferenceError as exc:
        return _error(exc)
    return Response(
        CampaignDateOptionSerializer(option).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def campaign_date_option_detail(request, slug: str, option_id: int):
    """Update or deactivate one campaign date while the campaign is editable."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    option = get_object_or_404(
        CampaignDateOption,
        pk=option_id,
        campaign=campaign,
    )
    if request.method == "DELETE":
        try:
            deactivate_date_option(campaign.id, option.id, request.user)
        except CampaignPreferenceError as exc:
            return _error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CampaignDateOptionSerializer(
        option,
        data=request.data,
        partial=request.method == "PATCH",
    )
    serializer.is_valid(raise_exception=True)
    try:
        option = update_date_option(
            campaign.id,
            option.id,
            request.user,
            dict(serializer.validated_data),
        )
    except CampaignPreferenceError as exc:
        return _error(exc)
    return Response(CampaignDateOptionSerializer(option).data)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def campaign_price_options(request, slug: str):
    """List active prices publicly and let an owner or administrator add prices."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    if request.method == "GET":
        private_response = _not_found_if_private(campaign, request.user)
        if private_response is not None:
            return private_response
        options = campaign.price_options.filter(active=True)
        return Response(CampaignPriceOptionSerializer(options, many=True).data)

    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication is required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    serializer = CampaignPriceOptionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        option = create_price_option(
            campaign.id,
            request.user,
            dict(serializer.validated_data),
        )
    except CampaignPreferenceError as exc:
        return _error(exc)
    return Response(
        CampaignPriceOptionSerializer(option).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def campaign_price_option_detail(request, slug: str, option_id: int):
    """Update or deactivate one ticket-price choice while editable."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    option = get_object_or_404(
        CampaignPriceOption,
        pk=option_id,
        campaign=campaign,
    )
    if request.method == "DELETE":
        try:
            deactivate_price_option(campaign.id, option.id, request.user)
        except CampaignPreferenceError as exc:
            return _error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CampaignPriceOptionSerializer(
        option,
        data=request.data,
        partial=request.method == "PATCH",
    )
    serializer.is_valid(raise_exception=True)
    try:
        option = update_price_option(
            campaign.id,
            option.id,
            request.user,
            dict(serializer.validated_data),
        )
    except CampaignPreferenceError as exc:
        return _error(exc)
    return Response(CampaignPriceOptionSerializer(option).data)


@api_view(["GET", "POST", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def campaign_supporter_preference(request, slug: str):
    """Read or upsert only the authenticated user's campaign preference."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    private_response = _not_found_if_private(campaign, request.user)
    if private_response is not None:
        return private_response
    existing = current_user_preference(campaign, request.user)
    if request.method == "GET":
        return Response(
            {
                "preference": (
                    SupporterPreferenceSerializer(existing).data
                    if existing is not None
                    else None
                )
            }
        )

    serializer = SupporterPreferenceSerializer(
        existing,
        data=request.data,
        partial=request.method == "PATCH",
        context={"campaign": campaign},
    )
    serializer.is_valid(raise_exception=True)
    try:
        preference, created = upsert_supporter_preference(
            campaign.id,
            request.user,
            dict(serializer.validated_data),
        )
    except CampaignPreferenceError as exc:
        return _error(exc)
    return Response(
        SupporterPreferenceSerializer(preference).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def campaign_preference_summary(request, slug: str):
    """Return aggregate demand without user IDs, emails, or private notes."""

    campaign = get_object_or_404(DemandCampaign, slug=slug)
    private_response = _not_found_if_private(campaign, request.user)
    if private_response is not None:
        return private_response
    return Response(build_preference_summary(campaign))
