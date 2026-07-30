from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import GigUserProfile
from .social_auth import extract_avatar


@receiver(post_save, sender=get_user_model())
def ensure_gig_profile(sender, instance, created, **kwargs):
    if created:
        GigUserProfile.objects.get_or_create(user=instance)


def _synchronize_profile(user, extra):
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
except ImportError:  # pragma: no cover - dependency is installed in runtime environments
    user_signed_up = social_account_added = social_account_updated = None


if user_signed_up is not None:

    @receiver(user_signed_up)
    def synchronize_new_social_profile(request, user, sociallogin=None, **kwargs):
        if sociallogin is not None:
            _synchronize_profile(user, sociallogin.account.extra_data or {})

    @receiver([social_account_added, social_account_updated])
    def synchronize_existing_social_profile(request, sociallogin, **kwargs):
        _synchronize_profile(sociallogin.user, sociallogin.account.extra_data or {})
