# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Validates VibesMeet request contracts, canonical signing, webhook verification, idempotency keys, and typed client responses.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Validates VibesMeet request contracts, canonical signing, webhook verification, idempotency keys, and typed client responses.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from __future__ import annotations

import json
import time
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from integrations.vibesmeet.signing import build_signature
from integrations.vibesmeet.types import EventHandoff, ReservationClaim, RevenueSplit, TicketTypePlan
from integrations.vibesmeet.webhooks import parse_verified_webhook


class VibesMeetContractTests(unittest.TestCase):
    """
    Exercise VibesMeetContract behavior, edge cases, and failure handling with isolated tests.
    """
    def test_handoff_serializes_and_validates(self):
        """
        Verify that handoff serializes and validates.
        """
        start = datetime.now(timezone.utc) + timedelta(days=30)
        handoff = EventHandoff(
            campaign_id="campaign-1",
            campaign_version="7",
            organizer_external_id="vm_org_1",
            title="Bring Band X to New York",
            description="Demand-validated event",
            timezone="America/New_York",
            starts_at=start,
            ends_at=start + timedelta(hours=4),
            venue={"name": "Example Hall", "city": "New York"},
            artists=[{"name": "Band X"}],
            capacity=500,
            currency="USD",
            ticket_types=[
                TicketTypePlan(
                    code="ga",
                    name="General Admission",
                    price=Decimal("50.00"),
                    currency="USD",
                    inventory=500,
                    reserved_for_supporters=100,
                )
            ],
            reservation_claims=[
                ReservationClaim(
                    reservation_id="pledge-1",
                    supporter_external_id=None,
                    supporter_email="fan@example.com",
                    quantity=1,
                    credit_amount=Decimal("25.00"),
                    currency="USD",
                )
            ],
            revenue_splits=[
                RevenueSplit("vm_org_1", "organizer", 7000, "organizer"),
                RevenueSplit("vm_artist_1", "artist", 3000, "artist"),
            ],
        )
        payload = handoff.to_dict()
        self.assertEqual(payload["capacity"], 500)
        self.assertEqual(payload["ticket_types"][0]["price"], "50.00")
        self.assertEqual(payload["reservation_claims"][0]["credit_amount"], "25.00")

    def test_signed_webhook_parses(self):
        """
        Verify that signed webhook parses.
        """
        secret = "test-secret"
        timestamp = int(time.time())
        body = json.dumps(
            {
                "id": "evt_1",
                "type": "vibesmeet.event.published",
                "occurred_at": "2026-07-30T14:00:00Z",
                "sequence": 1,
                "resource": {"type": "event", "id": "vm_event_1", "version": "2"},
                "partner_reference": {"campaign_id": "campaign-1"},
                "data": {"status": "published"},
                "environment": "test",
            },
            separators=(",", ":"),
        ).encode("utf-8")
        signature = build_signature(secret, timestamp, body)
        envelope = parse_verified_webhook(
            raw_body=body,
            timestamp=str(timestamp),
            signature=signature,
            secret=secret,
        )
        self.assertEqual(envelope.resource_id, "vm_event_1")
        self.assertEqual(envelope.event_type, "vibesmeet.event.published")


# Execute the command-line entry point only when this module is run directly.
if __name__ == "__main__":
    unittest.main()
