"""Small environment parsers with configuration errors that do not reveal values."""

import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be set.")
    return value


def boolean(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ImproperlyConfigured(f"{name} must be true or false.")


def positive_integer(name, *, default, maximum):
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        raise ImproperlyConfigured(f"{name} must be a positive integer.") from None
    if not 1 <= value <= maximum:
        raise ImproperlyConfigured(f"{name} is outside its supported range.")
    return value


def csv(name: str, *, default: str = "") -> list[str]:
    return [value.strip() for value in os.environ.get(name, default).split(",") if value.strip()]


def database(name: str, *, default: str | None = None) -> dict:
    value = os.environ.get(name, default)
    if not value or not value.strip():
        raise ImproperlyConfigured(f"{name} must be set to a PostgreSQL URL.")
    try:
        config = dj_database_url.parse(value, conn_max_age=0, conn_health_checks=True)
    except ValueError, KeyError:
        raise ImproperlyConfigured(f"{name} must be a valid PostgreSQL URL.") from None
    if config["ENGINE"] != "django.db.backends.postgresql" or not config.get("NAME"):
        raise ImproperlyConfigured(f"{name} must select a PostgreSQL database.")
    config.setdefault("OPTIONS", {}).setdefault("connect_timeout", 5)
    return config
