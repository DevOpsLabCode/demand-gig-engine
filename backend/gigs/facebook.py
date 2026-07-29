from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class MetaAPIError(RuntimeError):
    """Raised when Meta returns a failed Graph API response."""


@dataclass(frozen=True)
class FacebookShareLink:
    campaign_url: str
    share_dialog_url: str


def _graph_url(path: str) -> str:
    version = settings.META_GRAPH_API_VERSION.strip("/")
    return f"https://graph.facebook.com/{version}/{path.lstrip('/')}"


def _request_json(path: str, *, params: dict[str, Any], method: str = "GET") -> dict[str, Any]:
    encoded = urlencode({key: value for key, value in params.items() if value not in (None, "")}).encode()
    if method.upper() == "GET":
        request = Request(f"{_graph_url(path)}?{encoded.decode()}", method="GET")
    else:
        request = Request(
            _graph_url(path),
            data=encoded,
            method=method.upper(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    try:
        with urlopen(request, timeout=12) as response:  # noqa: S310 - fixed Meta host
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MetaAPIError(f"Meta API returned HTTP {exc.code}: {detail[:500]}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise MetaAPIError(f"Meta API request failed: {exc}") from exc

    if "error" in payload:
        message = payload["error"].get("message", "Unknown Meta API error")
        raise MetaAPIError(message)
    return payload


def build_campaign_share_link(
    campaign_slug: str,
    *,
    source: str = "facebook_group",
    group_name: str = "",
    referral_code: str = "",
) -> FacebookShareLink:
    query = urlencode(
        {
            "source": source,
            "group": group_name,
            "ref": referral_code,
        }
    )
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    campaign_url = f"{base}/share/campaign/{campaign_slug}/?{query}"
    dialog_query = urlencode({"href": campaign_url, "display": "popup"})
    if settings.META_APP_ID:
        dialog_query += f"&app_id={settings.META_APP_ID}"
    return FacebookShareLink(
        campaign_url=campaign_url,
        share_dialog_url=f"https://www.facebook.com/dialog/share?{dialog_query}",
    )


def verify_facebook_user(access_token: str) -> dict[str, Any]:
    if not settings.META_APP_ID or not settings.META_APP_SECRET:
        raise MetaAPIError("META_APP_ID and META_APP_SECRET must be configured.")

    debug = _request_json(
        "debug_token",
        params={
            "input_token": access_token,
            "access_token": f"{settings.META_APP_ID}|{settings.META_APP_SECRET}",
        },
    ).get("data", {})
    if not debug.get("is_valid") or str(debug.get("app_id")) != str(settings.META_APP_ID):
        raise MetaAPIError("The Facebook access token is invalid or belongs to another app.")

    profile = _request_json(
        "me",
        params={
            "fields": "id,name,email,picture.width(160).height(160)",
            "access_token": access_token,
        },
    )
    return {
        "id": profile.get("id"),
        "name": profile.get("name"),
        "email": profile.get("email", ""),
        "picture_url": (((profile.get("picture") or {}).get("data") or {}).get("url", "")),
        "token_expires_at": debug.get("expires_at"),
    }


def list_managed_pages(user_access_token: str) -> list[dict[str, Any]]:
    payload = _request_json(
        "me/accounts",
        params={
            "fields": "id,name,access_token,tasks,category,picture.width(96).height(96)",
            "access_token": user_access_token,
            "limit": 100,
        },
    )
    pages = []
    for page in payload.get("data", []):
        pages.append(
            {
                "id": page.get("id"),
                "name": page.get("name"),
                "category": page.get("category", ""),
                "tasks": page.get("tasks", []),
                "page_access_token": page.get("access_token", ""),
                "picture_url": (((page.get("picture") or {}).get("data") or {}).get("url", "")),
            }
        )
    return pages


def publish_campaign_to_page(
    *,
    page_id: str,
    page_access_token: str,
    message: str,
    link: str,
) -> dict[str, Any]:
    return _request_json(
        f"{page_id}/feed",
        params={
            "message": message,
            "link": link,
            "published": "true",
            "access_token": page_access_token,
        },
        method="POST",
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def send_conversion_event(
    *,
    event_name: str,
    event_id: str,
    event_source_url: str,
    email: str = "",
    value: Decimal | float | str | None = None,
    currency: str = "USD",
    custom_data: dict[str, Any] | None = None,
    action_source: str = "website",
) -> dict[str, Any] | None:
    """Send a best-effort server event to Meta Conversions API.

    Returns None when the integration is not configured. Callers should not make
    core campaign behavior depend on advertising attribution availability.
    """
    if not settings.META_PIXEL_ID or not settings.META_CONVERSIONS_API_TOKEN:
        return None

    user_data: dict[str, Any] = {}
    if email:
        user_data["em"] = [_sha256(email)]

    event_custom_data = dict(custom_data or {})
    if value is not None:
        event_custom_data.update({"value": float(value), "currency": currency.upper()})

    event = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "event_id": event_id,
        "event_source_url": event_source_url,
        "action_source": action_source,
        "user_data": user_data,
        "custom_data": event_custom_data,
    }
    params: dict[str, Any] = {
        "data": json.dumps([event]),
        "access_token": settings.META_CONVERSIONS_API_TOKEN,
    }
    if settings.META_TEST_EVENT_CODE:
        params["test_event_code"] = settings.META_TEST_EVENT_CODE
    return _request_json(f"{settings.META_PIXEL_ID}/events", params=params, method="POST")
