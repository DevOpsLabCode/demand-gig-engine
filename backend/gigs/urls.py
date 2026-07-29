from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    CampaignViewSet,
    facebook_config,
    facebook_login,
    facebook_pages,
    stripe_webhook,
)

router = DefaultRouter()
router.register("campaigns", CampaignViewSet, basename="campaign")

urlpatterns = [
    path("", include(router.urls)),
    path("facebook/config/", facebook_config, name="facebook-config"),
    path("facebook/login/", facebook_login, name="facebook-login"),
    path("facebook/pages/", facebook_pages, name="facebook-pages"),
    path("payments/stripe/webhook/", stripe_webhook, name="stripe-webhook"),
]
