# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Records the database schema transition represented by migration 0003_scope_pledge_idempotency.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Records the database schema transition represented by migration 0003_scope_pledge_idempotency.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Describe the database schema transition and its dependency on earlier migrations.
    """
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
