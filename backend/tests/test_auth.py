from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.db import close_old_connections
from django.test import Client, override_settings
from django.utils import timezone

from apps.access.models import PrivilegeLock
from apps.accounts.auth.throttle import consume_attempt
from apps.accounts.models import LoginAttempt, User, UserRole
from apps.audit.models import AuditLog

pytestmark = pytest.mark.django_db
PASSWORD = "synthetic-browser-password-123"


@pytest.fixture
def user():
    PrivilegeLock.objects.get_or_create(pk=1)
    account = User.objects.create_user("member@iut.example", PASSWORD, display_name="Test Member")
    User.objects.filter(pk=account.pk).update(state="ACTIVE", email_verified_at=timezone.now())
    account.refresh_from_db()
    return account


def browser():
    client = Client(enforce_csrf_checks=True)
    response = client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json() == {"user": None}
    return client


def post(client, path="/api/auth/login", data=None, **extra):
    return client.post(
        path,
        data
        if data is not None
        else {
            "email": "member@iut.example",
            "password": PASSWORD,
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        **extra,
    )


def test_login_session_logout_and_real_audit_permission(user):
    UserRole.objects.create(user=user, role="ADMINISTRATOR")
    client = browser()
    response = post(client, data={"email": " MEMBER@IUT.EXAMPLE ", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(user.pk)
    assert response.json()["user"]["roles"] == ["ADMINISTRATOR", "STUDENT"]
    assert response["Cache-Control"] == "no-store"
    cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["httponly"] and cookie["samesite"] == "Lax"
    assert client.get("/api/audit").status_code == 200
    assert client.get("/api/auth/session").json()["user"]["email"] == user.email
    key = client.cookies[settings.SESSION_COOKIE_NAME].value
    assert post(client, "/api/auth/logout", {}).status_code == 204
    assert not Session.objects.filter(session_key=key).exists()
    assert client.get("/api/auth/session").json() == {"user": None}
    assert client.get("/api/audit").status_code == 403
    assert AuditLog.objects.filter(action="auth.login.succeeded").count() == 1
    assert (
        AuditLog.objects.filter(action="auth.session.ended", new_value__outcome="logout").count()
        == 1
    )


def test_session_fixation_and_csrf_rotation(user):
    client = browser()
    pre_login = client.session
    pre_login["anonymous_test"] = "synthetic"
    pre_login.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = pre_login.session_key
    old_key = pre_login.session_key
    old_csrf = client.cookies["csrftoken"].value
    assert post(client).status_code == 200
    assert client.cookies[settings.SESSION_COOKIE_NAME].value != old_key
    assert client.cookies["csrftoken"].value != old_csrf
    assert not Session.objects.filter(session_key=old_key).exists()
    replay = Client()
    replay.cookies[settings.SESSION_COOKIE_NAME] = old_key
    assert replay.get("/api/auth/session").json() == {"user": None}
    assert (
        client.post(
            "/api/auth/logout", {}, content_type="application/json", HTTP_X_CSRFTOKEN=old_csrf
        ).status_code
        == 403
    )


@pytest.mark.parametrize("path", ["/api/auth/login", "/api/auth/logout"])
def test_csrf_required_even_for_anonymous_requests(user, path):
    client = browser()
    assert client.post(path, {}, content_type="application/json").status_code == 403
    assert post(client, path, {}, HTTP_ORIGIN="https://hostile.invalid").status_code == 403
    assert not AuditLog.objects.exists()


@pytest.mark.parametrize(
    "case", ["wrong", "missing", "pending", "suspended", "archived", "anonymized", "unusable"]
)
def test_invalid_credentials_are_indistinguishable(user, case):
    email, password = user.email, PASSWORD
    if case == "wrong":
        password = "synthetic-wrong"
    elif case == "missing":
        email = "missing@iut.example"
    elif case == "unusable":
        user.set_unusable_password()
        user.save(update_fields=["password"])
    else:
        User.objects.filter(pk=user.pk).update(state=case.upper())
    client = browser()
    response = post(client, data={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json() == {
        "code": "invalid_credentials",
        "message": "Unable to sign in with those details.",
        "request_id": None,
    }
    assert settings.SESSION_COOKIE_NAME not in response.cookies
    assert client.get("/api/auth/session").json() == {"user": None}
    event = AuditLog.objects.get(action="auth.login.failed")
    assert event.actor_id is None
    assert email not in str(event.__dict__) and password not in str(event.__dict__)


@pytest.mark.parametrize("state", ["INACTIVE", "GRADUATED", "ALUMNI"])
def test_inactive_reactivates_and_alumni_keep_login(user, state):
    User.objects.filter(pk=user.pk).update(state=state)
    response = post(browser())
    assert response.status_code == 200
    assert response.json()["user"]["state"] == ("ACTIVE" if state == "INACTIVE" else state)
    assert AuditLog.objects.filter(action="accounts.state.changed").count() == int(
        state == "INACTIVE"
    )


@pytest.mark.parametrize("state", ["PENDING", "SUSPENDED", "ARCHIVED", "ANONYMIZED"])
def test_detected_forbidden_state_deletes_session_and_restoration_cannot_revive_it(user, state):
    client = browser()
    assert post(client).status_code == 200
    key = client.cookies[settings.SESSION_COOKIE_NAME].value
    User.objects.filter(pk=user.pk).update(state=state)
    assert client.get("/api/auth/session").json() == {"user": None}
    assert not Session.objects.filter(session_key=key).exists()
    User.objects.filter(pk=user.pk).update(state="ACTIVE")  # Trusted fixture restoration only.
    client.cookies[settings.SESSION_COOKIE_NAME] = key
    assert client.get("/api/auth/session").json() == {"user": None}
    assert AuditLog.objects.filter(
        action="auth.session.ended", new_value__outcome="revoked"
    ).exists()


def test_password_change_and_expiry_reject_old_sessions(user):
    client = browser()
    post(client)
    user.set_password("synthetic-new-password")
    user.save(update_fields=["password"])
    assert client.get("/api/auth/session").json() == {"user": None}
    post(client, data={"email": user.email, "password": "synthetic-new-password"})
    key = client.cookies[settings.SESSION_COOKIE_NAME].value
    Session.objects.filter(pk=key).update(expire_date=timezone.now() - timedelta(seconds=1))
    assert client.get("/api/auth/session").json() == {"user": None}


@override_settings(LOGIN_ATTEMPT_LIMIT=2, LOGIN_IP_LIMIT=10, LOGIN_WINDOW_SECONDS=60)
def test_lockout_is_shared_case_insensitive_and_recovers_without_extending(user):
    first, second = browser(), browser()
    for client in [first, second]:
        assert (
            post(client, data={"email": " MEMBER@IUT.EXAMPLE ", "password": "wrong"}).status_code
            == 401
        )
    snapshots = list(LoginAttempt.objects.values_list("key", "resets_at"))
    response = post(first)
    assert response.status_code == 429
    assert 0 < int(response["Retry-After"]) <= 60
    assert list(LoginAttempt.objects.values_list("key", "resets_at")) == snapshots
    assert all(user.email not in key and "127.0.0.1" not in key for key, _ in snapshots)
    LoginAttempt.objects.all().update(resets_at=timezone.now() - timedelta(seconds=1))
    assert post(second).status_code == 200


@override_settings(LOGIN_ATTEMPT_LIMIT=2, LOGIN_IP_LIMIT=10)
def test_unknown_identifiers_lock_the_same_way_as_known_accounts(user):
    client = browser()
    for _ in range(2):
        assert (
            post(client, data={"email": "missing@iut.example", "password": "wrong"}).status_code
            == 401
        )
    assert (
        post(client, data={"email": "missing@iut.example", "password": "wrong"}).status_code == 429
    )


@override_settings(LOGIN_ATTEMPT_LIMIT=10, LOGIN_IP_LIMIT=2)
def test_peer_limit_spans_identifiers_and_ignores_forwarded_headers(user):
    client = browser()
    for index in range(2):
        assert (
            post(
                client,
                data={"email": f"missing{index}@iut.example", "password": "wrong"},
                HTTP_X_FORWARDED_FOR=f"192.0.2.{index}",
            ).status_code
            == 401
        )
    assert post(client, HTTP_X_FORWARDED_FOR="198.51.100.1").status_code == 429
    assert LoginAttempt.objects.count() == 3  # One peer + two attempted identities.
    assert (
        post(client, data={"email": "another-new@iut.example", "password": "wrong"}).status_code
        == 429
    )
    assert LoginAttempt.objects.count() == 3


def test_oversized_request_body_is_rejected_before_authentication(user):
    client = browser()
    response = post(client, data={"email": user.email, "password": "x" * 10000})
    assert response.status_code == 400
    assert not LoginAttempt.objects.exists()


def test_expired_counter_cleanup_preserves_live_lockouts(user):
    consume_attempt(user.email, "192.0.2.1")
    row = LoginAttempt.objects.first()
    LoginAttempt.objects.filter(pk=row.pk).update(resets_at=timezone.now() - timedelta(seconds=1))
    call_command("clear_expired_login_attempts")
    assert LoginAttempt.objects.count() == 1


@override_settings(SESSION_COOKIE_AGE=60, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
def test_secure_cookie_flags_and_absolute_session_lifetime(user):
    client = Client(enforce_csrf_checks=True)
    response = client.get("/api/auth/session", secure=True)
    assert response.cookies["csrftoken"]["secure"]
    response = post(client, secure=True, HTTP_ORIGIN="https://testserver")
    assert response.status_code == 200
    assert response.cookies[settings.SESSION_COOKIE_NAME]["secure"]
    expires = client.session.get_expiry_date()
    assert 0 < (expires - timezone.now()).total_seconds() <= 60
    client.get("/api/auth/session", secure=True)
    assert client.session.get_expiry_date() == expires


@pytest.mark.parametrize(
    "data",
    [
        {"email": "member@iut.example", "password": PASSWORD, "roles": ["ADMINISTRATOR"]},
        {"email": "member@iut.example", "password": 123},
        {"email": "member@iut.example", "password": "x" * 1025},
    ],
)
def test_login_rejects_extra_fields_types_and_oversize(user, data):
    assert post(browser(), data=data).status_code == 400


def test_unauthenticated_logout_is_idempotent_and_get_cannot_mutate(user):
    client = browser()
    assert post(client, "/api/auth/logout", {}).status_code == 204
    for path in ["/api/auth/login", "/api/auth/logout"]:
        assert client.get(path).status_code == 405


def test_audit_failure_does_not_commit_a_login_session(user, monkeypatch):
    client = browser()

    def fail(**kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("apps.accounts.auth.services.record_event", fail)
    with pytest.raises(RuntimeError):
        post(client)
    assert not Session.objects.exists()
    user.refresh_from_db()
    assert user.last_login is None


@pytest.mark.django_db(transaction=True)
@override_settings(LOGIN_ATTEMPT_LIMIT=2, LOGIN_IP_LIMIT=10)
def test_concurrent_attempts_cannot_exceed_shared_budget():
    barrier = Barrier(4)

    def attempt(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return consume_attempt("concurrent@iut.example", "192.0.2.1")
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(attempt, range(4)))
    assert results.count(None) == 2
    assert len([result for result in results if result is not None]) == 2
