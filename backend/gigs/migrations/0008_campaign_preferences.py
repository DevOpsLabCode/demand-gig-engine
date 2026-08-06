# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Adds campaign dates, ticket-price choices, and one supporter preference per user and campaign.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gigs", "0007_campaign_review"),
    ]

    operations = [
        migrations.CreateModel(
            name="CampaignDateOption",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("start_datetime", models.DateTimeField()),
                ("end_datetime", models.DateTimeField(blank=True, null=True)),
                (
                    "venue_timezone",
                    models.CharField(
                        default="America/New_York",
                        max_length=64,
                    ),
                ),
                ("label", models.CharField(blank=True, max_length=160)),
                ("active", models.BooleanField(default=True)),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="date_options",
                        to="gigs.demandcampaign",
                    ),
                ),
            ],
            options={
                "ordering": ["start_datetime", "id"],
            },
        ),
        migrations.CreateModel(
            name="CampaignPriceOption",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("label", models.CharField(blank=True, max_length=160)),
                ("active", models.BooleanField(default=True)),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="price_options",
                        to="gigs.demandcampaign",
                    ),
                ),
            ],
            options={
                "ordering": ["amount", "id"],
            },
        ),
        migrations.CreateModel(
            name="SupporterPreference",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("expected_quantity", models.PositiveIntegerField(default=1)),
                (
                    "attendance_mode",
                    models.CharField(
                        choices=[
                            ("physical", "Physical attendance"),
                            ("virtual", "Virtual attendance"),
                        ],
                        default="physical",
                        max_length=16,
                    ),
                ),
                (
                    "preferred_neighborhood",
                    models.CharField(blank=True, max_length=160),
                ),
                ("accessibility_notes", models.TextField(blank=True)),
                (
                    "referral_source",
                    models.CharField(blank=True, max_length=120),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="supporter_preferences",
                        to="gigs.demandcampaign",
                    ),
                ),
                (
                    "selected_date_option",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="preferences",
                        to="gigs.campaigndateoption",
                    ),
                ),
                (
                    "selected_price_option",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="preferences",
                        to="gigs.campaignpriceoption",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="campaign_preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["campaign_id", "user_id"],
            },
        ),
        migrations.AddConstraint(
            model_name="campaigndateoption",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("end_datetime__isnull", True))
                    | models.Q(("end_datetime__gt", models.F("start_datetime")))
                ),
                name="campaign_date_end_after_start",
            ),
        ),
        migrations.AddIndex(
            model_name="campaigndateoption",
            index=models.Index(
                fields=["campaign", "active", "start_datetime"],
                name="gig_date_campaign_active_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="campaignpriceoption",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount__gte", 0)),
                name="campaign_price_amount_gte_0",
            ),
        ),
        migrations.AddIndex(
            model_name="campaignpriceoption",
            index=models.Index(
                fields=["campaign", "active", "amount"],
                name="gig_price_campaign_active_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="supporterpreference",
            constraint=models.UniqueConstraint(
                fields=("campaign", "user"),
                name="supporter_preference_campaign_user_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="supporterpreference",
            constraint=models.CheckConstraint(
                condition=models.Q(("expected_quantity__gte", 1)),
                name="supporter_preference_quantity_gte_1",
            ),
        ),
        migrations.AddIndex(
            model_name="supporterpreference",
            index=models.Index(
                fields=["campaign", "attendance_mode"],
                name="gig_pref_campaign_mode_idx",
            ),
        ),
    ]
