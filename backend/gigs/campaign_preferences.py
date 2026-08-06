# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Manages campaign choices, private supporter votes, and privacy-safe aggregate demand calculations.

"""Transactional Phase 2 campaign preference services."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from .campaign_approval import can_review_campaigns
from .campaign_preference_models import (
    AttendanceMode,
    CampaignDateOption,
    CampaignPriceOption,
    SupporterPreference,
)
from .models import CampaignEvent, DemandCampaign, Pledge, SponsorCommitment


PUBLIC_CAMPAIGN_STATUSES = {
    "approved",
    "collecting",
    "target_reached",
    "threshold_reached",
    "confirming",
    "feasibility_review",
    "conditionally_ready",
    "ready",
    "handed_off",
    "confirmed",
    "live",
    "completed",
}
OPTION_EDITABLE_STATUSES = {"draft", "rejected"}
VOTING_STATUSES = {
    "approved",
    "collecting",
    "target_reached",
    "threshold_reached",
    "feasibility_review",
    "conditionally_ready",
    "ready",
}


class CampaignPreferenceError(ValueError):
    """Raised when an option or vote violates the Phase 2 state machine."""


class CampaignPreferencePermissionError(CampaignPreferenceError):
    """Raised when an actor may not manage the selected campaign."""


def _may_manage(campaign: DemandCampaign, user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and (
            campaign.owner_id == user.id
            or user.is_staff
            or can_review_campaigns(user)
        )
    )


def _ensure_option_management(campaign: DemandCampaign, user) -> None:
    if not _may_manage(campaign, user):
        raise CampaignPreferencePermissionError(
            "Only the campaign owner or an administrator may manage options."
        )
    if campaign.status not in OPTION_EDITABLE_STATUSES:
        raise CampaignPreferenceError(
            "Campaign options can be changed only while draft or rejected."
        )


def _event(campaign: DemandCampaign, event_type: str, **payload) -> None:
    CampaignEvent.objects.create(
        campaign=campaign,
        event_type=event_type,
        payload=payload,
    )


@transaction.atomic
def replace_campaign_options(
    campaign_id,
    user,
    *,
    date_options: list[dict] | None = None,
    price_options: list[dict] | None = None,
) -> DemandCampaign:
    """Replace supplied option groups while the campaign remains editable."""

    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    _ensure_option_management(campaign, user)

    if date_options is not None:
        campaign.date_options.all().delete()
        CampaignDateOption.objects.bulk_create(
            [
                CampaignDateOption(campaign=campaign, **item)
                for item in date_options
            ]
        )
    if price_options is not None:
        campaign.price_options.all().delete()
        CampaignPriceOption.objects.bulk_create(
            [
                CampaignPriceOption(
                    campaign=campaign,
                    currency=str(item.get("currency", campaign.currency)).upper(),
                    amount=item["amount"],
                    label=item.get("label", ""),
                    active=item.get("active", True),
                )
                for item in price_options
            ]
        )

    _event(
        campaign,
        "campaign.options.replaced",
        actor_id=user.id,
        date_option_count=campaign.date_options.count(),
        price_option_count=campaign.price_options.count(),
    )
    return campaign


@transaction.atomic
def create_date_option(campaign_id, user, data: dict) -> CampaignDateOption:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    _ensure_option_management(campaign, user)
    option = CampaignDateOption.objects.create(campaign=campaign, **data)
    _event(
        campaign,
        "campaign.date_option.created",
        actor_id=user.id,
        option_id=option.id,
    )
    return option


@transaction.atomic
def update_date_option(
    campaign_id,
    option_id: int,
    user,
    data: dict,
) -> CampaignDateOption:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    _ensure_option_management(campaign, user)
    option = CampaignDateOption.objects.select_for_update().get(
        pk=option_id,
        campaign=campaign,
    )
    for field, value in data.items():
        setattr(option, field, value)
    option.full_clean()
    option.save()
    _event(
        campaign,
        "campaign.date_option.updated",
        actor_id=user.id,
        option_id=option.id,
    )
    return option


@transaction.atomic
def deactivate_date_option(campaign_id, option_id: int, user) -> None:
    update_date_option(campaign_id, option_id, user, {"active": False})


@transaction.atomic
def create_price_option(campaign_id, user, data: dict) -> CampaignPriceOption:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    _ensure_option_management(campaign, user)
    option = CampaignPriceOption.objects.create(campaign=campaign, **data)
    _event(
        campaign,
        "campaign.price_option.created",
        actor_id=user.id,
        option_id=option.id,
    )
    return option


@transaction.atomic
def update_price_option(
    campaign_id,
    option_id: int,
    user,
    data: dict,
) -> CampaignPriceOption:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    _ensure_option_management(campaign, user)
    option = CampaignPriceOption.objects.select_for_update().get(
        pk=option_id,
        campaign=campaign,
    )
    for field, value in data.items():
        setattr(option, field, value)
    option.full_clean()
    option.save()
    _event(
        campaign,
        "campaign.price_option.updated",
        actor_id=user.id,
        option_id=option.id,
    )
    return option


@transaction.atomic
def deactivate_price_option(campaign_id, option_id: int, user) -> None:
    update_price_option(campaign_id, option_id, user, {"active": False})


@transaction.atomic
def upsert_supporter_preference(
    campaign_id,
    user,
    data: dict,
) -> tuple[SupporterPreference, bool]:
    """Create or update the current user's single preference record."""

    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.status not in VOTING_STATUSES:
        raise CampaignPreferenceError(
            "This campaign is not accepting attendance preferences."
        )

    preference = (
        SupporterPreference.objects.select_for_update()
        .filter(campaign=campaign, user=user)
        .first()
    )
    created = preference is None
    if created:
        preference = SupporterPreference(
            campaign=campaign,
            user=user,
        )

    for field, value in data.items():
        setattr(preference, field, value)
    preference.full_clean()
    preference.save()

    _event(
        campaign,
        "supporter_preference.created"
        if created
        else "supporter_preference.updated",
        preference_id=preference.id,
        expected_quantity=preference.expected_quantity,
        attendance_mode=preference.attendance_mode,
        selected_date_option_id=preference.selected_date_option_id,
        selected_price_option_id=preference.selected_price_option_id,
    )
    return preference, created


def build_preference_summary(campaign: DemandCampaign) -> dict:
    """Return aggregate demand without supporter identity or private notes."""

    preferences = list(
        campaign.supporter_preferences.select_related(
            "selected_date_option",
            "selected_price_option",
        ).all()
    )
    date_options = list(campaign.date_options.filter(active=True))
    price_options = list(campaign.price_options.filter(active=True))

    date_results = {
        option.id: {
            "option_id": option.id,
            "label": option.label,
            "start_datetime": option.start_datetime,
            "end_datetime": option.end_datetime,
            "venue_timezone": option.venue_timezone,
            "supporter_count": 0,
            "expected_attendance": 0,
            "physical_expected_attendance": 0,
            "virtual_expected_attendance": 0,
        }
        for option in date_options
    }
    price_results = {
        option.id: {
            "option_id": option.id,
            "label": option.label,
            "amount": str(option.amount),
            "currency": option.currency,
            "supporter_count": 0,
            "expected_attendance": 0,
            "projected_revenue": Decimal("0.00"),
        }
        for option in price_options
    }

    physical = 0
    virtual = 0
    projected_revenue = Decimal("0.00")

    for preference in preferences:
        quantity = preference.expected_quantity
        revenue = (
            Decimal(quantity)
            * preference.selected_price_option.amount
        )
        projected_revenue += revenue

        if preference.attendance_mode == AttendanceMode.PHYSICAL:
            physical += quantity
        else:
            virtual += quantity

        date_result = date_results.get(preference.selected_date_option_id)
        if date_result is not None:
            date_result["supporter_count"] += 1
            date_result["expected_attendance"] += quantity
            if preference.attendance_mode == AttendanceMode.PHYSICAL:
                date_result["physical_expected_attendance"] += quantity
            else:
                date_result["virtual_expected_attendance"] += quantity

        price_result = price_results.get(preference.selected_price_option_id)
        if price_result is not None:
            price_result["supporter_count"] += 1
            price_result["expected_attendance"] += quantity
            price_result["projected_revenue"] += revenue

    deposits = campaign.pledges.filter(
        status__in=Pledge.active_statuses()
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    sponsors = campaign.sponsorships.filter(
        status__in=SponsorCommitment.active_statuses()
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    for result in price_results.values():
        result["projected_revenue"] = str(
            result["projected_revenue"].quantize(Decimal("0.01"))
        )

    return {
        "supporter_count": len(preferences),
        "expected_attendance": physical + virtual,
        "physical_expected_attendance": physical,
        "virtual_expected_attendance": virtual,
        "projected_ticket_revenue": str(
            projected_revenue.quantize(Decimal("0.01"))
        ),
        "deposits_collected": str(deposits.quantize(Decimal("0.01"))),
        "sponsor_commitments": str(sponsors.quantize(Decimal("0.01"))),
        "total_conditional_funding": str(
            (deposits + sponsors).quantize(Decimal("0.01"))
        ),
        "date_results": list(date_results.values()),
        "price_results": list(price_results.values()),
    }


def current_user_preference(campaign: DemandCampaign, user):
    if not getattr(user, "is_authenticated", False):
        return None
    return (
        campaign.supporter_preferences.filter(user=user)
        .select_related("selected_date_option", "selected_price_option")
        .first()
    )
