from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from gigs.models import (
    CampaignStatus,
    DemandCampaign,
    GoalType,
    PledgeStatus,
    SponsorStatus,
)
from gigs.services import (
    CampaignStateError,
    confirm_artist,
    confirm_venue,
    create_pledge,
    create_sponsorship,
    fail_and_refund_campaign,
    finalize_campaign,
    launch_campaign,
)


class DemandCampaignFlowTests(TestCase):
    def make_campaign(self, **overrides):
        data = {
            "title": "Bring Band X to New York",
            "pitch": "Prove demand before the venue and artist are booked.",
            "artist_name": "Band X",
            "city": "New York",
            "deadline": timezone.now() + timedelta(days=30),
            "goal_type": GoalType.BOTH,
            "supporter_target": 2,
            "amount_target": Decimal("50.00"),
            "suggested_deposit": Decimal("25.00"),
            "organizer_name": "Open Concert",
            "organizer_email": "organizer@example.com",
        }
        data.update(overrides)
        return DemandCampaign.objects.create(**data)

    def pledge_data(self, key: str, **overrides):
        data = {
            "supporter_name": "Fan",
            "supporter_email": f"{key}@example.com",
            "quantity": 1,
            "amount": Decimal("25.00"),
            "idempotency_key": key,
            "source": "facebook_group",
            "source_label": "Band X NYC Fans",
        }
        data.update(overrides)
        return data

    def test_threshold_confirmation_and_finalization(self):
        campaign = launch_campaign(self.make_campaign().id)
        self.assertEqual(campaign.status, CampaignStatus.COLLECTING)

        for index in range(2):
            create_pledge(campaign.id, self.pledge_data(f"test-{index}"))

        campaign.refresh_from_db()
        self.assertEqual(campaign.status, CampaignStatus.TARGET_REACHED)
        self.assertTrue(campaign.target_reached)

        sponsorship = create_sponsorship(
            campaign.id,
            {
                "sponsor_name": "Local Sponsor",
                "contact_name": "Sponsor Contact",
                "contact_email": "sponsor@example.com",
                "amount": Decimal("1000.00"),
                "benefits_requested": "Logo placement",
            },
        )
        confirm_artist(campaign.id, "Artist LOI signed")
        campaign = confirm_venue(campaign.id, "Venue hold confirmed")
        self.assertEqual(campaign.status, CampaignStatus.CONFIRMED)

        campaign = finalize_campaign(campaign.id, "vibes-event-123")
        sponsorship.refresh_from_db()
        self.assertEqual(campaign.status, CampaignStatus.LIVE)
        self.assertFalse(campaign.pledges.exclude(status=PledgeStatus.CAPTURED).exists())
        self.assertEqual(sponsorship.status, SponsorStatus.FINALIZED)

    def test_failed_campaign_refunds_paid_and_cancels_nonfinancial_support(self):
        campaign = launch_campaign(self.make_campaign().id)
        paid, _ = create_pledge(campaign.id, self.pledge_data("refund-test"))
        committed, _ = create_pledge(
            campaign.id,
            self.pledge_data("commit-only", amount=Decimal("0.00")),
        )
        sponsorship = create_sponsorship(
            campaign.id,
            {
                "sponsor_name": "Community Sponsor",
                "contact_name": "Contact",
                "contact_email": "contact@example.com",
                "amount": Decimal("10.00"),
                "benefits_requested": "",
            },
        )

        campaign = fail_and_refund_campaign(campaign.id)
        paid.refresh_from_db()
        committed.refresh_from_db()
        sponsorship.refresh_from_db()

        self.assertEqual(campaign.status, CampaignStatus.REFUNDED)
        self.assertEqual(paid.status, PledgeStatus.REFUNDED)
        self.assertEqual(committed.status, PledgeStatus.CANCELED)
        self.assertEqual(sponsorship.status, SponsorStatus.CANCELED)

    def test_idempotency_is_scoped_to_campaign(self):
        first = launch_campaign(self.make_campaign().id)
        second = launch_campaign(
            self.make_campaign(title="Bring Band X to Boston", city="Boston").id
        )
        first_pledge, _ = create_pledge(first.id, self.pledge_data("shared-key"))
        repeated, _ = create_pledge(first.id, self.pledge_data("shared-key"))
        second_pledge, _ = create_pledge(second.id, self.pledge_data("shared-key"))

        self.assertEqual(first_pledge.id, repeated.id)
        self.assertNotEqual(first_pledge.id, second_pledge.id)
        self.assertEqual(first.pledges.count(), 1)
        self.assertEqual(second.pledges.count(), 1)

    def test_sponsor_commitment_can_reach_money_goal(self):
        campaign = launch_campaign(
            self.make_campaign(
                goal_type=GoalType.MONEY,
                supporter_target=0,
                amount_target=Decimal("1000.00"),
            ).id
        )
        create_sponsorship(
            campaign.id,
            {
                "sponsor_name": "Sponsor",
                "contact_name": "Contact",
                "contact_email": "sponsor@example.com",
                "amount": Decimal("1000.00"),
                "benefits_requested": "",
            },
        )
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, CampaignStatus.TARGET_REACHED)

    def test_confirmation_is_blocked_before_threshold(self):
        campaign = launch_campaign(self.make_campaign().id)
        with self.assertRaises(CampaignStateError):
            confirm_artist(campaign.id, "Too early")

    def test_launch_rejects_expired_campaign(self):
        campaign = self.make_campaign(deadline=timezone.now() - timedelta(minutes=1))
        with self.assertRaises(CampaignStateError):
            launch_campaign(campaign.id)

    def test_slug_is_unique(self):
        first = self.make_campaign()
        second = self.make_campaign(title="Same artist, same city")
        self.assertEqual(first.slug, "band-x-new-york")
        self.assertEqual(second.slug, "band-x-new-york-2")
