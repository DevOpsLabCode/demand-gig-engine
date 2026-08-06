# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies Phase 2 option management, private voting, aggregate calculations, and privacy boundaries.

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
from gigs.campaign_preferences import build_preference_summary
from gigs.models import (
    CampaignEvent,
    DemandCampaign,
    GoalType,
    Pledge,
    PledgeStatus,
    SponsorCommitment,
    SponsorStatus,
)


class CampaignPreferenceTests(TestCase):
    """Exercise campaign date/price choices and one mutable vote per user."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="phase2-owner",
            email="owner@example.com",
            password="StrongPass123!",
        )
        self.supporter = get_user_model().objects.create_user(
            username="phase2-supporter",
            email="supporter@example.com",
            password="StrongPass123!",
        )
        self.second_supporter = get_user_model().objects.create_user(
            username="phase2-second",
            email="second@example.com",
            password="StrongPass123!",
        )
        self.other = get_user_model().objects.create_user(
            username="phase2-other",
            email="other@example.com",
            password="StrongPass123!",
        )
        self.admin = get_user_model().objects.create_user(
            username="phase2-admin",
            email="admin@example.com",
            password="StrongPass123!",
            is_staff=True,
        )

    def campaign_payload(self, title="Bring Artist X to New York"):
        start = timezone.now() + timedelta(days=45)
        return {
            "title": title,
            "pitch": "Vote on dates, price, and attendance before production.",
            "artist_name": "Artist X",
            "city": "New York",
            "country": "United States",
            "deadline": (timezone.now() + timedelta(days=30)).isoformat(),
            "goal_type": "supporters",
            "supporter_target": 100,
            "amount_target": "0.00",
            "suggested_deposit": "25.00",
            "currency": "USD",
            "organizer_name": "Open Concert",
            "organizer_email": "owner@example.com",
            "date_options": [
                {
                    "start_datetime": start.isoformat(),
                    "end_datetime": (start + timedelta(hours=3)).isoformat(),
                    "venue_timezone": "America/New_York",
                    "label": "Friday night",
                    "active": True,
                },
                {
                    "start_datetime": (start + timedelta(days=1)).isoformat(),
                    "end_datetime": (
                        start + timedelta(days=1, hours=3)
                    ).isoformat(),
                    "venue_timezone": "America/New_York",
                    "label": "Saturday night",
                    "active": True,
                },
            ],
            "price_options": [
                {
                    "amount": "40.00",
                    "currency": "usd",
                    "label": "$40 acceptable",
                    "active": True,
                },
                {
                    "amount": "60.00",
                    "currency": "USD",
                    "label": "$60 acceptable",
                    "active": True,
                },
            ],
        }

    def make_campaign(self, status="collecting", **overrides):
        values = {
            "owner": self.owner,
            "title": "Bring Artist X to New York",
            "pitch": "Vote before production.",
            "artist_name": "Artist X",
            "city": "New York",
            "deadline": timezone.now() + timedelta(days=30),
            "goal_type": GoalType.SUPPORTERS,
            "supporter_target": 100,
            "amount_target": Decimal("0.00"),
            "suggested_deposit": Decimal("25.00"),
            "organizer_name": "Open Concert",
            "organizer_email": "owner@example.com",
            "status": status,
        }
        values.update(overrides)
        return DemandCampaign.objects.create(**values)

    def add_options(self, campaign):
        start = timezone.now() + timedelta(days=45)
        date_one = CampaignDateOption.objects.create(
            campaign=campaign,
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
            venue_timezone="America/New_York",
            label="Friday",
        )
        date_two = CampaignDateOption.objects.create(
            campaign=campaign,
            start_datetime=start + timedelta(days=1),
            end_datetime=start + timedelta(days=1, hours=3),
            venue_timezone="America/New_York",
            label="Saturday",
        )
        price_low = CampaignPriceOption.objects.create(
            campaign=campaign,
            amount=Decimal("40.00"),
            currency="usd",
            label="$40",
        )
        price_high = CampaignPriceOption.objects.create(
            campaign=campaign,
            amount=Decimal("60.00"),
            currency="USD",
            label="$60",
        )
        price_low.refresh_from_db()
        return date_one, date_two, price_low, price_high

    def preference_payload(
        self,
        date_option,
        price_option,
        *,
        quantity=2,
        mode=AttendanceMode.PHYSICAL,
    ):
        return {
            "expected_quantity": quantity,
            "attendance_mode": mode,
            "selected_date_option": date_option.id,
            "selected_price_option": price_option.id,
            "preferred_neighborhood": "Greenwich Village",
            "accessibility_notes": "Step-free access requested",
            "referral_source": "facebook_group",
        }

    def test_nested_campaign_creation_adds_multiple_dates_and_prices(self):
        client = APIClient()
        client.force_authenticate(self.owner)

        response = client.post(
            "/api/campaigns/",
            self.campaign_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        campaign = DemandCampaign.objects.get(slug=response.data["slug"])
        self.assertEqual(campaign.date_options.count(), 2)
        self.assertEqual(campaign.price_options.count(), 2)
        self.assertEqual(response.data["date_options"][0]["label"], "Friday night")
        self.assertEqual(response.data["price_options"][0]["currency"], "USD")
        self.assertEqual(
            response.data["preference_summary"]["projected_ticket_revenue"],
            "0.00",
        )

    def test_option_management_requires_owner_or_admin_and_editable_status(self):
        campaign = self.make_campaign(status="draft")
        date_one, _, _, _ = self.add_options(campaign)

        other_client = APIClient()
        other_client.force_authenticate(self.other)
        denied = other_client.post(
            f"/api/campaigns/{campaign.slug}/date-options/",
            {
                "start_datetime": (
                    timezone.now() + timedelta(days=60)
                ).isoformat(),
                "venue_timezone": "America/New_York",
                "label": "Denied",
            },
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        owner_client = APIClient()
        owner_client.force_authenticate(self.owner)
        changed = owner_client.patch(
            f"/api/campaigns/{campaign.slug}/date-options/{date_one.id}/",
            {"label": "Updated Friday"},
            format="json",
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.data["label"], "Updated Friday")

        campaign.status = "collecting"
        campaign.save(update_fields=["status", "updated_at"])
        blocked = owner_client.post(
            f"/api/campaigns/{campaign.slug}/price-options/",
            {"amount": "80.00", "currency": "USD", "label": "$80"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 409)

    def test_admin_can_manage_options_and_delete_means_deactivate(self):
        campaign = self.make_campaign(status="draft")
        date_one, _, price_low, _ = self.add_options(campaign)
        client = APIClient()
        client.force_authenticate(self.admin)

        removed = client.delete(
            f"/api/campaigns/{campaign.slug}/date-options/{date_one.id}/"
        )
        self.assertEqual(removed.status_code, 204)
        date_one.refresh_from_db()
        self.assertFalse(date_one.active)

        price_removed = client.delete(
            f"/api/campaigns/{campaign.slug}/price-options/{price_low.id}/"
        )
        self.assertEqual(price_removed.status_code, 204)
        price_low.refresh_from_db()
        self.assertFalse(price_low.active)

        visible = client.get(
            f"/api/campaigns/{campaign.slug}/date-options/"
        )
        self.assertEqual(visible.status_code, 200)
        self.assertNotIn(date_one.id, [item["id"] for item in visible.data])

    def test_authenticated_supporter_can_create_and_change_one_preference(self):
        campaign = self.make_campaign()
        date_one, date_two, price_low, price_high = self.add_options(campaign)
        client = APIClient()
        client.force_authenticate(self.supporter)

        created = client.post(
            f"/api/campaigns/{campaign.slug}/preference/",
            self.preference_payload(date_one, price_low),
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(
            SupporterPreference.objects.filter(
                campaign=campaign,
                user=self.supporter,
            ).count(),
            1,
        )

        updated = client.patch(
            f"/api/campaigns/{campaign.slug}/preference/",
            {
                "expected_quantity": 3,
                "attendance_mode": "virtual",
                "selected_date_option": date_two.id,
                "selected_price_option": price_high.id,
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["expected_quantity"], 3)
        self.assertEqual(
            SupporterPreference.objects.filter(
                campaign=campaign,
                user=self.supporter,
            ).count(),
            1,
        )
        self.assertTrue(
            CampaignEvent.objects.filter(
                campaign=campaign,
                event_type="supporter_preference.updated",
            ).exists()
        )

    def test_anonymous_vote_is_rejected_and_private_get_is_user_scoped(self):
        campaign = self.make_campaign()
        date_one, _, price_low, _ = self.add_options(campaign)

        anonymous = APIClient().post(
            f"/api/campaigns/{campaign.slug}/preference/",
            self.preference_payload(date_one, price_low),
            format="json",
        )
        self.assertIn(anonymous.status_code, (401, 403))

        supporter_client = APIClient()
        supporter_client.force_authenticate(self.supporter)
        supporter_client.post(
            f"/api/campaigns/{campaign.slug}/preference/",
            self.preference_payload(date_one, price_low),
            format="json",
        )

        other_client = APIClient()
        other_client.force_authenticate(self.other)
        private = other_client.get(
            f"/api/campaigns/{campaign.slug}/preference/"
        )
        self.assertEqual(private.status_code, 200)
        self.assertIsNone(private.data["preference"])

    def test_draft_rejected_and_expired_campaigns_do_not_accept_votes(self):
        for blocked_status in ("draft", "rejected", "expired"):
            with self.subTest(status=blocked_status):
                campaign = self.make_campaign(
                    status=blocked_status,
                    title=f"Blocked {blocked_status}",
                )
                date_one, _, price_low, _ = self.add_options(campaign)
                client = APIClient()
                client.force_authenticate(self.owner)
                response = client.post(
                    f"/api/campaigns/{campaign.slug}/preference/",
                    self.preference_payload(date_one, price_low),
                    format="json",
                )
                self.assertEqual(response.status_code, 409)
                self.assertFalse(
                    SupporterPreference.objects.filter(
                        campaign=campaign,
                        user=self.supporter,
                    ).exists()
                )

    def test_cross_campaign_or_inactive_options_are_rejected(self):
        campaign = self.make_campaign()
        date_one, _, price_low, _ = self.add_options(campaign)
        other_campaign = self.make_campaign(
            title="Different campaign",
            status="collecting",
        )
        other_date, _, other_price, _ = self.add_options(other_campaign)
        client = APIClient()
        client.force_authenticate(self.supporter)

        cross_campaign = client.post(
            f"/api/campaigns/{campaign.slug}/preference/",
            self.preference_payload(other_date, other_price),
            format="json",
        )
        self.assertEqual(cross_campaign.status_code, 400)

        date_one.active = False
        date_one.save(update_fields=["active"])
        inactive = client.post(
            f"/api/campaigns/{campaign.slug}/preference/",
            self.preference_payload(date_one, price_low),
            format="json",
        )
        self.assertEqual(inactive.status_code, 400)

    def test_aggregate_separates_attendance_revenue_deposits_and_sponsors(self):
        campaign = self.make_campaign()
        date_one, date_two, price_low, price_high = self.add_options(campaign)
        SupporterPreference.objects.create(
            campaign=campaign,
            user=self.supporter,
            expected_quantity=2,
            attendance_mode=AttendanceMode.PHYSICAL,
            selected_date_option=date_one,
            selected_price_option=price_low,
            preferred_neighborhood="Greenwich Village",
            accessibility_notes="Private note one",
        )
        SupporterPreference.objects.create(
            campaign=campaign,
            user=self.second_supporter,
            expected_quantity=3,
            attendance_mode=AttendanceMode.VIRTUAL,
            selected_date_option=date_two,
            selected_price_option=price_high,
            accessibility_notes="Private note two",
        )
        Pledge.objects.create(
            campaign=campaign,
            supporter_user=self.supporter,
            supporter_name="Supporter",
            supporter_email="supporter@example.com",
            quantity=1,
            amount=Decimal("25.00"),
            currency="USD",
            status=PledgeStatus.COMMITTED,
            payment_provider="none",
            idempotency_key="phase2-deposit",
        )
        SponsorCommitment.objects.create(
            campaign=campaign,
            contact_user=self.second_supporter,
            sponsor_name="Sponsor",
            contact_name="Second",
            contact_email="second@example.com",
            amount=Decimal("100.00"),
            currency="USD",
            status=SponsorStatus.PLEDGED,
        )

        summary = build_preference_summary(campaign)
        self.assertEqual(summary["supporter_count"], 2)
        self.assertEqual(summary["expected_attendance"], 5)
        self.assertEqual(summary["physical_expected_attendance"], 2)
        self.assertEqual(summary["virtual_expected_attendance"], 3)
        self.assertEqual(summary["projected_ticket_revenue"], "260.00")
        self.assertEqual(summary["deposits_collected"], "25.00")
        self.assertEqual(summary["sponsor_commitments"], "100.00")
        self.assertEqual(summary["total_conditional_funding"], "125.00")

    def test_public_summary_does_not_expose_supporter_identity_or_notes(self):
        campaign = self.make_campaign()
        date_one, _, price_low, _ = self.add_options(campaign)
        SupporterPreference.objects.create(
            campaign=campaign,
            user=self.supporter,
            expected_quantity=2,
            attendance_mode=AttendanceMode.PHYSICAL,
            selected_date_option=date_one,
            selected_price_option=price_low,
            accessibility_notes="Sensitive private accessibility information",
        )

        response = APIClient().get(
            f"/api/campaigns/{campaign.slug}/preference-summary/"
        )
        self.assertEqual(response.status_code, 200)
        serialized = str(response.data)
        self.assertNotIn("supporter@example.com", serialized)
        self.assertNotIn("phase2-supporter", serialized)
        self.assertNotIn("Sensitive private accessibility information", serialized)
        self.assertEqual(response.data["projected_ticket_revenue"], "80.00")

    def test_enriched_public_campaign_payload_contains_only_aggregate_vote_data(self):
        campaign = self.make_campaign()
        date_one, _, price_low, _ = self.add_options(campaign)
        SupporterPreference.objects.create(
            campaign=campaign,
            user=self.supporter,
            expected_quantity=4,
            attendance_mode=AttendanceMode.VIRTUAL,
            selected_date_option=date_one,
            selected_price_option=price_low,
            accessibility_notes="Never public",
        )

        response = APIClient().get(f"/api/campaigns/{campaign.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["preference_summary"]["virtual_expected_attendance"],
            4,
        )
        self.assertIsNone(response.data["my_preference"])
        self.assertNotIn("Never public", str(response.data))

    def test_invalid_nested_option_shape_and_end_before_start_are_rejected(self):
        client = APIClient()
        client.force_authenticate(self.owner)
        payload = self.campaign_payload("Invalid nested options")
        payload["date_options"] = {"not": "a list"}
        response = client.post("/api/campaigns/", payload, format="json")
        self.assertEqual(response.status_code, 400)

        payload = self.campaign_payload("Invalid date ordering")
        start = timezone.now() + timedelta(days=45)
        payload["date_options"][0]["start_datetime"] = start.isoformat()
        payload["date_options"][0]["end_datetime"] = (
            start - timedelta(hours=1)
        ).isoformat()
        invalid_date = client.post("/api/campaigns/", payload, format="json")
        self.assertEqual(invalid_date.status_code, 400)

    def test_anonymous_campaign_visibility_hides_private_lifecycle_states(self):
        draft = self.make_campaign(status="draft", title="Private draft")
        collecting = self.make_campaign(status="collecting", title="Public campaign")

        anonymous = APIClient()
        listing = anonymous.get("/api/campaigns/")
        self.assertEqual(listing.status_code, 200)
        slugs = {item["slug"] for item in listing.data}
        self.assertIn(collecting.slug, slugs)
        self.assertNotIn(draft.slug, slugs)

        hidden_detail = anonymous.get(f"/api/campaigns/{draft.slug}/")
        self.assertEqual(hidden_detail.status_code, 404)

        owner_client = APIClient()
        owner_client.force_authenticate(self.owner)
        owner_detail = owner_client.get(f"/api/campaigns/{draft.slug}/")
        self.assertEqual(owner_detail.status_code, 200)
        self.assertEqual(owner_detail.data["slug"], draft.slug)

