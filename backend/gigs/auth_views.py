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


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def auth_config(request):
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
    profile, _ = GigUserProfile.objects.get_or_create(user=request.user)
    if request.method == "PATCH":
        serializer = GigUserProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(_serialize_user(request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Lightweight ALB/container readiness endpoint."""
    return Response({"status": "ok", "service": "demand-gig-backend"})
