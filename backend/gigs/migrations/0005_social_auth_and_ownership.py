from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gigs", "0004_vibesmeet_integration_foundation"),
    ]

    operations = [
        migrations.CreateModel(
            name="GigUserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account_type", models.CharField(choices=[("fan", "Fan"), ("band", "Band / artist"), ("venue", "Venue"), ("organizer", "Organizer / promoter"), ("rental", "Equipment rental"), ("sponsor", "Sponsor")], default="fan", max_length=20)),
                ("display_name", models.CharField(blank=True, max_length=160)),
                ("company_name", models.CharField(blank=True, max_length=180)),
                ("avatar_url", models.URLField(blank=True)),
                ("bio", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=120)),
                ("country", models.CharField(blank=True, max_length=80)),
                ("verified", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="gig_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name="demandcampaign",
            name="owner",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="owned_campaigns", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="pledge",
            name="supporter_user",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="gig_pledges", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="sponsorcommitment",
            name="contact_user",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="gig_sponsorships", to=settings.AUTH_USER_MODEL),
        ),
    ]
