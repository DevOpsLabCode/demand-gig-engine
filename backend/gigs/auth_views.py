# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Returns frontend authentication configuration, authenticated profile data, logout behavior, and health status.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Returns frontend authentication configuration, authenticated profile data, logout behavior, and health status.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from __future__ import annotations

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


def _serialize_user(user):
    """
    Convert the authenticated Django user and linked social identities into the frontend profile contract.
    
    Args:
        user: Authenticated or newly created Django user whose profile is being processed.
    
    Returns:
        The typed result described in the function summary and return annotation.
    """
    profile, _ = GigUserProfile.objects.get_or_create(user=user)
    social_accounts = list(user.socialaccount_set.all())
    avatar_url = profile.avatar_url
    # Fall back to the linked provider avatar only when the local profile has no explicit avatar URL.
    if not avatar_url:
        # Process each `account` from `social_accounts` in a deterministic order.
        for account in social_accounts:
            avatar_url = extract_avatar(account.extra_data or {})
            # Include the normalized avatar field only when a usable URL was found.
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


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def auth_config(request):
    """
    Return enabled social-login providers, the current user profile, and a CSRF token for the browser.
    
    Args:
        request: Incoming Django/DRF request, including the authenticated user and payload.
    
    Returns:
        The typed result described in the function summary and return annotation.
    """
    return Response(
        {
            "authenticated": request.user.is_authenticated,
            "user": _serialize_user(request.user) if request.user.is_authenticated else None,
            "providers": provider_payload(),
            "csrf_token": get_token(request),
            "account_types": [{"value": value, "label": label} for value, label in AccountType.choices],
        }
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def auth_profile(request):
    """
    Validate and persist the authenticated user's editable organizer profile fields.
    
    Args:
        request: Incoming Django/DRF request, including the authenticated user and payload.
    
    Returns:
        The typed result described in the function summary and return annotation.
    """
    profile, _ = GigUserProfile.objects.get_or_create(user=request.user)
    # Apply a partial profile update for PATCH requests; plain GET requests only serialize current data.
    if request.method == "PATCH":
        serializer = GigUserProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(_serialize_user(request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    """
    End the current Django session and return an empty success response.
    
    Args:
        request: Incoming Django/DRF request, including the authenticated user and payload.
    
    Returns:
        The typed result described in the function summary and return annotation.
    """
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Provide a dependency-light liveness endpoint for containers and the load balancer."""
    return Response({"status": "ok", "service": "demand-gig-backend"})
