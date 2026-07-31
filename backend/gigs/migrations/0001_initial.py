# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Records the database schema transition represented by migration 0001_initial.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Records the database schema transition represented by migration 0001_initial.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

# Generated manually for the Demand Gig MVP.
import uuid
from decimal import Decimal
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Describe the database schema transition and its dependency on earlier migrations.
    """
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DemandCampaign",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=180)),
                ("slug", models.SlugField(blank=True, max_length=210, unique=True)),
                ("pitch", models.TextField()),
                ("artist_name", models.CharField(max_length=160)),
                ("city", models.CharField(max_length=120)),
                ("country", models.CharField(default="United States", max_length=80)),
                ("proposed_date", models.DateField(blank=True, null=True)),
                ("deadline", models.DateTimeField()),
                ("goal_type", models.CharField(choices=[("supporters", "Supporters"), ("money", "Committed amount"), ("both", "Both supporters and amount")], default="supporters", max_length=20)),
                ("supporter_target", models.PositiveIntegerField(default=500)),
                ("amount_target", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("suggested_deposit", models.DecimalField(decimal_places=2, default=Decimal("25.00"), max_digits=10)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("collecting", "Collecting support"), ("target_reached", "Target reached"), ("confirming", "Confirming artist and venue"), ("confirmed", "Confirmed"), ("live", "Live event"), ("completed", "Completed"), ("failed", "Target not reached"), ("refunding", "Refunding"), ("refunded", "Refunded"), ("canceled", "Canceled")], default="draft", max_length=24)),
                ("artist_confirmed", models.BooleanField(default=False)),
                ("venue_confirmed", models.BooleanField(default=False)),
                ("confirmed_artist_details", models.TextField(blank=True)),
                ("confirmed_venue_details", models.TextField(blank=True)),
                ("event_id", models.CharField(blank=True, help_text="ID of the confirmed event in the host platform", max_length=100)),
                ("organizer_name", models.CharField(max_length=160)),
                ("organizer_email", models.EmailField(max_length=254)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CampaignEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(max_length=80)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="gigs.demandcampaign")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="Pledge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("supporter_name", models.CharField(max_length=160)),
                ("supporter_email", models.EmailField(max_length=254)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("status", models.CharField(choices=[("pending", "Pending payment"), ("paid", "Paid refundable deposit"), ("committed", "Attendance commitment"), ("captured", "Finalized"), ("refund_pending", "Refund pending"), ("refunded", "Refunded"), ("canceled", "Canceled"), ("failed", "Payment failed")], default="pending", max_length=20)),
                ("payment_provider", models.CharField(default="none", max_length=30)),
                ("payment_reference", models.CharField(blank=True, max_length=180)),
                ("idempotency_key", models.CharField(max_length=100, unique=True)),
                ("referral_code", models.CharField(blank=True, max_length=80)),
                ("source", models.CharField(blank=True, help_text="Example: facebook_group", max_length=80)),
                ("source_label", models.CharField(blank=True, help_text="Example: Band X NYC Fans", max_length=180)),
                ("terms_accepted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pledges", to="gigs.demandcampaign")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SponsorCommitment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sponsor_name", models.CharField(max_length=180)),
                ("contact_name", models.CharField(max_length=160)),
                ("contact_email", models.EmailField(max_length=254)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("status", models.CharField(choices=[("pledged", "Pledged"), ("paid", "Paid"), ("finalized", "Finalized"), ("refund_pending", "Refund pending"), ("refunded", "Refunded"), ("canceled", "Canceled")], default="pledged", max_length=20)),
                ("payment_reference", models.CharField(blank=True, max_length=180)),
                ("benefits_requested", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sponsorships", to="gigs.demandcampaign")),
            ],
        ),
        migrations.AddIndex(model_name="demandcampaign", index=models.Index(fields=["status", "deadline"], name="gig_status_deadline_idx")),
        migrations.AddIndex(model_name="demandcampaign", index=models.Index(fields=["artist_name", "city"], name="gig_artist_city_idx")),
        migrations.AddConstraint(model_name="pledge", constraint=models.CheckConstraint(condition=models.Q(quantity__gte=1), name="pledge_quantity_gte_1")),
        migrations.AddConstraint(model_name="pledge", constraint=models.CheckConstraint(condition=models.Q(amount__gte=0), name="pledge_amount_gte_0")),
    ]
