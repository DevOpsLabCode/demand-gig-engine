from django.test import SimpleTestCase, override_settings

from gigs.facebook import build_campaign_share_link


class FacebookLinkTests(SimpleTestCase):
    @override_settings(PUBLIC_BASE_URL="https://example.com", META_APP_ID="12345")
    def test_share_link_tracks_and_encodes_group_and_referral(self):
        link = build_campaign_share_link(
            "band-x-new-york",
            source="facebook_group",
            group_name="Band X NYC Fans & Friends",
            referral_code="admin jane",
        )
        self.assertIn("source=facebook_group", link.campaign_url)
        self.assertIn("group=Band+X+NYC+Fans+%26+Friends", link.campaign_url)
        self.assertIn("ref=admin+jane", link.campaign_url)
        self.assertIn("app_id=12345", link.share_dialog_url)
        self.assertIn("facebook.com/dialog/share", link.share_dialog_url)
