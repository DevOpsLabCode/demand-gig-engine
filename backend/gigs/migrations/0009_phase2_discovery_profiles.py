# Generated for the Open Concert Phase 2 discovery/profile foundation.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import gigs.discovery_models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("gigs", "0008_campaign_preferences"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserDiscoveryProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("state", models.CharField(blank=True, max_length=80)),
                ("preferred_cities", models.JSONField(blank=True, default=list)),
                ("home_latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("home_longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="discovery_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="CampaignLocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("state", models.CharField(blank=True, max_length=80)),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("campaign", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="location_details", to="gigs.demandcampaign")),
            ],
        ),
        migrations.CreateModel(
            name="ProfileMedia",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("media_type", models.CharField(choices=[("avatar", "Profile photo"), ("cover", "Cover image"), ("image", "Gallery image"), ("video", "Profile video")], max_length=12)),
                ("file", models.FileField(upload_to=gigs.discovery_models.profile_media_upload_to)),
                ("caption", models.CharField(blank=True, max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="profile_media", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["media_type", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="campaignlocation",
            index=models.Index(fields=["state"], name="gig_location_state_idx"),
        ),
        migrations.AddIndex(
            model_name="profilemedia",
            index=models.Index(fields=["user", "media_type"], name="profile_media_user_type_idx"),
        ),
    ]
