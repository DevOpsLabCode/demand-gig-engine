# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies authentication configuration, session profile, logout, provider redirects, and ownership behavior.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Verifies authentication configuration, session profile, logout, provider redirects, and ownership behavior.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from datetime import timedelta
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import Client, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from gigs.models import (
    AccountType,
    CampaignStatus,
    DemandCampaign,
    GigUserProfile,
    Pledge,
    SponsorCommitment,
)
from gigs.signals import _synchronize_profile
from gigs.social_auth import (
    extract_avatar,
    provider_enabled,
    provider_login_path,
    provider_payload,
)


def campaign_payload(title="Bring Band X"):
    """
    Build a valid campaign API payload and merge caller-provided overrides.
    
    Args:
        title: Campaign title used to generate a stable slug or fixture.
    
    Returns:
        The typed result described in the function summary and return annotation.
    """
    return {
        "title": title,
        "pitch": "Demand first",
        "artist_name": "Band X",
        "city": "New York",
        "country": "United States",
        "deadline": (timezone.now() + timedelta(days=30)).isoformat(),
        "goal_type": "supporters",
        "supporter_target": 100,
        "amount_target": "0.00",
        "suggested_deposit": "25.00",
        "currency": "USD",
        "organizer_name": "Owner",
        "organizer_email": "owner@example.com",
    }


class TestSocialAuth:
    """
    Exercise TestSocialAuth behavior, edge cases, and failure handling with isolated tests.
    """
    def test_health_endpoint(self):
        """
        Verify that health endpoint.
        """
        response = APIClient().get("/api/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "demand-gig-backend"}

    @override_settings(ALLOWED_HOSTS=["example.com"])
    def test_health_endpoint_accepts_alb_private_ip_host(self):
        """Serve ALB probes without allowing private-IP hosts on application routes."""
        response = Client().get(
            "/api/health/",
            HTTP_HOST="10.0.1.23:8000",
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "demand-gig-backend",
        }

    @patch(
        "rest_framework.authentication.SessionAuthentication.authenticate",
        side_effect=OperationalError("session database unavailable"),
    )
    def test_health_endpoint_does_not_load_session(self, _authenticate):
        """Keep the ALB liveness check independent from the session database."""
        response = APIClient().get(
            "/api/health/",
            HTTP_COOKIE="sessionid=00000000000000000000000000000000",
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "demand-gig-backend"}

    def test_readiness_endpoint_checks_database(self, db):
        """Verify that deployment readiness includes the database used by login sessions."""
        response = APIClient().get("/api/readiness/")
        assert response.status_code == 200
        assert response.data == {"status": "ready", "service": "demand-gig-backend"}

    @patch(
        "gigs.auth_views.connection.cursor",
        side_effect=OperationalError("database unavailable"),
    )
    def test_readiness_endpoint_reports_database_failure(self, _cursor):
        """Return 503 when the running API task cannot reach its session database."""
        response = APIClient().get("/api/readiness/")
        assert response.status_code == 503
        assert response.data == {
            "status": "unavailable",
            "service": "demand-gig-backend",
        }

    def test_avatar_extraction(self):
        """
        Verify that avatar extraction.
        """
        assert extract_avatar({"picture": "https://example.com/a.png"}).endswith("a.png")
        assert extract_avatar({"picture": {"data": {"url": "https://example.com/b.png"}}}).endswith("b.png")
        assert extract_avatar({"avatar_url": "https://example.com/c.png"}).endswith("c.png")
        assert extract_avatar({"avatar": "https://example.com/d.png"}).endswith("d.png")
        assert extract_avatar({"picture": {"data": "bad"}}) == ""
        assert extract_avatar({}) == ""

    @override_settings(
        SOCIAL_AUTH_ALLOWED_PROVIDERS={"google"},
        SOCIALACCOUNT_PROVIDERS={"google": {"APP": {"client_id": "id", "secret": "secret"}}},
    )
    def test_provider_enabled(self):
        """
        Verify that provider enabled.
        """
        assert provider_enabled("google") is True
        assert provider_enabled("facebook") is False

    @override_settings(
        SOCIAL_AUTH_ALLOWED_PROVIDERS={"google"},
        SOCIALACCOUNT_PROVIDERS={"google": {"APP": {"client_id": "", "secret": ""}}},
    )
    def test_provider_requires_credentials(self):
        """
        Verify that provider requires credentials.
        """
        assert provider_enabled("google") is False

    def test_provider_routes(self):
        """
        Verify that provider routes.
        """
        assert provider_login_path("google").endswith("/accounts/google/login/")
        assert provider_login_path("not-a-provider") == ""

    @patch("gigs.social_auth.provider_login_path", side_effect=lambda provider: f"/accounts/{provider}/login/")
    def test_provider_payload_lists_all_providers(self, _mock):
        """
        Verify that provider payload lists all providers.
        
        Args:
            _mock: Injected mock object supplied by the test framework.
        """
        payload = provider_payload()
        assert [item["id"] for item in payload] == ["google", "facebook", "instagram", "tiktok"]
        assert all(item["callback_path"].endswith("/login/callback/") for item in payload)

    @override_settings(
        SOCIAL_AUTH_ALLOWED_PROVIDERS={"google"},
        SOCIALACCOUNT_PROVIDERS={"google": {"APP": {"client_id": "id", "secret": "secret"}}},
    )
    @patch("gigs.social_auth.provider_login_path", return_value="")
    def test_provider_without_registered_route_is_disabled(self, _mock):
        """
        Verify that provider without registered route is disabled.
        
        Args:
            _mock: Injected mock object supplied by the test framework.
        """
        assert provider_payload()[0]["enabled"] is False

    def test_auth_config_anonymous_and_profile_update(self, db):
        """
        Verify that auth config anonymous and profile update.
        
        Args:
            db: Django database alias on which the signal or transaction is operating.
        """
        client = APIClient()
        response = client.get("/api/auth/config/")
        assert response.status_code == 200
        assert response.data["authenticated"] is False
        assert len(response.data["providers"]) == 4
        assert response.data["csrf_token"]

        assert client.get("/api/auth/profile/").status_code in (401, 403)

        user = get_user_model().objects.create_user(username="organizer", email="organizer@example.com")
        client.force_login(user)
        response = client.patch(
            "/api/auth/profile/",
            {
                "account_type": AccountType.ORGANIZER,
                "display_name": "  Gig Maker  ",
                "company_name": "  Open Concert  ",
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["account_type"] == AccountType.ORGANIZER
        profile = GigUserProfile.objects.get(user=user)
        assert profile.display_name == "Gig Maker"
        assert profile.company_name == "Open Concert"

        bad = client.patch("/api/auth/profile/", {"account_type": "invalid"}, format="json")
        assert bad.status_code == 400
        bad_url = client.patch("/api/auth/profile/", {"avatar_url": "not-a-url"}, format="json")
        assert bad_url.status_code == 400

        logout = client.post("/api/auth/logout/")
        assert logout.status_code == 204

    @patch(
        "rest_framework.authentication.SessionAuthentication.authenticate",
        side_effect=OperationalError("session database unavailable"),
    )
    def test_auth_config_survives_session_database_failure(self, _authenticate):
        """Keep public sign-in discovery available when a stale session cannot be loaded."""
        response = APIClient().get(
            "/api/auth/config/",
            HTTP_COOKIE="sessionid=00000000000000000000000000000000",
        )

        assert response.status_code == 200
        assert response.data["authenticated"] is False
        assert len(response.data["providers"]) == 4
        assert response.data["csrf_token"]

    def test_auth_config_serializes_social_account_and_avatar(self, db):
        """
        Verify that auth config serializes social account and avatar.
        
        Args:
            db: Django database alias on which the signal or transaction is operating.
        """
        user = get_user_model().objects.create_user(username="fan", email="fan@example.com")
        SocialAccount.objects.create(
            user=user,
            provider="google",
            uid="google-user-1",
            extra_data={"name": "Social Fan", "picture": "https://example.com/fan.png"},
        )
        client = APIClient()
        client.force_login(user)
        response = client.get("/api/auth/config/")
        assert response.status_code == 200
        assert response.data["user"]["linked_providers"] == ["google"]
        assert response.data["user"]["avatar_url"] == "https://example.com/fan.png"

    def test_profile_signal_sync(self, db):
        """
        Verify that profile signal sync.
        
        Args:
            db: Django database alias on which the signal or transaction is operating.
        """
        user = get_user_model().objects.create_user(username="band", email="band@example.com")
        profile = GigUserProfile.objects.get(user=user)
        assert profile.account_type == AccountType.FAN

        _synchronize_profile(
            user,
            {"name": "The Test Band", "picture": {"data": {"url": "https://example.com/band.png"}}},
        )
        profile.refresh_from_db()
        assert profile.display_name == "The Test Band"
        assert profile.avatar_url == "https://example.com/band.png"

        # Reapplying identical data should be a no-op.
        _synchronize_profile(user, {"name": "The Test Band", "picture": "https://example.com/band.png"})

    def test_authenticated_campaign_is_owned(self, db):
        """
        Verify that authenticated campaign is owned.
        
        Args:
            db: Django database alias on which the signal or transaction is operating.
        """
        user = get_user_model().objects.create_user(username="owner", email="owner@example.com")
        client = APIClient()
        client.force_login(user)
        response = client.post("/api/campaigns/", campaign_payload(), format="json")
        assert response.status_code == 201
        campaign = DemandCampaign.objects.get(slug=response.data["slug"])
        assert campaign.owner == user
        assert response.data["owner"]["id"] == user.id

    def test_campaign_management_requires_owner_but_allows_staff(self, db):
        """
        Verify that campaign management requires owner but allows staff.
        
        Args:
            db: Django database alias on which the signal or transaction is operating.
        """
        client = APIClient()
        payload = campaign_payload("Protected gig")
        assert client.post("/api/campaigns/", payload, format="json").status_code in (401, 403)

        owner = get_user_model().objects.create_user(username="owner2", email="owner2@example.com")
        other = get_user_model().objects.create_user(username="other", email="other@example.com")
        staff = get_user_model().objects.create_user(username="staff", email="staff@example.com", is_staff=True)
        client.force_login(owner)
        created = client.post("/api/campaigns/", payload, format="json")
        assert created.status_code == 201
        slug = created.data["slug"]

        client.force_login(other)
        assert client.post(f"/api/campaigns/{slug}/launch/", {}, format="json").status_code == 403

        client.force_login(staff)
        launched = client.post(f"/api/campaigns/{slug}/launch/", {}, format="json")
        assert launched.status_code == 200
        assert launched.data["status"] == CampaignStatus.COLLECTING

    def test_authenticated_pledge_and_sponsor_are_linked_to_user(self, db):
        """
        Verify that authenticated pledge and sponsor are linked to user.
        
        Args:
            db: Django database alias on which the signal or transaction is operating.
        """
        owner = get_user_model().objects.create_user(username="gig-owner", email="gig-owner@example.com")
        supporter = get_user_model().objects.create_user(username="supporter", email="supporter@example.com")
        client = APIClient()
        client.force_login(owner)
        created = client.post("/api/campaigns/", campaign_payload("Owned gig"), format="json")
        slug = created.data["slug"]
        assert client.post(f"/api/campaigns/{slug}/launch/", {}, format="json").status_code == 200

        client.force_login(supporter)
        pledge = client.post(
            f"/api/campaigns/{slug}/pledge/",
            {
                "supporter_name": "Supporter",
                "supporter_email": "supporter@example.com",
                "quantity": 1,
                "amount": "0.00",
                "idempotency_key": "social-auth-pledge-1",
            },
            format="json",
        )
        assert pledge.status_code == 201
        assert Pledge.objects.get(pk=pledge.data["pledge"]["id"]).supporter_user == supporter

        sponsor = client.post(
            f"/api/campaigns/{slug}/sponsor/",
            {
                "sponsor_name": "Sponsor Inc",
                "contact_name": "Supporter",
                "contact_email": "supporter@example.com",
                "amount": "500.00",
                "benefits_requested": "Logo placement",
            },
            format="json",
        )
        assert sponsor.status_code == 201
        assert SponsorCommitment.objects.get(pk=sponsor.data["id"]).contact_user == supporter
