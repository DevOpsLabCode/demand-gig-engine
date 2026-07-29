from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("gigs", "0002_facebook_hub_urls")]

    operations = [
        migrations.AlterField(
            model_name="pledge",
            name="idempotency_key",
            field=models.CharField(max_length=100),
        ),
        migrations.AddConstraint(
            model_name="pledge",
            constraint=models.UniqueConstraint(
                fields=("campaign", "idempotency_key"),
                name="pledge_campaign_idempotency_uniq",
            ),
        ),
    ]
