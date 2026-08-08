# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Ensures SES diagnostics, direct verification delivery, signed confirmation, and safe failures behave correctly.

from unittest.mock import Mock, patch

from allauth.account.models import EmailAddress
from botocore.exceptions import ClientError
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.test import override_settings
from rest_framework.test import APIClient

from config.ses_email_backend import EmailBackend, SES_BACKEND, safe_ses_send_error, ses_delivery_status
from gigs.email_verification import _verification_token, confirm_verification_token


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
def test_ses_sandbox_is_not_ready_without_a_verified_recipient():
    sesv2 = Mock()
    sesv2.get_account.return_value = {"SendingEnabled": True, "ProductionAccessEnabled": False}
    sesv2.get_email_identity.return_value = {"VerifiedForSendingStatus": True}
    with patch("config.ses_email_backend.boto3.client", return_value=sesv2):
        result = ses_delivery_status()
    assert result["ready"] is False
    assert result["reason"] == "ses_sandbox"


@override_settings(
    EMAIL_BACKEND=SES_BACKEND,
    AWS_REGION="us-east-1",
    DEFAULT_FROM_EMAIL="Open Concert <no-reply@devopslabinc.com>",
    SES_IDENTITY="devopslabinc.com",
)
def test_ses_sandbox_allows_recipient_covered_by_verified_domain():
    sesv2 = Mock()
    sesv2.get_account.return_value = {"SendingEnabled": True, "ProductionAccessEnabled": False}
    sesv2.get_email_identity.return_value = {"VerifiedForSendingStatus": True}
    with patch("config.ses_email_backend.boto3.client", return_value=sesv2):
        result = ses_delivery_status("hello@devopslabinc.com")
    assert result["ready"] is True
    assert result["recipient_verified"] is True
    assert result["reason"] == "ready_sandbox_verified_recipient"
    sesv2.get_email_identity.assert_called_once_with(EmailIdentity="devopslabinc.com")


@override_settings(
    EMAIL_BACKEND=SES_BACKEND,
    AWS_REGION="us-east-1",
    DEFAULT_FROM_EMAIL="Open Concert <no-reply@devopslabinc.com>",
    SES_IDENTITY="devopslabinc.com",
)
def test_ses_verified_production_account_is_ready():
    sesv2 = Mock()
    sesv2.get_account.return_value = {"SendingEnabled": True, "ProductionAccessEnabled": True}
    sesv2.get_email_identity.return_value = {"VerifiedForSendingStatus": True}
    with patch("config.ses_email_backend.boto3.client", return_value=sesv2):
        result = ses_delivery_status("listener@example.com")
    assert result["ready"] is True
    assert result["reason"] == "ready"


@override_settings(
    EMAIL_BACKEND=SES_BACKEND,
    AWS_REGION="us-east-1",
    DEFAULT_FROM_EMAIL="Open Concert <no-reply@devopslabinc.com>",
    SES_IDENTITY="devopslabinc.com",
)
def test_ses_diagnostic_access_denied_does_not_claim_send_failure():
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
    assert result["reason"] == "account_diagnostic_denied"


def _signed_in_client(email="delivery@example.com"):
    user = get_user_model().objects.create_user(
        username=f"delivery-{email.split('@', 1)[0]}",
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
    with patch("gigs.email_views.ses_delivery_status", return_value=delivery), patch(
        "gigs.email_views.send_verification_email",
        return_value=1,
    ) as send_verification:
        response = client.post("/api/auth/email/resend-verification/", {}, format="json")
    assert response.status_code == 202
    assert response.data["delivery"]["accepted"] is True
    assert response.data["delivery"]["reason"] == "accepted"
    send_verification.assert_called_once()


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
        {"Error": {"Code": "MessageRejected", "Message": "Email address is not verified."}},
        "SendRawEmail",
    )
    with patch("gigs.email_views.ses_delivery_status", return_value=delivery), patch(
        "gigs.email_views.send_verification_email",
        side_effect=rejection,
    ):
        response = client.post("/api/auth/email/resend-verification/", {}, format="json")
    assert response.status_code == 503
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
    with patch("gigs.email_views.ses_delivery_status", return_value=delivery), patch(
        "gigs.email_views.send_verification_email",
        return_value=1,
    ) as send_verification:
        response = client.post("/api/auth/email/resend-verification/", {}, format="json")
    assert response.status_code == 202
    assert response.data["delivery"]["accepted"] is True
    send_verification.assert_called_once()
    assert EmailAddress.objects.get(user=user).verified is False


def test_email_delivery_status_endpoint_passes_signed_in_recipient(db):
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
    with patch("gigs.email_views.ses_delivery_status", return_value=delivery) as delivery_status:
        response = client.get("/api/auth/email/status/")
    assert response.status_code == 200
    assert response.data["reason"] == "identity_diagnostic_denied"
    assert "code" not in response.data
    delivery_status.assert_called_once_with("status@example.com")


def test_safe_ses_send_error_classifies_access_denied():
    exc = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "not authorized"}},
        "SendRawEmail",
    )
    reason, detail = safe_ses_send_error(exc)
    assert reason == "send_permission_denied"
    assert "task role" in detail.lower()


@override_settings(AWS_REGION="us-east-1", DEFAULT_FROM_EMAIL="Open Concert <no-reply@devopslabinc.com>")
def test_ses_backend_normalizes_envelope_addresses():
    ses = Mock()
    ses.send_raw_email.return_value = {"MessageId": "message-123"}
    message = EmailMessage(
        subject="Verify",
        body="hello",
        from_email="Open Concert <no-reply@devopslabinc.com>",
        to=["Listener <hello@devopslabinc.com>"],
    )
    with patch("config.ses_email_backend.boto3.client", return_value=ses):
        sent = EmailBackend().send_messages([message])
    assert sent == 1
    kwargs = ses.send_raw_email.call_args.kwargs
    assert kwargs["Source"] == "no-reply@devopslabinc.com"
    assert kwargs["Destinations"] == ["hello@devopslabinc.com"]


def test_signed_verification_token_marks_matching_email_verified(db):
    user = get_user_model().objects.create_user(
        username="signed-token-user",
        email="verified@example.com",
        password="OpenConcert!2026-Ready",
    )
    address = EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=False)
    token = _verification_token(user.pk, user.email)
    assert confirm_verification_token(token) is True
    address.refresh_from_db()
    assert address.verified is True
