from django.contrib import admin
from .models import (
    CampaignEvent,
    DemandCampaign,
    ExternalResourceLink,
    IntegrationWebhookEvent,
    Pledge,
    SponsorCommitment,
)


@admin.register(DemandCampaign)
class DemandCampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "artist_name", "city", "status", "deadline", "artist_confirmed", "venue_confirmed")
    list_filter = ("status", "goal_type", "city")
    search_fields = ("title", "artist_name", "organizer_email")
    prepopulated_fields = {"slug": ("artist_name", "city")}


@admin.register(Pledge)
class PledgeAdmin(admin.ModelAdmin):
    list_display = ("supporter_email", "campaign", "amount", "status", "source", "created_at")
    list_filter = ("status", "source", "payment_provider")
    search_fields = ("supporter_email", "payment_reference", "source_label")


@admin.register(SponsorCommitment)
class SponsorCommitmentAdmin(admin.ModelAdmin):
    list_display = ("sponsor_name", "campaign", "amount", "status")


@admin.register(CampaignEvent)
class CampaignEventAdmin(admin.ModelAdmin):
    list_display = ("campaign", "event_type", "created_at")
    readonly_fields = ("campaign", "event_type", "payload", "created_at")


@admin.register(ExternalResourceLink)
class ExternalResourceLinkAdmin(admin.ModelAdmin):
    list_display = ("provider", "local_resource_type", "local_resource_id", "remote_resource_type", "remote_resource_id", "sync_status", "last_synced_at")
    list_filter = ("provider", "sync_status", "local_resource_type", "remote_resource_type")
    search_fields = ("local_resource_id", "remote_resource_id")


@admin.register(IntegrationWebhookEvent)
class IntegrationWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("provider", "event_type", "resource_type", "resource_id", "status", "received_at", "processed_at")
    list_filter = ("provider", "status", "event_type", "resource_type")
    search_fields = ("event_id", "resource_id")
    readonly_fields = ("provider", "event_id", "event_type", "resource_type", "resource_id", "resource_version", "sequence", "payload", "received_at", "processed_at")
