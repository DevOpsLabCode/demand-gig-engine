# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Prevents verification email from reporting success when SES is sandboxed, disabled, or unverified.

from unittest.mock import Mock, patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from config.ses_email_backend import SES_BACKEND, ses_delivery_status


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_non_ses_backend_is_ready_without_aws_calls():
    with patch("config.ses_email_backend.boto3.client") as client:
        result = ses_delivery_status()
    assert result["ready"] is True
    assert result["provider"] == "non_ses"
    client.assert_not_called()


@override_settings(
    EMAIL_BACKEND=SES_BACKEND,
    AWS_REGION="us-east-1",
    DEFAULT_FROM_EMAIL="Open Concert <no-reply@devopslabinc.com>",
    SES_IDENTITY="devopslabinc.com",
)
def test_ses_sandbox_is_not_ready():
    sesv2 = Mock()
    sesv2.get_account.return_value = {
        "SendingEnabled": True,
        "ProductionAccessEnabled": False,
    }
    sesv2.get_email_identity.return_value = {"VerifiedForSendingStatus": True}

    with patch("config.ses_email_backend.boto3.client", return_value=sesv2):
        result = ses_delivery_status()

    assert result["ready"] is False
    assert result["production_access"] is False
    assert result["sender_verified"] is True
    assert "sandbox" in result["detail"].lower()


@override_settings(
    EMAIL_BACKEND=SES_BACKEND,
    AWS_REGION="us-east-1",
    DEFAULT_FROM_EMAIL="Open Concert <no-reply@devopslabinc.com>",
    SES_IDENTITY="devopslabinc.com",
)
def test_ses_verified_production_account_is_ready():
    sesv2 = Mock()
    sesv2.get_account.return_value = {
        "SendingEnabled": True,
        "ProductionAccessEnabled": True,
    }
    sesv2.get_email_identity.return_value = {"VerifiedForSendingStatus": True}

    with patch("config.ses_email_backend.boto3.client", return_value=sesv2):
        result = ses_delivery_status()

    assert result["ready"] is True
    assert result["production_access"] is True
    assert result["sender_verified"] is True


def _signed_in_client(email="delivery@example.com"):
    user = get_user_model().objects.create_user(
        username="delivery-member",
        email=email,
        password="OpenConcert!2026-Ready",
    )
    EmailAddress.objects.create(user=user, email=email, primary=True, verified=False)
    client = APIClient()
    client.force_login(user)
    return client, user


def test_resend_returns_503_when_delivery_is_not_ready(db):
    client, _user = _signed_in_client()
    delivery = {
        "provider": "ses",
        "ready": False,
        "sending_enabled": True,
        "production_access": False,
        "sender_verified": True,
        "detail": "Amazon SES is still in sandbox mode. Public verification emails require SES production access.",
    }

    with patch("gigs.email_views.ses_delivery_status", return_value=delivery):
        response = client.post("/api/auth/email/resend-verification/", {}, format="json")

    assert response.status_code == 503
    assert response.data["email_verified"] is False
    assert response.data["delivery"]["ready"] is False
    assert "sandbox" in response.data["detail"].lower()


def test_resend_returns_202_after_provider_accepts_message(db):
    client, user = _signed_in_client("accepted@example.com")
    delivery = {
        "provider": "ses",
        "ready": True,
        "sending_enabled": True,
        "production_access": True,
        "sender_verified": True,
        "detail": "Amazon SES is ready for public verification-email delivery.",
    }

    with patch("gigs.email_views.ses_delivery_status", return_value=delivery), patch.object(
        EmailAddress,
        "send_confirmation",
    ) as send_confirmation:
        response = client.post("/api/auth/email/resend-verification/", {}, format="json")

    assert response.status_code == 202
    assert response.data["email_verified"] is False
    assert response.data["delivery"]["ready"] is True
    send_confirmation.assert_called_once()
    assert EmailAddress.objects.get(user=user).verified is False


def test_email_delivery_status_endpoint_is_safe(db):
    client, _user = _signed_in_client("status@example.com")
    delivery = {
        "provider": "ses",
        "ready": False,
        "sending_enabled": False,
        "production_access": False,
        "sender_verified": False,
        "detail": "The Open Concert sender identity is not verified in Amazon SES.",
        "code": "AccessDeniedException",
    }

    with patch("gigs.email_views.ses_delivery_status", return_value=delivery):
        response = client.get("/api/auth/email/status/")

    assert response.status_code == 200
    assert response.data["ready"] is False
    assert response.data["detail"] == delivery["detail"]
    assert "code" not in response.data
