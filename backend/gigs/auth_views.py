from __future__ import annotations

from django.contrib.auth import logout
from django.core.cache import cache
from django.db import connection
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


def _readiness_status():
    checks = {"database": "ok", "cache": "ok"}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # pragma: no cover - exact driver failures vary by backend
        checks["database"] = "error"

    cache_key = "demand-gig-readiness"
    cache_value = "ready"
    try:
        cache.set(cache_key, cache_value, timeout=10)
        if cache.get(cache_key) != cache_value:
            raise RuntimeError("cache round-trip failed")
        cache.delete(cache_key)
    except Exception:  # pragma: no cover - exact cache failures vary by backend
        checks["cache"] = "error"

    ready = all(value == "ok" for value in checks.values())
    return ready, checks


@api_view(["GET"])
@permission_classes([AllowAny])
def health_live(request):
    """Process-level liveness endpoint used by the container health check."""
    return Response({"status": "ok", "service": "demand-gig-backend"})


@api_view(["GET"])
@permission_classes([AllowAny])
def health_ready(request):
    """Dependency-aware readiness endpoint used by the ALB and deployments."""
    ready, checks = _readiness_status()
    return Response(
        {
            "status": "ok" if ready else "unavailable",
            "service": "demand-gig-backend",
            "checks": checks,
        },
        status=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


# Preserve the original route as a readiness alias for compatibility.
health = health_ready
