from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.urls import NoReverseMatch, reverse


@dataclass(frozen=True)
class SocialProvider:
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
    if provider_id not in settings.SOCIAL_AUTH_ALLOWED_PROVIDERS:
        return False
    config: dict[str, Any] = settings.SOCIALACCOUNT_PROVIDERS.get(provider_id, {})
    app = config.get("APP", {})
    return bool(app.get("client_id") and app.get("secret"))


def provider_login_path(provider_id: str) -> str:
    try:
        return reverse(f"{provider_id}_login")
    except NoReverseMatch:
        return ""


def provider_payload() -> list[dict[str, Any]]:
    payload = []
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
    picture = extra_data.get("picture") or extra_data.get("avatar_url") or extra_data.get("avatar")
    if isinstance(picture, str):
        return picture
    if isinstance(picture, dict):
        data = picture.get("data", picture)
        if isinstance(data, dict):
            return str(data.get("url", ""))
    return ""
