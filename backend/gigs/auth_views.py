# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Returns frontend authentication configuration, authenticated profile data, logout behavior, and health status.

"""
Returns frontend authentication configuration, authenticated profile data,
logout behavior, and health status.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from __future__ import annotations

import logging

from django.contrib.auth import logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AccountType, GigUserProfile
from .serializers import GigUserProfileUpdateSerializer
from .social_auth import extract_avatar, provider_payload

logger = logging.getLogger(__name__)


def _serialize_user(user):
    """Convert a Django user and linked social identities into the frontend profile contract."""
    profile, _ = GigUserProfile.objects.get_or_create(user=user)
    social_accounts = list(user.socialaccount_set.all())
    avatar_url = profile.avatar_url

    if not avatar_url:
        for account in social_accounts:
            avatar_url = extract_avatar(account.extra_data or {})
            if avatar_url:
                break

    return {
        "id": user.pk,
        "username": user.get_username(),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": profile.display_name or user.get_full_name() or user.get_username(),
        "avatar_url": avatar_url,
        "account_type": profile.account_type,
        "company_name": profile.company_name,
        "bio": profile.bio,
        "city": profile.city,
        "country": profile.country,
        "verified": profile.verified,
        "linked_providers": sorted(account.provider for account in social_accounts),
    }


def _safe_provider_payload():
    """Return provider configuration without allowing URL/configuration errors to break login discovery."""
    try:
        return provider_payload()
    except Exception:
        logger.exception("Unable to build social-login provider configuration")
        return []


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def auth_config(request):
    """
    Return authentication state and provider configuration.

    This endpoint is intentionally failure-tolerant because it controls whether
    the frontend can render the login panel. Provider discovery, session
    loading, or profile serialization failures are logged, but anonymous login
    discovery still receives valid JSON instead of an HTML 500 response.
    """
    providers = _safe_provider_payload()

    try:
        csrf_token = get_token(request)
    except Exception:
        logger.exception("Unable to generate CSRF token for auth configuration")
        csrf_token = ""

    authenticated = False
    serialized_user = None

    try:
        authenticated = bool(request.user.is_authenticated)
    except Exception:
        logger.exception("Unable to load authentication session")

    if authenticated:
        try:
            serialized_user = _serialize_user(request.user)
        except Exception:
            logger.exception("Unable to serialize authenticated user")
            authenticated = False
            serialized_user = None

    return Response(
        {
            "authenticated": authenticated,
            "user": serialized_user,
            "providers": providers,
            "csrf_token": csrf_token,
            "account_types": [
                {"value": value, "label": label}
                for value, label in AccountType.choices
            ],
        }
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def auth_profile(request):
    """Validate and persist the authenticated user's editable organizer profile."""
    profile, _ = GigUserProfile.objects.get_or_create(user=request.user)

    if request.method == "PATCH":
        serializer = GigUserProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

    return Response(_serialize_user(request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    """End the current Django session."""
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Provide a dependency-light liveness endpoint."""
    return Response({"status": "ok", "service": "demand-gig-backend"})
