# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Stores campaign date choices, ticket-price choices, and one mutable supporter preference per campaign.

"""Phase 2 campaign option and supporter-preference models."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AttendanceMode(models.TextChoices):
    """Stable physical and virtual attendance values."""

    PHYSICAL = "physical", "Physical attendance"
    VIRTUAL = "virtual", "Virtual attendance"


class CampaignDateOption(models.Model):
    """One organizer-proposed date that supporters may select."""

    campaign = models.ForeignKey(
        "gigs.DemandCampaign",
        related_name="date_options",
        on_delete=models.CASCADE,
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    venue_timezone = models.CharField(max_length=64, default="America/New_York")
    label = models.CharField(max_length=160, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_datetime", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(end_datetime__isnull=True)
                    | models.Q(end_datetime__gt=models.F("start_datetime"))
                ),
                name="campaign_date_end_after_start",
            ),
        ]
        indexes = [
            models.Index(
                fields=["campaign", "active", "start_datetime"],
                name="gig_date_campaign_active_idx",
            ),
        ]

    def clean(self):
        if self.end_datetime and self.end_datetime <= self.start_datetime:
            raise ValidationError(
                {"end_datetime": "End time must be later than the start time."}
            )

    def __str__(self):
        return self.label or self.start_datetime.isoformat()


class CampaignPriceOption(models.Model):
    """One acceptable ticket-price choice that supporters may select."""

    campaign = models.ForeignKey(
        "gigs.DemandCampaign",
        related_name="price_options",
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    label = models.CharField(max_length=160, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["amount", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="campaign_price_amount_gte_0",
            ),
        ]
        indexes = [
            models.Index(
                fields=["campaign", "active", "amount"],
                name="gig_price_campaign_active_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        self.currency = self.currency.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label or f"{self.currency} {self.amount}"


class SupporterPreference(models.Model):
    """The current date, price, quantity, and attendance preference for one user."""

    campaign = models.ForeignKey(
        "gigs.DemandCampaign",
        related_name="supporter_preferences",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="campaign_preferences",
        on_delete=models.CASCADE,
    )
    expected_quantity = models.PositiveIntegerField(default=1)
    attendance_mode = models.CharField(
        max_length=16,
        choices=AttendanceMode.choices,
        default=AttendanceMode.PHYSICAL,
    )
    selected_date_option = models.ForeignKey(
        CampaignDateOption,
        related_name="preferences",
        on_delete=models.PROTECT,
    )
    selected_price_option = models.ForeignKey(
        CampaignPriceOption,
        related_name="preferences",
        on_delete=models.PROTECT,
    )
    preferred_neighborhood = models.CharField(max_length=160, blank=True)
    accessibility_notes = models.TextField(blank=True)
    referral_source = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["campaign_id", "user_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "user"],
                name="supporter_preference_campaign_user_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(expected_quantity__gte=1),
                name="supporter_preference_quantity_gte_1",
            ),
        ]
        indexes = [
            models.Index(
                fields=["campaign", "attendance_mode"],
                name="gig_pref_campaign_mode_idx",
            ),
        ]

    def clean(self):
        errors = {}
        if (
            self.selected_date_option_id
            and self.selected_date_option.campaign_id != self.campaign_id
        ):
            errors["selected_date_option"] = (
                "The selected date does not belong to this campaign."
            )
        if (
            self.selected_price_option_id
            and self.selected_price_option.campaign_id != self.campaign_id
        ):
            errors["selected_price_option"] = (
                "The selected price does not belong to this campaign."
            )
        if self.selected_date_option_id and not self.selected_date_option.active:
            errors["selected_date_option"] = "The selected date is not active."
        if self.selected_price_option_id and not self.selected_price_option.active:
            errors["selected_price_option"] = "The selected price is not active."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.campaign.slug}: preference {self.pk}"
