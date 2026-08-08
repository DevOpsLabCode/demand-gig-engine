# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Sends Django email through Amazon SES using the ECS task IAM role while keeping diagnostics informative instead of blocking real delivery.

from __future__ import annotations

import logging
from email.utils import parseaddr

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

SES_BACKEND = "config.ses_email_backend.EmailBackend"


def _configured_identity() -> str:
    """Return the SES identity to validate without exposing account information."""

    configured = str(getattr(settings, "SES_IDENTITY", "") or "").strip()
    if configured:
        return configured

    address = parseaddr(str(getattr(settings, "DEFAULT_FROM_EMAIL", "")))[1].strip()
    if "@" in address:
        return address.rsplit("@", 1)[1].lower()
    return address.lower()


def _normalize_address(value: str | None) -> str:
    return parseaddr(str(value or ""))[1].strip().lower()


def _identity_covers_recipient(identity: str, recipient: str) -> bool:
    """Return True when a verified SES identity inherently covers the recipient."""

    normalized_identity = _normalize_address(identity) or str(identity or "").strip().lower()
    normalized_recipient = _normalize_address(recipient)
    if not normalized_identity or not normalized_recipient:
        return False
    if "@" in normalized_identity:
        return normalized_identity == normalized_recipient
    return normalized_recipient.endswith(f"@{normalized_identity}")


def _client_error_code(exc: Exception) -> str:
    if isinstance(exc, ClientError):
        return str(exc.response.get("Error", {}).get("Code") or "ClientError")
    if isinstance(exc, BotoCoreError):
        return exc.__class__.__name__
    return exc.__class__.__name__


def _client_error_message(exc: Exception) -> str:
    if isinstance(exc, ClientError):
        return str(exc.response.get("Error", {}).get("Message") or "")
    return str(exc)


def safe_ses_send_error(exc: Exception) -> tuple[str, str]:
    """Translate provider failures into safe, actionable UI text without leaking AWS IDs."""

    code = _client_error_code(exc)
    message = _client_error_message(exc).lower()
    normalized = code.lower()

    if "accessdenied" in normalized or "unauthorized" in normalized:
        return (
            "send_permission_denied",
            "Amazon SES denied the application's send request. The ECS task role or its permissions boundary must allow SES sending for the configured Open Concert sender.",
        )

    if "mailfromdomainnotverified" in normalized:
        return (
            "mail_from_not_verified",
            "Amazon SES rejected the message because the configured MAIL FROM domain is not verified.",
        )

    if "messagerejected" in normalized or "message rejected" in message:
        if "not verified" in message or "identity" in message and "verified" in message:
            return (
                "identity_not_verified",
                "Amazon SES rejected the verification email because a required sender or recipient identity is not verified. If this AWS account is still in the SES sandbox, ordinary public recipient addresses must also be verified or the account must be moved to production access.",
            )
        if "suppression" in message or "suppressed" in message:
            return (
                "recipient_suppressed",
                "Amazon SES rejected the recipient because the address is on the account suppression list.",
            )
        return (
            "message_rejected",
            "Amazon SES rejected the verification email. Check the sender identity, SES account access, and recipient suppression status.",
        )

    if "throttl" in normalized or "toomanyrequests" in normalized:
        return (
            "ses_throttled",
            "Amazon SES is temporarily rate-limiting email delivery. Please retry shortly.",
        )

    if isinstance(exc, BotoCoreError):
        return (
            "ses_unavailable",
            "Amazon SES could not be reached from the application. Please retry shortly.",
        )

    return (
        "ses_send_failed",
        "Amazon SES could not accept the verification email. Check the Open Concert sender identity and SES account status.",
    )


def _diagnostic_error(operation: str, exc: Exception) -> tuple[str, str]:
    """Return a safe diagnostic reason while preserving the real AWS error only in logs."""

    code = _client_error_code(exc)
    normalized = code.lower()
    logger.warning("SES diagnostic failed operation=%s code=%s", operation, code)

    if "accessdenied" in normalized or "unauthorized" in normalized:
        return (
            f"{operation}_diagnostic_denied",
            "SES diagnostic access is limited for this task role. Open Concert will still test delivery directly when you resend the verification email.",
        )
    if "notfound" in normalized:
        return (
            f"{operation}_not_found",
            "The configured Open Concert sender identity was not found in this SES region. Verify the sender identity and AWS region.",
        )
    return (
        f"{operation}_diagnostic_unavailable",
        "Amazon SES diagnostic status is temporarily unavailable. Open Concert will still test delivery directly when you resend the verification email.",
    )


def ses_delivery_status(recipient: str | None = None) -> dict[str, object]:
    """Return safe SES readiness diagnostics for the actual recipient when known."""

    backend = str(getattr(settings, "EMAIL_BACKEND", ""))
    if backend != SES_BACKEND:
        return {
            "provider": "non_ses",
            "ready": True,
            "diagnostics_complete": True,
            "sending_enabled": True,
            "production_access": True,
            "sender_verified": True,
            "recipient_verified": True,
            "reason": "non_ses_backend",
            "detail": "Email delivery is using the configured non-SES backend.",
        }

    region_name = str(getattr(settings, "AWS_REGION", "") or "us-east-1")
    identity = _configured_identity()
    normalized_recipient = _normalize_address(recipient)
    if not identity:
        return {
            "provider": "ses",
            "ready": False,
            "diagnostics_complete": True,
            "sending_enabled": False,
            "production_access": False,
            "sender_verified": False,
            "recipient_verified": False,
            "reason": "sender_not_configured",
            "detail": "Verification email is unavailable because the sender identity is not configured.",
        }

    try:
        client = boto3.client("sesv2", region_name=region_name)
    except (BotoCoreError, ClientError) as exc:
        reason, detail = _diagnostic_error("client", exc)
        return {
            "provider": "ses",
            "ready": False,
            "diagnostics_complete": False,
            "sending_enabled": False,
            "production_access": False,
            "sender_verified": False,
            "recipient_verified": False,
            "reason": reason,
            "detail": detail,
        }

    account: dict[str, object] | None = None
    identity_result: dict[str, object] | None = None
    recipient_result: dict[str, object] | None = None
    diagnostic_reasons: list[tuple[str, str]] = []

    try:
        account = client.get_account()
    except (BotoCoreError, ClientError) as exc:
        diagnostic_reasons.append(_diagnostic_error("account", exc))

    try:
        identity_result = client.get_email_identity(EmailIdentity=identity)
    except (BotoCoreError, ClientError) as exc:
        diagnostic_reasons.append(_diagnostic_error("identity", exc))

    sending_enabled = bool(account.get("SendingEnabled")) if account is not None else False
    production_access = bool(account.get("ProductionAccessEnabled")) if account is not None else False
    sender_verified = bool(identity_result.get("VerifiedForSendingStatus")) if identity_result is not None else False
    diagnostics_complete = account is not None and identity_result is not None

    recipient_verified = False
    if normalized_recipient and sender_verified and _identity_covers_recipient(identity, normalized_recipient):
        recipient_verified = True
    elif normalized_recipient and not production_access:
        try:
            recipient_result = client.get_email_identity(EmailIdentity=normalized_recipient)
            recipient_verified = bool(recipient_result.get("VerifiedForSendingStatus"))
        except (BotoCoreError, ClientError) as exc:
            logger.info(
                "SES recipient identity diagnostic unavailable recipient_domain=%s code=%s",
                normalized_recipient.rsplit("@", 1)[-1] if "@" in normalized_recipient else "unknown",
                _client_error_code(exc),
            )

    if diagnostics_complete:
        if not sender_verified:
            reason = "sender_unverified"
            detail = "The Open Concert sender identity is not verified in Amazon SES."
        elif not sending_enabled:
            reason = "sending_disabled"
            detail = "Amazon SES sending is disabled for this AWS account."
        elif production_access:
            reason = "ready"
            detail = "Amazon SES diagnostics are healthy. Verification email can be submitted for delivery."
        elif normalized_recipient and recipient_verified:
            reason = "ready_sandbox_verified_recipient"
            detail = "Amazon SES is in sandbox mode, but this email address is covered by a verified SES identity and can receive the verification message."
        else:
            reason = "ses_sandbox"
            detail = "Amazon SES is still in sandbox mode. This recipient must be verified in SES or the account must have production access."
        ready = sending_enabled and sender_verified and (production_access or recipient_verified)
    else:
        reason, detail = diagnostic_reasons[0] if diagnostic_reasons else (
            "diagnostic_unavailable",
            "Amazon SES diagnostic status is incomplete. Open Concert will test delivery directly when you resend the verification email.",
        )
        ready = False

    return {
        "provider": "ses",
        "ready": ready,
        "diagnostics_complete": diagnostics_complete,
        "sending_enabled": sending_enabled,
        "production_access": production_access,
        "sender_verified": sender_verified,
        "recipient_verified": recipient_verified,
        "reason": reason,
        "detail": detail,
    }


class EmailBackend(BaseEmailBackend):
    """Django email backend backed by the SES API and ambient AWS credentials."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.region_name = getattr(settings, "AWS_REGION", None) or "us-east-1"

    def send_messages(self, email_messages):
        """Submit messages directly to SES; read-only diagnostics must never gate delivery."""

        if not email_messages:
            return 0

        client = boto3.client("ses", region_name=self.region_name)
        sent = 0
        for message in email_messages:
            recipients = message.recipients()
            if not recipients:
                continue
            try:
                raw_message = message.message().as_bytes(linesep="\r\n")
                response = client.send_raw_email(
                    Source=message.from_email or settings.DEFAULT_FROM_EMAIL,
                    Destinations=recipients,
                    RawMessage={"Data": raw_message},
                )
                message_id = str(response.get("MessageId") or "")
                logger.info(
                    "SES accepted email recipients=%s subject=%s message_id=%s",
                    recipients,
                    message.subject,
                    message_id,
                )
                sent += 1
            except Exception as exc:
                reason, detail = safe_ses_send_error(exc)
                logger.exception(
                    "SES email delivery failed recipients=%s subject=%s reason=%s detail=%s",
                    recipients,
                    message.subject,
                    reason,
                    detail,
                )
                if not self.fail_silently:
                    raise
        return sent
