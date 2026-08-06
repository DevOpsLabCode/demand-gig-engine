# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Covers atomic owner seed edits, option synchronization, rollback, and cross-campaign protection.

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from gigs.campaign_preference_models import (
    AttendanceMode,
    CampaignDateOption,
    CampaignPriceOption,
    SupporterPreference,
)
from gigs.models import CampaignEvent, DemandCampaign, GoalType


class OwnerSeedEditingTests(TestCase):
    """Verify the full owner editor coordinates existing services atomically."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="seed-owner",
            email="seed-owner@example.com",
            password="StrongPass123!",
        )
        self.supporter = get_user_model().objects.create_user(
            username="seed-supporter",
            email="seed-supporter@example.com",
            password="StrongPass123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.campaign = DemandCampaign.objects.create(
            owner=self.owner,
            title="Original campaign seed",
            pitch="Original public story.",
            artist_name="Artist X",
            city="New York",
            country="United States",
            deadline=timezone.now() + timedelta(days=30),
            goal_type=GoalType.BOTH,
            supporter_target=100,
            amount_target=Decimal("5000.00"),
            suggested_deposit=Decimal("25.00"),
            currency="USD",
            organizer_name="Open Concert",
            organizer_email="seed-owner@example.com",
            status="live",
        )
        start = timezone.now() + timedelta(days=45)
        self.date_one = CampaignDateOption.objects.create(
            campaign=self.campaign,
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
            venue_timezone="America/New_York",
            label="Friday",
        )
        self.date_two = CampaignDateOption.objects.create(
            campaign=self.campaign,
            start_datetime=start + timedelta(days=1),
            end_datetime=start + timedelta(days=1, hours=3),
            venue_timezone="America/New_York",
            label="Saturday",
        )
        self.price_one = CampaignPriceOption.objects.create(
            campaign=self.campaign,
            amount=Decimal("40.00"),
            currency="USD",
            label="$40",
        )
        self.price_two = CampaignPriceOption.objects.create(
            campaign=self.campaign,
            amount=Decimal("60.00"),
            currency="USD",
            label="$60",
        )

    def date_payload(self, option, *, label=None):
        return {
            "id": option.id,
            "start_datetime": option.start_datetime.isoformat(),
            "end_datetime": option.end_datetime.isoformat(),
            "venue_timezone": option.venue_timezone,
            "label": label or option.label,
            "active": True,
        }

    def price_payload(self, option, *, label=None):
        return {
            "id": option.id,
            "amount": str(option.amount),
            "currency": option.currency,
            "label": label or option.label,
            "active": True,
        }

    def test_full_seed_edit_updates_creates_and_deactivates_options(self):
        new_start = timezone.now() + timedelta(days=60)
        response = self.client.patch(
            f"/api/campaigns/{self.campaign.slug}/",
            {
                "title": "Updated live campaign seed",
                "pitch": "The owner can keep this seed accurate while live.",
                "date_options": [
                    self.date_payload(self.date_one, label="Updated Friday"),
                    {
                        "start_datetime": new_start.isoformat(),
                        "end_datetime": (
                            new_start + timedelta(hours=3)
                        ).isoformat(),
                        "venue_timezone": "America/New_York",
                        "label": "Sunday",
                        "active": True,
                    },
                ],
                "price_options": [
                    self.price_payload(self.price_one, label="Updated $40"),
                    {
                        "amount": "80.00",
                        "currency": "usd",
                        "label": "$80",
                        "active": True,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.campaign.refresh_from_db()
        self.date_one.refresh_from_db()
        self.date_two.refresh_from_db()
        self.price_one.refresh_from_db()
        self.price_two.refresh_from_db()
        self.assertEqual(self.campaign.status, "live")
        self.assertEqual(self.campaign.title, "Updated live campaign seed")
        self.assertEqual(self.date_one.label, "Updated Friday")
        self.assertFalse(self.date_two.active)
        self.assertEqual(self.price_one.label, "Updated $40")
        self.assertFalse(self.price_two.active)
        self.assertTrue(
            self.campaign.date_options.filter(label="Sunday", active=True).exists()
        )
        self.assertTrue(
            self.campaign.price_options.filter(
                label="$80",
                currency="USD",
                active=True,
            ).exists()
        )
        event = CampaignEvent.objects.filter(
            campaign=self.campaign,
            event_type="campaign.owner_edited",
        ).latest("created_at")
        self.assertTrue(event.payload["date_options_edited"])
        self.assertTrue(event.payload["price_options_edited"])
        self.assertIn("status", event.payload["protected_fields_unchanged"])

    def test_voted_option_removal_rolls_back_entire_seed_edit(self):
        SupporterPreference.objects.create(
            campaign=self.campaign,
            user=self.supporter,
            expected_quantity=2,
            attendance_mode=AttendanceMode.PHYSICAL,
            selected_date_option=self.date_two,
            selected_price_option=self.price_two,
        )
        original_title = self.campaign.title
        original_label = self.date_one.label

        response = self.client.patch(
            f"/api/campaigns/{self.campaign.slug}/",
            {
                "title": "This must roll back",
                "date_options": [
                    self.date_payload(self.date_one, label="Temporary change")
                ],
                "price_options": [self.price_payload(self.price_one)],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.campaign.refresh_from_db()
        self.date_one.refresh_from_db()
        self.date_two.refresh_from_db()
        self.price_two.refresh_from_db()
        self.assertEqual(self.campaign.title, original_title)
        self.assertEqual(self.date_one.label, original_label)
        self.assertTrue(self.date_two.active)
        self.assertTrue(self.price_two.active)
        self.assertFalse(
            CampaignEvent.objects.filter(
                campaign=self.campaign,
                event_type="campaign.owner_edited",
            ).exists()
        )

    def test_foreign_option_id_and_empty_option_group_are_rejected(self):
        other_campaign = DemandCampaign.objects.create(
            owner=self.owner,
            title="Other campaign",
            pitch="Other seed.",
            artist_name="Artist Y",
            city="Boston",
            deadline=timezone.now() + timedelta(days=30),
            goal_type=GoalType.SUPPORTERS,
            supporter_target=10,
            amount_target=Decimal("0.00"),
            suggested_deposit=Decimal("0.00"),
            organizer_name="Open Concert",
            organizer_email="seed-owner@example.com",
        )
        foreign_date = CampaignDateOption.objects.create(
            campaign=other_campaign,
            start_datetime=timezone.now() + timedelta(days=70),
            venue_timezone="America/New_York",
            label="Foreign",
        )

        foreign = self.client.patch(
            f"/api/campaigns/{self.campaign.slug}/",
            {
                "date_options": [
                    {
                        "id": foreign_date.id,
                        "start_datetime": foreign_date.start_datetime.isoformat(),
                        "end_datetime": None,
                        "venue_timezone": foreign_date.venue_timezone,
                        "label": foreign_date.label,
                        "active": True,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(foreign.status_code, 400)

        empty = self.client.patch(
            f"/api/campaigns/{self.campaign.slug}/",
            {"price_options": []},
            format="json",
        )
        self.assertEqual(empty.status_code, 400)
