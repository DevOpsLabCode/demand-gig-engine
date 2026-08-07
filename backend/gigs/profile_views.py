# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Exposes user discovery preferences, private-storage profile media, and email-verification resend endpoints.

from __future__ import annotations

from pathlib import Path

from allauth.account.models import EmailAddress
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .account_trust import email_is_verified
from .discovery_models import ProfileMedia, ProfileMediaType, UserDiscoveryProfile


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
IMAGE_MAX_BYTES = 10 * 1024 * 1024
VIDEO_MAX_BYTES = 200 * 1024 * 1024
MAX_GALLERY_IMAGES = 16
MAX_PROFILE_VIDEOS = 4


def _file_url(media: ProfileMedia) -> str:
    try:
        return media.file.url
    except Exception:
        return ""


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
        "email_verified": email_is_verified(user),
        "media": [serialize_media(item) for item in user.profile_media.all()],
    }


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def discovery_profile(request):
    """Read or update the signed-in user's home state and followed cities."""

    profile, _ = UserDiscoveryProfile.objects.get_or_create(user=request.user)
    if request.method == "PATCH":
        if "state" in request.data:
            profile.state = str(request.data.get("state", "")).strip()[:80]
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
        profile.save()

    return Response(serialize_discovery_profile(request.user))


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
            return Response({"detail": "A profile can contain up to 4 videos."}, status=status.HTTP_409_CONFLICT)
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
    address.send_confirmation(request, signup=False)
    return Response({"detail": "Verification email sent.", "email_verified": False})
