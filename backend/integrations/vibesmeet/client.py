from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .exceptions import VibesMeetAuthError, VibesMeetRemoteError, VibesMeetValidationError
from .types import EventHandoff


@dataclass(frozen=True)
class VibesMeetConfig:
    base_url: str
    access_token: str
    timeout_seconds: float = 15.0
    user_agent: str = "DemandGigEngine-VibesMeetBridge/0.1"

    def validate(self) -> None:
        if not self.base_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise VibesMeetValidationError("VibesMeet base URL must use HTTPS outside local development.")
        if not self.access_token:
            raise VibesMeetAuthError("VibesMeet access token is not configured.")
        if self.timeout_seconds <= 0:
            raise VibesMeetValidationError("Timeout must be greater than zero.")


class VibesMeetClient:
    """Small dependency-free HTTP client for the proposed partner contract.

    Endpoint paths are intentionally isolated in this class so they can be
    changed after VibesMeet confirms its private API contract.
    """

    def __init__(self, config: VibesMeetConfig):
        config.validate()
        self.config = config

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/v1/partner/health")

    def capabilities(self) -> dict[str, Any]:
        return self._request("GET", "/v1/partner/capabilities")

    def create_draft_event(
        self,
        handoff: EventHandoff,
        *,
        idempotency_key: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/partner/events/drafts",
            payload=handoff.to_dict(),
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    def update_event(
        self,
        event_id: str,
        patch: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        if not event_id:
            raise VibesMeetValidationError("Event ID is required.")
        return self._request(
            "PATCH",
            f"/v1/partner/events/{event_id}",
            payload=patch,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    def create_reservation_claims(
        self,
        event_id: str,
        claims: list[dict[str, Any]],
        *,
        idempotency_key: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/partner/events/{event_id}/reservation-claims:batchCreate",
            payload={"claims": claims},
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    def request_publish(
        self,
        event_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/partner/events/{event_id}/publish-requests",
            payload={},
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    def get_event(self, event_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/partner/events/{event_id}")

    def attendance_summary(self, event_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/partner/events/{event_id}/attendance/summary")

    def order_summary(self, event_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/partner/events/{event_id}/orders/summary")

    def payout_summary(self, event_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/partner/events/{event_id}/payouts/summary")

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        if query:
            path = f"{path}?{urlencode(query)}"
        url = f"{self.config.base_url.rstrip('/')}{path}"
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config.access_token}",
            "User-Agent": self.config.user_agent,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id

        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read()
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            raw = exc.read()
            decoded: object
            try:
                decoded = json.loads(raw.decode("utf-8")) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                decoded = raw.decode("utf-8", errors="replace")
            if exc.code in (401, 403):
                raise VibesMeetAuthError(f"VibesMeet authorization failed ({exc.code}).") from exc
            raise VibesMeetRemoteError(
                f"VibesMeet request failed ({exc.code}).",
                status_code=exc.code,
                body=decoded,
            ) from exc
        except (URLError, socket.timeout, TimeoutError) as exc:
            raise VibesMeetRemoteError("VibesMeet request could not be completed.") from exc
        except json.JSONDecodeError as exc:
            raise VibesMeetRemoteError("VibesMeet returned invalid JSON.") from exc
