"""Validated registration/mail configuration; empty allowlist disables signup."""

import os
import re
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email

from .environment import boolean, csv, positive_integer

INSTITUTIONAL_EMAIL_DOMAINS = tuple(value.lower() for value in csv("INSTITUTIONAL_EMAIL_DOMAINS"))
for domain in INSTITUTIONAL_EMAIL_DOMAINS:
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", domain):
        raise ImproperlyConfigured("INSTITUTIONAL_EMAIL_DOMAINS must contain exact DNS domains.")
    try:
        validate_email("registration@" + domain)
    except ValidationError:
        raise ImproperlyConfigured(
            "INSTITUTIONAL_EMAIL_DOMAINS must contain exact DNS domains."
        ) from None
REGISTRATION_REQUIRE_APPROVAL = boolean("REGISTRATION_REQUIRE_APPROVAL", default=False)
VERIFICATION_TOKEN_SECONDS = positive_integer(
    "VERIFICATION_TOKEN_SECONDS", default=86400, maximum=604800
)
REGISTRATION_EMAIL_LIMIT = positive_integer("REGISTRATION_EMAIL_LIMIT", default=3, maximum=100)
REGISTRATION_IP_LIMIT = positive_integer("REGISTRATION_IP_LIMIT", default=30, maximum=1000)
REGISTRATION_WINDOW_SECONDS = positive_integer(
    "REGISTRATION_WINDOW_SECONDS", default=900, maximum=86400
)
PUBLIC_APP_ORIGIN = os.environ.get("PUBLIC_APP_ORIGIN", "http://127.0.0.1:5173").rstrip("/")
try:
    origin = urlsplit(PUBLIC_APP_ORIGIN)
    valid_origin = (
        not any(char.isspace() for char in PUBLIC_APP_ORIGIN)
        and origin.scheme in {"http", "https"}
        and origin.hostname
        and not origin.username
        and not origin.password
        and not origin.path
        and not origin.query
        and not origin.fragment
    )
    origin_port = origin.port
except ValueError:
    valid_origin = False
if not valid_origin:
    raise ImproperlyConfigured(
        "PUBLIC_APP_ORIGIN must be one HTTP(S) origin without credentials or path."
    )
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL") or "no-reply@archive.example.invalid"
try:
    validate_email(DEFAULT_FROM_EMAIL)
except ValidationError:
    raise ImproperlyConfigured("DEFAULT_FROM_EMAIL must be a valid mailbox.") from None
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = positive_integer("EMAIL_PORT", default=587, maximum=65535)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = boolean("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = boolean("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = positive_integer("EMAIL_TIMEOUT", default=10, maximum=60)
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured("EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be true.")
