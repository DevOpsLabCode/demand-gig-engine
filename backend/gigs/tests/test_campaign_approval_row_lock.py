# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Prevents PostgreSQL approval failures caused by locking a nullable joined owner row.

from django.test import SimpleTestCase

from gigs.campaign_approval import _campaign_review_queryset


class CampaignApprovalRowLockQueryTests(SimpleTestCase):
    """Verify the approval query locks only the campaign table row."""

    def test_nullable_owner_join_is_excluded_from_for_update_lock(self):
        queryset = _campaign_review_queryset()

        self.assertTrue(queryset.query.select_for_update)
        self.assertEqual(queryset.query.select_for_update_of, ("self",))
        self.assertIn("owner", queryset.query.select_related)
