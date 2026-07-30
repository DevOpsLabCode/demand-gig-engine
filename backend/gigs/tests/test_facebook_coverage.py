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
    @staticmethod
    def response(payload):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(payload).encode("utf-8")
        return response

    @override_settings(META_GRAPH_API_VERSION="/v25.0/")
    def test_graph_url_normalizes_slashes(self):
        self.assertEqual(
            facebook._graph_url("/me"),
            "https://graph.facebook.com/v25.0/me",
        )

    def test_request_json_get_and_post(self):
        with patch.object(facebook, "urlopen", return_value=self.response({"ok": True})) as mocked:
            self.assertEqual(
                facebook._request_json("me", params={"a": "1", "empty": "", "none": None}),
                {"ok": True},
            )
            request = mocked.call_args.args[0]
            self.assertEqual(request.get_method(), "GET")
            self.assertIn("a=1", request.full_url)
            self.assertNotIn("empty", request.full_url)

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
        http_error = HTTPError(
            "https://graph.facebook.com",
            400,
            "bad",
            {},
            io.BytesIO(b'{"error":"invalid"}'),
        )
        with patch.object(facebook, "urlopen", side_effect=http_error):
            with self.assertRaisesRegex(MetaAPIError, "HTTP 400"):
                facebook._request_json("me", params={})

        for error in (URLError("offline"), TimeoutError("slow")):
            with self.subTest(error=type(error).__name__), patch.object(facebook, "urlopen", side_effect=error):
                with self.assertRaisesRegex(MetaAPIError, "request failed"):
                    facebook._request_json("me", params={})

        invalid = MagicMock()
        invalid.__enter__.return_value = invalid
        invalid.read.return_value = b"not-json"
        with patch.object(facebook, "urlopen", return_value=invalid):
            with self.assertRaisesRegex(MetaAPIError, "request failed"):
                facebook._request_json("me", params={})

        with patch.object(
            facebook,
            "urlopen",
            return_value=self.response({"error": {"message": "Denied"}}),
        ):
            with self.assertRaisesRegex(MetaAPIError, "Denied"):
                facebook._request_json("me", params={})

        with patch.object(facebook, "urlopen", return_value=self.response({"error": {}})):
            with self.assertRaisesRegex(MetaAPIError, "Unknown Meta API error"):
                facebook._request_json("me", params={})

    @override_settings(PUBLIC_BASE_URL="https://example.com/", META_APP_ID="")
    def test_share_link_without_app_id(self):
        result = facebook.build_campaign_share_link("gig")
        self.assertEqual(
            result.campaign_url,
            "https://example.com/share/campaign/gig/?source=facebook_group&group=&ref=",
        )
        self.assertNotIn("app_id", result.share_dialog_url)

    @override_settings(META_APP_ID="", META_APP_SECRET="")
    def test_verify_user_requires_app_configuration(self):
        with self.assertRaisesRegex(MetaAPIError, "must be configured"):
            facebook.verify_facebook_user("token")

    @override_settings(META_APP_ID="app", META_APP_SECRET="secret")
    def test_verify_user_rejects_invalid_or_wrong_app_token(self):
        for debug in ({"is_valid": False, "app_id": "app"}, {"is_valid": True, "app_id": "other"}):
            with self.subTest(debug=debug), patch.object(
                facebook,
                "_request_json",
                return_value={"data": debug},
            ):
                with self.assertRaisesRegex(MetaAPIError, "invalid or belongs"):
                    facebook.verify_facebook_user("token")

    @override_settings(META_APP_ID="123", META_APP_SECRET="secret")
    def test_verify_user_returns_normalized_profile(self):
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
        with patch.object(facebook, "_request_json", return_value=payload) as mocked:
            pages = facebook.list_managed_pages("user-token")
        self.assertEqual(pages[0]["picture_url"], "https://img")
        self.assertEqual(pages[1]["category"], "")
        self.assertEqual(pages[1]["tasks"], [])
        self.assertEqual(pages[1]["page_access_token"], "")
        mocked.assert_called_once()

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
        expected = hashlib.sha256(b"fan@example.com").hexdigest()
        self.assertEqual(facebook._sha256("  FAN@EXAMPLE.COM "), expected)

    @override_settings(META_PIXEL_ID="", META_CONVERSIONS_API_TOKEN="")
    def test_conversion_event_is_optional(self):
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
