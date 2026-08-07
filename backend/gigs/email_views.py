# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Reports safe verification-email diagnostics and treats the actual SES send result as the delivery source of truth.

from __future__ import annotations

import logging

from allauth.account.models import EmailAddress
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from config.ses_email_backend import safe_ses_send_error, ses_delivery_status

from .account_trust import email_is_verified

logger = logging.getLogger(__name__)


def _safe_delivery(delivery: dict[str, object]) -> dict[str, object]:
    return {
        "ready": bool(delivery.get("ready")),
        "provider": str(delivery.get("provider") or "unknown"),
        "diagnostics_complete": bool(delivery.get("diagnostics_complete", True)),
        "sending_enabled": bool(delivery.get("sending_enabled")),
        "production_access": bool(delivery.get("production_access")),
        "sender_verified": bool(delivery.get("sender_verified")),
        "reason": str(delivery.get("reason") or "unknown"),
        "detail": str(delivery.get("detail") or "Email delivery status is unavailable."),
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def email_delivery_status_view(request):
    """Return a safe user-facing summary without exposing AWS account data or credentials."""

    return Response(_safe_delivery(ses_delivery_status()))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resend_email_verification(request):
    """Attempt the real confirmation send; SES diagnostics are informative, not a delivery gate."""

    if email_is_verified(request.user):
        return Response(
            {
                "detail": "Email address is already verified.",
                "email_verified": True,
                "delivery": {
                    "ready": True,
                    "accepted": True,
                    "reason": "already_verified",
                },
            }
        )

    email = str(request.user.email or "").strip()
    if not email:
        return Response(
            {"detail": "Add an email address before requesting verification."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Read-only SES diagnostics are useful to explain sandbox/identity state, but
    # they must never stop a send attempt. IAM boundaries can intentionally deny
    # diagnostic APIs while still allowing ses:SendRawEmail.
    diagnostics = _safe_delivery(ses_delivery_status())

    address, _ = EmailAddress.objects.get_or_create(
        user=request.user,
        email=email,
        defaults={"primary": True, "verified": False},
    )
    if not address.primary:
        address.primary = True
        address.save(update_fields=["primary"])

    try:
        address.send_confirmation(request, signup=False)
    except Exception as exc:
        reason, detail = safe_ses_send_error(exc)
        logger.exception(
            "Unable to resend email verification user_id=%s reason=%s",
            request.user.pk,
            reason,
        )
        return Response(
            {
                "detail": detail,
                "email_verified": False,
                "delivery": {
                    **diagnostics,
                    "accepted": False,
                    "reason": reason,
                    "detail": detail,
                },
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "detail": "Amazon SES accepted the verification email for delivery. Check your inbox and spam folder.",
            "email_verified": False,
            "delivery": {
                **diagnostics,
                "accepted": True,
                "reason": "accepted",
                "detail": "Amazon SES accepted the verification email for delivery.",
            },
        },
        status=status.HTTP_202_ACCEPTED,
    )
