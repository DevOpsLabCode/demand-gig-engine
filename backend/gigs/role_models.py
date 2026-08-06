# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Defines multiple marketplace roles, user-role verification state, and immutable role audit events.

"""Persistent models for multiple marketplace roles and administrator verification."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class RoleCode(models.TextChoices):
    """Stable role identifiers used by the API, database, and frontend."""

    FAN = "fan", "Fan"
    ARTIST = "artist", "Artist"
    VENUE = "venue", "Venue"
    ORGANIZER = "organizer", "Organizer"
    SPONSOR = "sponsor", "Sponsor"
    VENDOR = "vendor", "Vendor"
    EQUIPMENT_RENTAL = "equipment_rental", "Equipment rental"
    ADMINISTRATOR = "administrator", "Administrator"


class RoleVerificationStatus(models.TextChoices):
    """Review states for one user's requested marketplace role."""

    PENDING = "pending", "Pending verification"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"


class Role(models.Model):
    """Catalog one role that can be assigned to multiple users."""

    code = models.CharField(max_length=32, choices=RoleCode.choices, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    requires_verification = models.BooleanField(default=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_name", "code"]

    def __str__(self) -> str:
        return self.display_name


class UserRole(models.Model):
    """Associate a user with one role and its independent verification state."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="role_assignments",
        on_delete=models.CASCADE,
    )
    role = models.ForeignKey(
        Role,
        related_name="user_assignments",
        on_delete=models.PROTECT,
    )
    organization_name = models.CharField(max_length=180, blank=True)
    profile_data = models.JSONField(default=dict, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=RoleVerificationStatus.choices,
        default=RoleVerificationStatus.PENDING,
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="verified_role_assignments",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id", "role__display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                name="gig_user_role_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=["verification_status", "role"],
                name="gig_role_review_idx",
            )
        ]

    @property
    def is_verified(self) -> bool:
        return self.verification_status == RoleVerificationStatus.VERIFIED

    def __str__(self) -> str:
        return f"{self.user} — {self.role.display_name}"


class RoleAuditEvent(models.Model):
    """Append-only evidence for role requests and administrator decisions."""

    assignment = models.ForeignKey(
        UserRole,
        related_name="audit_events",
        on_delete=models.CASCADE,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="role_audit_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=40)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.assignment} — {self.event_type}"
