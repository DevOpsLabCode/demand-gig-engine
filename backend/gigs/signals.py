# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Responds to Django and social-authentication signals to create or update related application profile data.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Responds to Django and social-authentication signals to create or update related application profile data.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import GigUserProfile
from .social_auth import extract_avatar


@receiver(post_save, sender=get_user_model())
def ensure_gig_profile(sender, instance, created, **kwargs):
    """
    Create the application-specific profile whenever a Django user is created.
    
    Args:
        sender: Django signal sender that triggered this receiver.
        instance: Model instance created or updated by the signal.
        created: True when Django created the model instance during this operation.
        **kwargs: Additional keyword arguments forwarded to the underlying implementation.
    """
    # Initialize defaults only for a newly created record so reruns remain idempotent.
    if created:
        GigUserProfile.objects.get_or_create(user=instance)


def _synchronize_profile(user, extra):
    """
    Copy trusted social-account details such as avatar and display name into the local profile.
    
    Args:
        user: Authenticated or newly created Django user whose profile is being processed.
        extra: Additional structured data included with the webhook or integration event.
    """
    profile, _ = GigUserProfile.objects.get_or_create(user=user)
    changed = []
    avatar = extract_avatar(extra)
    # Write the provider avatar only when it is present and different, avoiding unnecessary database updates.
    if avatar and avatar != profile.avatar_url:
        profile.avatar_url = avatar
        changed.append("avatar_url")
    display_name = extra.get("name") or extra.get("display_name") or user.get_full_name()
    # Synchronize a changed provider display name while respecting the model length limit.
    if display_name and str(display_name) != profile.display_name:
        profile.display_name = str(display_name)[:160]
        changed.append("display_name")
    # Persist only fields that actually changed and update the profile timestamp in the same write.
    if changed:
        changed.append("updated_at")
        profile.save(update_fields=changed)


# Allow dependency-free tooling to import this module even when django-allauth is not installed locally.
try:
    from allauth.account.signals import user_signed_up
    from allauth.socialaccount.signals import social_account_added, social_account_updated
except ImportError:  # pragma: no cover - dependency is installed in runtime environments
    user_signed_up = social_account_added = social_account_updated = None


# Register allauth receivers only when django-allauth is installed in the current runtime.
if user_signed_up is not None:

    @receiver(user_signed_up)
    def synchronize_new_social_profile(request, user, sociallogin=None, **kwargs):
        """
        Populate the local user profile from trusted social-account data immediately after sign-up.
        
        Args:
            request: Incoming Django/DRF request, including the authenticated user and payload.
            user: Authenticated or newly created Django user whose profile is being processed.
            sociallogin: django-allauth social-login object containing the provider account and extra data.
            **kwargs: Additional keyword arguments forwarded to the underlying implementation.
        """
        # Synchronize provider data only when the signup signal includes a social-login account.
        if sociallogin is not None:
            _synchronize_profile(user, sociallogin.account.extra_data or {})

    @receiver([social_account_added, social_account_updated])
    def synchronize_existing_social_profile(request, sociallogin, **kwargs):
        """
        Refresh the local profile when a linked social account is added or updated.
        
        Args:
            request: Incoming Django/DRF request, including the authenticated user and payload.
            sociallogin: django-allauth social-login object containing the provider account and extra data.
            **kwargs: Additional keyword arguments forwarded to the underlying implementation.
        """
        _synchronize_profile(sociallogin.user, sociallogin.account.extra_data or {})
