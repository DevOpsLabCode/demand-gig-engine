# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Centralizes verified-email trust checks used by campaign and professional-account actions.

from __future__ import annotations

from allauth.account.models import EmailAddress
from rest_framework import status
from rest_framework.response import Response


def email_is_verified(user) -> bool:
    """Return True only when the authenticated user's current email is verified by django-allauth."""

    if not getattr(user, "is_authenticated", False) or not getattr(user, "email", ""):
        return False
    return EmailAddress.objects.filter(
        user=user,
        email__iexact=user.email,
        verified=True,
    ).exists()


def require_verified_email(user) -> Response | None:
    """Return a consistent 403 response when a trust-sensitive action requires email verification."""

    if email_is_verified(user):
        return None
    return Response(
        {
            "detail": "Verify your email address before performing this action.",
            "error_code": "email_verification_required",
        },
        status=status.HTTP_403_FORBIDDEN,
    )
