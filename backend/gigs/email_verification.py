# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Owns the Open Concert verification-email link, rendering, sending, and signed-token confirmation flow.

from __future__ import annotations

from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse

EMAIL_VERIFICATION_SALT = "open-concert-email-verification-v1"
DEFAULT_MAX_AGE_SECONDS = 48 * 60 * 60


def _normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def _verification_token(user_id: int, email: str) -> str:
    return signing.dumps(
        {"uid": int(user_id), "email": _normalize_email(email)},
        salt=EMAIL_VERIFICATION_SALT,
        compress=True,
    )


def _verification_url(request, user_id: int, email: str) -> str:
    token = _verification_token(user_id, email)
    path = reverse("auth-email-verify-token", kwargs={"token": token})
    return request.build_absolute_uri(path)


def send_verification_email(request, address: EmailAddress, *, signup: bool = False) -> int:
    """Send one Open Concert verification email using Django's configured backend.

    This intentionally avoids allauth's internal mail-adapter path so provider
    errors come directly from the configured email backend and can be diagnosed
    accurately by the API.
    """

    email = _normalize_email(address.email)
    if not email:
        raise ValueError("Verification email address is empty.")

    activate_url = _verification_url(request, address.user_id, email)
    prefix = "email_confirmation_signup" if signup else "email_confirmation"
    context = {
        "activate_url": activate_url,
        "user": address.user,
        "email": email,
    }

    subject = render_to_string(f"account/email/{prefix}_subject.txt", context).strip()
    subject = " ".join(subject.splitlines())
    text_body = render_to_string(f"account/email/{prefix}_message.txt", context)
    html_body = render_to_string(f"account/email/{prefix}_message.html", context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    message.attach_alternative(html_body, "text/html")
    sent = message.send(fail_silently=False)
    if sent != 1:
        raise RuntimeError("The configured email backend did not accept the verification email.")
    return sent


def _frontend_redirect_url(result: str) -> str:
    base = str(getattr(settings, "FRONTEND_URL", "") or "/").strip() or "/"
    parts = urlsplit(base)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["email_verification"] = result
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", urlencode(query), parts.fragment))


def confirm_verification_token(token: str) -> bool:
    max_age = int(getattr(settings, "EMAIL_VERIFICATION_MAX_AGE_SECONDS", DEFAULT_MAX_AGE_SECONDS))
    payload = signing.loads(token, salt=EMAIL_VERIFICATION_SALT, max_age=max_age)
    user_id = int(payload["uid"])
    email = _normalize_email(payload["email"])

    user = get_user_model().objects.get(pk=user_id)
    if _normalize_email(getattr(user, "email", "")) != email:
        return False

    address, _ = EmailAddress.objects.get_or_create(
        user=user,
        email=email,
        defaults={"primary": True, "verified": True},
    )
    changed_fields: list[str] = []
    if not address.verified:
        address.verified = True
        changed_fields.append("verified")
    if not address.primary:
        address.primary = True
        changed_fields.append("primary")
    if changed_fields:
        address.save(update_fields=changed_fields)
    return True


def verify_email_token_view(request, token: str):
    """Confirm a signed verification link and return the user to the frontend."""

    try:
        verified = confirm_verification_token(token)
    except (signing.BadSignature, signing.SignatureExpired, KeyError, TypeError, ValueError, get_user_model().DoesNotExist):
        verified = False
    return redirect(_frontend_redirect_url("verified" if verified else "invalid"))
