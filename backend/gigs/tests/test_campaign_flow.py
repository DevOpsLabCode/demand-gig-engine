# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Exercises the end-to-end campaign lifecycle from creation and launch through pledges, threshold evaluation, confirmation, expiry, and refunds.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Exercises the end-to-end campaign lifecycle from creation and launch through pledges, threshold evaluation, confirmation, expiry, and refunds.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

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
    """
    Exercise DemandCampaignFlow behavior, edge cases, and failure handling with isolated tests.
    """
    def make_campaign(self, **overrides):
        """
        Create a campaign test fixture with valid defaults and optional field overrides.
        
        Args:
            **overrides: Additional keyword arguments forwarded to the underlying implementation.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
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
        """
        Build a valid pledge payload and merge test-specific overrides.
        
        Args:
            key: Configuration or object key currently being validated.
            **overrides: Additional keyword arguments forwarded to the underlying implementation.
        
        Returns:
            The typed result described in the function summary and return annotation.
        """
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
        """
        Verify that threshold confirmation and finalization.
        """
        campaign = launch_campaign(self.make_campaign().id)
        self.assertEqual(campaign.status, CampaignStatus.COLLECTING)

        # Process each `index` from `range(2)` in a deterministic order.
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
        """
        Verify that failed campaign refunds paid and cancels nonfinancial support.
        """
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
        """
        Verify that idempotency is scoped to campaign.
        """
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
        """
        Verify that sponsor commitment can reach money goal.
        """
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
        """
        Verify that confirmation is blocked before threshold.
        """
        campaign = launch_campaign(self.make_campaign().id)
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with self.assertRaises(CampaignStateError):
            confirm_artist(campaign.id, "Too early")

    def test_launch_rejects_expired_campaign(self):
        """
        Verify that launch rejects expired campaign.
        """
        campaign = self.make_campaign(deadline=timezone.now() - timedelta(minutes=1))
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with self.assertRaises(CampaignStateError):
            launch_campaign(campaign.id)

    def test_slug_is_unique(self):
        """
        Verify that slug is unique.
        """
        first = self.make_campaign()
        second = self.make_campaign(title="Same artist, same city")
        self.assertEqual(first.slug, "band-x-new-york")
        self.assertEqual(second.slug, "band-x-new-york-2")
