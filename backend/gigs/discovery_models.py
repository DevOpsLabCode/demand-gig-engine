# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Adds location discovery, rich public-profile metadata, and user media without changing the mature campaign table.

from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


class ProfileMediaType(models.TextChoices):
    AVATAR = "avatar", "Profile photo"
    COVER = "cover", "Cover image"
    IMAGE = "image", "Gallery image"
    VIDEO = "video", "Profile video"


def profile_media_upload_to(instance: "ProfileMedia", filename: str) -> str:
    suffix = Path(filename).suffix.lower()[:12]
    return f"profiles/{instance.user_id}/{instance.media_type}/{uuid.uuid4().hex}{suffix}"


class UserDiscoveryProfile(models.Model):
    """Discovery preferences plus the shared public identity used by fans and professional profiles."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="discovery_profile",
        on_delete=models.CASCADE,
    )
    state = models.CharField(max_length=80, blank=True)
    preferred_cities = models.JSONField(default=list, blank=True)
    home_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    home_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    headline = models.CharField(max_length=180, blank=True)
    genres = models.JSONField(default=list, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    external_video_urls = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Discovery profile for {self.user.get_username()}"


class CampaignLocation(models.Model):
    """Adds state and optional map coordinates to a campaign without mutating its core lifecycle model."""

    campaign = models.OneToOneField(
        "gigs.DemandCampaign",
        related_name="location_details",
        on_delete=models.CASCADE,
    )
    state = models.CharField(max_length=80, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["state"], name="gig_location_state_idx")]

    def __str__(self) -> str:
        return f"{self.campaign.city}, {self.state}".strip(", ")


class ProfileMedia(models.Model):
    """S3/file-system backed profile media owned by one authenticated user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="profile_media",
        on_delete=models.CASCADE,
    )
    media_type = models.CharField(max_length=12, choices=ProfileMediaType.choices)
    file = models.FileField(upload_to=profile_media_upload_to)
    caption = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["media_type", "-created_at"]
        indexes = [models.Index(fields=["user", "media_type"], name="profile_media_user_type_idx")]

    def __str__(self) -> str:
        return f"{self.user.get_username()} {self.media_type}"
