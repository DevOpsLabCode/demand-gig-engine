# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Registers domain models with Django Admin and selects useful list, search, and filtering fields.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Registers domain models with Django Admin and selects useful list, search, and filtering fields.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from django.contrib import admin
from .models import (
    CampaignEvent,
    DemandCampaign,
    ExternalResourceLink,
    GigUserProfile,
    IntegrationWebhookEvent,
    Pledge,
    SponsorCommitment,
)


@admin.register(DemandCampaign)
class DemandCampaignAdmin(admin.ModelAdmin):
    """
    Configure Django Admin list, search, filtering, and display behavior for DemandCampaign records.
    """
    list_display = ("title", "artist_name", "city", "status", "deadline", "artist_confirmed", "venue_confirmed")
    list_filter = ("status", "goal_type", "city")
    search_fields = ("title", "artist_name", "organizer_email")
    prepopulated_fields = {"slug": ("artist_name", "city")}


@admin.register(Pledge)
class PledgeAdmin(admin.ModelAdmin):
    """
    Configure Django Admin list, search, filtering, and display behavior for Pledge records.
    """
    list_display = ("supporter_email", "campaign", "amount", "status", "source", "created_at")
    list_filter = ("status", "source", "payment_provider")
    search_fields = ("supporter_email", "payment_reference", "source_label")


@admin.register(SponsorCommitment)
class SponsorCommitmentAdmin(admin.ModelAdmin):
    """
    Configure Django Admin list, search, filtering, and display behavior for SponsorCommitment records.
    """
    list_display = ("sponsor_name", "campaign", "amount", "status")


@admin.register(CampaignEvent)
class CampaignEventAdmin(admin.ModelAdmin):
    """
    Configure Django Admin list, search, filtering, and display behavior for CampaignEvent records.
    """
    list_display = ("campaign", "event_type", "created_at")
    readonly_fields = ("campaign", "event_type", "payload", "created_at")


@admin.register(ExternalResourceLink)
class ExternalResourceLinkAdmin(admin.ModelAdmin):
    """
    Configure Django Admin list, search, filtering, and display behavior for ExternalResourceLink records.
    """
    list_display = ("provider", "local_resource_type", "local_resource_id", "remote_resource_type", "remote_resource_id", "sync_status", "last_synced_at")
    list_filter = ("provider", "sync_status", "local_resource_type", "remote_resource_type")
    search_fields = ("local_resource_id", "remote_resource_id")


@admin.register(IntegrationWebhookEvent)
class IntegrationWebhookEventAdmin(admin.ModelAdmin):
    """
    Configure Django Admin list, search, filtering, and display behavior for IntegrationWebhookEvent records.
    """
    list_display = ("provider", "event_type", "resource_type", "resource_id", "status", "received_at", "processed_at")
    list_filter = ("provider", "status", "event_type", "resource_type")
    search_fields = ("event_id", "resource_id")
    readonly_fields = ("provider", "event_id", "event_type", "resource_type", "resource_id", "resource_version", "sequence", "payload", "received_at", "processed_at")


@admin.register(GigUserProfile)
class GigUserProfileAdmin(admin.ModelAdmin):
    """
    Configure Django Admin list, search, filtering, and display behavior for GigUserProfile records.
    """
    list_display = ("user", "display_name", "account_type", "company_name", "verified", "updated_at")
    list_filter = ("account_type", "verified", "country")
    search_fields = ("user__username", "user__email", "display_name", "company_name")
