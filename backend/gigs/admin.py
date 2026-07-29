from django.contrib import admin
from .models import CampaignEvent, DemandCampaign, Pledge, SponsorCommitment


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
