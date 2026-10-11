"""Local settings; .env is loaded by `uv run --env-file .env`, not implicitly."""

import os

from .base import *
from .environment import boolean, csv, database

DEBUG = boolean("DJANGO_DEBUG", default=True)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-local-development-only")
ALLOWED_HOSTS = csv("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = csv("DJANGO_CSRF_TRUSTED_ORIGINS")
DATABASES = {
    "default": database(
        "DATABASE_URL",
        default="postgresql://aarchive:replace-local-password@localhost:5432/aarchive",
    )
}
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
