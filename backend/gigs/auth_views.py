# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Provides credential/social authentication, registration, profile updates, logout, and service health endpoints.

"""
Provides credential and social authentication, account registration, profile
updates, logout behavior, and service health endpoints.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from __future__ import annotations

import logging
from re import sub

from django.contrib.auth import (
    authenticate,
    get_user_model,
    login as django_login,
    logout,
)
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.middleware.csrf import get_token
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AccountType, GigUserProfile
from .serializers import (
    CredentialLoginSerializer,
    GigUserProfileUpdateSerializer,
    UserRegistrationSerializer,
)
from .social_auth import extract_avatar, provider_payload

logger = logging.getLogger(__name__)


class ResilientSessionAuthentication(SessionAuthentication):
    """Treat an unavailable optional session as anonymous on public discovery endpoints."""

    def authenticate(self, request):
        """Load a session when possible without allowing a backend outage to hide sign-in options."""
        try:
            return super().authenticate(request)
        except (DatabaseError, RedisError):
            logger.exception("Unable to load the optional authentication session")
            return None


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
        "display_name": profile.display_name
        or user.get_full_name()
        or user.get_username(),
        "avatar_url": avatar_url,
        "account_type": profile.account_type,
        "company_name": profile.company_name,
        "bio": profile.bio,
        "city": profile.city,
        "country": profile.country,
        "verified": profile.verified,
        "linked_providers": sorted(
            account.provider for account in social_accounts
        ),
    }


def _safe_provider_payload():
    """Return provider configuration without allowing URL/configuration errors to break login discovery."""
    try:
        return provider_payload()
    except Exception:
        logger.exception("Unable to build social-login provider configuration")
        return []


def _unique_username(email: str) -> str:
    """Generate a readable unique Django username from a validated email address."""
    user_model = get_user_model()
    local_part = email.split("@", 1)[0]
    base = slugify(sub(r"[^a-zA-Z0-9._-]+", "-", local_part)) or "member"
    max_length = user_model._meta.get_field(user_model.USERNAME_FIELD).max_length or 150
    base = base[:max_length]
    candidate = base
    suffix = 2

    while user_model._default_manager.filter(
        **{f"{user_model.USERNAME_FIELD}__iexact": candidate}
    ).exists():
        suffix_text = f"-{suffix}"
        candidate = f"{base[: max_length - len(suffix_text)]}{suffix_text}"
        suffix += 1

    return candidate


@api_view(["GET"])
@authentication_classes([ResilientSessionAuthentication])
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
            "password_auth_enabled": True,
            "account_types": [
                {"value": value, "label": label}
                for value, label in AccountType.choices
            ],
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_login(request):
    """Authenticate an active account by username or email and start a server session."""
    serializer = CredentialLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user_model = get_user_model()
    identifier = serializer.validated_data["identifier"]
    password = serializer.validated_data["password"]
    login_name = identifier

    email_user = user_model._default_manager.filter(
        email__iexact=identifier
    ).only(user_model.USERNAME_FIELD).first()
    if email_user is not None:
        login_name = getattr(email_user, user_model.USERNAME_FIELD)

    user = authenticate(
        request,
        **{
            user_model.USERNAME_FIELD: login_name,
            "password": password,
        },
    )

    if user is None or not user.is_active:
        return Response(
            {"detail": "The email/username or password is incorrect."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    django_login(request, user)
    return Response(_serialize_user(user))


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_register(request):
    """Create a community-member account, sign it in, and return its profile."""
    serializer = UserRegistrationSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    user_model = get_user_model()
    email = serializer.validated_data["email"]
    display_name = serializer.validated_data["display_name"]
    password = serializer.validated_data["password"]

    try:
        with transaction.atomic():
            user = user_model._default_manager.create_user(
                **{
                    user_model.USERNAME_FIELD: _unique_username(email),
                    "email": email,
                    "password": password,
                }
            )
            profile, _ = GigUserProfile.objects.get_or_create(user=user)
            profile.display_name = display_name
            profile.account_type = AccountType.FAN
            profile.save(update_fields=["display_name", "account_type", "updated_at"])
    except IntegrityError:
        return Response(
            {"email": ["An account with this email already exists."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    django_login(
        request,
        user,
        backend="django.contrib.auth.backends.ModelBackend",
    )
    return Response(_serialize_user(user), status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def auth_profile(request):
    """Validate and persist the authenticated user's editable marketplace profile."""
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
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    """Provide a dependency-light liveness endpoint."""
    return Response({"status": "ok", "service": "demand-gig-backend"})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def readiness(request):
    """Verify that the API task can reach the database required for login sessions."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        logger.exception("Database readiness check failed")
        return Response(
            {"status": "unavailable", "service": "demand-gig-backend"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({"status": "ready", "service": "demand-gig-backend"})
