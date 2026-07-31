# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Builds and verifies HMAC signatures used to authenticate VibesMeet webhook and API payloads.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Builds and verifies HMAC signatures used to authenticate VibesMeet webhook and API payloads.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from __future__ import annotations

import hashlib
import hmac
import time

from .exceptions import VibesMeetAuthError


def build_signature(secret: str, timestamp: int | str, body: bytes) -> str:
    """Create the timestamped HMAC signature used to authenticate outbound webhook payloads."""
    # Refuse to sign or verify webhooks without a shared secret.
    if not secret:
        raise VibesMeetAuthError("Webhook secret is not configured.")
    timestamp_text = str(timestamp)
    message = timestamp_text.encode("utf-8") + b"." + body
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_signature(
    *,
    secret: str,
    timestamp: int | str,
    body: bytes,
    supplied_signature: str,
    tolerance_seconds: int = 300,
    now: int | None = None,
) -> None:
    """
    Validate timestamp freshness and compare the webhook HMAC in constant time.

    Raises ``VibesMeetAuthError`` instead of returning false so callers cannot
    accidentally ignore a failed check.
    """
    # Parse the timestamp and signature defensively before freshness and constant-time HMAC checks.
    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise VibesMeetAuthError("Invalid webhook timestamp.") from exc

    current = int(time.time()) if now is None else int(now)
    # Reject missing, stale, or tampered webhook signatures before parsing untrusted payload data.
    if abs(current - timestamp_int) > tolerance_seconds:
        raise VibesMeetAuthError("Webhook timestamp is outside the allowed tolerance.")

    expected = build_signature(secret, timestamp_int, body)
    normalized = supplied_signature.removeprefix("sha256=").strip().lower()
    # Reject missing, stale, or tampered webhook signatures before parsing untrusted payload data.
    if not normalized or not hmac.compare_digest(expected, normalized):
        raise VibesMeetAuthError("Invalid webhook signature.")
