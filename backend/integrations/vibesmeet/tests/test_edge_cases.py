from __future__ import annotations

import io
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import pytest

from integrations.vibesmeet.client import VibesMeetClient, VibesMeetConfig
from integrations.vibesmeet.exceptions import (
    VibesMeetAuthError,
    VibesMeetRemoteError,
    VibesMeetValidationError,
)
from integrations.vibesmeet.signing import build_signature, verify_signature
from integrations.vibesmeet.types import (
    EventHandoff,
    ReservationClaim,
    RevenueSplit,
    TicketTypePlan,
)
from integrations.vibesmeet.webhooks import parse_verified_webhook


def valid_ticket(**overrides):
    data = dict(code="ga", name="General", price=Decimal("10"), currency="USD", inventory=10)
    data.update(overrides)
    return TicketTypePlan(**data)


def valid_handoff(**overrides):
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    data = dict(
        campaign_id="c1", campaign_version="1", organizer_external_id="o1",
        title="Gig", description="Desc", timezone="UTC", starts_at=start,
        ends_at=start + timedelta(hours=2), venue={}, artists=[], capacity=10,
        currency="usd", ticket_types=[valid_ticket()],
    )
    data.update(overrides)
    return EventHandoff(**data)


@pytest.mark.parametrize("kwargs", [
    {"code": ""}, {"name": ""}, {"price": Decimal("-1")}, {"inventory": -1},
    {"reserved_for_supporters": -1}, {"inventory": 1, "reserved_for_supporters": 2},
    {"currency": "US"},
])
def test_ticket_validation_errors(kwargs):
    with pytest.raises(VibesMeetValidationError):
        valid_ticket(**kwargs).validate()


def test_ticket_serializes_dates_and_currency():
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    data = valid_ticket(price=Decimal("1.2"), currency="usd", sales_start=now, sales_end=now).to_dict()
    assert data["price"] == "1.20" and data["currency"] == "USD"
    assert data["sales_start"] == now.isoformat()


@pytest.mark.parametrize("kwargs", [
    {"reservation_id": ""}, {"supporter_email": ""}, {"quantity": 0},
    {"credit_amount": Decimal("-1")},
])
def test_reservation_validation_errors(kwargs):
    data = dict(reservation_id="r1", supporter_external_id=None, supporter_email="a@b.com",
                quantity=1, credit_amount=Decimal("1"), currency="usd")
    data.update(kwargs)
    with pytest.raises(VibesMeetValidationError):
        ReservationClaim(**data).validate()


def test_reservation_serialization_optional_dates():
    deadline = datetime(2030, 1, 1, tzinfo=timezone.utc)
    claim = ReservationClaim("r1", "u1", "a@b.com", 2, Decimal("2.5"), "usd", conversion_deadline=deadline)
    data = claim.to_dict()
    assert data["credit_amount"] == "2.50" and data["currency"] == "USD"
    assert data["conversion_deadline"] == deadline.isoformat()


@pytest.mark.parametrize("participant,bps", [("", 1), ("p", -1), ("p", 10001)])
def test_split_validation_errors(participant, bps):
    with pytest.raises(VibesMeetValidationError):
        RevenueSplit(participant, "artist", bps, "artist").validate()


def test_split_to_dict():
    assert RevenueSplit("p", "artist", 10000, "artist").to_dict()["basis_points"] == 10000


@pytest.mark.parametrize("overrides", [
    {"campaign_id": ""}, {"campaign_version": ""}, {"organizer_external_id": ""},
    {"title": ""}, {"timezone": ""},
    {"ends_at": datetime(2029, 1, 1, tzinfo=timezone.utc)}, {"capacity": 0}, {"ticket_types": []},
])
def test_handoff_validation_errors(overrides):
    with pytest.raises(VibesMeetValidationError):
        valid_handoff(**overrides).validate()


def test_handoff_rejects_bad_nested_values_and_split_total():
    with pytest.raises(VibesMeetValidationError):
        valid_handoff(ticket_types=[valid_ticket(price=Decimal("-1"))]).validate()
    bad_claim = ReservationClaim("", None, "a@b.com", 1, Decimal("0"), "USD")
    with pytest.raises(VibesMeetValidationError):
        valid_handoff(reservation_claims=[bad_claim]).validate()
    with pytest.raises(VibesMeetValidationError):
        valid_handoff(revenue_splits=[RevenueSplit("p", "artist", 9999, "artist")]).validate()


def test_handoff_full_serialization():
    split = RevenueSplit("p", "artist", 10000, "artist")
    data = valid_handoff(revenue_splits=[split], sponsor_opportunity={"x": 1}).to_dict()
    assert data["currency"] == "USD" and data["revenue_splits"][0]["basis_points"] == 10000


def test_signature_success_and_failures():
    body = b"{}"
    sig = build_signature("secret", 100, body)
    verify_signature(secret="secret", timestamp=100, body=body, supplied_signature="sha256=" + sig, now=100)
    with pytest.raises(VibesMeetAuthError): build_signature("", 100, body)
    with pytest.raises(VibesMeetAuthError): verify_signature(secret="s", timestamp="bad", body=body, supplied_signature="x", now=100)
    with pytest.raises(VibesMeetAuthError): verify_signature(secret="s", timestamp=1, body=body, supplied_signature="x", now=1000)
    with pytest.raises(VibesMeetAuthError): verify_signature(secret="s", timestamp=100, body=body, supplied_signature="", now=100)


def signed_payload(payload):
    body = json.dumps(payload).encode()
    ts = "100"
    return body, ts, build_signature("s", ts, body)


def test_webhook_unknown_and_defaults():
    body, ts, sig = signed_payload({"id":"e","type":"future.event","occurred_at":"x","resource":{"type":"event","id":"r"}})
    with patch("integrations.vibesmeet.signing.time.time", return_value=100):
        env = parse_verified_webhook(raw_body=body, timestamp=ts, signature=sig, secret="s")
    assert env.event_type == "unknown:future.event" and env.sequence == 0 and env.data == {}


def test_webhook_validation_errors():
    body=b"not-json"; sig=build_signature("s",100,body)
    with patch("integrations.vibesmeet.signing.time.time", return_value=100), pytest.raises(VibesMeetValidationError):
        parse_verified_webhook(raw_body=body,timestamp="100",signature=sig,secret="s")
    for payload in ({}, {"id":"e","type":"x","occurred_at":"x","resource":{"type":"event","id":"r"},"sequence":"bad"}):
        body,ts,sig=signed_payload(payload)
        with patch("integrations.vibesmeet.signing.time.time", return_value=100), pytest.raises(VibesMeetValidationError):
            parse_verified_webhook(raw_body=body,timestamp=ts,signature=sig,secret="s")


@pytest.mark.parametrize("config", [
    VibesMeetConfig("http://example.com", "t"), VibesMeetConfig("https://x", ""), VibesMeetConfig("https://x", "t", 0),
])
def test_config_validation_errors(config):
    with pytest.raises((VibesMeetValidationError, VibesMeetAuthError)): config.validate()


def test_client_routes_and_request_success():
    client=VibesMeetClient(VibesMeetConfig("https://x", "t"))
    client._request=Mock(return_value={"ok":True})
    assert client.health()["ok"] and client.capabilities()["ok"]
    assert client.get_event("e")["ok"] and client.attendance_summary("e")["ok"]
    assert client.order_summary("e")["ok"] and client.payout_summary("e")["ok"]
    client.create_draft_event(valid_handoff(), idempotency_key="i", correlation_id="c")
    client.create_reservation_claims("e", [], idempotency_key="i", correlation_id="c")
    client.request_publish("e", idempotency_key="i", correlation_id="c")
    client.update_event("e", {}, idempotency_key="i", correlation_id="c")
    with pytest.raises(VibesMeetValidationError): client.update_event("", {}, idempotency_key="i", correlation_id="c")


def response(raw):
    obj=Mock(); obj.read.return_value=raw; obj.__enter__=Mock(return_value=obj); obj.__exit__=Mock(return_value=False); return obj


def test_low_level_request_success_empty_invalid_and_network():
    client=VibesMeetClient(VibesMeetConfig("https://x", "t"))
    with patch("integrations.vibesmeet.client.urlopen", return_value=response(b'{"ok":true}')):
        assert client._request("POST","/p",payload={"a":1},query={"q":"x"},idempotency_key="i",correlation_id="c")["ok"]
    with patch("integrations.vibesmeet.client.urlopen", return_value=response(b"")):
        assert client._request("GET","/p") == {}
    with patch("integrations.vibesmeet.client.urlopen", return_value=response(b"bad")), pytest.raises(VibesMeetRemoteError):
        client._request("GET","/p")
    with patch("integrations.vibesmeet.client.urlopen", side_effect=URLError("down")), pytest.raises(VibesMeetRemoteError):
        client._request("GET","/p")


@pytest.mark.parametrize("code,raw,exc", [(401,b'{}',VibesMeetAuthError),(403,b'{}',VibesMeetAuthError),(500,b'{"x":1}',VibesMeetRemoteError),(500,b'bad',VibesMeetRemoteError)])
def test_low_level_http_errors(code, raw, exc):
    client=VibesMeetClient(VibesMeetConfig("https://x", "t"))
    err=HTTPError("https://x",code,"bad",{},io.BytesIO(raw))
    with patch("integrations.vibesmeet.client.urlopen", side_effect=err), pytest.raises(exc):
        client._request("GET","/p")
