"""Exercise startup in fresh processes so module caching cannot hide bad settings."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Synthetic test values only. They do not refer to any deployed resource.
PRODUCTION_ENV = {
    "DJANGO_SECRET_KEY": "synthetic-test-key-0123456789-abcdefghijklmnopqrstuvwxyz-ABCDEFGHIJ",
    "DJANGO_ALLOWED_HOSTS": "archive.example.invalid",
    "DATABASE_URL": "postgresql://fixture:synthetic-password@db.invalid:5432/archive",
}
INSPECT = """
import json
import django
django.setup()
from django.conf import settings
print(json.dumps({
    'debug': settings.DEBUG,
    'engine': settings.DATABASES['default']['ENGINE'],
    'database': settings.DATABASES['default']['NAME'],
    'host': settings.DATABASES['default']['HOST'],
    'port': settings.DATABASES['default']['PORT'],
    'sslmode': settings.DATABASES['default'].get('OPTIONS', {}).get('sslmode'),
    'secure_session': settings.SESSION_COOKIE_SECURE,
    'secure_csrf': settings.CSRF_COOKIE_SECURE,
    'redirect_https': settings.SECURE_SSL_REDIRECT,
    'apps': settings.INSTALLED_APPS,
}))
"""


def startup(profile, overrides=None, *, script=INSPECT):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("DJANGO_")
        and key not in {"DATABASE_URL", "TEST_DATABASE_URL", "PYTHONPATH"}
    }
    env.update(overrides or {})
    env["DJANGO_SETTINGS_MODULE"] = f"config.settings.{profile}"
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_production_valid_configuration_uses_postgres_and_secure_defaults():
    env = {**PRODUCTION_ENV, "DATABASE_URL": PRODUCTION_ENV["DATABASE_URL"] + "?sslmode=require"}
    result = startup("production", env)
    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout)
    assert state == {
        "debug": False,
        "engine": "django.db.backends.postgresql",
        "database": "archive",
        "host": "db.invalid",
        "port": 5432,
        "sslmode": "require",
        "secure_session": True,
        "secure_csrf": True,
        "redirect_https": True,
        "apps": [
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.sessions",
            "apps.accounts.apps.AccountsConfig",
            "apps.audit.apps.AuditConfig",
            "apps.access.apps.AccessConfig",
            "apps.academics.apps.AcademicsConfig",
            "rest_framework",
        ],
    }


@pytest.mark.parametrize("missing", ["DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "DATABASE_URL"])
def test_production_missing_configuration_fails_startup(missing):
    env = {key: value for key, value in PRODUCTION_ENV.items() if key != missing}
    result = startup("production", env)
    assert result.returncode != 0
    assert missing in result.stderr
    assert "ImproperlyConfigured" in result.stderr
    assert "synthetic-password" not in result.stderr


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DJANGO_SECRET_KEY", "replace-with-a-generated-local-secret"),
        ("DJANGO_SECRET_KEY", "x" * 60),
        ("DJANGO_DEBUG", "true"),
        ("DJANGO_DEBUG", "not-a-boolean"),
        ("AUTH_SESSION_SECONDS", "0"),
        ("PASSWORD_RESET_SECONDS", "0"),
        ("INVITATION_SECONDS", "0"),
        ("INVITATION_RESEND_SECONDS", "-1"),
        ("INVITATIONS_ENABLED", "maybe"),
        ("PASSWORD_RESET_ENABLED", "maybe"),
        ("RECOVERY_IDENTITY_LIMIT", "-1"),
        ("RECOVERY_IP_LIMIT", "1001"),
        ("RECOVERY_WINDOW_SECONDS", "invalid"),
        ("INSTITUTIONAL_EMAIL_DOMAINS", "*.example.com"),
        ("REGISTRATION_REQUIRE_APPROVAL", "maybe"),
        ("VERIFICATION_TOKEN_SECONDS", "0"),
        ("REGISTRATION_EMAIL_LIMIT", "-1"),
        ("PUBLIC_APP_ORIGIN", "https://user:secret@archive.example.invalid"),
        ("PUBLIC_APP_ORIGIN", "https://archive.example.invalid/path"),
        ("EMAIL_PORT", "70000"),
        ("EMAIL_USE_SSL", "true"),
        ("DEFAULT_FROM_EMAIL", "invalid"),
        ("AUTH_LOGIN_WINDOW_SECONDS", "-1"),
        ("AUTH_LOGIN_ATTEMPT_LIMIT", "invalid"),
        ("DJANGO_ALLOWED_HOSTS", "*"),
        ("DJANGO_CSRF_TRUSTED_ORIGINS", "http://archive.example.invalid"),
        ("DATABASE_URL", "sqlite:///db.sqlite3"),
        ("DATABASE_URL", "postgresql://fixture@db.invalid/archive"),
        ("DATABASE_URL", "postgresql://fixture:replace-local-password@db.invalid/archive"),
        ("DATABASE_URL", "postgresql://fixture:synthetic-password@db.invalid:bad/archive"),
    ],
)
def test_production_invalid_configuration_fails_without_leaking_values(name, value):
    result = startup("production", {**PRODUCTION_ENV, name: value})
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert name in result.stderr
    assert "synthetic-password" not in result.stderr
    assert PRODUCTION_ENV["DJANGO_SECRET_KEY"] not in result.stderr


def test_development_database_url_is_respected():
    result = startup(
        "development", {"DATABASE_URL": "postgresql://fixture:example@localhost:5544/custom"}
    )
    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout)
    assert state["database"] == "custom"
    assert state["port"] == 5544


def test_tests_ignore_developer_database_and_select_postgres():
    result = startup("test", {"DATABASE_URL": "sqlite:///never-use-this.sqlite3"})
    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout)
    assert state["engine"] == "django.db.backends.postgresql"
    assert state["database"] == "aarchive_test"


def test_test_database_override_is_respected():
    result = startup("test", {"TEST_DATABASE_URL": "postgresql://fixture:example@db:5545/isolated"})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["database"] == "isolated"


@pytest.mark.parametrize("entrypoint", ["wsgi", "asgi"])
def test_server_entrypoints_default_to_production_and_fail_without_secrets(entrypoint):
    script = f"import os; os.environ.pop('DJANGO_SETTINGS_MODULE'); import config.{entrypoint}"
    result = startup("development", script=script)
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY must be set" in result.stderr


def test_production_registration_requires_https_and_configured_mail():
    enabled = {**PRODUCTION_ENV, "INSTITUTIONAL_EMAIL_DOMAINS": "iut.example"}
    result = startup("production", enabled)
    assert result.returncode != 0 and "PUBLIC_APP_ORIGIN" in result.stderr
    enabled["PUBLIC_APP_ORIGIN"] = "https://archive.example.invalid"
    result = startup("production", enabled)
    assert result.returncode != 0 and "EMAIL_HOST" in result.stderr
    enabled["EMAIL_HOST"] = "smtp.example.invalid"
    result = startup("production", enabled)
    assert result.returncode != 0 and "DEFAULT_FROM_EMAIL" in result.stderr
    enabled["DEFAULT_FROM_EMAIL"] = "archive@iut.example"
    result = startup("production", enabled)
    assert result.returncode == 0, result.stderr


def test_mail_adapters_are_profile_specific():
    script = "from django.conf import settings; print(settings.EMAIL_BACKEND)"
    assert "console.EmailBackend" in startup("development", script=script).stdout
    assert "locmem.EmailBackend" in startup("test", script=script).stdout
    assert "smtp.EmailBackend" in startup("production", PRODUCTION_ENV, script=script).stdout


def test_production_recovery_opt_in_requires_mail_even_when_signup_disabled():
    env = {**PRODUCTION_ENV, "PASSWORD_RESET_ENABLED": "true", "INSTITUTIONAL_EMAIL_DOMAINS": ""}
    result = startup("production", env)
    assert result.returncode != 0 and "PUBLIC_APP_ORIGIN" in result.stderr
    env.update(
        PUBLIC_APP_ORIGIN="https://archive.example.invalid",
        EMAIL_HOST="smtp.example.invalid",
        DEFAULT_FROM_EMAIL="archive@iut.example",
    )
    result = startup("production", env)
    assert result.returncode == 0, result.stderr


def test_recovery_default_is_off_in_production_and_on_locally():
    script = "from django.conf import settings; print(settings.PASSWORD_RESET_ENABLED)"
    assert startup("production", PRODUCTION_ENV, script=script).stdout.strip() == "False"
    assert startup("development", script=script).stdout.strip() == "True"


def test_production_invitation_opt_in_requires_mail():
    env = {**PRODUCTION_ENV, "INVITATIONS_ENABLED": "true"}
    result = startup("production", env)
    assert result.returncode != 0 and "PUBLIC_APP_ORIGIN" in result.stderr
    env.update(
        PUBLIC_APP_ORIGIN="https://archive.example.invalid",
        EMAIL_HOST="smtp.example.invalid",
        DEFAULT_FROM_EMAIL="archive@iut.example",
    )
    result = startup("production", env)
    assert result.returncode == 0, result.stderr
