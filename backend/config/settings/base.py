"""Shared settings. Secrets and database values belong to a concrete profile."""

from pathlib import Path

from .environment import boolean, positive_integer
from .registration import *  # noqa: F403

BASE_DIR = Path(__file__).resolve().parents[3]
DEBUG = False
ALLOWED_HOSTS = []

# The custom User is created in accounts.0001_initial. Django authentication,
# sessions and their middleware are wired in S008; no default auth_user is created.
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "apps.accounts.apps.AccountsConfig",
    "apps.audit.apps.AuditConfig",
    "apps.access.apps.AccessConfig",
    "apps.academics.apps.AcademicsConfig",
    "rest_framework",
]
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.auth.backend.PlatformBackend"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.auth.middleware.AccountSessionMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

REST_FRAMEWORK = {
    # New views are denied by default; only health explicitly allows anonymous access.
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
APPEND_SLASH = False
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "apps.accounts.auth.views.csrf_failure"
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = positive_integer("AUTH_SESSION_SECONDS", default=43200, maximum=604800)
SESSION_SAVE_EVERY_REQUEST = False
LOGIN_ATTEMPT_LIMIT = positive_integer("AUTH_LOGIN_ATTEMPT_LIMIT", default=5, maximum=100)
LOGIN_IP_LIMIT = positive_integer("AUTH_LOGIN_IP_LIMIT", default=30, maximum=1000)
LOGIN_WINDOW_SECONDS = positive_integer("AUTH_LOGIN_WINDOW_SECONDS", default=900, maximum=86400)


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Recovery remains available to eligible alumni regardless of signup domain policy.
PASSWORD_RESET_SECONDS = positive_integer("PASSWORD_RESET_SECONDS", default=3600, maximum=86400)
RECOVERY_IDENTITY_LIMIT = positive_integer("RECOVERY_IDENTITY_LIMIT", default=3, maximum=100)
RECOVERY_IP_LIMIT = positive_integer("RECOVERY_IP_LIMIT", default=30, maximum=1000)
RECOVERY_WINDOW_SECONDS = positive_integer("RECOVERY_WINDOW_SECONDS", default=900, maximum=86400)
PASSWORD_RESET_ENABLED = boolean("PASSWORD_RESET_ENABLED", default=True)

INVITATIONS_ENABLED = boolean("INVITATIONS_ENABLED", default=True)
INVITATION_SECONDS = positive_integer("INVITATION_SECONDS", default=86400, maximum=604800)
INVITATION_RESEND_SECONDS = positive_integer("INVITATION_RESEND_SECONDS", default=60, maximum=86400)
