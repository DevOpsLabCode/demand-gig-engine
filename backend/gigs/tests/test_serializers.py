# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies API serializer validation for campaign creation, pledges, sponsors, and external integration inputs.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Verifies API serializer validation for campaign creation, pledges, sponsors, and external integration inputs.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from gigs.serializers import CampaignSerializer


class CampaignSerializerTests(SimpleTestCase):
    """
    Exercise CampaignSerializer behavior, edge cases, and failure handling with isolated tests.
    """
    def base_data(self):
        """
        Return a valid baseline serializer payload for focused validation tests.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
        return {
            "title": "Bring Band X to New York",
            "pitch": "Prove demand first.",
            "artist_name": "Band X",
            "city": "New York",
            "country": "United States",
            "deadline": (timezone.now() + timedelta(days=30)).isoformat(),
            "goal_type": "both",
            "supporter_target": 500,
            "amount_target": "25000.00",
            "suggested_deposit": "25.00",
            "currency": "usd",
            "organizer_name": "Open Concert",
            "organizer_email": "organizer@example.com",
        }

    def test_normalizes_currency(self):
        """
        Verify that normalizes currency.
        """
        serializer = CampaignSerializer(data=self.base_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["currency"], "USD")

    def test_rejects_zero_amount_for_money_goal(self):
        """
        Verify that rejects zero amount for money goal.
        """
        data = self.base_data()
        data["goal_type"] = "money"
        data["amount_target"] = "0.00"
        serializer = CampaignSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount_target", serializer.errors)
