# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Registers campaign, integration, profile, role, preference, and immutable audit models with Django Admin.

"""Django Admin registrations for the demand-gig domain."""

from django.contrib import admin

from .campaign_preference_models import (
    CampaignDateOption,
    CampaignPriceOption,
    SupporterPreference,
)
from .campaign_review_models import CampaignReview
from .models import (
    CampaignEvent,
    DemandCampaign,
    ExternalResourceLink,
    GigUserProfile,
    IntegrationWebhookEvent,
    Pledge,
    SponsorCommitment,
)
from .role_models import Role, RoleAuditEvent, UserRole


@admin.register(DemandCampaign)
class DemandCampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "artist_name", "city", "status", "deadline", "artist_confirmed", "venue_confirmed")
    list_filter = ("status", "goal_type", "city")
    search_fields = ("title", "artist_name", "organizer_email")
    prepopulated_fields = {"slug": ("artist_name", "city")}


@admin.register(CampaignDateOption)
class CampaignDateOptionAdmin(admin.ModelAdmin):
    list_display = ("campaign", "label", "start_datetime", "end_datetime", "venue_timezone", "active")
    list_filter = ("active", "venue_timezone")
    search_fields = ("campaign__title", "campaign__slug", "label")


@admin.register(CampaignPriceOption)
class CampaignPriceOptionAdmin(admin.ModelAdmin):
    list_display = ("campaign", "label", "amount", "currency", "active")
    list_filter = ("active", "currency")
    search_fields = ("campaign__title", "campaign__slug", "label")


@admin.register(SupporterPreference)
class SupporterPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "campaign",
        "user",
        "attendance_mode",
        "expected_quantity",
        "selected_date_option",
        "selected_price_option",
        "updated_at",
    )
    list_filter = ("attendance_mode", "campaign")
    search_fields = (
        "campaign__title",
        "campaign__slug",
        "user__username",
        "user__email",
        "preferred_neighborhood",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(CampaignReview)
class CampaignReviewAdmin(admin.ModelAdmin):
    list_display = ("campaign", "decision", "reviewer", "previous_status", "resulting_status", "reviewed_at")
    list_filter = ("decision", "previous_status", "resulting_status", "reviewed_at")
    search_fields = ("campaign__title", "campaign__slug", "reviewer__username", "notes")
    readonly_fields = (
        "campaign",
        "decision",
        "reviewer",
        "notes",
        "checks",
        "reviewed_at",
        "previous_status",
        "resulting_status",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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


@admin.register(GigUserProfile)
class GigUserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "account_type", "company_name", "verified", "updated_at")
    list_filter = ("account_type", "verified", "country")
    search_fields = ("user__username", "user__email", "display_name", "company_name")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "display_name", "requires_verification", "active")
    list_filter = ("requires_verification", "active")
    search_fields = ("code", "display_name")


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "organization_name", "verification_status", "verified_by", "updated_at")
    list_filter = ("verification_status", "role")
    search_fields = ("user__username", "user__email", "organization_name")
    readonly_fields = ("verified_by", "verified_at", "created_at", "updated_at")


@admin.register(RoleAuditEvent)
class RoleAuditEventAdmin(admin.ModelAdmin):
    list_display = ("assignment", "event_type", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("assignment__user__username", "assignment__user__email")
    readonly_fields = ("assignment", "actor", "event_type", "payload", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
