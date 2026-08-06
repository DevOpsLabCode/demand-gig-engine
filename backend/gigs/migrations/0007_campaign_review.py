# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Adds immutable campaign-review evidence without changing valid collecting campaigns.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def reverse_new_review_statuses(apps, schema_editor):
    """Return Phase 1B-only campaign states to draft before rolling back the model."""

    DemandCampaign = apps.get_model("gigs", "DemandCampaign")
    DemandCampaign.objects.filter(
        status__in=["pending_review", "approved", "rejected"]
    ).update(status="draft")


class Migration(migrations.Migration):
    dependencies = [
        ("gigs", "0006_multiple_roles"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="demandcampaign",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("collecting", "Collecting support"),
                    ("target_reached", "Target reached"),
                    ("confirming", "Confirming artist and venue"),
                    ("confirmed", "Confirmed"),
                    ("live", "Live event"),
                    ("completed", "Completed"),
                    ("failed", "Target not reached"),
                    ("refunding", "Refunding"),
                    ("refunded", "Refunded"),
                    ("canceled", "Canceled"),
                    ("pending_review", "Pending review"),
                    ("approved", "Approved"),
                    ("threshold_reached", "Threshold reached"),
                    ("feasibility_review", "Feasibility review"),
                    ("conditionally_ready", "Conditionally ready"),
                    ("ready", "Ready"),
                    ("handed_off", "Handed off"),
                    ("rejected", "Rejected"),
                    ("expired", "Expired"),
                    ("cancelled", "Cancelled"),
                    ("not_viable", "Not viable"),
                    ("refund_pending", "Refund pending"),
                ],
                default="draft",
                max_length=24,
            ),
        ),
        migrations.CreateModel(
            name="CampaignReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "decision",
                    models.CharField(
                        choices=[
                            ("auto_approved", "Automatically approved"),
                            ("manual_review_required", "Manual review required"),
                            ("manual_approved", "Manually approved"),
                            ("rejected", "Rejected"),
                        ],
                        max_length=32,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("checks", models.JSONField(blank=True, default=list)),
                ("reviewed_at", models.DateTimeField(auto_now_add=True)),
                ("previous_status", models.CharField(max_length=24)),
                ("resulting_status", models.CharField(max_length=24)),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews",
                        to="gigs.demandcampaign",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="campaign_reviews_completed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["reviewed_at", "id"]},
        ),
        migrations.AddIndex(
            model_name="campaignreview",
            index=models.Index(
                fields=["campaign", "reviewed_at"],
                name="gig_review_campaign_time_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaignreview",
            index=models.Index(
                fields=["decision", "reviewed_at"],
                name="gig_review_decision_time_idx",
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, reverse_new_review_statuses),
    ]
