# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Exposes rich user/band profiles, private-storage media, public profile data, and reliable email verification resend.

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .account_trust import email_is_verified
from .discovery_models import ProfileMedia, ProfileMediaType, UserDiscoveryProfile
from .models import GigUserProfile

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
IMAGE_MAX_BYTES = 10 * 1024 * 1024
VIDEO_MAX_BYTES = 200 * 1024 * 1024
MAX_GALLERY_IMAGES = 16
MAX_PROFILE_VIDEOS = 4
MAX_EXTERNAL_VIDEOS = 8
MAX_GENRES = 12
ALLOWED_SOCIAL_KEYS = {
    "website",
    "youtube",
    "instagram",
    "facebook",
    "tiktok",
    "spotify",
    "soundcloud",
    "bandcamp",
    "x",
}
VIDEO_HOST_SUFFIXES = (
    "youtube.com",
    "youtu.be",
    "vimeo.com",
    "twitch.tv",
    "instagram.com",
    "tiktok.com",
    "facebook.com",
)


def _file_url(media: ProfileMedia) -> str:
    try:
        return media.file.url
    except Exception:
        return ""


def _valid_https_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_social_links(value) -> tuple[dict[str, str] | None, str | None]:
    if not isinstance(value, dict):
        return None, "Provide social_links as an object."
    normalized: dict[str, str] = {}
    for raw_key, raw_url in value.items():
        key = str(raw_key).strip().lower()
        url = str(raw_url).strip()
        if key not in ALLOWED_SOCIAL_KEYS:
            continue
        if not url:
            continue
        if not _valid_https_url(url):
            return None, f"{key} must be a valid http/https URL."
        normalized[key] = url[:500]
    return normalized, None


def _normalize_external_videos(value) -> tuple[list[str] | None, str | None]:
    if not isinstance(value, list):
        return None, "Provide external_video_urls as a list."
    normalized: list[str] = []
    for raw_url in value[:MAX_EXTERNAL_VIDEOS]:
        url = str(raw_url).strip()
        if not url:
            continue
        if not _valid_https_url(url):
            return None, "External videos must use valid http/https URLs."
        host = (urlparse(url).hostname or "").lower()
        if not any(host == suffix or host.endswith(f".{suffix}") for suffix in VIDEO_HOST_SUFFIXES):
            return None, "External videos must use YouTube, Vimeo, Twitch, Instagram, TikTok, or Facebook URLs."
        if url not in normalized:
            normalized.append(url[:500])
    return normalized, None


def serialize_media(media: ProfileMedia) -> dict:
    return {
        "id": str(media.id),
        "media_type": media.media_type,
        "url": _file_url(media),
        "caption": media.caption,
        "created_at": media.created_at,
    }


def serialize_discovery_profile(user) -> dict:
    profile, _ = UserDiscoveryProfile.objects.get_or_create(user=user)
    return {
        "state": profile.state,
        "preferred_cities": profile.preferred_cities,
        "home_latitude": str(profile.home_latitude) if profile.home_latitude is not None else None,
        "home_longitude": str(profile.home_longitude) if profile.home_longitude is not None else None,
        "headline": profile.headline,
        "genres": profile.genres,
        "social_links": profile.social_links,
        "external_video_urls": profile.external_video_urls,
        "email_verified": email_is_verified(user),
        "media": [serialize_media(item) for item in user.profile_media.all()],
    }


def serialize_public_profile(user) -> dict:
    marketplace, _ = GigUserProfile.objects.get_or_create(user=user)
    discovery = serialize_discovery_profile(user)
    media = discovery.pop("media")
    discovery.pop("email_verified", None)
    return {
        "username": user.get_username(),
        "display_name": marketplace.display_name or user.get_full_name() or user.get_username(),
        "account_type": marketplace.account_type,
        "company_name": marketplace.company_name,
        "bio": marketplace.bio,
        "city": marketplace.city,
        "country": marketplace.country,
        "verified": marketplace.verified,
        **discovery,
        "media": media,
        "linked_providers": sorted(account.provider for account in user.socialaccount_set.all()),
    }


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def discovery_profile(request):
    """Read or update the signed-in user's full discovery/public-profile metadata."""

    profile, _ = UserDiscoveryProfile.objects.get_or_create(user=request.user)
    if request.method == "PATCH":
        if "state" in request.data:
            profile.state = str(request.data.get("state", "")).strip()[:80]
        if "headline" in request.data:
            profile.headline = str(request.data.get("headline", "")).strip()[:180]
        if "preferred_cities" in request.data:
            cities = request.data.get("preferred_cities")
            if not isinstance(cities, list):
                return Response(
                    {"preferred_cities": ["Provide a JSON list of city labels."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            normalized = []
            for value in cities[:12]:
                label = str(value).strip()[:160]
                if label and label not in normalized:
                    normalized.append(label)
            profile.preferred_cities = normalized
        if "genres" in request.data:
            genres = request.data.get("genres")
            if not isinstance(genres, list):
                return Response({"genres": ["Provide genres as a JSON list."]}, status=status.HTTP_400_BAD_REQUEST)
            profile.genres = list(dict.fromkeys(str(value).strip()[:80] for value in genres if str(value).strip()))[:MAX_GENRES]
        if "social_links" in request.data:
            social_links, error = _normalize_social_links(request.data.get("social_links"))
            if error:
                return Response({"social_links": [error]}, status=status.HTTP_400_BAD_REQUEST)
            profile.social_links = social_links or {}
        if "external_video_urls" in request.data:
            external_videos, error = _normalize_external_videos(request.data.get("external_video_urls"))
            if error:
                return Response({"external_video_urls": [error]}, status=status.HTTP_400_BAD_REQUEST)
            profile.external_video_urls = external_videos or []
        profile.save()

    return Response(serialize_discovery_profile(request.user))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def public_profile(request, username):
    """Return a safe public profile without exposing email, private IDs, or session data."""

    user_model = get_user_model()
    user = user_model._default_manager.filter(**{f"{user_model.USERNAME_FIELD}__iexact": username}).first()
    if user is None or not user.is_active:
        return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(serialize_public_profile(user))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def profile_media_collection(request):
    """List or upload profile photos, cover art, gallery images, and short profile videos."""

    if request.method == "GET":
        return Response([serialize_media(item) for item in request.user.profile_media.all()])

    upload = request.FILES.get("file")
    media_type = str(request.data.get("media_type", "")).strip().lower()
    caption = str(request.data.get("caption", "")).strip()[:240]

    if upload is None:
        return Response({"file": ["Choose a file to upload."]}, status=status.HTTP_400_BAD_REQUEST)
    if media_type not in ProfileMediaType.values:
        return Response({"media_type": ["Choose avatar, cover, image, or video."]}, status=status.HTTP_400_BAD_REQUEST)

    extension = Path(upload.name).suffix.lower()
    content_type = str(getattr(upload, "content_type", "")).lower()
    is_video = media_type == ProfileMediaType.VIDEO

    if is_video:
        if extension not in VIDEO_EXTENSIONS or not content_type.startswith("video/"):
            return Response({"file": ["Profile videos must be MP4, WebM, MOV, or M4V."]}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > VIDEO_MAX_BYTES:
            return Response({"file": ["Profile videos are limited to 200 MB."]}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.profile_media.filter(media_type=ProfileMediaType.VIDEO).count() >= MAX_PROFILE_VIDEOS:
            return Response({"detail": "A profile can contain up to 4 uploaded videos."}, status=status.HTTP_409_CONFLICT)
    else:
        if extension not in IMAGE_EXTENSIONS or not content_type.startswith("image/"):
            return Response({"file": ["Images must be JPG, PNG, or WebP."]}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > IMAGE_MAX_BYTES:
            return Response({"file": ["Images are limited to 10 MB."]}, status=status.HTTP_400_BAD_REQUEST)
        if media_type == ProfileMediaType.IMAGE and request.user.profile_media.filter(media_type=ProfileMediaType.IMAGE).count() >= MAX_GALLERY_IMAGES:
            return Response({"detail": "A profile can contain up to 16 gallery images."}, status=status.HTTP_409_CONFLICT)

    if media_type in {ProfileMediaType.AVATAR, ProfileMediaType.COVER}:
        request.user.profile_media.filter(media_type=media_type).delete()

    media = ProfileMedia.objects.create(
        user=request.user,
        media_type=media_type,
        file=upload,
        caption=caption,
    )
    return Response(serialize_media(media), status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def profile_media_detail(request, media_id):
    """Delete only media owned by the signed-in user."""

    media = request.user.profile_media.filter(pk=media_id).first()
    if media is None:
        return Response({"detail": "Profile media not found."}, status=status.HTTP_404_NOT_FOUND)
    storage = media.file.storage
    name = media.file.name
    media.delete()
    if name:
        storage.delete(name)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resend_email_verification(request):
    """Send a fresh django-allauth verification message for the current primary email."""

    if email_is_verified(request.user):
        return Response({"detail": "Email address is already verified.", "email_verified": True})

    email = str(request.user.email or "").strip()
    if not email:
        return Response({"detail": "Add an email address before requesting verification."}, status=status.HTTP_400_BAD_REQUEST)

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
            {"detail": "Verification email could not be delivered. Please try again shortly.", "email_verified": False},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({"detail": "Verification email sent. Check your inbox and spam folder.", "email_verified": False})
