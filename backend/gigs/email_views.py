# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Reports safe verification-email readiness and resends confirmation only when the configured delivery service is actually usable.

from __future__ import annotations

import logging

from allauth.account.models import EmailAddress
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from config.ses_email_backend import ses_delivery_status

from .account_trust import email_is_verified

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def email_delivery_status_view(request):
    """Return a safe user-facing summary without exposing AWS account data or credentials."""

    delivery = ses_delivery_status()
    return Response(
        {
            "ready": bool(delivery.get("ready")),
            "provider": str(delivery.get("provider") or "unknown"),
            "sending_enabled": bool(delivery.get("sending_enabled")),
            "production_access": bool(delivery.get("production_access")),
            "sender_verified": bool(delivery.get("sender_verified")),
            "detail": str(delivery.get("detail") or "Email delivery status is unavailable."),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resend_email_verification(request):
    """Send a fresh confirmation only after the delivery provider passes readiness checks."""

    if email_is_verified(request.user):
        return Response(
            {
                "detail": "Email address is already verified.",
                "email_verified": True,
                "delivery": {"ready": True},
            }
        )

    email = str(request.user.email or "").strip()
    if not email:
        return Response(
            {"detail": "Add an email address before requesting verification."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    delivery = ses_delivery_status()
    safe_delivery = {
        "ready": bool(delivery.get("ready")),
        "provider": str(delivery.get("provider") or "unknown"),
        "sending_enabled": bool(delivery.get("sending_enabled")),
        "production_access": bool(delivery.get("production_access")),
        "sender_verified": bool(delivery.get("sender_verified")),
        "detail": str(delivery.get("detail") or "Email delivery status is unavailable."),
    }
    if not safe_delivery["ready"]:
        return Response(
            {
                "detail": safe_delivery["detail"],
                "email_verified": False,
                "delivery": safe_delivery,
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

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
    except Exception:
        logger.exception("Unable to resend email verification user_id=%s", request.user.pk)
        return Response(
            {
                "detail": "Amazon SES rejected the verification message. Check the sender identity, account access, and application logs.",
                "email_verified": False,
                "delivery": safe_delivery,
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "detail": "Verification email was accepted for delivery. Check your inbox and spam folder.",
            "email_verified": False,
            "delivery": safe_delivery,
        },
        status=status.HTTP_202_ACCEPTED,
    )
