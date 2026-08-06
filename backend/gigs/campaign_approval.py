# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Runs deterministic campaign checks, routes failures to administrators, and enforces approved launch.

"""Transactional campaign approval and launch services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .campaign_review_models import CampaignReview, CampaignReviewDecision
from .models import CampaignEvent, DemandCampaign
from .role_models import RoleCode, RoleVerificationStatus, UserRole


DRAFT = "draft"
PENDING_REVIEW = "pending_review"
APPROVED = "approved"
COLLECTING = "collecting"
REJECTED = "rejected"


class CampaignApprovalError(ValueError):
    """Raised when a campaign approval transition is not permitted."""


@dataclass(frozen=True)
class AutomaticCheck:
    """One deterministic auto-review condition and its human-readable result."""

    key: str
    passed: bool
    message: str

    def as_dict(self) -> dict:
        return {"key": self.key, "passed": self.passed, "message": self.message}


def can_review_campaigns(user) -> bool:
    """Return whether a user may make administrator campaign decisions."""

    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff:
        return True
    return UserRole.objects.filter(
        user=user,
        role__code=RoleCode.ADMINISTRATOR,
        verification_status=RoleVerificationStatus.VERIFIED,
    ).exists()


def _owner_has_verified_organizer_role(campaign: DemandCampaign) -> bool:
    """Require a verified organizer or administrator role for automatic approval."""

    if not campaign.owner_id:
        return False
    if campaign.owner.is_staff:
        return True
    return UserRole.objects.filter(
        user_id=campaign.owner_id,
        role__code__in=[RoleCode.ORGANIZER, RoleCode.ADMINISTRATOR],
        verification_status=RoleVerificationStatus.VERIFIED,
    ).exists()


def run_automatic_campaign_checks(campaign: DemandCampaign) -> list[AutomaticCheck]:
    """Evaluate transparent, deterministic checks without AI or owner overrides."""

    try:
        campaign.clean()
        model_valid = True
        model_message = "Campaign targets and monetary values are valid."
    except ValidationError as exc:
        model_valid = False
        model_message = "; ".join(exc.messages)

    required_values = (
        campaign.title,
        campaign.pitch,
        campaign.artist_name,
        campaign.city,
        campaign.organizer_name,
        campaign.organizer_email,
    )
    verified_organizer = _owner_has_verified_organizer_role(campaign)
    no_early_support = not campaign.pledges.exists() and not campaign.sponsorships.exists()
    return [
        AutomaticCheck(
            "owner_present",
            bool(campaign.owner_id),
            "Campaign has an authenticated owner."
            if campaign.owner_id
            else "An authenticated campaign owner is required.",
        ),
        AutomaticCheck(
            "verified_organizer",
            verified_organizer,
            "Owner has a verified organizer or administrator role."
            if verified_organizer
            else "Owner needs a verified organizer role or administrator review.",
        ),
        AutomaticCheck(
            "required_content",
            all(bool(value) for value in required_values),
            "Required campaign and organizer fields are complete."
            if all(bool(value) for value in required_values)
            else "Required campaign or organizer information is missing.",
        ),
        AutomaticCheck(
            "future_deadline",
            campaign.deadline > timezone.now(),
            "Campaign deadline is in the future."
            if campaign.deadline > timezone.now()
            else "Campaign deadline must be in the future.",
        ),
        AutomaticCheck("model_validation", model_valid, model_message),
        AutomaticCheck(
            "no_support_before_approval",
            no_early_support,
            "No supporter or sponsor money was accepted before approval."
            if no_early_support
            else "Support or sponsorship already exists and requires administrator review.",
        ),
    ]


def _record_review(
    *,
    campaign: DemandCampaign,
    decision: str,
    previous_status: str,
    resulting_status: str,
    checks: Iterable[AutomaticCheck] = (),
    reviewer=None,
    notes: str = "",
) -> CampaignReview:
    """Create one immutable review and matching campaign audit event."""

    serialized_checks = [
        check.as_dict() if isinstance(check, AutomaticCheck) else dict(check)
        for check in checks
    ]
    review = CampaignReview.objects.create(
        campaign=campaign,
        decision=decision,
        reviewer=reviewer,
        notes=notes.strip(),
        checks=serialized_checks,
        previous_status=previous_status,
        resulting_status=resulting_status,
    )
    CampaignEvent.objects.create(
        campaign=campaign,
        event_type=f"campaign.review.{decision}",
        payload={
            "review_id": review.id,
            "reviewer_id": getattr(reviewer, "id", None),
            "previous_status": previous_status,
            "resulting_status": resulting_status,
            "notes": review.notes,
            "checks": serialized_checks,
        },
    )
    return review


@transaction.atomic
def submit_campaign_for_review(campaign_id, actor) -> tuple[DemandCampaign, CampaignReview]:
    """Auto-approve a passing submission or route failed checks to manual review."""

    campaign = (
        DemandCampaign.objects.select_for_update()
        .select_related("owner")
        .get(pk=campaign_id)
    )
    if campaign.owner_id != getattr(actor, "id", None):
        raise CampaignApprovalError("Only the campaign owner may submit it for review.")
    if campaign.status not in [DRAFT, REJECTED]:
        raise CampaignApprovalError("Only a draft or rejected campaign can be submitted.")

    previous_status = campaign.status
    checks = run_automatic_campaign_checks(campaign)
    failed = [check for check in checks if not check.passed]

    if failed:
        campaign.status = PENDING_REVIEW
        campaign.save(update_fields=["status", "updated_at"])
        notes = "Automatic checks requiring administrator review: " + "; ".join(
            check.message for check in failed
        )
        review = _record_review(
            campaign=campaign,
            decision=CampaignReviewDecision.MANUAL_REVIEW_REQUIRED,
            previous_status=previous_status,
            resulting_status=PENDING_REVIEW,
            checks=checks,
            notes=notes,
        )
        return campaign, review

    campaign.status = APPROVED
    campaign.save(update_fields=["status", "updated_at"])
    review = _record_review(
        campaign=campaign,
        decision=CampaignReviewDecision.AUTO_APPROVED,
        previous_status=previous_status,
        resulting_status=APPROVED,
        checks=checks,
        notes="All deterministic campaign approval checks passed.",
    )
    return campaign, review


@transaction.atomic
def approve_campaign_manually(
    campaign_id,
    reviewer,
    notes: str,
) -> tuple[DemandCampaign, CampaignReview]:
    """Allow an administrator to approve a failed auto-review with written notes."""

    if not can_review_campaigns(reviewer):
        raise CampaignApprovalError("Administrator campaign-review permission is required.")

    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.owner_id == reviewer.id:
        raise CampaignApprovalError("Campaign owners may not manually approve their own campaigns.")
    if campaign.status != PENDING_REVIEW:
        raise CampaignApprovalError("Only a campaign pending review can be approved.")

    previous_status = campaign.status
    campaign.status = APPROVED
    campaign.save(update_fields=["status", "updated_at"])
    review = _record_review(
        campaign=campaign,
        decision=CampaignReviewDecision.MANUAL_APPROVED,
        previous_status=previous_status,
        resulting_status=APPROVED,
        reviewer=reviewer,
        notes=notes or "Administrator approved after manual review.",
    )
    return campaign, review


@transaction.atomic
def reject_campaign_manually(
    campaign_id,
    reviewer,
    notes: str,
) -> tuple[DemandCampaign, CampaignReview]:
    """Return a pending campaign to its owner with mandatory rejection notes."""

    if not can_review_campaigns(reviewer):
        raise CampaignApprovalError("Administrator campaign-review permission is required.")
    if not notes or not notes.strip():
        raise CampaignApprovalError("Rejection notes are required.")

    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.owner_id == reviewer.id:
        raise CampaignApprovalError("Campaign owners may not manually reject their own campaigns.")
    if campaign.status != PENDING_REVIEW:
        raise CampaignApprovalError("Only a campaign pending review can be rejected.")

    previous_status = campaign.status
    campaign.status = REJECTED
    campaign.save(update_fields=["status", "updated_at"])
    review = _record_review(
        campaign=campaign,
        decision=CampaignReviewDecision.REJECTED,
        previous_status=previous_status,
        resulting_status=REJECTED,
        reviewer=reviewer,
        notes=notes,
    )
    return campaign, review


@transaction.atomic
def launch_approved_campaign(campaign_id, actor) -> DemandCampaign:
    """Start support collection only after automatic or administrator approval."""

    campaign = DemandCampaign.objects.select_for_update().get(pk=campaign_id)
    if not getattr(actor, "is_authenticated", False):
        raise CampaignApprovalError("Authentication is required.")
    if campaign.owner_id != actor.id and not actor.is_staff:
        raise CampaignApprovalError("Only the campaign owner or an administrator may launch it.")
    if campaign.status != APPROVED:
        raise CampaignApprovalError("Campaign approval is required before launch.")
    if campaign.deadline <= timezone.now():
        raise CampaignApprovalError("Campaign deadline must be in the future.")

    campaign.clean()
    previous_status = campaign.status
    campaign.status = COLLECTING
    campaign.save(update_fields=["status", "updated_at"])
    CampaignEvent.objects.create(
        campaign=campaign,
        event_type="campaign.launched",
        payload={
            "actor_id": actor.id,
            "previous_status": previous_status,
            "approval_review_id": campaign.reviews.order_by("-reviewed_at", "-id")
            .values_list("id", flat=True)
            .first(),
        },
    )
    return campaign
