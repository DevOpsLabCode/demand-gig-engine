from __future__ import annotations

import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class CampaignStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    COLLECTING = "collecting", "Collecting support"
    TARGET_REACHED = "target_reached", "Target reached"
    CONFIRMING = "confirming", "Confirming artist and venue"
    CONFIRMED = "confirmed", "Confirmed"
    LIVE = "live", "Live event"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Target not reached"
    REFUNDING = "refunding", "Refunding"
    REFUNDED = "refunded", "Refunded"
    CANCELED = "canceled", "Canceled"


class GoalType(models.TextChoices):
    SUPPORTERS = "supporters", "Supporters"
    MONEY = "money", "Committed amount"
    BOTH = "both", "Both supporters and amount"


class DemandCampaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=210, unique=True, blank=True)
    pitch = models.TextField()
    artist_name = models.CharField(max_length=160)
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=80, default="United States")
    proposed_date = models.DateField(null=True, blank=True)
    deadline = models.DateTimeField()

    goal_type = models.CharField(max_length=20, choices=GoalType.choices, default=GoalType.SUPPORTERS)
    supporter_target = models.PositiveIntegerField(default=500)
    amount_target = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    suggested_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("25.00"))
    currency = models.CharField(max_length=3, default="USD")

    status = models.CharField(max_length=24, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT)
    artist_confirmed = models.BooleanField(default=False)
    venue_confirmed = models.BooleanField(default=False)
    confirmed_artist_details = models.TextField(blank=True)
    confirmed_venue_details = models.TextField(blank=True)
    event_id = models.CharField(max_length=100, blank=True, help_text="ID of the confirmed event in the host platform")

    organizer_name = models.CharField(max_length=160)
    organizer_email = models.EmailField()
    facebook_event_url = models.URLField(blank=True, help_text="Existing Facebook Event used as the discovery hub")
    facebook_group_url = models.URLField(blank=True, help_text="Primary Facebook Group or fan community")
    facebook_page_url = models.URLField(blank=True, help_text="Organizer, artist, or venue Facebook Page")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "deadline"], name="gig_status_deadline_idx"),
            models.Index(fields=["artist_name", "city"], name="gig_artist_city_idx"),
        ]

    def clean(self):
        if self.goal_type in (GoalType.SUPPORTERS, GoalType.BOTH) and self.supporter_target < 1:
            raise ValidationError("Supporter target must be at least 1.")
        if self.goal_type in (GoalType.MONEY, GoalType.BOTH) and self.amount_target <= 0:
            raise ValidationError("Amount target must be greater than zero.")

    def save(self, *args, **kwargs):
        if not self.slug:
            root = slugify(f"{self.artist_name}-{self.city}")[:180] or "gig"
            candidate = root
            counter = 2
            while DemandCampaign.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{root}-{counter}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    @property
    def active_supporter_count(self) -> int:
        return self.pledges.filter(status__in=Pledge.active_statuses()).aggregate(
            total=models.Sum("quantity")
        )["total"] or 0

    @property
    def committed_amount(self) -> Decimal:
        supporter_total = self.pledges.filter(status__in=Pledge.active_statuses()).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")
        sponsor_total = self.sponsorships.filter(status__in=SponsorCommitment.active_statuses()).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")
        return supporter_total + sponsor_total

    @property
    def target_reached(self) -> bool:
        supporters_met = self.active_supporter_count >= self.supporter_target
        amount_met = self.committed_amount >= self.amount_target
        if self.goal_type == GoalType.SUPPORTERS:
            return supporters_met
        if self.goal_type == GoalType.MONEY:
            return amount_met
        return supporters_met and amount_met

    @property
    def progress_percent(self) -> int:
        supporter_pct = 100 if not self.supporter_target else int(self.active_supporter_count * 100 / self.supporter_target)
        amount_pct = 100 if not self.amount_target else int(self.committed_amount * 100 / self.amount_target)
        if self.goal_type == GoalType.SUPPORTERS:
            return min(100, supporter_pct)
        if self.goal_type == GoalType.MONEY:
            return min(100, amount_pct)
        return min(100, min(supporter_pct, amount_pct))

    def __str__(self):
        return self.title


class PledgeStatus(models.TextChoices):
    PENDING = "pending", "Pending payment"
    PAID = "paid", "Paid refundable deposit"
    COMMITTED = "committed", "Attendance commitment"
    CAPTURED = "captured", "Finalized"
    REFUND_PENDING = "refund_pending", "Refund pending"
    REFUNDED = "refunded", "Refunded"
    CANCELED = "canceled", "Canceled"
    FAILED = "failed", "Payment failed"


class Pledge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(DemandCampaign, related_name="pledges", on_delete=models.CASCADE)
    supporter_name = models.CharField(max_length=160)
    supporter_email = models.EmailField()
    quantity = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=PledgeStatus.choices, default=PledgeStatus.PENDING)
    payment_provider = models.CharField(max_length=30, default="none")
    payment_reference = models.CharField(max_length=180, blank=True)
    idempotency_key = models.CharField(max_length=100)
    referral_code = models.CharField(max_length=80, blank=True)
    source = models.CharField(max_length=80, blank=True, help_text="Example: facebook_group")
    source_label = models.CharField(max_length=180, blank=True, help_text="Example: Band X NYC Fans")
    terms_accepted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="pledge_quantity_gte_1"),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="pledge_amount_gte_0"),
            models.UniqueConstraint(
                fields=["campaign", "idempotency_key"],
                name="pledge_campaign_idempotency_uniq",
            ),
        ]

    @classmethod
    def active_statuses(cls):
        return [PledgeStatus.PAID, PledgeStatus.COMMITTED, PledgeStatus.CAPTURED]

    def __str__(self):
        return f"{self.supporter_email} → {self.campaign.title}"


class SponsorStatus(models.TextChoices):
    PLEDGED = "pledged", "Pledged"
    PAID = "paid", "Paid"
    FINALIZED = "finalized", "Finalized"
    REFUND_PENDING = "refund_pending", "Refund pending"
    REFUNDED = "refunded", "Refunded"
    CANCELED = "canceled", "Canceled"


class SponsorCommitment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(DemandCampaign, related_name="sponsorships", on_delete=models.CASCADE)
    sponsor_name = models.CharField(max_length=180)
    contact_name = models.CharField(max_length=160)
    contact_email = models.EmailField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=SponsorStatus.choices, default=SponsorStatus.PLEDGED)
    payment_reference = models.CharField(max_length=180, blank=True)
    benefits_requested = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def active_statuses(cls):
        return [SponsorStatus.PLEDGED, SponsorStatus.PAID, SponsorStatus.FINALIZED]


class CampaignEvent(models.Model):
    """Immutable business-event log for auditability and later analytics."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(DemandCampaign, related_name="events", on_delete=models.CASCADE)
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class IntegrationSyncStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SYNCED = "synced", "Synced"
    CONFLICT = "conflict", "Conflict"
    FAILED = "failed", "Failed"
    DISCONNECTED = "disconnected", "Disconnected"


class ExternalResourceLink(models.Model):
    """Durable mapping between a local record and a partner resource."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=40, default="vibesmeet")
    local_resource_type = models.CharField(max_length=80)
    local_resource_id = models.CharField(max_length=180)
    remote_resource_type = models.CharField(max_length=80)
    remote_resource_id = models.CharField(max_length=180)
    remote_version = models.CharField(max_length=100, blank=True)
    sync_status = models.CharField(
        max_length=20,
        choices=IntegrationSyncStatus.choices,
        default=IntegrationSyncStatus.PENDING,
    )
    metadata = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "local_resource_type", "local_resource_id", "remote_resource_type"],
                name="int_local_resource_uniq",
            ),
            models.UniqueConstraint(
                fields=["provider", "remote_resource_type", "remote_resource_id"],
                name="int_remote_resource_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "sync_status"], name="int_provider_status_idx"),
        ]


class IntegrationWebhookStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    PROCESSED = "processed", "Processed"
    QUARANTINED = "quarantined", "Quarantined"
    FAILED = "failed", "Failed"


class IntegrationWebhookEvent(models.Model):
    """Idempotent webhook inbox for partner events and replay."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=40, default="vibesmeet")
    event_id = models.CharField(max_length=180)
    event_type = models.CharField(max_length=160)
    resource_type = models.CharField(max_length=80, blank=True)
    resource_id = models.CharField(max_length=180, blank=True)
    resource_version = models.CharField(max_length=100, blank=True)
    sequence = models.BigIntegerField(default=0)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=IntegrationWebhookStatus.choices,
        default=IntegrationWebhookStatus.RECEIVED,
    )
    error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_id"],
                name="int_provider_event_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["provider", "status", "received_at"], name="int_webhook_queue_idx"),
            models.Index(fields=["provider", "resource_type", "resource_id"], name="int_webhook_resource_idx"),
        ]
        ordering = ["received_at"]
