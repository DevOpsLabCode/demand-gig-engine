# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Synchronizes social-account identity data into the application profile while preserving local ownership rules.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Synchronizes social-account identity data into the application profile while preserving local ownership rules.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.urls import NoReverseMatch, reverse


@dataclass(frozen=True)
class SocialProvider:
    """
    Describe one supported social-login provider and its required configuration.
    """
    id: str
    label: str
    icon: str
    credential_names: tuple[str, str]


PROVIDERS = (
    SocialProvider("google", "Google", "google", ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET")),
    SocialProvider("facebook", "Facebook", "facebook", ("FACEBOOK_OAUTH_CLIENT_ID", "FACEBOOK_OAUTH_CLIENT_SECRET")),
    SocialProvider("instagram", "Instagram", "instagram", ("INSTAGRAM_OAUTH_CLIENT_ID", "INSTAGRAM_OAUTH_CLIENT_SECRET")),
    SocialProvider("tiktok", "TikTok", "tiktok", ("TIKTOK_OAUTH_CLIENT_KEY", "TIKTOK_OAUTH_CLIENT_SECRET")),
)


def provider_enabled(provider_id: str) -> bool:
    """
    Return whether a social provider has credentials and a resolvable django-allauth login route.
    
    Args:
        provider_id: Stable identifier of the requested social provider.
    
    Returns:
        True when the documented condition is satisfied; otherwise False.
    """
    # Reject unknown social-provider identifiers before resolving routes or exposing configuration.
    if provider_id not in settings.SOCIAL_AUTH_ALLOWED_PROVIDERS:
        return False
    config: dict[str, Any] = settings.SOCIALACCOUNT_PROVIDERS.get(provider_id, {})
    app = config.get("APP", {})
    return bool(app.get("client_id") and app.get("secret"))


def provider_login_path(provider_id: str) -> str:
    """
    Resolve the django-allauth login URL for one supported provider.
    
    Args:
        provider_id: Stable identifier of the requested social provider.
    
    Returns:
        The normalized, resolved, or provider-supplied string described above.
    """
    # Treat a missing django-allauth URL as a disabled provider instead of crashing configuration discovery.
    try:
        return reverse(f"{provider_id}_login")
    except NoReverseMatch:
        return ""


def provider_payload() -> list[dict[str, Any]]:
    """
    Build the frontend provider list with labels, routes, availability, and required configuration.
    
    Returns:
        The frontend-ready list of social providers and their availability state.
    """
    payload = []
    # Process each `provider` from `PROVIDERS` in a deterministic order.
    for provider in PROVIDERS:
        login_url = provider_login_path(provider.id)
        payload.append(
            {
                "id": provider.id,
                "label": provider.label,
                "icon": provider.icon,
                "enabled": provider_enabled(provider.id) and bool(login_url),
                "login_url": login_url,
                "callback_path": f"/accounts/{provider.id}/login/callback/",
            }
        )
    return payload


def extract_avatar(extra_data: dict[str, Any]) -> str:
    """
    Normalize avatar URLs from the different payload shapes returned by social providers.
    
    Args:
        extra_data: Provider-specific social-account payload used to synchronize local profile fields.
    
    Returns:
        The normalized avatar URL, or an empty string when none is available.
    """
    picture = extra_data.get("picture") or extra_data.get("avatar_url") or extra_data.get("avatar")
    # Accept providers that return the avatar directly as a URL string.
    if isinstance(picture, str):
        return picture
    # Handle providers that wrap avatar information in a nested object.
    if isinstance(picture, dict):
        data = picture.get("data", picture)
        # Read the nested avatar URL only when the provider returned the expected object shape.
        if isinstance(data, dict):
            return str(data.get("url", ""))
    return ""
