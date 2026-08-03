# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies credential registration, login, session handling, and marketplace-profile promotion.

"""Credential authentication and member-to-marketplace-profile tests."""

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from gigs.models import AccountType, GigUserProfile


STRONG_PASSWORD = "OpenConcert!2026-Ready"


def registration_payload(email="new-member@example.com"):
    """Return a valid first-page account-registration payload."""
    return {
        "display_name": "New Member",
        "email": email,
        "password": STRONG_PASSWORD,
        "password_confirm": STRONG_PASSWORD,
    }


class TestCredentialAuthentication:
    """Exercise the username/password entry flow shown on the first page."""

    def test_register_starts_session_as_community_member(self, db):
        """Create a normal user, default its marketplace profile, and sign it in."""
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            registration_payload(),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["email"] == "new-member@example.com"
        assert response.data["display_name"] == "New Member"
        assert response.data["account_type"] == AccountType.FAN

        user = get_user_model().objects.get(email="new-member@example.com")
        assert user.check_password(STRONG_PASSWORD)
        assert GigUserProfile.objects.get(user=user).account_type == AccountType.FAN

        config = client.get("/api/auth/config/")
        assert config.status_code == 200
        assert config.data["authenticated"] is True
        assert config.data["user"]["id"] == user.id
        assert config.data["password_auth_enabled"] is True

    def test_login_accepts_email_and_username(self, db):
        """Allow either familiar email login or the generated account username."""
        client = APIClient()
        registered = client.post(
            "/api/auth/register/",
            registration_payload("login-member@example.com"),
            format="json",
        )
        assert registered.status_code == 201
        username = registered.data["username"]

        assert client.post("/api/auth/logout/").status_code == 204

        by_email = client.post(
            "/api/auth/login/",
            {
                "identifier": "LOGIN-MEMBER@example.com",
                "password": STRONG_PASSWORD,
            },
            format="json",
        )
        assert by_email.status_code == 200

        assert client.post("/api/auth/logout/").status_code == 204

        by_username = client.post(
            "/api/auth/login/",
            {
                "identifier": username,
                "password": STRONG_PASSWORD,
            },
            format="json",
        )
        assert by_username.status_code == 200
        assert by_username.data["email"] == "login-member@example.com"

    def test_login_rejects_invalid_password_without_leaking_account_state(self, db):
        """Return one generic message for invalid credentials."""
        client = APIClient()
        client.post(
            "/api/auth/register/",
            registration_payload("protected@example.com"),
            format="json",
        )
        client.post("/api/auth/logout/")

        response = client.post(
            "/api/auth/login/",
            {
                "identifier": "protected@example.com",
                "password": "WrongPassword!2026",
            },
            format="json",
        )

        assert response.status_code == 401
        assert response.data["detail"] == (
            "The email/username or password is incorrect."
        )

    def test_registration_rejects_duplicate_email_and_password_mismatch(self, db):
        """Protect unique email identity and require explicit password confirmation."""
        client = APIClient()
        assert client.post(
            "/api/auth/register/",
            registration_payload("duplicate@example.com"),
            format="json",
        ).status_code == 201
        client.post("/api/auth/logout/")

        duplicate = client.post(
            "/api/auth/register/",
            registration_payload("DUPLICATE@example.com"),
            format="json",
        )
        assert duplicate.status_code == 400
        assert "email" in duplicate.data

        mismatch_payload = registration_payload("mismatch@example.com")
        mismatch_payload["password_confirm"] = "DifferentPassword!2026"
        mismatch = client.post(
            "/api/auth/register/",
            mismatch_payload,
            format="json",
        )
        assert mismatch.status_code == 400
        assert "password_confirm" in mismatch.data

    def test_member_can_be_promoted_to_venue_or_equipment_vendor(self, db):
        """Keep the same user identity while switching on a professional profile."""
        client = APIClient()
        registered = client.post(
            "/api/auth/register/",
            registration_payload("marketplace@example.com"),
            format="json",
        )
        user_id = registered.data["id"]

        venue = client.patch(
            "/api/auth/profile/",
            {
                "account_type": AccountType.VENUE,
                "company_name": "Open Concert Hall",
            },
            format="json",
        )
        assert venue.status_code == 200
        assert venue.data["id"] == user_id
        assert venue.data["account_type"] == AccountType.VENUE

        vendor = client.patch(
            "/api/auth/profile/",
            {
                "account_type": AccountType.RENTAL,
                "company_name": "Open Concert Equipment",
            },
            format="json",
        )
        assert vendor.status_code == 200
        assert vendor.data["id"] == user_id
        assert vendor.data["account_type"] == AccountType.RENTAL
        assert get_user_model().objects.filter(pk=user_id).exists()
