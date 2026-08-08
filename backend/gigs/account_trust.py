# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Centralizes verified-email trust checks used by campaign and professional-account actions.

from __future__ import annotations

from allauth.account.models import EmailAddress
from rest_framework import status
from rest_framework.response import Response


def email_is_verified(user) -> bool:
    """Return trust state for staff, legacy accounts, and explicitly verified modern accounts.

    New Open Concert registrations always create an EmailAddress row with
    verified=False until the confirmation link is used. Accounts that predate
    this feature may have no allauth EmailAddress row; those are grandfathered
    so the rollout does not unexpectedly disable existing organizers.
    """

    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True

    email = str(getattr(user, "email", "") or "").strip()
    if not email:
        return False

    addresses = EmailAddress.objects.filter(user=user, email__iexact=email)
    if not addresses.exists():
        return True
    return addresses.filter(verified=True).exists()


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
