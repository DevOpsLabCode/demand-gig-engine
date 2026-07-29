from django.db import migrations, models


class Migration(migrations.Migration):
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
