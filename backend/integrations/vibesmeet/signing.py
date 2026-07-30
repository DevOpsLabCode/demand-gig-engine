from __future__ import annotations

import hashlib
import hmac
import time

from .exceptions import VibesMeetAuthError


def build_signature(secret: str, timestamp: int | str, body: bytes) -> str:
    """Return a hex HMAC signature for ``<timestamp>.<raw-body>``."""
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
    """Validate webhook age and signature.

    Raises ``VibesMeetAuthError`` instead of returning false so callers cannot
    accidentally ignore a failed check.
    """
    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise VibesMeetAuthError("Invalid webhook timestamp.") from exc

    current = int(time.time()) if now is None else int(now)
    if abs(current - timestamp_int) > tolerance_seconds:
        raise VibesMeetAuthError("Webhook timestamp is outside the allowed tolerance.")

    expected = build_signature(secret, timestamp_int, body)
    normalized = supplied_signature.removeprefix("sha256=").strip().lower()
    if not normalized or not hmac.compare_digest(expected, normalized):
        raise VibesMeetAuthError("Invalid webhook signature.")
