# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Centralizes Django, database, cache, security, social-authentication, storage, tracing, and third-party runtime configuration.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Centralizes Django, database, cache, security, social-authentication, storage, tracing, and third-party runtime configuration.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from pathlib import Path
import os
import secrets
from urllib.parse import urlparse
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DEBUG", "true").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
# Require an explicit Django secret in production; the development fallback is used only when DEBUG is enabled.
if not SECRET_KEY:
    # Add localhost-oriented defaults only in development mode, never as production trust settings.
    if DEBUG:
        SECRET_KEY = secrets.token_urlsafe(50)
    else:
        raise RuntimeError("SECRET_KEY must be set when DEBUG is false")
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "allauth.socialaccount.providers.instagram",
    "allauth.socialaccount.providers.tiktok",
    "corsheaders",
    "rest_framework",
    "gigs.apps.GigsConfig",
]

AWS_XRAY_ENABLED = os.getenv("AWS_XRAY_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on"
}
if AWS_XRAY_ENABLED:
    # The Django app config initializes the global recorder before middleware
    # handles requests. Registering only the middleware leaves the recorder
    # without a segment name and causes every request to return HTTP 500.
    INSTALLED_APPS.append("aws_xray_sdk.ext.django")

MIDDLEWARE = [
    "config.middleware.LivenessMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
# Register X-Ray middleware and instrumentation only when tracing is enabled for this environment.
if AWS_XRAY_ENABLED:
    # Liveness must remain first because ALB probes use a private-IP Host value
    # that intentionally is not trusted for normal application requests.
    MIDDLEWARE.insert(1, "aws_xray_sdk.ext.django.middleware.XRayMiddleware")
    XRAY_RECORDER = {
        "AUTO_INSTRUMENT": True,
        "AWS_XRAY_DAEMON_ADDRESS": os.getenv(
            "AWS_XRAY_DAEMON_ADDRESS", "127.0.0.1:2000"
        ),
        "AWS_XRAY_TRACING_NAME": (
            os.getenv("AWS_XRAY_TRACING_NAME", "demand-gig-backend").strip()
            or "demand-gig-backend"
        ),
        "PLUGINS": ("ECSPlugin",),
    }

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"


AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Social-only customer authentication. Django admin can still use the regular
# ModelBackend. Provider credentials are loaded from environment variables so
# secrets remain in AWS Secrets Manager / the deployment environment, not DB rows.
SOCIALACCOUNT_ONLY = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_REQUESTS_TIMEOUT = 10
SOCIALACCOUNT_EMAIL_REQUIRED = False
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_SIGNUP_FIELDS = ["username*", "email"]
LOGIN_REDIRECT_URL = os.getenv("LOGIN_REDIRECT_URL", os.getenv("FRONTEND_URL", "http://localhost:5173"))
ACCOUNT_LOGOUT_REDIRECT_URL = LOGIN_REDIRECT_URL
SOCIAL_AUTH_ALLOWED_PROVIDERS = {
    provider.strip().lower()
    for provider in os.getenv(
        "SOCIAL_AUTH_ALLOWED_PROVIDERS", "google,facebook,instagram,tiktok"
    ).split(",")
    if provider.strip()
}


def _social_app(client_id_env: str, secret_env: str) -> dict:
    """
    Build one django-allauth provider configuration from environment-supplied client credentials.
    
    Args:
        client_id_env: Environment-variable name containing the provider client ID.
        secret_env: Environment-variable name containing the provider client secret.
    
    Returns:
        A JSON-compatible dictionary containing the normalized result.
    """
    client_id = os.getenv(client_id_env, "").strip()
    secret = os.getenv(secret_env, "").strip()
    # Omit this social provider from django-allauth when either credential is missing, preventing a broken login button.
    if not client_id or not secret:
        return {}
    return {"APP": {"client_id": client_id, "secret": secret, "key": ""}}


SOCIALACCOUNT_PROVIDERS = {
    "google": {
        **_social_app("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"),
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "EMAIL_AUTHENTICATION": True,
        "EMAIL_AUTHENTICATION_AUTO_CONNECT": True,
    },
    "facebook": {
        **_social_app("FACEBOOK_OAUTH_CLIENT_ID", "FACEBOOK_OAUTH_CLIENT_SECRET"),
        "METHOD": "oauth2",
        "SCOPE": ["email", "public_profile"],
        "FIELDS": ["id", "email", "name", "first_name", "last_name", "picture"],
    },
    "instagram": {
        **_social_app("INSTAGRAM_OAUTH_CLIENT_ID", "INSTAGRAM_OAUTH_CLIENT_SECRET"),
    },
    "tiktok": {
        **_social_app("TIKTOK_OAUTH_CLIENT_KEY", "TIKTOK_OAUTH_CLIENT_SECRET"),
    },
}

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
# Prefer the single deployment DATABASE_URL contract when supplied; otherwise use the individual PostgreSQL settings below.
if DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username,
            "PASSWORD": parsed.password,
            "HOST": parsed.hostname,
            "PORT": parsed.port or 5432,
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

REDIS_URL = os.getenv("REDIS_URL", "").strip()
# Use Redis for shared caching when configured; local-memory cache remains the dependency-free development fallback.
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": 300,
        }
    }
    # The database remains the durable source of truth while Redis accelerates
    # authenticated session reads and survives cache failover safely.
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

AUTH_PASSWORD_VALIDATORS = []

# Production security defaults. Each setting can be overridden explicitly for
# local development, reverse-proxy deployments, or test environments.
def env_bool(name: str, default: bool) -> bool:
    """
    Parse a boolean environment variable while honoring a safe default when it is unset.
    
    Args:
        name: Stable provider, configuration, or validation name.
        default: Fallback value returned when the environment variable is absent.
    
    Returns:
        True when the documented condition is satisfied; otherwise False.
    """
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", not DEBUG)
SECURE_PROXY_SSL_HEADER = (
    os.getenv("SECURE_PROXY_SSL_HEADER_NAME", "HTTP_X_FORWARDED_PROTO"),
    os.getenv("SECURE_PROXY_SSL_HEADER_VALUE", "https"),
)
_trusted_proxy_count = os.getenv("ALLAUTH_TRUSTED_PROXY_COUNT", "").strip()
# Trust forwarded HTTPS headers only when the deployment explicitly declares one or more front-end proxies.
if _trusted_proxy_count:
    ALLAUTH_TRUSTED_PROXY_COUNT = int(_trusted_proxy_count)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "").strip()
# Switch media storage to the private S3 backend only when a bucket has been provisioned.
if AWS_STORAGE_BUCKET_NAME:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "region_name": os.getenv("AWS_REGION", "us-east-1"),
                "default_acl": None,
                "querystring_auth": True,
                "file_overwrite": False,
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
    }
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
}

CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    x.strip() for x in os.getenv("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://localhost:8000").split(",") if x.strip()
]
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")

CORS_ALLOWED_ORIGINS = [
    x.strip() for x in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if x.strip()
]
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "fake")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Meta / Facebook integration
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v25.0")
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_PIXEL_ID = os.getenv("META_PIXEL_ID", "")
META_CONVERSIONS_API_TOKEN = os.getenv("META_CONVERSIONS_API_TOKEN", "")
META_TEST_EVENT_CODE = os.getenv("META_TEST_EVENT_CODE", "")
META_DEFAULT_SHARE_IMAGE = os.getenv("META_DEFAULT_SHARE_IMAGE", "")

# VibesMeet partner integration. Endpoint contract is proposed and must be
# confirmed with VibesMeet before production use.
VIBESMEET_BASE_URL = os.getenv("VIBESMEET_BASE_URL", "")
VIBESMEET_ACCESS_TOKEN = os.getenv("VIBESMEET_ACCESS_TOKEN", "")
VIBESMEET_WEBHOOK_SECRET = os.getenv("VIBESMEET_WEBHOOK_SECRET", "")
VIBESMEET_WEBHOOK_TOLERANCE_SECONDS = int(os.getenv("VIBESMEET_WEBHOOK_TOLERANCE_SECONDS", "300"))
VIBESMEET_TIMEOUT_SECONDS = float(os.getenv("VIBESMEET_TIMEOUT_SECONDS", "15"))
