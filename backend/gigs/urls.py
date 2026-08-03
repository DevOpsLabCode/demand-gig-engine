# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Maps application API paths to view sets, authentication endpoints, payment webhooks, and integration webhooks.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Maps application API paths to view sets, authentication endpoints, payment webhooks, and integration webhooks.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from .auth_views import (
    auth_config,
    auth_login,
    auth_logout,
    auth_profile,
    auth_register,
    health,
    readiness,
)
from django.urls import include, path
from rest_framework.routers import DefaultRouter
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
    path("", include(router.urls)),
    path("auth/config/", auth_config, name="auth-config"),
    path("auth/login/", auth_login, name="auth-login"),
    path("auth/register/", auth_register, name="auth-register"),
    path("auth/profile/", auth_profile, name="auth-profile"),
    path("auth/logout/", auth_logout, name="auth-logout"),
    path("facebook/config/", facebook_config, name="facebook-config"),
    path("facebook/login/", facebook_login, name="facebook-login"),
    path("facebook/pages/", facebook_pages, name="facebook-pages"),
    path("payments/stripe/webhook/", stripe_webhook, name="stripe-webhook"),
    path("vibesmeet/config/", vibesmeet_config, name="vibesmeet-config"),
    path("vibesmeet/webhook/", vibesmeet_webhook, name="vibesmeet-webhook"),
]
