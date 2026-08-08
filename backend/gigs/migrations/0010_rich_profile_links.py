# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Adds rich universal profile fields for fans, artists, bands, venues, organizers, sponsors, and vendors.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gigs", "0009_phase2_discovery_profiles"),
    ]

    operations = [
        migrations.AddField(
            model_name="userdiscoveryprofile",
            name="headline",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="userdiscoveryprofile",
            name="genres",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="userdiscoveryprofile",
            name="social_links",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="userdiscoveryprofile",
            name="external_video_urls",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
