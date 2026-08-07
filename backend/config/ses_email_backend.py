# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Sends Django email through Amazon SES using the ECS task IAM role and exposes safe delivery-readiness diagnostics.

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


def ses_delivery_status() -> dict[str, object]:
    """Return a safe readiness summary for public verification-email delivery."""

    backend = str(getattr(settings, "EMAIL_BACKEND", ""))
    if backend != SES_BACKEND:
        return {
            "provider": "non_ses",
            "ready": True,
            "sending_enabled": True,
            "production_access": True,
            "sender_verified": True,
            "detail": "Email delivery is using the configured non-SES backend.",
        }

    region_name = str(getattr(settings, "AWS_REGION", "") or "us-east-1")
    identity = _configured_identity()
    if not identity:
        return {
            "provider": "ses",
            "ready": False,
            "sending_enabled": False,
            "production_access": False,
            "sender_verified": False,
            "detail": "Verification email is unavailable because the sender identity is not configured.",
        }

    try:
        client = boto3.client("sesv2", region_name=region_name)
        account = client.get_account()
        identity_result = client.get_email_identity(EmailIdentity=identity)
    except (BotoCoreError, ClientError) as exc:
        error_code = "ses_unavailable"
        if isinstance(exc, ClientError):
            error_code = str(exc.response.get("Error", {}).get("Code") or error_code)
        logger.exception("Unable to verify SES delivery readiness identity=%s code=%s", identity, error_code)
        return {
            "provider": "ses",
            "ready": False,
            "sending_enabled": False,
            "production_access": False,
            "sender_verified": False,
            "detail": "Amazon SES could not validate the Open Concert sender. Check the SES identity and account status.",
            "code": error_code,
        }

    sending_enabled = bool(account.get("SendingEnabled"))
    production_access = bool(account.get("ProductionAccessEnabled"))
    sender_verified = bool(identity_result.get("VerifiedForSendingStatus"))
    ready = sending_enabled and production_access and sender_verified

    if not sender_verified:
        detail = "The Open Concert sender identity is not verified in Amazon SES."
    elif not sending_enabled:
        detail = "Amazon SES sending is disabled for this AWS account."
    elif not production_access:
        detail = "Amazon SES is still in sandbox mode. Public verification emails require SES production access."
    else:
        detail = "Amazon SES is ready for public verification-email delivery."

    return {
        "provider": "ses",
        "ready": ready,
        "sending_enabled": sending_enabled,
        "production_access": production_access,
        "sender_verified": sender_verified,
        "detail": detail,
    }


class EmailBackend(BaseEmailBackend):
    """Django email backend backed by the SES API and ambient AWS credentials."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.region_name = getattr(settings, "AWS_REGION", None) or "us-east-1"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        delivery = ses_delivery_status()
        if not delivery["ready"]:
            error = RuntimeError(str(delivery["detail"]))
            logger.error("SES delivery is not ready: %s", delivery["detail"])
            if self.fail_silently:
                return 0
            raise error

        client = boto3.client("ses", region_name=self.region_name)
        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            try:
                raw_message = message.message().as_bytes(linesep="\r\n")
                response = client.send_raw_email(
                    Source=message.from_email or settings.DEFAULT_FROM_EMAIL,
                    Destinations=message.recipients(),
                    RawMessage={"Data": raw_message},
                )
                message_id = str(response.get("MessageId") or "")
                logger.info(
                    "SES accepted email recipients=%s subject=%s message_id=%s",
                    message.recipients(),
                    message.subject,
                    message_id,
                )
                sent += 1
            except Exception:
                logger.exception(
                    "SES email delivery failed recipients=%s subject=%s",
                    message.recipients(),
                    message.subject,
                )
                if not self.fail_silently:
                    raise
        return sent
