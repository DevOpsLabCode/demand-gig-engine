# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies verified-email rollout, campaign location metadata, rich public profiles, SES delivery, and profile-media ownership for Phase 2.

from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.mail import EmailMessage
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from config.ses_email_backend import EmailBackend
from gigs.account_trust import email_is_verified
from gigs.campaign_approval import run_automatic_campaign_checks
from gigs.discovery_models import CampaignLocation, ProfileMedia
from gigs.models import DemandCampaign, GoalType
from gigs.serializers import CampaignSerializer


class Phase2DiscoveryProfileTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="phase2-member",
            email="member@example.com",
            password="StrongPass123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def campaign_data(self):
        return {
            "title": "Bring Band X to New York",
            "pitch": "Prove city demand before anyone takes the booking risk.",
            "artist_name": "Band X",
            "city": "New York",
            "state": "NY",
            "country": "United States",
            "deadline": timezone.now() + timedelta(days=30),
            "goal_type": GoalType.BOTH,
            "supporter_target": 100,
            "amount_target": Decimal("5000.00"),
            "suggested_deposit": Decimal("25.00"),
            "currency": "USD",
            "organizer_name": "Open Concert",
            "organizer_email": "member@example.com",
        }

    def test_legacy_account_without_allauth_record_is_grandfathered(self):
        self.assertTrue(email_is_verified(self.user))

    def test_explicit_unverified_email_requires_confirmation(self):
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            primary=True,
            verified=False,
        )
        self.assertFalse(email_is_verified(self.user))

        address = EmailAddress.objects.get(user=self.user, email=self.user.email)
        address.verified = True
        address.save(update_fields=["verified"])
        self.assertTrue(email_is_verified(self.user))

    @patch("allauth.account.models.EmailAddress.send_confirmation")
    def test_registration_creates_unverified_email_and_sends_confirmation(self, send_confirmation):
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            {
                "display_name": "New Member",
                "email": "newmember@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        registered = get_user_model().objects.get(email="newmember@example.com")
        address = EmailAddress.objects.get(user=registered, email="newmember@example.com")
        self.assertFalse(address.verified)
        self.assertFalse(response.data["email_verified"])
        self.assertTrue(response.data["verification_sent"])
        send_confirmation.assert_called_once()

    @patch("allauth.account.models.EmailAddress.send_confirmation", side_effect=RuntimeError("mail unavailable"))
    def test_registration_reports_verification_delivery_failure(self, _send_confirmation):
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            {
                "display_name": "Mail Test",
                "email": "mailfail@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["verification_sent"])
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_campaign_serializer_persists_state_without_changing_campaign_table(self):
        serializer = CampaignSerializer(data=self.campaign_data())
        serializer.is_valid(raise_exception=True)
        campaign = serializer.save(owner=self.user)

        location = CampaignLocation.objects.get(campaign=campaign)
        self.assertEqual(location.state, "NY")
        self.assertEqual(CampaignSerializer(campaign).data["state"], "NY")

    def test_stage2_check_blocks_explicitly_unverified_owner(self):
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            primary=True,
            verified=False,
        )
        campaign = DemandCampaign.objects.create(
            owner=self.user,
            **{key: value for key, value in self.campaign_data().items() if key != "state"},
        )

        checks = {item.key: item for item in run_automatic_campaign_checks(campaign)}
        self.assertIn("owner_email_verified", checks)
        self.assertFalse(checks["owner_email_verified"].passed)

        address = EmailAddress.objects.get(user=self.user, email=self.user.email)
        address.verified = True
        address.save(update_fields=["verified"])
        checks = {item.key: item for item in run_automatic_campaign_checks(campaign)}
        self.assertTrue(checks["owner_email_verified"].passed)

    def test_discovery_profile_updates_state_and_followed_cities(self):
        response = self.client.patch(
            "/api/auth/discovery-profile/",
            {"state": "NY", "preferred_cities": ["New York, NY", "Boston, MA"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], "NY")
        self.assertEqual(response.data["preferred_cities"], ["New York, NY", "Boston, MA"])

    def test_rich_profile_accepts_social_links_genres_and_external_videos(self):
        response = self.client.patch(
            "/api/auth/discovery-profile/",
            {
                "headline": "Brooklyn band ready for Northeast dates",
                "genres": ["Punk", "Rock", "Punk"],
                "social_links": {
                    "youtube": "https://youtube.com/@bandx",
                    "instagram": "https://instagram.com/bandx",
                    "website": "https://bandx.example.com",
                },
                "external_video_urls": [
                    "https://youtu.be/abc123",
                    "https://vimeo.com/123456",
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["headline"], "Brooklyn band ready for Northeast dates")
        self.assertEqual(response.data["genres"], ["Punk", "Rock"])
        self.assertEqual(response.data["social_links"]["youtube"], "https://youtube.com/@bandx")
        self.assertEqual(len(response.data["external_video_urls"]), 2)

    def test_rich_profile_rejects_invalid_social_and_video_urls(self):
        bad_social = self.client.patch(
            "/api/auth/discovery-profile/",
            {"social_links": {"youtube": "javascript:alert(1)"}},
            format="json",
        )
        self.assertEqual(bad_social.status_code, 400)

        bad_video = self.client.patch(
            "/api/auth/discovery-profile/",
            {"external_video_urls": ["https://untrusted.example/video"]},
            format="json",
        )
        self.assertEqual(bad_video.status_code, 400)

    def test_public_profile_exposes_identity_but_not_email(self):
        profile = self.user.gig_profile
        profile.display_name = "Band X"
        profile.account_type = "band"
        profile.bio = "Live band profile"
        profile.city = "New York"
        profile.country = "United States"
        profile.save()
        self.client.patch(
            "/api/auth/discovery-profile/",
            {
                "state": "NY",
                "headline": "Band X live",
                "genres": ["Punk"],
                "social_links": {"youtube": "https://youtube.com/@bandx"},
            },
            format="json",
        )

        public = APIClient().get("/api/profiles/phase2-member/")
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.data["display_name"], "Band X")
        self.assertEqual(public.data["account_type"], "band")
        self.assertEqual(public.data["state"], "NY")
        self.assertNotIn("email", public.data)
        self.assertNotIn("email_verified", public.data)

    def test_profile_media_upload_and_owner_only_delete(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            upload = SimpleUploadedFile(
                "profile.jpg",
                b"\xff\xd8\xff\xe0phase2-image",
                content_type="image/jpeg",
            )
            response = self.client.post(
                "/api/auth/profile/media/",
                {"media_type": "image", "caption": "Live show", "file": upload},
                format="multipart",
            )
            self.assertEqual(response.status_code, 201)
            media = ProfileMedia.objects.get(pk=response.data["id"])
            self.assertEqual(media.user, self.user)

            other = get_user_model().objects.create_user(
                username="phase2-other",
                email="other-phase2@example.com",
                password="StrongPass123!",
            )
            other_client = APIClient()
            other_client.force_authenticate(other)
            denied = other_client.delete(f"/api/auth/profile/media/{media.id}/")
            self.assertEqual(denied.status_code, 404)

            deleted = self.client.delete(f"/api/auth/profile/media/{media.id}/")
            self.assertEqual(deleted.status_code, 204)
            self.assertFalse(ProfileMedia.objects.filter(pk=media.id).exists())

    def test_profile_media_rejects_mismatched_extension_and_type(self):
        upload = SimpleUploadedFile(
            "not-video.txt",
            b"not a video",
            content_type="text/plain",
        )
        response = self.client.post(
            "/api/auth/profile/media/",
            {"media_type": "video", "file": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    @patch("allauth.account.models.EmailAddress.send_confirmation", side_effect=RuntimeError("SES unavailable"))
    def test_resend_verification_returns_503_when_delivery_fails(self, _send_confirmation):
        EmailAddress.objects.create(user=self.user, email=self.user.email, primary=True, verified=False)
        response = self.client.post("/api/auth/email/resend-verification/", {}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.data["email_verified"])

    @patch("config.ses_email_backend.boto3.client")
    def test_ses_backend_uses_task_role_client(self, client_factory):
        ses = MagicMock()
        client_factory.return_value = ses
        message = EmailMessage(
            subject="Verify your email",
            body="Use the confirmation link.",
            from_email="Open Concert <no-reply@example.com>",
            to=["member@example.com"],
        )
        backend = EmailBackend(fail_silently=False)
        self.assertEqual(backend.send_messages([message]), 1)
        client_factory.assert_called_once_with("ses", region_name="us-east-1")
        ses.send_raw_email.assert_called_once()
