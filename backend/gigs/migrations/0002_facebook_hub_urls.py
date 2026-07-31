# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Records the database schema transition represented by migration 0002_facebook_hub_urls.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Records the database schema transition represented by migration 0002_facebook_hub_urls.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Describe the database schema transition and its dependency on earlier migrations.
    """
    dependencies = [("gigs", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="demandcampaign",
            name="facebook_event_url",
            field=models.URLField(blank=True, help_text="Existing Facebook Event used as the discovery hub"),
        ),
        migrations.AddField(
            model_name="demandcampaign",
            name="facebook_group_url",
            field=models.URLField(blank=True, help_text="Primary Facebook Group or fan community"),
        ),
        migrations.AddField(
            model_name="demandcampaign",
            name="facebook_page_url",
            field=models.URLField(blank=True, help_text="Organizer, artist, or venue Facebook Page"),
        ),
    ]
