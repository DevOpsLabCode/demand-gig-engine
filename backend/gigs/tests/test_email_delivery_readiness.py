# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Ensures SES diagnostics explain delivery state without incorrectly blocking the real verification send.

from unittest.mock import Mock, patch

from allauth.account.models import EmailAddress
from botocore.exceptions import ClientError
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from config.ses_email_backend import SES_BACKEND, safe_ses_send_error, ses_delivery_status


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_non_ses_backend_is_ready_without_aws_calls():
    with patch("config.ses_email_backend.boto3.client") as client:
        result = ses_delivery_status()
    assert result["ready"] is True
    assert result["provider"] == "non_ses"
    assert result["diagnostics_complete"] is True
    client.assert_not_called()


@override_settings(
    EMAIL_BACKEND=SES_BACKEND,
    AWS_REGION="us-east-1",
    DEFAULT_FROM_EMAIL="Open Concert <no-reply@devopslabinc.com>",
    SES_IDENTITY="devopslabinc.com",
)
def test_ses_sandbox_is_not_ready_for_unknown_recipient():
    sesv2 = Mock()
    sesv2.get_account.return_value = {
        "SendingEnabled": True,
        "ProductionAccessEnabled": False,
    }
    sesv2.get_email_identity.return_value = {"VerifiedForSendingStatus": True}

    with patch("config.ses_email_backend.boto3.client", return_value=sesv2):
        result = ses_delivery_status()

    assert result["ready"] is False
    assert result["diagnostics_complete"] is True
    assert result["production_access"] is False
    assert result["sender_verified"] is True
    assert result["recipient_verified"] is False
    assert result["reason"] == "ses_sandbox"
    assert "sandbox" in result["detail"].lower()


@override_settings(
    EMAIL_BACKEND=SES_BACKEND,
    AWS_REGION="us-east-1",
    DEFAULT_FROM_EMAIL="Open Concert <no-reply@devopslabinc.com>",
    SES_IDENTITY="devopslabinc.com",
)
def test_ses_sandbox_allows_recipient_covered_by_verified_domain():
    sesv2 = Mock()
    sesv2.get_account.return_value = {
        "SendingEnabled": True,
        "ProductionAccessEnabled": False,
    }
    sesv2.get_email_identity.return_value = {"VerifiedForSendingStatus": True}

    with patch("config.ses_email_backend.boto3.client", return_value=sesv2):
        result = ses_delivery_status("hello@devopslabinc.com")

    assert result["ready"] is True
    assert result["production_access"] is False
    assert result["sender_verified"] is True
    assert result["recipient_verified"] is True
    assert result["reason"] == "ready_sandbox_verified_recipient"
    assert "can receive" in result["detail"].lower()
    assert sesv2.get_email_identity.call_count == 1


@override_settings(
    EMAIL_BACKEND=SES_BACKEND,
    AWS_REGION="us-east-1",
    DEFAULT_FROM_EMAIL="Open Concert <no-reply@devopslabinc.com>",
    SES_IDENTITY="devopslabinc.com",
)
def test_ses_sandbox_checks_external_recipient_identity():
    sesv2 = Mock()
    sesv2.get_account.return_value = {
        "SendingEnabled": True,
        "ProductionAccessEnabled": False,
    }
    sesv2.get_email_identity.side_effect = [
        {"VerifiedForSendingStatus": True},
        {"VerifiedForSendingStatus": True},
    ]

    with patch("config.ses_email_backend.boto3.client", return_value=sesv2):
        result = ses_delivery_status("verified@example.com")

    assert result["ready"] is True
    assert result["recipient_verified"] is True
    assert result["reason"] == "ready_sandbox_verified_recipient"
    assert sesv2.get_email_identity.call_count == 2


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
    assert result["diagnostics_complete"] is True
    assert result["production_access"] is True
    assert result["sender_verified"] is True
    assert result["reason"] == "ready"


@override_settings(
    EMAIL_BACKEND=SES_BACKEND,
    AWS_REGION="us-east-1",
    DEFAULT_FROM_EMAIL="Open Concert <no-reply@devopslabinc.com>",
    SES_IDENTITY="devopslabinc.com",
)
def test_ses_diagnostic_access_denied_is_specific_but_does_not_claim_send_failure():
    sesv2 = Mock()
    sesv2.get_account.side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "not authorized"}},
        "GetAccount",
    )
    sesv2.get_email_identity.return_value = {"VerifiedForSendingStatus": True}

    with patch("config.ses_email_backend.boto3.client", return_value=sesv2):
        result = ses_delivery_status()

    assert result["ready"] is False
    assert result["diagnostics_complete"] is False
    assert result["sender_verified"] is True
    assert result["reason"] == "account_diagnostic_denied"
    assert "still test delivery directly" in result["detail"].lower()


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


def test_resend_attempts_real_send_when_diagnostics_are_unavailable(db):
    client, _user = _signed_in_client()
    delivery = {
        "provider": "ses",
        "ready": False,
        "diagnostics_complete": False,
        "sending_enabled": False,
        "production_access": False,
        "sender_verified": True,
        "recipient_verified": False,
        "reason": "account_diagnostic_denied",
        "detail": "SES diagnostic access is limited. Direct delivery will still be attempted.",
    }

    with patch("gigs.email_views.ses_delivery_status", return_value=delivery) as diagnostic, patch.object(
        EmailAddress,
        "send_confirmation",
    ) as send_confirmation:
        response = client.post("/api/auth/email/resend-verification/", {}, format="json")

    assert response.status_code == 202
    assert response.data["email_verified"] is False
    assert response.data["delivery"]["accepted"] is True
    assert response.data["delivery"]["reason"] == "accepted"
    diagnostic.assert_called_once_with("delivery@example.com")
    send_confirmation.assert_called_once()


def test_resend_returns_503_only_when_actual_ses_send_is_rejected(db):
    client, _user = _signed_in_client("rejected@example.com")
    delivery = {
        "provider": "ses",
        "ready": False,
        "diagnostics_complete": True,
        "sending_enabled": True,
        "production_access": False,
        "sender_verified": True,
        "recipient_verified": False,
        "reason": "ses_sandbox",
        "detail": "Amazon SES is still in sandbox mode.",
    }
    rejection = ClientError(
        {
            "Error": {
                "Code": "MessageRejected",
                "Message": "Email address is not verified. The following identities failed the check.",
            }
        },
        "SendRawEmail",
    )

    with patch("gigs.email_views.ses_delivery_status", return_value=delivery), patch.object(
        EmailAddress,
        "send_confirmation",
        side_effect=rejection,
    ):
        response = client.post("/api/auth/email/resend-verification/", {}, format="json")

    assert response.status_code == 503
    assert response.data["email_verified"] is False
    assert response.data["delivery"]["accepted"] is False
    assert response.data["delivery"]["reason"] == "identity_not_verified"
    assert "sandbox" in response.data["detail"].lower()


def test_resend_returns_202_after_provider_accepts_message(db):
    client, user = _signed_in_client("accepted@example.com")
    delivery = {
        "provider": "ses",
        "ready": True,
        "diagnostics_complete": True,
        "sending_enabled": True,
        "production_access": True,
        "sender_verified": True,
        "recipient_verified": True,
        "reason": "ready",
        "detail": "Amazon SES diagnostics are healthy.",
    }

    with patch("gigs.email_views.ses_delivery_status", return_value=delivery), patch.object(
        EmailAddress,
        "send_confirmation",
    ) as send_confirmation:
        response = client.post("/api/auth/email/resend-verification/", {}, format="json")

    assert response.status_code == 202
    assert response.data["email_verified"] is False
    assert response.data["delivery"]["accepted"] is True
    assert response.data["delivery"]["reason"] == "accepted"
    send_confirmation.assert_called_once()
    assert EmailAddress.objects.get(user=user).verified is False


def test_email_delivery_status_endpoint_uses_signed_in_recipient_and_is_safe(db):
    client, _user = _signed_in_client("status@example.com")
    delivery = {
        "provider": "ses",
        "ready": False,
        "diagnostics_complete": False,
        "sending_enabled": False,
        "production_access": False,
        "sender_verified": False,
        "recipient_verified": False,
        "reason": "identity_diagnostic_denied",
        "detail": "SES diagnostic access is limited for this task role.",
        "code": "AccessDeniedException",
    }

    with patch("gigs.email_views.ses_delivery_status", return_value=delivery) as diagnostic:
        response = client.get("/api/auth/email/status/")

    assert response.status_code == 200
    assert response.data["ready"] is False
    assert response.data["reason"] == "identity_diagnostic_denied"
    assert response.data["detail"] == delivery["detail"]
    assert response.data["recipient_verified"] is False
    assert "code" not in response.data
    diagnostic.assert_called_once_with("status@example.com")


def test_safe_ses_send_error_classifies_access_denied():
    exc = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "not authorized"}},
        "SendRawEmail",
    )
    reason, detail = safe_ses_send_error(exc)
    assert reason == "send_permission_denied"
    assert "task role" in detail.lower()
