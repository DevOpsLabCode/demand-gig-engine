# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies Facebook share-link construction, campaign tracking parameters, and public Meta integration behavior.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Verifies Facebook share-link construction, campaign tracking parameters, and public Meta integration behavior.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from django.test import SimpleTestCase, override_settings

from gigs.facebook import build_campaign_share_link


class FacebookLinkTests(SimpleTestCase):
    """
    Exercise FacebookLink behavior, edge cases, and failure handling with isolated tests.
    """
    @override_settings(PUBLIC_BASE_URL="https://example.com", META_APP_ID="12345")
    def test_share_link_tracks_and_encodes_group_and_referral(self):
        """
        Verify that share link tracks and encodes group and referral.
        """
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
