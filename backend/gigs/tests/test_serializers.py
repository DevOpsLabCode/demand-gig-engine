from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from gigs.serializers import CampaignSerializer


class CampaignSerializerTests(SimpleTestCase):
    def base_data(self):
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
        serializer = CampaignSerializer(data=self.base_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["currency"], "USD")

    def test_rejects_zero_amount_for_money_goal(self):
        data = self.base_data()
        data["goal_type"] = "money"
        data["amount_target"] = "0.00"
        serializer = CampaignSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount_target", serializer.errors)
