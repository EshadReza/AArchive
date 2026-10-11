"""Isolated test configuration; never inherits a developer's DATABASE_URL."""

import os

from .base import *
from .environment import database

DEBUG = False
SECRET_KEY = "test-only-key-never-used-by-production"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {
    "default": database(
        "TEST_DATABASE_URL",
        default="postgresql://aarchive:replace-local-password@localhost:5432/aarchive_test",
    )
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Browser runner owns an isolated temporary mailbox; never enabled in production.
if os.environ.get("AARCHIVE_TEST_MAIL_DIRECTORY"):
    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = os.environ["AARCHIVE_TEST_MAIL_DIRECTORY"]
