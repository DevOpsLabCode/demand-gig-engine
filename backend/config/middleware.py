from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings


class PublicBaseURLMiddleware:
    """Normalize externally visible scheme/host behind CloudFront and ALB.

    CloudFront deliberately does not forward the viewer Host header to an HTTPS
    ALB origin because the origin certificate covers the origin hostname. This
    middleware uses the configured canonical public URL for Django/Allauth
    absolute URLs while the ALB remains inaccessible without CloudFront's
    private origin-verification header.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        parsed = urlparse(getattr(settings, "PUBLIC_BASE_URL", ""))
        self.scheme = parsed.scheme
        self.host = parsed.netloc

    def __call__(self, request):
        if self.host:
            request.META["HTTP_X_FORWARDED_HOST"] = self.host
        if self.scheme:
            request.META["HTTP_X_FORWARDED_VIEWER_PROTO"] = self.scheme
        return self.get_response(request)
