# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Implements transactional campaign lifecycle rules, threshold evaluation, confirmations, payment finalization, expiration, and refunds.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Implements transactional campaign lifecycle rules, threshold evaluation, confirmations, payment finalization, expiration, and refunds.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

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
    """
    Signal that a requested campaign transition violates the lifecycle state machine.
    """
    pass


def log_event(campaign: DemandCampaign, event_type: str, **payload) -> None:
    """
    Append an immutable campaign audit event with structured context for troubleshooting and integrations.
    
    Args:
        campaign: Campaign instance being read, audited, or updated.
        event_type: Stable event name written to the campaign audit trail.
        **payload: Additional keyword arguments forwarded to the underlying implementation.
    """
    CampaignEvent.objects.create(campaign=campaign, event_type=event_type, payload=payload)


def _send_meta_event_safely(**kwargs) -> None:
    """Send optional Meta attribution after commit without allowing advertising failures to break core business transactions."""
    # Contain optional Meta attribution failures so the already-committed campaign transaction remains successful.
    try:
        send_conversion_event(**kwargs)
    except MetaAPIError:
        pass


@transaction.atomic
def launch_campaign(campaign_id) -> DemandCampaign:
    """
    Move a valid draft campaign into supporter collection while holding a database row lock.
    
    Args:
        campaign_id: Database identifier of the campaign to lock and load.
    
    Returns:
        The campaign after it has been persisted in COLLECTING state.
    
    Raises:
        CampaignStateError: When the documented validation or integration precondition fails.
    """
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    # Enforce the state machine: only a draft campaign may enter supporter collection.
    if campaign.status != CampaignStatus.DRAFT:
        raise CampaignStateError("Only a draft campaign can be launched.")
    # Reject an expired campaign before accepting a launch, pledge, or sponsorship.
    if campaign.deadline <= timezone.now():
        raise CampaignStateError("Campaign deadline must be in the future.")
    campaign.full_clean()
    campaign.status = CampaignStatus.COLLECTING
    campaign.save(update_fields=["status", "updated_at"])
    log_event(campaign, "campaign.launched")
    return campaign


@transaction.atomic
def create_pledge(campaign_id, data: dict) -> tuple[Pledge, str]:
    """
    Create or resume an idempotent supporter pledge, collect an optional deposit, and re-evaluate the threshold.
    
    Args:
        campaign_id: Database identifier of the campaign to lock and load.
        data: Validated input payload supplied by the serializer or caller.
    
    Returns:
        The persisted pledge and the payment client secret, or an empty secret when no browser payment step is required.
    
    Raises:
        CampaignStateError: When the documented validation or integration precondition fails.
    """
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    # Accept new support only in lifecycle states that are still gathering or confirming demand.
    if campaign.status not in [CampaignStatus.COLLECTING, CampaignStatus.TARGET_REACHED]:
        raise CampaignStateError("This campaign is not accepting support.")
    # Reject an expired campaign before accepting a launch, pledge, or sponsorship.
    if campaign.deadline <= timezone.now():
        raise CampaignStateError("The campaign deadline has passed.")

    existing = Pledge.objects.filter(
        campaign=campaign,
        idempotency_key=data["idempotency_key"],
    ).first()
    # Treat the matching idempotency key as a retry and reuse the original record instead of creating a duplicate charge.
    if existing:
        client_secret = ""
        # Resume the original pending Stripe payment so a retried browser request receives the same client secret.
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

    # Contact the payment provider only for monetary support; zero-dollar attendance commitments need no payment intent.
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
    """
    Record a sponsor commitment, audit it, and re-evaluate whether the campaign target is reached.
    
    Args:
        campaign_id: Database identifier of the campaign to lock and load.
        data: Validated input payload supplied by the serializer or caller.
    
    Returns:
        The persisted sponsor commitment after threshold re-evaluation.
    
    Raises:
        CampaignStateError: When the documented validation or integration precondition fails.
    """
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    # Accept new support only in lifecycle states that are still gathering or confirming demand.
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
    """Advance a locked collecting campaign to TARGET_REACHED when its configured threshold is satisfied."""
    # Advance the lifecycle once the configured supporter-count or funding threshold has actually been met.
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
    """
    Record artist confirmation after demand reaches the threshold and advance the confirmation state.
    
    Args:
        campaign_id: Database identifier of the campaign to lock and load.
        details: Structured diagnostic or provider details attached to the result.
    
    Returns:
        The campaign after artist confirmation and any resulting state transition.
    
    Raises:
        CampaignStateError: When the documented validation or integration precondition fails.
    """
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    # Reject an invalid lifecycle transition before any payment, confirmation, or persistence side effect occurs.
    if campaign.status not in [CampaignStatus.TARGET_REACHED, CampaignStatus.CONFIRMING]:
        raise CampaignStateError("Artist confirmation starts only after the target is reached.")
    campaign.artist_confirmed = True
    campaign.confirmed_artist_details = details
    campaign.status = CampaignStatus.CONFIRMING
    # Move directly to CONFIRMED when the venue was already approved; otherwise wait for the remaining confirmation.
    if campaign.venue_confirmed:
        campaign.status = CampaignStatus.CONFIRMED
    campaign.save(update_fields=["artist_confirmed", "confirmed_artist_details", "status", "updated_at"])
    log_event(campaign, "artist.confirmed")
    return campaign


@transaction.atomic
def confirm_venue(campaign_id, details: str) -> DemandCampaign:
    """
    Record venue confirmation after demand reaches the threshold and advance the confirmation state.
    
    Args:
        campaign_id: Database identifier of the campaign to lock and load.
        details: Structured diagnostic or provider details attached to the result.
    
    Returns:
        The campaign after venue confirmation and any resulting state transition.
    
    Raises:
        CampaignStateError: When the documented validation or integration precondition fails.
    """
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    # Reject an invalid lifecycle transition before any payment, confirmation, or persistence side effect occurs.
    if campaign.status not in [CampaignStatus.TARGET_REACHED, CampaignStatus.CONFIRMING]:
        raise CampaignStateError("Venue confirmation starts only after the target is reached.")
    campaign.venue_confirmed = True
    campaign.confirmed_venue_details = details
    campaign.status = CampaignStatus.CONFIRMING
    # Move directly to CONFIRMED when the artist was already approved; otherwise wait for the remaining confirmation.
    if campaign.artist_confirmed:
        campaign.status = CampaignStatus.CONFIRMED
    campaign.save(update_fields=["venue_confirmed", "confirmed_venue_details", "status", "updated_at"])
    log_event(campaign, "venue.confirmed")
    return campaign


@transaction.atomic
def finalize_campaign(campaign_id, event_id: str) -> DemandCampaign:
    """
    Finalize all eligible payments and mark a fully confirmed campaign ready for production.
    
    Args:
        campaign_id: Database identifier of the campaign to lock and load.
        event_id: Provider event identifier used for deduplication and audit correlation.
    
    Returns:
        The campaign after eligible payments are finalized and the event is marked live.
    
    Raises:
        CampaignStateError: When the documented validation or integration precondition fails.
    """
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    # Reject an invalid lifecycle transition before any payment, confirmation, or persistence side effect occurs.
    if campaign.status != CampaignStatus.CONFIRMED:
        raise CampaignStateError("Artist and venue must both be confirmed first.")

    provider = get_payment_provider()
    # Process each `pledge` from
    # `campaign.pledges.select_for_update().filter(status=PledgeStatus.PAID)` in a deterministic
    # order.
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
    """
    Move an unsuccessful campaign through refunding, reverse eligible payments, and record any failures.
    
    Args:
        campaign_id: Database identifier of the campaign to lock and load.
        reason: Human-readable explanation recorded for a failure, refund, or quarantine decision.
    
    Returns:
        The campaign after refund attempts and final failure-state persistence.
    
    Raises:
        CampaignStateError: When the documented validation or integration precondition fails.
    """
    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    # Reject an invalid lifecycle transition before any payment, confirmation, or persistence side effect occurs.
    if campaign.status in [CampaignStatus.LIVE, CampaignStatus.COMPLETED, CampaignStatus.REFUNDED]:
        raise CampaignStateError("This campaign can no longer be refunded through the failure flow.")

    campaign.status = CampaignStatus.REFUNDING
    campaign.save(update_fields=["status", "updated_at"])
    provider = get_payment_provider()

    campaign.pledges.select_for_update().filter(
        status__in=[PledgeStatus.PENDING, PledgeStatus.COMMITTED]
    ).update(status=PledgeStatus.CANCELED, updated_at=timezone.now())

    refundable = campaign.pledges.select_for_update().filter(status=PledgeStatus.PAID).exclude(payment_reference="")
    # Process each `pledge` from `refundable` in a deterministic order.
    for pledge in refundable:
        pledge.status = PledgeStatus.REFUND_PENDING
        pledge.save(update_fields=["status", "updated_at"])
        # Attempt each refund independently; record provider failures without skipping the remaining supporters or sponsors.
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
    # Process each `sponsorship` from `paid_sponsors` in a deterministic order.
    for sponsorship in paid_sponsors:
        # Cancel a paid-looking sponsor record that lacks the provider reference required to issue a real refund.
        if not sponsorship.payment_reference:
            sponsorship.status = SponsorStatus.CANCELED
            sponsorship.save(update_fields=["status", "updated_at"])
            continue
        sponsorship.status = SponsorStatus.REFUND_PENDING
        sponsorship.save(update_fields=["status", "updated_at"])
        # Attempt each refund independently; record provider failures without skipping the remaining supporters or sponsors.
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
    """
    Find collecting campaigns past their deadline and fail/refund only those that missed the target.
    
    Returns:
        The number of overdue campaigns that were failed and processed for refunds.
    """
    ids = DemandCampaign.objects.filter(
        deadline__lte=timezone.now(),
        status__in=[CampaignStatus.COLLECTING, CampaignStatus.TARGET_REACHED, CampaignStatus.CONFIRMING],
    ).values_list("id", flat=True)
    count = 0
    # Process each `campaign_id` from `list(ids)` in a deterministic order.
    for campaign_id in list(ids):
        campaign = DemandCampaign.objects.get(pk=campaign_id)
        # Block confirmation until verified supporter or sponsor demand reaches the campaign threshold.
        if campaign.status == CampaignStatus.COLLECTING and not campaign.target_reached:
            fail_and_refund_campaign(campaign_id)
            count += 1
    return count
