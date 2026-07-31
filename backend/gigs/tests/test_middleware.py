from django.test import RequestFactory, override_settings

from config.middleware import PublicBaseURLMiddleware


@override_settings(PUBLIC_BASE_URL="https://gig.example.com")
def test_public_base_url_middleware_normalizes_external_request():
    request = RequestFactory().get("/accounts/google/login/callback/")
    middleware = PublicBaseURLMiddleware(lambda normalized: normalized)

    normalized = middleware(request)

    assert normalized.META["HTTP_X_FORWARDED_HOST"] == "gig.example.com"
    assert normalized.META["HTTP_X_FORWARDED_VIEWER_PROTO"] == "https"
