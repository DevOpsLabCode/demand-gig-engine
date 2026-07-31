# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Defines the project-level URL router that connects administration, authentication, health, API, and integration endpoints.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Defines the project-level URL router that connects administration, authentication, health, API, and integration endpoints.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from django.contrib import admin
from django.urls import include, path
from gigs.views import campaign_share_page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/", include("gigs.urls")),
    path("share/campaign/<slug:slug>/", campaign_share_page, name="campaign-share-page"),
]
