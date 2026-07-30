from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .events import KNOWN_EVENT_TYPES
from .exceptions import VibesMeetValidationError
from .signing import verify_signature


@dataclass(frozen=True)
class WebhookEnvelope:
    event_id: str
    event_type: str
    occurred_at: str
    sequence: int
    resource_type: str
    resource_id: str
    resource_version: str
    data: dict[str, Any]
    partner_reference: dict[str, Any]
    environment: str


def parse_verified_webhook(
    *,
    raw_body: bytes,
    timestamp: str,
    signature: str,
    secret: str,
    tolerance_seconds: int = 300,
) -> WebhookEnvelope:
    verify_signature(
        secret=secret,
        timestamp=timestamp,
        body=raw_body,
        supplied_signature=signature,
        tolerance_seconds=tolerance_seconds,
    )
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VibesMeetValidationError("Webhook body is not valid JSON.") from exc

    resource = payload.get("resource") or {}
    required = {
        "id": payload.get("id"),
        "type": payload.get("type"),
        "occurred_at": payload.get("occurred_at"),
        "resource.type": resource.get("type"),
        "resource.id": resource.get("id"),
    }
    missing = [name for name, value in required.items() if value in (None, "")]
    if missing:
        raise VibesMeetValidationError(f"Webhook is missing: {', '.join(missing)}")
    event_type = str(payload["type"])
    if event_type not in KNOWN_EVENT_TYPES:
        # Unknown events are valid integration input but must be quarantined until handled.
        event_type = f"unknown:{event_type}"[:160]

    try:
        sequence = int(payload.get("sequence", 0))
    except (TypeError, ValueError) as exc:
        raise VibesMeetValidationError("Webhook sequence must be an integer.") from exc

    return WebhookEnvelope(
        event_id=str(payload["id"]),
        event_type=event_type,
        occurred_at=str(payload["occurred_at"]),
        sequence=sequence,
        resource_type=str(resource["type"]),
        resource_id=str(resource["id"]),
        resource_version=str(resource.get("version", "")),
        data=payload.get("data") or {},
        partner_reference=payload.get("partner_reference") or {},
        environment=str(payload.get("environment", "")),
    )
