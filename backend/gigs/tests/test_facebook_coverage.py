# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Covers Meta Graph success, validation, pagination, provider errors, conversion events, and failure boundaries not exercised by the primary Facebook tests.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Covers Meta Graph success, validation, pagination, provider errors, conversion events, and failure boundaries not exercised by the primary Facebook tests.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

import hashlib
import io
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase, override_settings

from gigs import facebook
from gigs.facebook import MetaAPIError


class FacebookIntegrationCoverageTests(SimpleTestCase):
    """
    Exercise FacebookIntegrationCoverage behavior, edge cases, and failure handling with isolated tests.
    """
    @staticmethod
    def response(payload):
        """
        Build a lightweight HTTP response double with the requested payload and status code.
        
        Args:
            payload: Structured event or webhook data being validated or persisted.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(payload).encode("utf-8")
        return response

    @override_settings(META_GRAPH_API_VERSION="/v25.0/")
    def test_graph_url_normalizes_slashes(self):
        """
        Verify that graph URL normalizes slashes.
        """
        self.assertEqual(
            facebook._graph_url("/me"),
            "https://graph.facebook.com/v25.0/me",
        )

    def test_request_json_get_and_post(self):
        """
        Verify that request json get and post.
        """
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(facebook, "urlopen", return_value=self.response({"ok": True})) as mocked:
            self.assertEqual(
                facebook._request_json("me", params={"a": "1", "empty": "", "none": None}),
                {"ok": True},
            )
            request = mocked.call_args.args[0]
            self.assertEqual(request.get_method(), "GET")
            self.assertIn("a=1", request.full_url)
            self.assertNotIn("empty", request.full_url)

        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(facebook, "urlopen", return_value=self.response({"id": "post-1"})) as mocked:
            self.assertEqual(
                facebook._request_json("page/feed", params={"message": "hello"}, method="post"),
                {"id": "post-1"},
            )
            request = mocked.call_args.args[0]
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.headers["Content-type"], "application/x-www-form-urlencoded")
            self.assertEqual(request.data, b"message=hello")

    def test_request_json_maps_transport_and_payload_errors(self):
        """
        Verify that request json maps transport and payload errors.
        """
        http_error = HTTPError(
            "https://graph.facebook.com",
            400,
            "bad",
            {},
            io.BytesIO(b'{"error":"invalid"}'),
        )
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(facebook, "urlopen", side_effect=http_error):
            # Enter the context manager to scope resources, transactions, or cleanup to this block.
            with self.assertRaisesRegex(MetaAPIError, "HTTP 400"):
                facebook._request_json("me", params={})

        # Process each `error` from `(URLError("offline"), TimeoutError("slow"))` in a deterministic
        # order.
        for error in (URLError("offline"), TimeoutError("slow")):
            # Enter the context manager to scope resources, transactions, or cleanup to this block.
            with self.subTest(error=type(error).__name__), patch.object(facebook, "urlopen", side_effect=error):
                # Enter the context manager to scope resources, transactions, or cleanup to this
                # block.
                with self.assertRaisesRegex(MetaAPIError, "request failed"):
                    facebook._request_json("me", params={})

        invalid = MagicMock()
        invalid.__enter__.return_value = invalid
        invalid.read.return_value = b"not-json"
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(facebook, "urlopen", return_value=invalid):
            # Enter the context manager to scope resources, transactions, or cleanup to this block.
            with self.assertRaisesRegex(MetaAPIError, "request failed"):
                facebook._request_json("me", params={})

        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(
            facebook,
            "urlopen",
            return_value=self.response({"error": {"message": "Denied"}}),
        ):
            # Enter the context manager to scope resources, transactions, or cleanup to this block.
            with self.assertRaisesRegex(MetaAPIError, "Denied"):
                facebook._request_json("me", params={})

        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(facebook, "urlopen", return_value=self.response({"error": {}})):
            # Enter the context manager to scope resources, transactions, or cleanup to this block.
            with self.assertRaisesRegex(MetaAPIError, "Unknown Meta API error"):
                facebook._request_json("me", params={})

    @override_settings(PUBLIC_BASE_URL="https://example.com/", META_APP_ID="")
    def test_share_link_without_app_id(self):
        """
        Verify that share link without app ID.
        """
        result = facebook.build_campaign_share_link("gig")
        self.assertEqual(
            result.campaign_url,
            "https://example.com/share/campaign/gig/?source=facebook_group&group=&ref=",
        )
        self.assertNotIn("app_id", result.share_dialog_url)

    @override_settings(META_APP_ID="", META_APP_SECRET="")
    def test_verify_user_requires_app_configuration(self):
        """
        Verify that verify user requires app configuration.
        """
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with self.assertRaisesRegex(MetaAPIError, "must be configured"):
            facebook.verify_facebook_user("token")

    @override_settings(META_APP_ID="app", META_APP_SECRET="secret")
    def test_verify_user_rejects_invalid_or_wrong_app_token(self):
        """
        Verify that verify user rejects invalid or wrong app token.
        """
        # Process each `debug` from `({"is_valid": False, "app_id": "app"}, {"is_valid": True,
        # "app_id":...` in a deterministic order.
        for debug in ({"is_valid": False, "app_id": "app"}, {"is_valid": True, "app_id": "other"}):
            # Enter the context manager to scope resources, transactions, or cleanup to this block.
            with self.subTest(debug=debug), patch.object(
                facebook,
                "_request_json",
                return_value={"data": debug},
            ):
                # Enter the context manager to scope resources, transactions, or cleanup to this
                # block.
                with self.assertRaisesRegex(MetaAPIError, "invalid or belongs"):
                    facebook.verify_facebook_user("token")

    @override_settings(META_APP_ID="123", META_APP_SECRET="secret")
    def test_verify_user_returns_normalized_profile(self):
        """
        Verify that verify user returns normalized profile.
        """
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(
            facebook,
            "_request_json",
            side_effect=[
                {"data": {"is_valid": True, "app_id": 123, "expires_at": 99}},
                {
                    "id": "u1",
                    "name": "Fan",
                    "picture": {"data": {"url": "https://img"}},
                },
            ],
        ):
            self.assertEqual(
                facebook.verify_facebook_user("token"),
                {
                    "id": "u1",
                    "name": "Fan",
                    "email": "",
                    "picture_url": "https://img",
                    "token_expires_at": 99,
                },
            )

    def test_list_pages_and_publish(self):
        """
        Verify that list pages and publish.
        """
        payload = {
            "data": [
                {
                    "id": "p1",
                    "name": "Page",
                    "category": "Music",
                    "tasks": ["CREATE_CONTENT"],
                    "access_token": "secret",
                    "picture": {"data": {"url": "https://img"}},
                },
                {"id": "p2", "name": "Bare Page"},
            ]
        }
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(facebook, "_request_json", return_value=payload) as mocked:
            pages = facebook.list_managed_pages("user-token")
        self.assertEqual(pages[0]["picture_url"], "https://img")
        self.assertEqual(pages[1]["category"], "")
        self.assertEqual(pages[1]["tasks"], [])
        self.assertEqual(pages[1]["page_access_token"], "")
        mocked.assert_called_once()

        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(facebook, "_request_json", return_value={"id": "post"}) as mocked:
            result = facebook.publish_campaign_to_page(
                page_id="p1",
                page_access_token="page-token",
                message="Join us",
                link="https://example.com/gig",
            )
        self.assertEqual(result, {"id": "post"})
        self.assertEqual(mocked.call_args.kwargs["method"], "POST")
        self.assertEqual(mocked.call_args.args[0], "p1/feed")

    def test_sha256_normalizes_email(self):
        """
        Verify that sha256 normalizes email.
        """
        expected = hashlib.sha256(b"fan@example.com").hexdigest()
        self.assertEqual(facebook._sha256("  FAN@EXAMPLE.COM "), expected)

    @override_settings(META_PIXEL_ID="", META_CONVERSIONS_API_TOKEN="")
    def test_conversion_event_is_optional(self):
        """
        Verify that conversion event is optional.
        """
        self.assertIsNone(
            facebook.send_conversion_event(
                event_name="Lead",
                event_id="e1",
                event_source_url="https://example.com",
            )
        )

    @override_settings(
        META_PIXEL_ID="pixel",
        META_CONVERSIONS_API_TOKEN="token",
        META_TEST_EVENT_CODE="TEST123",
    )
    def test_conversion_event_builds_complete_payload(self):
        """
        Verify that conversion event builds complete payload.
        """
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(facebook.time, "time", return_value=1234), patch.object(
            facebook,
            "_request_json",
            return_value={"events_received": 1},
        ) as mocked:
            result = facebook.send_conversion_event(
                event_name="Purchase",
                event_id="e1",
                event_source_url="https://example.com/gig",
                email="Fan@Example.com",
                value=Decimal("25.50"),
                currency="usd",
                custom_data={"campaign": "gig"},
                action_source="website",
            )
        self.assertEqual(result, {"events_received": 1})
        path = mocked.call_args.args[0]
        params = mocked.call_args.kwargs["params"]
        event = json.loads(params["data"])[0]
        self.assertEqual(path, "pixel/events")
        self.assertEqual(event["event_time"], 1234)
        self.assertEqual(event["user_data"]["em"], [facebook._sha256("Fan@Example.com")])
        self.assertEqual(event["custom_data"], {"campaign": "gig", "value": 25.5, "currency": "USD"})
        self.assertEqual(params["test_event_code"], "TEST123")

    @override_settings(
        META_PIXEL_ID="pixel",
        META_CONVERSIONS_API_TOKEN="token",
        META_TEST_EVENT_CODE="",
    )
    def test_conversion_event_without_optional_user_or_value_data(self):
        """
        Verify that conversion event without optional user or value data.
        """
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with patch.object(facebook, "_request_json", return_value={}) as mocked:
            facebook.send_conversion_event(
                event_name="Lead",
                event_id="e2",
                event_source_url="https://example.com/gig",
            )
        params = mocked.call_args.kwargs["params"]
        event = json.loads(params["data"])[0]
        self.assertEqual(event["user_data"], {})
        self.assertEqual(event["custom_data"], {})
        self.assertNotIn("test_event_code", params)
