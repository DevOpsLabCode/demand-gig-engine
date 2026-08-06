# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies deterministic campaign auto-approval, manual fallback, permissions, and audit evidence.

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from gigs.campaign_approval import (
    APPROVED,
    COLLECTING,
    PENDING_REVIEW,
    REJECTED,
    CampaignApprovalError,
    approve_campaign_manually,
    launch_approved_campaign,
    reject_campaign_manually,
    submit_campaign_for_review,
)
from gigs.campaign_review_models import CampaignReview, CampaignReviewDecision
from gigs.models import CampaignEvent, DemandCampaign, GoalType
from gigs.role_models import Role, RoleCode, RoleVerificationStatus, UserRole


class CampaignApprovalTests(TestCase):
    """Exercise automatic approval and administrator fallback as one state machine."""

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="organizer-owner",
            email="owner@example.com",
            password="StrongPass123!",
        )
        self.admin = get_user_model().objects.create_user(
            username="campaign-admin",
            email="admin@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.other = get_user_model().objects.create_user(
            username="other-user",
            email="other@example.com",
            password="StrongPass123!",
        )
        self.organizer_role = Role.objects.get(code=RoleCode.ORGANIZER)

    def make_campaign(self, **overrides):
        data = {
            "owner": self.owner,
            "title": "Bring Band X to New York",
            "pitch": "Validate demand before booking the artist and venue.",
            "artist_name": "Band X",
            "city": "New York",
            "deadline": timezone.now() + timedelta(days=30),
            "goal_type": GoalType.BOTH,
            "supporter_target": 100,
            "amount_target": Decimal("5000.00"),
            "suggested_deposit": Decimal("25.00"),
            "organizer_name": "Open Concert",
            "organizer_email": "owner@example.com",
        }
        data.update(overrides)
        return DemandCampaign.objects.create(**data)

    def verify_owner_as_organizer(self):
        return UserRole.objects.update_or_create(
            user=self.owner,
            role=self.organizer_role,
            defaults={
                "verification_status": RoleVerificationStatus.VERIFIED,
                "verified_by": self.admin,
                "verified_at": timezone.now(),
            },
        )[0]

    def test_passing_checks_auto_approve_and_launch(self):
        self.verify_owner_as_organizer()
        campaign = self.make_campaign()

        campaign, review = submit_campaign_for_review(campaign.id, self.owner)
        self.assertEqual(campaign.status, APPROVED)
        self.assertEqual(review.decision, CampaignReviewDecision.AUTO_APPROVED)
        self.assertTrue(all(check["passed"] for check in review.checks))

        campaign = launch_approved_campaign(campaign.id, self.owner)
        self.assertEqual(campaign.status, COLLECTING)
        self.assertTrue(
            CampaignEvent.objects.filter(
                campaign=campaign,
                event_type="campaign.launched",
            ).exists()
        )

    def test_failed_check_routes_campaign_to_manual_review(self):
        campaign = self.make_campaign()
        campaign, review = submit_campaign_for_review(campaign.id, self.owner)

        self.assertEqual(campaign.status, PENDING_REVIEW)
        self.assertEqual(
            review.decision,
            CampaignReviewDecision.MANUAL_REVIEW_REQUIRED,
        )
        failed_keys = {
            item["key"] for item in review.checks if not item["passed"]
        }
        self.assertIn("verified_organizer", failed_keys)
        with self.assertRaises(CampaignApprovalError):
            launch_approved_campaign(campaign.id, self.owner)

    def test_admin_can_approve_failed_auto_review(self):
        campaign, _ = submit_campaign_for_review(self.make_campaign().id, self.owner)

        campaign, review = approve_campaign_manually(
            campaign.id,
            self.admin,
            "Organizer identity and campaign details reviewed.",
        )
        self.assertEqual(campaign.status, APPROVED)
        self.assertEqual(review.decision, CampaignReviewDecision.MANUAL_APPROVED)
        self.assertEqual(review.reviewer, self.admin)

    def test_owner_cannot_manually_approve_own_campaign(self):
        self.owner.is_staff = True
        self.owner.save(update_fields=["is_staff"])
        campaign = self.make_campaign(status=PENDING_REVIEW)

        with self.assertRaises(CampaignApprovalError):
            approve_campaign_manually(campaign.id, self.owner, "Self approval")

    def test_rejection_requires_notes_and_allows_resubmission(self):
        campaign, _ = submit_campaign_for_review(self.make_campaign().id, self.owner)

        with self.assertRaises(CampaignApprovalError):
            reject_campaign_manually(campaign.id, self.admin, "")

        campaign, review = reject_campaign_manually(
            campaign.id,
            self.admin,
            "Add verified organizer credentials.",
        )
        self.assertEqual(campaign.status, REJECTED)
        self.assertEqual(review.decision, CampaignReviewDecision.REJECTED)

        self.verify_owner_as_organizer()
        campaign, review = submit_campaign_for_review(campaign.id, self.owner)
        self.assertEqual(campaign.status, APPROVED)
        self.assertEqual(review.previous_status, REJECTED)

    def test_review_records_are_append_only(self):
        campaign, review = submit_campaign_for_review(self.make_campaign().id, self.owner)
        review.notes = "Changed"
        with self.assertRaises(Exception):
            review.save()
        with self.assertRaises(Exception):
            review.delete()
        self.assertEqual(CampaignReview.objects.filter(campaign=campaign).count(), 1)

    def test_api_blocks_direct_draft_launch_and_auto_approves_after_role_verification(self):
        self.verify_owner_as_organizer()
        campaign = self.make_campaign()
        client = APIClient()
        client.force_authenticate(self.owner)

        direct = client.post(f"/api/campaigns/{campaign.slug}/launch/", {}, format="json")
        self.assertEqual(direct.status_code, 409)

        submitted = client.post(
            f"/api/campaigns/{campaign.slug}/submit-review/",
            {},
            format="json",
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.data["status"], APPROVED)
        self.assertEqual(
            submitted.data["latest_review"]["decision"],
            CampaignReviewDecision.AUTO_APPROVED,
        )

        launched = client.post(
            f"/api/campaigns/{campaign.slug}/launch/",
            {},
            format="json",
        )
        self.assertEqual(launched.status_code, 200)
        self.assertEqual(launched.data["status"], COLLECTING)

    def test_api_manual_queue_and_decisions_require_admin(self):
        campaign, _ = submit_campaign_for_review(self.make_campaign().id, self.owner)

        owner_client = APIClient()
        owner_client.force_authenticate(self.owner)
        denied = owner_client.get("/api/campaigns/review-queue/")
        self.assertEqual(denied.status_code, 403)

        admin_client = APIClient()
        admin_client.force_authenticate(self.admin)
        queue = admin_client.get("/api/campaigns/review-queue/")
        self.assertEqual(queue.status_code, 200)
        self.assertEqual(queue.data[0]["slug"], campaign.slug)

        approved = admin_client.post(
            f"/api/campaigns/{campaign.slug}/approve/",
            {"notes": "Manual evidence reviewed."},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["status"], APPROVED)

    def test_api_editing_is_limited_to_draft_or_rejected(self):
        campaign = self.make_campaign()
        client = APIClient()
        client.force_authenticate(self.owner)

        draft_edit = client.patch(
            f"/api/campaigns/{campaign.slug}/",
            {"pitch": "Updated before review."},
            format="json",
        )
        self.assertEqual(draft_edit.status_code, 200)

        submit_campaign_for_review(campaign.id, self.owner)
        blocked = client.patch(
            f"/api/campaigns/{campaign.slug}/",
            {"pitch": "Silent change after submission."},
            format="json",
        )
        self.assertEqual(blocked.status_code, 409)

    def test_existing_collecting_campaign_remains_valid_and_is_not_reviewed(self):
        campaign = self.make_campaign(status=COLLECTING)
        self.assertEqual(campaign.status, COLLECTING)
        self.assertFalse(CampaignReview.objects.filter(campaign=campaign).exists())
