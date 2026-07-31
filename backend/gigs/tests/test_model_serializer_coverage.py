# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Exercises model validation, computed progress, string representations, serializer rules, and boundary conditions across campaign entities.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Exercises model validation, computed progress, string representations, serializer rules, and boundary conditions across campaign entities.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from gigs.models import (
    DemandCampaign,
    GoalType,
    Pledge,
    PledgeStatus,
    SponsorCommitment,
    SponsorStatus,
)
from gigs.serializers import CampaignSerializer


class ModelAndSerializerCoverageTests(TestCase):
    """
    Exercise ModelAndSerializerCoverage behavior, edge cases, and failure handling with isolated tests.
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
            "title": "Bring Band X",
            "pitch": "Demand first",
            "artist_name": "Band X",
            "city": "New York",
            "deadline": timezone.now() + timedelta(days=5),
            "goal_type": GoalType.SUPPORTERS,
            "supporter_target": 2,
            "amount_target": Decimal("0.00"),
            "organizer_name": "Organizer",
            "organizer_email": "organizer@example.com",
        }
        data.update(overrides)
        return DemandCampaign.objects.create(**data)

    def test_campaign_clean_validation_branches(self):
        """
        Verify that campaign clean validation branches.
        """
        campaign = DemandCampaign(
            goal_type=GoalType.SUPPORTERS,
            supporter_target=0,
            amount_target=Decimal("0"),
        )
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with self.assertRaisesRegex(ValidationError, "Supporter target"):
            campaign.clean()

        campaign.goal_type = GoalType.MONEY
        campaign.supporter_target = 1
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with self.assertRaisesRegex(ValidationError, "Amount target"):
            campaign.clean()

        campaign.amount_target = Decimal("1")
        campaign.clean()

    def test_slug_fallback_and_string_representations(self):
        """
        Verify that slug fallback and string representations.
        """
        campaign = self.make_campaign(title="Untitled", artist_name="", city="")
        self.assertEqual(campaign.slug, "gig")
        self.assertEqual(str(campaign), "Untitled")
        pledge = Pledge.objects.create(
            campaign=campaign,
            supporter_name="Fan",
            supporter_email="fan@example.com",
            quantity=1,
            amount=0,
            currency="USD",
            status=PledgeStatus.COMMITTED,
            idempotency_key="str",
        )
        self.assertEqual(str(pledge), "fan@example.com → Untitled")
        self.assertEqual(
            Pledge.active_statuses(),
            [PledgeStatus.PAID, PledgeStatus.COMMITTED, PledgeStatus.CAPTURED],
        )
        self.assertEqual(
            SponsorCommitment.active_statuses(),
            [SponsorStatus.PLEDGED, SponsorStatus.PAID, SponsorStatus.FINALIZED],
        )

    def test_target_and_progress_for_each_goal_type(self):
        """
        Verify that target and progress for each goal type.
        """
        supporters = self.make_campaign(title="Supporters")
        self.assertFalse(supporters.target_reached)
        self.assertEqual(supporters.progress_percent, 0)
        Pledge.objects.create(
            campaign=supporters,
            supporter_name="Fan",
            supporter_email="fan@example.com",
            quantity=3,
            amount=0,
            status=PledgeStatus.COMMITTED,
            idempotency_key="supporters",
        )
        self.assertTrue(supporters.target_reached)
        self.assertEqual(supporters.progress_percent, 100)

        money = self.make_campaign(
            title="Money",
            goal_type=GoalType.MONEY,
            supporter_target=0,
            amount_target=Decimal("100"),
        )
        SponsorCommitment.objects.create(
            campaign=money,
            sponsor_name="Sponsor",
            contact_name="Contact",
            contact_email="s@example.com",
            amount=Decimal("50"),
            status=SponsorStatus.PLEDGED,
        )
        self.assertFalse(money.target_reached)
        self.assertEqual(money.progress_percent, 50)
        SponsorCommitment.objects.create(
            campaign=money,
            sponsor_name="Sponsor 2",
            contact_name="Contact",
            contact_email="s2@example.com",
            amount=Decimal("75"),
            status=SponsorStatus.PAID,
        )
        self.assertTrue(money.target_reached)
        self.assertEqual(money.progress_percent, 100)

        both = self.make_campaign(
            title="Both",
            goal_type=GoalType.BOTH,
            supporter_target=2,
            amount_target=Decimal("100"),
        )
        Pledge.objects.create(
            campaign=both,
            supporter_name="Fan",
            supporter_email="both@example.com",
            quantity=2,
            amount=Decimal("50"),
            status=PledgeStatus.PAID,
            idempotency_key="both",
        )
        self.assertFalse(both.target_reached)
        self.assertEqual(both.progress_percent, 50)
        SponsorCommitment.objects.create(
            campaign=both,
            sponsor_name="Sponsor",
            contact_name="Contact",
            contact_email="both-s@example.com",
            amount=Decimal("50"),
            status=SponsorStatus.FINALIZED,
        )
        self.assertTrue(both.target_reached)
        self.assertEqual(both.progress_percent, 100)

        zero_targets = self.make_campaign(
            title="Zero targets",
            goal_type=GoalType.BOTH,
            supporter_target=0,
            amount_target=Decimal("0"),
        )
        self.assertEqual(zero_targets.progress_percent, 100)

    def test_campaign_serializer_remaining_validation_paths(self):
        """
        Verify that campaign serializer remaining validation paths.
        """
        base = {
            "title": "Bring Band X",
            "pitch": "Demand first",
            "artist_name": "Band X",
            "city": "New York",
            "deadline": (timezone.now() + timedelta(days=3)).isoformat(),
            "goal_type": "supporters",
            "supporter_target": 1,
            "amount_target": "0.00",
            "suggested_deposit": "25.00",
            "currency": "USD",
            "organizer_name": "Organizer",
            "organizer_email": "organizer@example.com",
        }
        past = dict(base, deadline=(timezone.now() - timedelta(seconds=1)).isoformat())
        serializer = CampaignSerializer(data=past)
        self.assertFalse(serializer.is_valid())
        self.assertIn("deadline", serializer.errors)

        invalid_supporters = dict(base, supporter_target=0)
        serializer = CampaignSerializer(data=invalid_supporters)
        self.assertFalse(serializer.is_valid())
        self.assertIn("supporter_target", serializer.errors)

        campaign = self.make_campaign(title="Existing")
        serializer = CampaignSerializer(campaign, data={"title": "Updated"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("currency", serializer.validated_data)
