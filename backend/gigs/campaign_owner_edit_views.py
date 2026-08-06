# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Allows owners to edit campaign seed content at any lifecycle stage while preserving protected state and audit history.

"""Owner-safe campaign retrieval, editing, and restricted deletion."""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .campaign_approval import DRAFT, REJECTED
from .campaign_approval_views import (
    _campaign_payload,
    _can_view_private_campaign,
    _split_campaign_input,
)
from .campaign_preferences import PUBLIC_CAMPAIGN_STATUSES
from .models import CampaignEvent, DemandCampaign
from .serializers import CampaignSerializer


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def campaign_owner_edit_detail(request, slug: str):
    """Retrieve a campaign and allow its owner to edit seed content at any status."""

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
        CampaignEvent.objects.create(
            campaign=campaign,
            event_type="campaign.owner_edited",
            payload={
                "actor_id": request.user.id,
                "campaign_status": campaign.status,
                "changed_fields": changed_fields,
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

    return Response(_campaign_payload(campaign, request))
