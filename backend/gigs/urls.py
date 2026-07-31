from .auth_views import (
    auth_config,
    auth_logout,
    auth_profile,
    health,
    health_live,
    health_ready,
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
    path("health/live/", health_live, name="health-live"),
    path("health/ready/", health_ready, name="health-ready"),
    path("", include(router.urls)),
    path("auth/config/", auth_config, name="auth-config"),
    path("auth/profile/", auth_profile, name="auth-profile"),
    path("auth/logout/", auth_logout, name="auth-logout"),
    path("facebook/config/", facebook_config, name="facebook-config"),
    path("facebook/login/", facebook_login, name="facebook-login"),
    path("facebook/pages/", facebook_pages, name="facebook-pages"),
    path("payments/stripe/webhook/", stripe_webhook, name="stripe-webhook"),
    path("vibesmeet/config/", vibesmeet_config, name="vibesmeet-config"),
    path("vibesmeet/webhook/", vibesmeet_webhook, name="vibesmeet-webhook"),
]
