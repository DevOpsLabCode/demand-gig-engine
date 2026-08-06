# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Stores immutable automated and administrator campaign-review decisions.

"""Campaign review records for deterministic automatic approval and manual fallback."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .models import DemandCampaign


class CampaignReviewDecision(models.TextChoices):
    """Stable decisions produced by the automatic and administrator review paths."""

    AUTO_APPROVED = "auto_approved", "Automatically approved"
    MANUAL_REVIEW_REQUIRED = "manual_review_required", "Manual review required"
    MANUAL_APPROVED = "manual_approved", "Manually approved"
    REJECTED = "rejected", "Rejected"


class CampaignReview(models.Model):
    """Append-only evidence for each campaign submission or administrator decision."""

    campaign = models.ForeignKey(
        DemandCampaign,
        related_name="reviews",
        on_delete=models.CASCADE,
    )
    decision = models.CharField(max_length=32, choices=CampaignReviewDecision.choices)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="campaign_reviews_completed",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    checks = models.JSONField(default=list, blank=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)
    previous_status = models.CharField(max_length=24)
    resulting_status = models.CharField(max_length=24)

    class Meta:
        ordering = ["reviewed_at", "id"]
        indexes = [
            models.Index(
                fields=["campaign", "reviewed_at"],
                name="gig_review_campaign_time_idx",
            ),
            models.Index(
                fields=["decision", "reviewed_at"],
                name="gig_review_decision_time_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        """Keep review evidence immutable after its first successful insert."""

        if self.pk and CampaignReview.objects.filter(pk=self.pk).exists():
            raise ValidationError("Campaign review records are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent removal of an audit decision through application code."""

        raise ValidationError("Campaign review records are immutable.")

    def __str__(self):
        return f"{self.campaign.slug}: {self.decision}"
