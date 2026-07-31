# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Implements the signed, idempotent HTTP client used to exchange event, reservation, order, attendance, and payout data with VibesMeet.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Implements the signed, idempotent HTTP client used to exchange event, reservation, order, attendance, and payout data with VibesMeet.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

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
    """
    Hold and validate connection settings for the optional VibesMeet bridge.
    """
    base_url: str
    access_token: str
    timeout_seconds: float = 15.0
    user_agent: str = "DemandGigEngine-VibesMeetBridge/0.1"

    def validate(self) -> None:
        """
        Validate the bridge base URL, credentials, timeout, and webhook secret before use.
        
        Raises:
            VibesMeetAuthError: When the documented validation or integration precondition fails.
            VibesMeetValidationError: When the documented validation or integration precondition fails.
        """
        # Require HTTPS for remote bridge URLs while permitting loopback HTTP during local development.
        if not self.base_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise VibesMeetValidationError("VibesMeet base URL must use HTTPS outside local development.")
        # Require a bridge access token before any authenticated VibesMeet request can be made.
        if not self.access_token:
            raise VibesMeetAuthError("VibesMeet access token is not configured.")
        # Reject non-positive HTTP timeouts that would make request behavior undefined.
        if self.timeout_seconds <= 0:
            raise VibesMeetValidationError("Timeout must be greater than zero.")


class VibesMeetClient:
    """
    Encapsulate authenticated HTTP communication with the VibesMeet partner API.

    Endpoint paths are intentionally isolated in this class so they can be
    changed after VibesMeet confirms its private API contract.
    """

    def __init__(self, config: VibesMeetConfig):
        """
        Store validated bridge configuration and prepare the reusable HTTP client boundary.
        
        Args:
            config: Validated integration configuration used to build the client.
        """
        config.validate()
        self.config = config

    def health(self) -> dict[str, Any]:
        """
        Read the remote VibesMeet health endpoint.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
        return self._request("GET", "/v1/partner/health")

    def capabilities(self) -> dict[str, Any]:
        """
        Discover which integration capabilities the connected VibesMeet tenant exposes.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
        return self._request("GET", "/v1/partner/capabilities")

    def create_draft_event(
        self,
        handoff: EventHandoff,
        *,
        idempotency_key: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Create a VibesMeet draft event from the validated demand-campaign handoff contract.
        
        Args:
            handoff: Validated event handoff object being sent to VibesMeet.
            idempotency_key: Caller-supplied key that makes retries safe and prevents duplicate side effects.
            correlation_id: Trace identifier propagated across local and remote logs.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
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
        """
        Update a previously linked VibesMeet event with an idempotent request.
        
        Args:
            event_id: Provider event identifier used for deduplication and audit correlation.
            patch: Partial event fields to apply to an existing VibesMeet event.
            idempotency_key: Caller-supplied key that makes retries safe and prevents duplicate side effects.
            correlation_id: Trace identifier propagated across local and remote logs.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        
        Raises:
            VibesMeetValidationError: When the documented validation or integration precondition fails.
        """
        # Require the remote event identifier before attempting an update.
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
        """
        Send supporter reservation claims to the linked VibesMeet event.
        
        Args:
            event_id: Provider event identifier used for deduplication and audit correlation.
            claims: Validated supporter reservation claims being synchronized.
            idempotency_key: Caller-supplied key that makes retries safe and prevents duplicate side effects.
            correlation_id: Trace identifier propagated across local and remote logs.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
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
        """
        Ask VibesMeet to publish an event after local confirmation requirements are met.
        
        Args:
            event_id: Provider event identifier used for deduplication and audit correlation.
            idempotency_key: Caller-supplied key that makes retries safe and prevents duplicate side effects.
            correlation_id: Trace identifier propagated across local and remote logs.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
        return self._request(
            "POST",
            f"/v1/partner/events/{event_id}/publish-requests",
            payload={},
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    def get_event(self, event_id: str) -> dict[str, Any]:
        """
        Fetch the current remote event representation.
        
        Args:
            event_id: Provider event identifier used for deduplication and audit correlation.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
        return self._request("GET", f"/v1/partner/events/{event_id}")

    def attendance_summary(self, event_id: str) -> dict[str, Any]:
        """
        Fetch aggregated attendance data for reconciliation and reporting.
        
        Args:
            event_id: Provider event identifier used for deduplication and audit correlation.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
        return self._request("GET", f"/v1/partner/events/{event_id}/attendance/summary")

    def order_summary(self, event_id: str) -> dict[str, Any]:
        """
        Fetch aggregated order data for reconciliation and reporting.
        
        Args:
            event_id: Provider event identifier used for deduplication and audit correlation.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
        return self._request("GET", f"/v1/partner/events/{event_id}/orders/summary")

    def payout_summary(self, event_id: str) -> dict[str, Any]:
        """
        Fetch aggregated payout data for reconciliation and reporting.
        
        Args:
            event_id: Provider event identifier used for deduplication and audit correlation.
        
        Returns:
            A JSON-compatible dictionary containing the normalized result.
        """
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
        """
        Send one authenticated VibesMeet request with correlation, idempotency, timeout, and controlled error mapping.
        
        Args:
            method: HTTP method used for the outbound integration request.
            path: Relative API path appended to the configured service base URL.
            payload: Structured event or webhook data being validated or persisted.
            query: Optional query-string parameters for the outbound request.
            idempotency_key: Caller-supplied key that makes retries safe and prevents duplicate side effects.
            correlation_id: Trace identifier propagated across local and remote logs.
        
        Returns:
            The decoded JSON object returned by the remote endpoint.
        
        Raises:
            VibesMeetAuthError: When the documented validation or integration precondition fails.
            VibesMeetRemoteError: When the documented validation or integration precondition fails.
        """
        # Append encoded query parameters only when the caller supplied them.
        if query:
            path = f"{path}?{urlencode(query)}"
        url = f"{self.config.base_url.rstrip('/')}{path}"
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config.access_token}",
            "User-Agent": self.config.user_agent,
        }
        # Serialize a JSON request body only for operations that carry a payload.
        if body is not None:
            headers["Content-Type"] = "application/json"
        # Send an idempotency key for mutating calls so retries cannot create duplicate remote resources.
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        # Propagate the correlation ID so local and remote logs can be traced as one transaction.
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id

        request = Request(url, data=body, headers=headers, method=method)
        # Translate network failures, invalid JSON, and HTTP errors into typed VibesMeet exceptions with diagnostic context.
        try:
            # Enter the context manager to scope resources, transactions, or cleanup to this block.
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read()
                # Treat an empty successful response as an empty object instead of forcing JSON parsing.
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            raw = exc.read()
            decoded: object
            # Translate network failures, invalid JSON, and HTTP errors into typed VibesMeet exceptions with diagnostic context.
            try:
                decoded = json.loads(raw.decode("utf-8")) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                decoded = raw.decode("utf-8", errors="replace")
            # Map authorization failures separately so operators can distinguish credentials from remote service errors.
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
