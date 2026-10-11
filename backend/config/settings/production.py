"""Fail closed on missing deployment configuration; no development fallbacks."""

from django.core.exceptions import ImproperlyConfigured

from .base import *
from .environment import boolean, csv, database, required

SECRET_KEY = required("DJANGO_SECRET_KEY")
if (
    len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
    or SECRET_KEY.startswith(("django-insecure-", "replace-", "test-only-"))
):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be a generated production secret.")

if boolean("DJANGO_DEBUG", default=False):
    raise ImproperlyConfigured("DJANGO_DEBUG must be false in production.")
DEBUG = False
ALLOWED_HOSTS = csv("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must list explicit production hosts.")
CSRF_TRUSTED_ORIGINS = csv("DJANGO_CSRF_TRUSTED_ORIGINS")
if any(not origin.startswith("https://") or "*" in origin for origin in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured("DJANGO_CSRF_TRUSTED_ORIGINS must list explicit HTTPS origins.")
DATABASES = {"default": database("DATABASE_URL")}
if not DATABASES["default"].get("USER") or not DATABASES["default"].get("PASSWORD"):
    raise ImproperlyConfigured("DATABASE_URL must include a database user and password.")
if DATABASES["default"]["PASSWORD"].startswith("replace-"):
    raise ImproperlyConfigured("DATABASE_URL must not use the example password.")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
# Do not trust forwarded headers until the deployment's proxy boundary is defined.
SECURE_PROXY_SSL_HEADER = None

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
PASSWORD_RESET_ENABLED = boolean("PASSWORD_RESET_ENABLED", default=False)
INVITATIONS_ENABLED = boolean("INVITATIONS_ENABLED", default=False)
if INSTITUTIONAL_EMAIL_DOMAINS or PASSWORD_RESET_ENABLED or INVITATIONS_ENABLED:
    if not PUBLIC_APP_ORIGIN.startswith("https://"):
        raise ImproperlyConfigured("PUBLIC_APP_ORIGIN must use HTTPS for production account email.")
    if not EMAIL_HOST:
        raise ImproperlyConfigured(
            "EMAIL_HOST must be set when production account email is enabled."
        )
    if DEFAULT_FROM_EMAIL.endswith(".invalid"):
        raise ImproperlyConfigured(
            "DEFAULT_FROM_EMAIL must be configured for production account email."
        )
