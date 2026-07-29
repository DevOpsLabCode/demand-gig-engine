from django.contrib import admin
from django.urls import include, path
from gigs.views import campaign_share_page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("gigs.urls")),
    path("share/campaign/<slug:slug>/", campaign_share_page, name="campaign-share-page"),
]
