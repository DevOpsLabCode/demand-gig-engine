# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates the multiple-role schema, seeds the role catalog, and safely backfills legacy account types.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


ROLE_DEFINITIONS = (
    ("fan", "Fan", "Support, reserve, vote, and share campaigns.", False),
    ("artist", "Artist", "Represent an artist or performing act.", True),
    ("venue", "Venue", "Represent a performance venue or space.", True),
    ("organizer", "Organizer", "Create and coordinate demand-driven events.", True),
    ("sponsor", "Sponsor", "Support campaigns and event production.", True),
    ("vendor", "Vendor", "Provide event-related professional services.", True),
    ("equipment_rental", "Equipment rental", "Provide sound, lighting, staging, or rental inventory.", True),
    ("administrator", "Administrator", "Review role and platform approval requests.", True),
)

LEGACY_ACCOUNT_ROLE_MAP = {
    "fan": "fan",
    "band": "artist",
    "venue": "venue",
    "organizer": "organizer",
    "rental": "equipment_rental",
    "sponsor": "sponsor",
}


def seed_roles_and_backfill(apps, schema_editor):
    """Seed stable role codes and create idempotent fan plus legacy assignments."""

    Role = apps.get_model("gigs", "Role")
    UserRole = apps.get_model("gigs", "UserRole")
    RoleAuditEvent = apps.get_model("gigs", "RoleAuditEvent")
    GigUserProfile = apps.get_model("gigs", "GigUserProfile")

    roles = {}
    for code, display_name, description, requires_verification in ROLE_DEFINITIONS:
        role, _ = Role.objects.update_or_create(
            code=code,
            defaults={
                "display_name": display_name,
                "description": description,
                "requires_verification": requires_verification,
                "active": True,
            },
        )
        roles[code] = role

    for profile in GigUserProfile.objects.all().iterator():
        fan_assignment, fan_created = UserRole.objects.get_or_create(
            user_id=profile.user_id,
            role=roles["fan"],
            defaults={
                "verification_status": "verified",
                "organization_name": "",
                "profile_data": {},
            },
        )
        if fan_created:
            RoleAuditEvent.objects.create(
                assignment=fan_assignment,
                event_type="legacy_role_backfilled",
                payload={"source": "automatic_fan"},
            )

        role_code = LEGACY_ACCOUNT_ROLE_MAP.get(profile.account_type, "fan")
        if role_code == "fan":
            continue
        profile_data = {
            key: value
            for key, value in {
                "display_name": profile.display_name,
                "bio": profile.bio,
                "city": profile.city,
                "country": profile.country,
            }.items()
            if value
        }
        assignment, created = UserRole.objects.get_or_create(
            user_id=profile.user_id,
            role=roles[role_code],
            defaults={
                "organization_name": profile.company_name,
                "profile_data": profile_data,
                "verification_status": (
                    "verified" if profile.verified else "pending"
                ),
            },
        )
        if created:
            RoleAuditEvent.objects.create(
                assignment=assignment,
                event_type="legacy_role_backfilled",
                payload={"source_account_type": profile.account_type},
            )


def reverse_backfill(apps, schema_editor):
    """No reverse data copy is needed because account_type remains intact."""


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gigs", "0005_social_auth_and_ownership"),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(choices=[("fan", "Fan"), ("artist", "Artist"), ("venue", "Venue"), ("organizer", "Organizer"), ("sponsor", "Sponsor"), ("vendor", "Vendor"), ("equipment_rental", "Equipment rental"), ("administrator", "Administrator")], max_length=32, unique=True)),
                ("display_name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("requires_verification", models.BooleanField(default=True)),
                ("active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["display_name", "code"]},
        ),
        migrations.CreateModel(
            name="UserRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("organization_name", models.CharField(blank=True, max_length=180)),
                ("profile_data", models.JSONField(blank=True, default=dict)),
                ("verification_status", models.CharField(choices=[("pending", "Pending verification"), ("verified", "Verified"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="user_assignments", to="gigs.role")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_assignments", to=settings.AUTH_USER_MODEL)),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="verified_role_assignments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["user_id", "role__display_name"]},
        ),
        migrations.CreateModel(
            name="RoleAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=40)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="role_audit_events", to=settings.AUTH_USER_MODEL)),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="gigs.userrole")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.AddConstraint(
            model_name="userrole",
            constraint=models.UniqueConstraint(fields=("user", "role"), name="gig_user_role_unique"),
        ),
        migrations.AddIndex(
            model_name="userrole",
            index=models.Index(fields=["verification_status", "role"], name="gig_role_review_idx"),
        ),
        migrations.RunPython(seed_roles_and_backfill, reverse_backfill),
    ]
