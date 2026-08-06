# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Creates profiles, assigns the fan role, mirrors legacy account types, and synchronizes trusted social profile data.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""Django and social-authentication signal handlers for profile and role state."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import GigUserProfile
from .role_models import (
    Role,
    RoleAuditEvent,
    RoleCode,
    RoleVerificationStatus,
    UserRole,
)
from .social_auth import extract_avatar


LEGACY_ACCOUNT_ROLE_MAP = {
    "fan": RoleCode.FAN,
    "band": RoleCode.ARTIST,
    "venue": RoleCode.VENUE,
    "organizer": RoleCode.ORGANIZER,
    "rental": RoleCode.EQUIPMENT_RENTAL,
    "sponsor": RoleCode.SPONSOR,
}

ROLE_DEFAULTS = {
    RoleCode.FAN: ("Fan", "Support, reserve, vote, and share campaigns.", False),
    RoleCode.ARTIST: ("Artist", "Represent an artist or performing act.", True),
    RoleCode.VENUE: ("Venue", "Represent a performance venue or space.", True),
    RoleCode.ORGANIZER: ("Organizer", "Create and coordinate demand-driven events.", True),
    RoleCode.SPONSOR: ("Sponsor", "Support campaigns and event production.", True),
    RoleCode.VENDOR: ("Vendor", "Provide event-related professional services.", True),
    RoleCode.EQUIPMENT_RENTAL: (
        "Equipment rental",
        "Provide sound, lighting, staging, or rental inventory.",
        True,
    ),
    RoleCode.ADMINISTRATOR: (
        "Administrator",
        "Review role and platform approval requests.",
        True,
    ),
}


def _role(code: str) -> Role:
    """Return a seeded role, creating the stable definition only when required."""

    display_name, description, requires_verification = ROLE_DEFAULTS[code]
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={
            "display_name": display_name,
            "description": description,
            "requires_verification": requires_verification,
            "active": True,
        },
    )
    return role


def _ensure_assignment(profile: GigUserProfile, code: str) -> None:
    """Create one idempotent role assignment derived from trusted profile state."""

    role = _role(code)
    assignment, created = UserRole.objects.get_or_create(
        user=profile.user,
        role=role,
        defaults={
            "organization_name": profile.company_name if code != RoleCode.FAN else "",
            "profile_data": {},
            "verification_status": (
                RoleVerificationStatus.VERIFIED
                if code == RoleCode.FAN
                else RoleVerificationStatus.PENDING
            ),
        },
    )
    if created:
        RoleAuditEvent.objects.create(
            assignment=assignment,
            actor=profile.user,
            event_type="role_assigned" if code == RoleCode.FAN else "legacy_role_requested",
            payload={"source_account_type": profile.account_type},
        )


@receiver(post_save, sender=get_user_model())
def ensure_gig_profile(sender, instance, created, **kwargs):
    """Create the application profile whenever a Django user is created."""

    if created:
        GigUserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=GigUserProfile)
def synchronize_profile_roles(sender, instance, **kwargs):
    """Assign fan automatically and mirror the temporary account_type field safely."""

    try:
        _ensure_assignment(instance, RoleCode.FAN)
        role_code = LEGACY_ACCOUNT_ROLE_MAP.get(instance.account_type, RoleCode.FAN)
        if role_code != RoleCode.FAN:
            _ensure_assignment(instance, role_code)
    except DatabaseError:
        return


def _synchronize_profile(user, extra):
    """Copy trusted social-account details into the local profile."""

    profile, _ = GigUserProfile.objects.get_or_create(user=user)
    changed = []
    avatar = extract_avatar(extra)
    if avatar and avatar != profile.avatar_url:
        profile.avatar_url = avatar
        changed.append("avatar_url")
    display_name = extra.get("name") or extra.get("display_name") or user.get_full_name()
    if display_name and str(display_name) != profile.display_name:
        profile.display_name = str(display_name)[:160]
        changed.append("display_name")
    if changed:
        changed.append("updated_at")
        profile.save(update_fields=changed)


try:
    from allauth.account.signals import user_signed_up
    from allauth.socialaccount.signals import social_account_added, social_account_updated
except ImportError:  # pragma: no cover - installed in runtime environments
    user_signed_up = social_account_added = social_account_updated = None


if user_signed_up is not None:

    @receiver(user_signed_up)
    def synchronize_new_social_profile(request, user, sociallogin=None, **kwargs):
        """Populate the local profile from trusted social data after sign-up."""

        if sociallogin is not None:
            _synchronize_profile(user, sociallogin.account.extra_data or {})

    @receiver([social_account_added, social_account_updated])
    def synchronize_existing_social_profile(request, sociallogin, **kwargs):
        """Refresh the local profile when a linked social account changes."""

        _synchronize_profile(sociallogin.user, sociallogin.account.extra_data or {})
