from __future__ import annotations

from decimal import Decimal
from functools import partial
from django.db import transaction
from django.utils import timezone

from .models import (
    CampaignEvent,
    CampaignStatus,
    DemandCampaign,
    Pledge,
    PledgeStatus,
    SponsorCommitment,
    SponsorStatus,
)
from .facebook import MetaAPIError, build_campaign_share_link, send_conversion_event
from .payments import get_payment_provider


class CampaignStateError(ValueError):
    pass


def log_event(campaign: DemandCampaign, event_type: str, **payload) -> None:
    CampaignEvent.objects.create(campaign=campaign, event_type=event_type, payload=payload)


def _send_meta_event_safely(**kwargs) -> None:
    """Advertising attribution must never break the core campaign flow."""
    try:
        send_conversion_event(**kwargs)
    except MetaAPIError:
        pass


@transaction.atomic
def launch_campaign(campaign_id) -> DemandCampaign:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.status != CampaignStatus.DRAFT:
        raise CampaignStateError("Only a draft campaign can be launched.")
    if campaign.deadline <= timezone.now():
        raise CampaignStateError("Campaign deadline must be in the future.")
    campaign.full_clean()
    campaign.status = CampaignStatus.COLLECTING
    campaign.save(update_fields=["status", "updated_at"])
    log_event(campaign, "campaign.launched")
    return campaign


@transaction.atomic
def create_pledge(campaign_id, data: dict) -> tuple[Pledge, str]:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.status not in [CampaignStatus.COLLECTING, CampaignStatus.TARGET_REACHED]:
        raise CampaignStateError("This campaign is not accepting support.")
    if campaign.deadline <= timezone.now():
        raise CampaignStateError("The campaign deadline has passed.")

    existing = Pledge.objects.filter(
        campaign=campaign,
        idempotency_key=data["idempotency_key"],
    ).first()
    if existing:
        client_secret = ""
        if existing.payment_provider == "stripe" and existing.payment_reference and existing.status == PledgeStatus.PENDING:
            client_secret = get_payment_provider().get_client_secret(
                payment_reference=existing.payment_reference,
            )
        return existing, client_secret

    amount = Decimal(str(data.get("amount", 0)))
    provider_name = "none"
    payment_reference = ""
    client_secret = ""
    status = PledgeStatus.COMMITTED

    if amount > 0:
        provider = get_payment_provider()
        result = provider.collect_refundable_deposit(
            amount=amount,
            currency=campaign.currency,
            email=data["supporter_email"],
            idempotency_key=data["idempotency_key"],
            metadata={"campaign_id": str(campaign.id), "campaign_slug": campaign.slug},
        )
        provider_name = provider.name
        payment_reference = result.reference
        client_secret = result.client_secret
        status = PledgeStatus.PAID if result.status in ["paid", "succeeded"] else PledgeStatus.PENDING

    pledge = Pledge.objects.create(
        campaign=campaign,
        supporter_user=data.get("supporter_user"),
        supporter_name=data["supporter_name"],
        supporter_email=data["supporter_email"],
        quantity=data.get("quantity", 1),
        amount=amount,
        currency=campaign.currency,
        status=status,
        payment_provider=provider_name,
        payment_reference=payment_reference,
        idempotency_key=data["idempotency_key"],
        referral_code=data.get("referral_code", ""),
        source=data.get("source", ""),
        source_label=data.get("source_label", ""),
    )
    log_event(
        campaign,
        "pledge.created",
        pledge_id=str(pledge.id),
        amount=str(amount),
        quantity=pledge.quantity,
        source=pledge.source,
        source_label=pledge.source_label,
    )
    evaluate_threshold_locked(campaign)

    share = build_campaign_share_link(
        campaign.slug,
        source=pledge.source or "direct",
        group_name=pledge.source_label,
        referral_code=pledge.referral_code,
    )
    meta_event_name = "InitiateCheckout" if amount > 0 else "Lead"
    transaction.on_commit(
        partial(
            _send_meta_event_safely,
            event_name=meta_event_name,
            event_id=f"pledge:{pledge.id}:created",
            event_source_url=share.campaign_url,
            email=pledge.supporter_email,
            value=amount if amount > 0 else None,
            currency=campaign.currency,
            custom_data={
                "content_name": campaign.title,
                "content_category": "demand_driven_gig",
                "campaign_slug": campaign.slug,
                "source": pledge.source,
                "source_label": pledge.source_label,
                "quantity": pledge.quantity,
            },
        )
    )
    return pledge, client_secret


@transaction.atomic
def create_sponsorship(campaign_id, data: dict) -> SponsorCommitment:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.status not in [CampaignStatus.COLLECTING, CampaignStatus.TARGET_REACHED, CampaignStatus.CONFIRMING]:
        raise CampaignStateError("This campaign is not accepting sponsor commitments.")
    sponsorship = SponsorCommitment.objects.create(campaign=campaign, currency=campaign.currency, **data)
    log_event(campaign, "sponsor.pledged", sponsorship_id=str(sponsorship.id), amount=str(sponsorship.amount))
    evaluate_threshold_locked(campaign)
    share = build_campaign_share_link(campaign.slug, source="facebook_sponsor")
    transaction.on_commit(
        partial(
            _send_meta_event_safely,
            event_name="Lead",
            event_id=f"sponsor:{sponsorship.id}:pledged",
            event_source_url=share.campaign_url,
            email=sponsorship.contact_email,
            value=sponsorship.amount,
            currency=campaign.currency,
            custom_data={
                "content_name": campaign.title,
                "content_category": "sponsor_commitment",
                "campaign_slug": campaign.slug,
            },
        )
    )
    return sponsorship


def evaluate_threshold_locked(campaign: DemandCampaign) -> DemandCampaign:
    """Caller must hold a SELECT FOR UPDATE lock on the campaign."""
    if campaign.target_reached and campaign.status == CampaignStatus.COLLECTING:
        campaign.status = CampaignStatus.TARGET_REACHED
        campaign.save(update_fields=["status", "updated_at"])
        log_event(
            campaign,
            "campaign.target_reached",
            supporters=campaign.active_supporter_count,
            amount=str(campaign.committed_amount),
        )
    return campaign


@transaction.atomic
def confirm_artist(campaign_id, details: str) -> DemandCampaign:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.status not in [CampaignStatus.TARGET_REACHED, CampaignStatus.CONFIRMING]:
        raise CampaignStateError("Artist confirmation starts only after the target is reached.")
    campaign.artist_confirmed = True
    campaign.confirmed_artist_details = details
    campaign.status = CampaignStatus.CONFIRMING
    if campaign.venue_confirmed:
        campaign.status = CampaignStatus.CONFIRMED
    campaign.save(update_fields=["artist_confirmed", "confirmed_artist_details", "status", "updated_at"])
    log_event(campaign, "artist.confirmed")
    return campaign


@transaction.atomic
def confirm_venue(campaign_id, details: str) -> DemandCampaign:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.status not in [CampaignStatus.TARGET_REACHED, CampaignStatus.CONFIRMING]:
        raise CampaignStateError("Venue confirmation starts only after the target is reached.")
    campaign.venue_confirmed = True
    campaign.confirmed_venue_details = details
    campaign.status = CampaignStatus.CONFIRMING
    if campaign.artist_confirmed:
        campaign.status = CampaignStatus.CONFIRMED
    campaign.save(update_fields=["venue_confirmed", "confirmed_venue_details", "status", "updated_at"])
    log_event(campaign, "venue.confirmed")
    return campaign


@transaction.atomic
def finalize_campaign(campaign_id, event_id: str) -> DemandCampaign:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.status != CampaignStatus.CONFIRMED:
        raise CampaignStateError("Artist and venue must both be confirmed first.")

    provider = get_payment_provider()
    for pledge in campaign.pledges.select_for_update().filter(status=PledgeStatus.PAID):
        provider.finalize(payment_reference=pledge.payment_reference)
        pledge.status = PledgeStatus.CAPTURED
        pledge.save(update_fields=["status", "updated_at"])
        share = build_campaign_share_link(
            campaign.slug,
            source=pledge.source or "direct",
            group_name=pledge.source_label,
            referral_code=pledge.referral_code,
        )
        transaction.on_commit(
            partial(
                _send_meta_event_safely,
                event_name="Purchase",
                event_id=f"pledge:{pledge.id}:captured",
                event_source_url=share.campaign_url,
                email=pledge.supporter_email,
                value=pledge.amount,
                currency=campaign.currency,
                custom_data={
                    "content_name": campaign.title,
                    "content_category": "confirmed_gig",
                    "campaign_slug": campaign.slug,
                    "event_id": event_id,
                    "quantity": pledge.quantity,
                },
            )
        )

    campaign.sponsorships.select_for_update().filter(
        status__in=[SponsorStatus.PLEDGED, SponsorStatus.PAID]
    ).update(status=SponsorStatus.FINALIZED, updated_at=timezone.now())

    campaign.event_id = event_id
    campaign.status = CampaignStatus.LIVE
    campaign.save(update_fields=["event_id", "status", "updated_at"])
    log_event(campaign, "campaign.finalized", event_id=event_id)
    return campaign


@transaction.atomic
def fail_and_refund_campaign(campaign_id, reason: str = "Target not reached") -> DemandCampaign:
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.status in [CampaignStatus.LIVE, CampaignStatus.COMPLETED, CampaignStatus.REFUNDED]:
        raise CampaignStateError("This campaign can no longer be refunded through the failure flow.")

    campaign.status = CampaignStatus.REFUNDING
    campaign.save(update_fields=["status", "updated_at"])
    provider = get_payment_provider()

    campaign.pledges.select_for_update().filter(
        status__in=[PledgeStatus.PENDING, PledgeStatus.COMMITTED]
    ).update(status=PledgeStatus.CANCELED, updated_at=timezone.now())

    refundable = campaign.pledges.select_for_update().filter(status=PledgeStatus.PAID).exclude(payment_reference="")
    for pledge in refundable:
        pledge.status = PledgeStatus.REFUND_PENDING
        pledge.save(update_fields=["status", "updated_at"])
        try:
            refund_reference = provider.refund(payment_reference=pledge.payment_reference)
            pledge.status = PledgeStatus.REFUNDED
            pledge.save(update_fields=["status", "updated_at"])
            log_event(campaign, "pledge.refunded", pledge_id=str(pledge.id), refund_reference=refund_reference)
        except Exception as exc:
            log_event(campaign, "pledge.refund_failed", pledge_id=str(pledge.id), error=str(exc))

    campaign.sponsorships.select_for_update().filter(status=SponsorStatus.PLEDGED).update(
        status=SponsorStatus.CANCELED,
        updated_at=timezone.now(),
    )
    paid_sponsors = campaign.sponsorships.select_for_update().filter(
        status__in=[SponsorStatus.PAID, SponsorStatus.FINALIZED]
    )
    for sponsorship in paid_sponsors:
        if not sponsorship.payment_reference:
            sponsorship.status = SponsorStatus.CANCELED
            sponsorship.save(update_fields=["status", "updated_at"])
            continue
        sponsorship.status = SponsorStatus.REFUND_PENDING
        sponsorship.save(update_fields=["status", "updated_at"])
        try:
            refund_reference = provider.refund(payment_reference=sponsorship.payment_reference)
            sponsorship.status = SponsorStatus.REFUNDED
            sponsorship.save(update_fields=["status", "updated_at"])
            log_event(
                campaign,
                "sponsor.refunded",
                sponsorship_id=str(sponsorship.id),
                refund_reference=refund_reference,
            )
        except Exception as exc:
            log_event(
                campaign,
                "sponsor.refund_failed",
                sponsorship_id=str(sponsorship.id),
                error=str(exc),
            )

    remaining = (
        campaign.pledges.filter(status=PledgeStatus.REFUND_PENDING).exists()
        or campaign.sponsorships.filter(status=SponsorStatus.REFUND_PENDING).exists()
    )
    campaign.status = CampaignStatus.REFUNDING if remaining else CampaignStatus.REFUNDED
    campaign.save(update_fields=["status", "updated_at"])
    log_event(campaign, "campaign.failed", reason=reason)
    return campaign


def expire_due_campaigns() -> int:
    ids = DemandCampaign.objects.filter(
        deadline__lte=timezone.now(),
        status__in=[CampaignStatus.COLLECTING, CampaignStatus.TARGET_REACHED, CampaignStatus.CONFIRMING],
    ).values_list("id", flat=True)
    count = 0
    for campaign_id in list(ids):
        campaign = DemandCampaign.objects.get(pk=campaign_id)
        if campaign.status == CampaignStatus.COLLECTING and not campaign.target_reached:
            fail_and_refund_campaign(campaign_id)
            count += 1
    return count
