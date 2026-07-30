from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from gigs.facebook import FacebookShareLink, MetaAPIError
from gigs.models import (
    CampaignStatus,
    DemandCampaign,
    GoalType,
    Pledge,
    PledgeStatus,
    SponsorCommitment,
    SponsorStatus,
)
from gigs.payments import PaymentResult
from gigs.services import (
    CampaignStateError,
    _send_meta_event_safely,
    confirm_artist,
    confirm_venue,
    create_pledge,
    create_sponsorship,
    evaluate_threshold_locked,
    expire_due_campaigns,
    fail_and_refund_campaign,
    finalize_campaign,
    launch_campaign,
)


class ServiceEdgeCoverageTests(TestCase):
    def make_campaign(self, **overrides):
        data = {
            "title": "Bring Band X",
            "pitch": "Demand first",
            "artist_name": "Band X",
            "city": "New York",
            "deadline": timezone.now() + timedelta(days=5),
            "goal_type": GoalType.SUPPORTERS,
            "supporter_target": 2,
            "amount_target": Decimal("0"),
            "organizer_name": "Organizer",
            "organizer_email": "organizer@example.com",
        }
        data.update(overrides)
        return DemandCampaign.objects.create(**data)

    def pledge_data(self, key="key", **overrides):
        data = {
            "supporter_name": "Fan",
            "supporter_email": "fan@example.com",
            "quantity": 1,
            "amount": Decimal("0"),
            "idempotency_key": key,
        }
        data.update(overrides)
        return data

    def test_meta_event_wrapper_swallows_only_meta_errors(self):
        with patch("gigs.services.send_conversion_event") as mocked:
            _send_meta_event_safely(event_name="Lead")
            mocked.assert_called_once_with(event_name="Lead")
        with patch("gigs.services.send_conversion_event", side_effect=MetaAPIError("no")):
            _send_meta_event_safely(event_name="Lead")

    def test_launch_and_create_reject_invalid_states_and_expired_deadline(self):
        campaign = self.make_campaign(status=CampaignStatus.COLLECTING)
        with self.assertRaisesRegex(CampaignStateError, "Only a draft"):
            launch_campaign(campaign.id)

        draft = self.make_campaign(title="Draft")
        with self.assertRaisesRegex(CampaignStateError, "not accepting"):
            create_pledge(draft.id, self.pledge_data("draft"))

        expired = self.make_campaign(
            title="Expired",
            status=CampaignStatus.COLLECTING,
            deadline=timezone.now() - timedelta(seconds=1),
        )
        with self.assertRaisesRegex(CampaignStateError, "deadline has passed"):
            create_pledge(expired.id, self.pledge_data("expired"))

        with self.assertRaisesRegex(CampaignStateError, "not accepting sponsor"):
            create_sponsorship(
                draft.id,
                {
                    "sponsor_name": "S",
                    "contact_name": "C",
                    "contact_email": "s@example.com",
                    "amount": Decimal("1"),
                },
            )

    def test_existing_pending_stripe_pledge_returns_client_secret(self):
        campaign = self.make_campaign(status=CampaignStatus.COLLECTING)
        pledge = Pledge.objects.create(
            campaign=campaign,
            supporter_name="Fan",
            supporter_email="fan@example.com",
            quantity=1,
            amount=Decimal("25"),
            currency="USD",
            status=PledgeStatus.PENDING,
            payment_provider="stripe",
            payment_reference="pi_1",
            idempotency_key="same",
        )
        provider = Mock()
        provider.get_client_secret.return_value = "secret"
        with patch("gigs.services.get_payment_provider", return_value=provider):
            existing, secret = create_pledge(campaign.id, self.pledge_data("same"))
        self.assertEqual(existing.id, pledge.id)
        self.assertEqual(secret, "secret")

    def test_paid_pledge_can_remain_pending_and_schedule_checkout_event(self):
        campaign = self.make_campaign(status=CampaignStatus.COLLECTING)
        provider = Mock(name="provider")
        provider.name = "stripe"
        provider.collect_refundable_deposit.return_value = PaymentResult(
            reference="pi_pending",
            client_secret="client-secret",
            status="requires_action",
        )
        share = FacebookShareLink("https://example.com/campaign", "https://facebook.com/share")
        with patch("gigs.services.get_payment_provider", return_value=provider), patch(
            "gigs.services.build_campaign_share_link", return_value=share
        ), patch("gigs.services.send_conversion_event") as conversion, self.captureOnCommitCallbacks(
            execute=True
        ):
            pledge, secret = create_pledge(
                campaign.id,
                self.pledge_data("pending", amount=Decimal("25")),
            )
        self.assertEqual(pledge.status, PledgeStatus.PENDING)
        self.assertEqual(secret, "client-secret")
        self.assertEqual(conversion.call_args.kwargs["event_name"], "InitiateCheckout")
        self.assertEqual(conversion.call_args.kwargs["value"], Decimal("25"))

    def test_commitment_schedules_lead_and_threshold_noop(self):
        campaign = self.make_campaign(status=CampaignStatus.COLLECTING, supporter_target=5)
        with patch(
            "gigs.services.build_campaign_share_link",
            return_value=FacebookShareLink("https://example.com", "https://facebook.com"),
        ), patch("gigs.services.send_conversion_event") as conversion, self.captureOnCommitCallbacks(
            execute=True
        ):
            pledge, _ = create_pledge(campaign.id, self.pledge_data("lead"))
        self.assertEqual(pledge.status, PledgeStatus.COMMITTED)
        self.assertEqual(conversion.call_args.kwargs["event_name"], "Lead")
        campaign.refresh_from_db()
        self.assertEqual(evaluate_threshold_locked(campaign).status, CampaignStatus.COLLECTING)

    def test_artist_and_venue_confirmation_edge_paths(self):
        blocked = self.make_campaign(status=CampaignStatus.COLLECTING)
        with self.assertRaisesRegex(CampaignStateError, "Venue confirmation"):
            confirm_venue(blocked.id, "too early")

        venue_first = self.make_campaign(
            title="Venue first",
            status=CampaignStatus.TARGET_REACHED,
        )
        venue_first = confirm_venue(venue_first.id, "venue held")
        self.assertEqual(venue_first.status, CampaignStatus.CONFIRMING)

        campaign = self.make_campaign(
            title="Artist last",
            status=CampaignStatus.CONFIRMING,
            venue_confirmed=True,
        )
        campaign = confirm_artist(campaign.id, "artist signed")
        self.assertEqual(campaign.status, CampaignStatus.CONFIRMED)

    def test_finalize_rejects_unconfirmed_campaign(self):
        campaign = self.make_campaign(status=CampaignStatus.TARGET_REACHED)
        with self.assertRaisesRegex(CampaignStateError, "both be confirmed"):
            finalize_campaign(campaign.id, "event")

    def test_failure_flow_rejects_terminal_campaign(self):
        for status in (CampaignStatus.LIVE, CampaignStatus.COMPLETED, CampaignStatus.REFUNDED):
            campaign = self.make_campaign(title=f"Terminal {status}", status=status)
            with self.subTest(status=status), self.assertRaisesRegex(CampaignStateError, "can no longer"):
                fail_and_refund_campaign(campaign.id)

    def test_pledge_refund_failure_leaves_campaign_refunding(self):
        campaign = self.make_campaign(status=CampaignStatus.COLLECTING)
        pledge = Pledge.objects.create(
            campaign=campaign,
            supporter_name="Fan",
            supporter_email="fan@example.com",
            quantity=1,
            amount=Decimal("25"),
            status=PledgeStatus.PAID,
            payment_provider="fake",
            payment_reference="pi_fail",
            idempotency_key="refund-fail",
        )
        provider = Mock()
        provider.refund.side_effect = RuntimeError("refund unavailable")
        with patch("gigs.services.get_payment_provider", return_value=provider):
            campaign = fail_and_refund_campaign(campaign.id, reason="No venue")
        pledge.refresh_from_db()
        self.assertEqual(pledge.status, PledgeStatus.REFUND_PENDING)
        self.assertEqual(campaign.status, CampaignStatus.REFUNDING)
        self.assertTrue(campaign.events.filter(event_type="pledge.refund_failed").exists())

    def test_paid_sponsor_without_reference_is_canceled(self):
        campaign = self.make_campaign(status=CampaignStatus.COLLECTING)
        sponsor = SponsorCommitment.objects.create(
            campaign=campaign,
            sponsor_name="Sponsor",
            contact_name="Contact",
            contact_email="s@example.com",
            amount=Decimal("100"),
            status=SponsorStatus.PAID,
            payment_reference="",
        )
        campaign = fail_and_refund_campaign(campaign.id)
        sponsor.refresh_from_db()
        self.assertEqual(sponsor.status, SponsorStatus.CANCELED)
        self.assertEqual(campaign.status, CampaignStatus.REFUNDED)

    def test_paid_sponsor_refund_success_and_failure(self):
        success_campaign = self.make_campaign(status=CampaignStatus.COLLECTING)
        success = SponsorCommitment.objects.create(
            campaign=success_campaign,
            sponsor_name="Success",
            contact_name="Contact",
            contact_email="success@example.com",
            amount=Decimal("100"),
            status=SponsorStatus.PAID,
            payment_reference="sp_success",
        )
        provider = Mock()
        provider.refund.return_value = "re_success"
        with patch("gigs.services.get_payment_provider", return_value=provider):
            campaign = fail_and_refund_campaign(success_campaign.id)
        success.refresh_from_db()
        self.assertEqual(success.status, SponsorStatus.REFUNDED)
        self.assertEqual(campaign.status, CampaignStatus.REFUNDED)
        self.assertTrue(campaign.events.filter(event_type="sponsor.refunded").exists())

        failure_campaign = self.make_campaign(title="Sponsor failure", status=CampaignStatus.COLLECTING)
        failed = SponsorCommitment.objects.create(
            campaign=failure_campaign,
            sponsor_name="Failure",
            contact_name="Contact",
            contact_email="failure@example.com",
            amount=Decimal("100"),
            status=SponsorStatus.FINALIZED,
            payment_reference="sp_fail",
        )
        provider.refund.side_effect = RuntimeError("processor down")
        with patch("gigs.services.get_payment_provider", return_value=provider):
            campaign = fail_and_refund_campaign(failure_campaign.id)
        failed.refresh_from_db()
        self.assertEqual(failed.status, SponsorStatus.REFUND_PENDING)
        self.assertEqual(campaign.status, CampaignStatus.REFUNDING)
        self.assertTrue(campaign.events.filter(event_type="sponsor.refund_failed").exists())

    def test_expire_due_campaigns_only_fails_unmet_collecting_campaigns(self):
        due = timezone.now() - timedelta(minutes=1)
        collecting = self.make_campaign(title="Collecting", status=CampaignStatus.COLLECTING, deadline=due)
        self.make_campaign(title="Reached", status=CampaignStatus.TARGET_REACHED, deadline=due)
        self.make_campaign(title="Confirming", status=CampaignStatus.CONFIRMING, deadline=due)
        with patch("gigs.services.fail_and_refund_campaign") as fail:
            self.assertEqual(expire_due_campaigns(), 1)
        fail.assert_called_once_with(collecting.id)
