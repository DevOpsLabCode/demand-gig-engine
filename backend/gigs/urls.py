# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Maps application API paths to campaigns, approvals, authentication, multiple roles, payments, and integrations.

"""URL routing for the demand-gig API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .auth_views import (
    auth_config,
    auth_login,
    auth_logout,
    auth_profile,
    auth_register,
    health,
    readiness,
)
from .campaign_approval_views import (
    campaign_approve,
    campaign_collection,
    campaign_detail,
    campaign_launch,
    campaign_reject,
    campaign_review_queue,
    campaign_submit_review,
)
from .role_views import reject_role, role_collection, verify_role
from .views import (
    CampaignViewSet,
    facebook_config,
    facebook_login,
    facebook_pages,
    stripe_webhook,
    vibesmeet_config,
    vibesmeet_webhook,
)

router = DefaultRouter()
router.register("campaigns", CampaignViewSet, basename="campaign")

urlpatterns = [
    path("health/", health, name="health"),
    path("readiness/", readiness, name="readiness"),
    # Phase 1B routes precede the router so the protected detail and launch
    # implementations replace the legacy direct-draft launch behavior.
    path("campaigns/review-queue/", campaign_review_queue, name="campaign-review-queue"),
    path("campaigns/", campaign_collection, name="campaign-collection"),
    path("campaigns/<slug:slug>/submit-review/", campaign_submit_review, name="campaign-submit-review"),
    path("campaigns/<slug:slug>/approve/", campaign_approve, name="campaign-approve"),
    path("campaigns/<slug:slug>/reject/", campaign_reject, name="campaign-reject"),
    path("campaigns/<slug:slug>/launch/", campaign_launch, name="campaign-approved-launch"),
    path("campaigns/<slug:slug>/", campaign_detail, name="campaign-protected-detail"),
    path("", include(router.urls)),
    path("auth/config/", auth_config, name="auth-config"),
    path("auth/login/", auth_login, name="auth-login"),
    path("auth/register/", auth_register, name="auth-register"),
    path("auth/profile/", auth_profile, name="auth-profile"),
    path("auth/roles/", role_collection, name="auth-roles"),
    path("auth/roles/<int:assignment_id>/verify/", verify_role, name="auth-role-verify"),
    path("auth/roles/<int:assignment_id>/reject/", reject_role, name="auth-role-reject"),
    path("auth/logout/", auth_logout, name="auth-logout"),
    path("facebook/config/", facebook_config, name="facebook-config"),
    path("facebook/login/", facebook_login, name="facebook-login"),
    path("facebook/pages/", facebook_pages, name="facebook-pages"),
    path("payments/stripe/webhook/", stripe_webhook, name="stripe-webhook"),
    path("vibesmeet/config/", vibesmeet_config, name="vibesmeet-config"),
    path("vibesmeet/webhook/", vibesmeet_webhook, name="vibesmeet-webhook"),
]
