from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

import pytest
from django.core import mail
from django.db import close_old_connections
from django.test import Client, override_settings
from django.utils import timezone

from apps.access.models import PrivilegeLock
from apps.accounts.models import EmailVerification, LoginAttempt, User
from apps.accounts.registration.services import account_digest, token_digest, verify
from apps.accounts.registration.throttle import consume_attempt
from apps.audit.models import AuditLog

pytestmark = pytest.mark.django_db
PASSWORD = "synthetic-registration-password-123"
DATA = {"email": "new@iut.example", "password": PASSWORD, "display_name": "New Student"}


@pytest.fixture(autouse=True)
def configuration():
    PrivilegeLock.objects.get_or_create(pk=1)
    with override_settings(
        INSTITUTIONAL_EMAIL_DOMAINS=("iut.example",),
        PUBLIC_APP_ORIGIN="https://archive.example.invalid",
        REGISTRATION_REQUIRE_APPROVAL=False,
    ):
        yield


def browser():
    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/session")
    return client


def post(client, path="register", data=None, **extra):
    return client.post(
        f"/api/auth/{path}",
        DATA if data is None else data,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        **extra,
    )


def create(client, callbacks, data=None):
    with callbacks(execute=True):
        response = post(client, data=data)
    assert response.status_code == 202
    return mail.outbox[-1].body.split("#token=")[1].split()[0]


def test_register_verify_login_and_safe_audit(django_capture_on_commit_callbacks):
    client = browser()
    token = create(
        client, django_capture_on_commit_callbacks, {**DATA, "email": " NEW@IUT.EXAMPLE "}
    )
    user = User.objects.get(email=DATA["email"])
    assert user.state == "PENDING" and not user.is_login_eligible
    assert user.check_password(PASSWORD)
    assert list(user.role_assignments.values_list("role", flat=True)) == ["STUDENT"]
    assert post(client, "login", {"email": user.email, "password": PASSWORD}).status_code == 401
    challenge = EmailVerification.objects.get(user=user)
    assert challenge.token_digest == token_digest(token) and token not in challenge.token_digest
    assert mail.outbox[0].to == [user.email]
    assert "https://archive.example.invalid/verify-email#token=" in mail.outbox[0].body
    assert post(client, "verify", {"token": token}).status_code == 200
    user.refresh_from_db()
    challenge.refresh_from_db()
    assert user.state == "ACTIVE" and user.email_verified_at and challenge.consumed_at
    assert client.get("/api/auth/session").json() == {"user": None}
    assert post(client, "login", {"email": user.email, "password": PASSWORD}).status_code == 200
    assert post(client, "verify", {"token": token}).status_code == 400
    events = AuditLog.objects.filter(
        action__in=[
            "auth.registration.created",
            "auth.verification.issued",
            "auth.verification.completed",
        ]
    )
    assert events.count() == 3
    serialized = str(list(events.values()))
    assert all(value not in serialized for value in [token, PASSWORD, user.email])


def test_approval_requirement_is_snapshotted_and_prevents_login(django_capture_on_commit_callbacks):
    client = browser()
    with override_settings(REGISTRATION_REQUIRE_APPROVAL=True):
        token = create(client, django_capture_on_commit_callbacks)
    assert post(client, "verify", {"token": token}).status_code == 200
    user = User.objects.get(email=DATA["email"])
    assert user.approval_required and user.state == "PENDING" and user.email_verified_at
    assert not user.is_login_eligible and user.approved_at is None
    assert post(client, "login", {"email": user.email, "password": PASSWORD}).status_code == 401


@pytest.mark.parametrize(
    "email", ["new@other.example", "new@sub.iut.example", "new@iut.example.evil.example"]
)
def test_domain_rejection_is_generic_and_creates_nothing(email, django_capture_on_commit_callbacks):
    client = browser()
    with django_capture_on_commit_callbacks(execute=True):
        rejected = post(client, data={**DATA, "email": email})
        accepted = post(client)
    assert rejected.status_code == accepted.status_code == 202
    assert rejected.json() == accepted.json()
    assert not User.objects.filter(email=email).exists()
    assert len(mail.outbox) == 1


def test_empty_allowlist_disables_registration():
    with override_settings(INSTITUTIONAL_EMAIL_DOMAINS=()):
        assert post(browser()).status_code == 202
    assert not User.objects.exists()


@pytest.mark.parametrize(
    "extra",
    [
        {"roles": ["ADMINISTRATOR"]},
        {"role": "TEACHER"},
        {"state": "ACTIVE"},
        {"approved_at": "today"},
        {"student_id": "someone-else"},
        {"email_verified_at": "today"},
    ],
)
def test_mass_assignment_fails(extra):
    response = post(browser(), data={**DATA, **extra})
    assert response.status_code == 400
    assert not User.objects.exists() and not EmailVerification.objects.exists()


@pytest.mark.parametrize(
    "password", ["short", "123456789012345", "administrator", "new@iut.example"]
)
def test_password_policy_applies_before_account_creation(password):
    assert post(browser(), data={**DATA, "password": password}).status_code == 400
    assert not User.objects.exists()


def test_existing_account_never_mutated_or_sent_registration_mail(
    django_capture_on_commit_callbacks,
):
    user = User.objects.create_user(DATA["email"], "original-password", display_name="Original")
    before = User.objects.values().get(pk=user.pk)
    with django_capture_on_commit_callbacks(execute=True):
        result = post(browser())
    assert result.status_code == 202
    assert User.objects.values().get(pk=user.pk) == before
    assert user.profile.display_name == "Original"
    assert not EmailVerification.objects.exists() and not mail.outbox


def test_resend_replaces_token_without_changing_password(django_capture_on_commit_callbacks):
    client = browser()
    old = create(client, django_capture_on_commit_callbacks)
    with django_capture_on_commit_callbacks(execute=True):
        response = post(client, "resend-verification", {"email": " NEW@IUT.EXAMPLE "})
    assert response.status_code == 202
    new = mail.outbox[-1].body.split("#token=")[1].split()[0]
    assert old != new and EmailVerification.objects.count() == 1
    assert post(client, "verify", {"token": old}).status_code == 400
    assert post(client, "verify", {"token": new}).status_code == 200
    assert User.objects.get(email=DATA["email"]).check_password(PASSWORD)


@pytest.mark.parametrize("state", ["SUSPENDED", "ARCHIVED", "ANONYMIZED"])
def test_closed_accounts_cannot_be_restored_by_verification(
    state, django_capture_on_commit_callbacks
):
    client = browser()
    token = create(client, django_capture_on_commit_callbacks)
    User.objects.update(state=state)
    assert post(client, "verify", {"token": token}).status_code == 400
    with django_capture_on_commit_callbacks(execute=True):
        assert post(client, "resend-verification", {"email": DATA["email"]}).status_code == 202
    assert len(mail.outbox) == 1
    assert User.objects.get().state == state


def test_expired_token_cannot_activate_and_can_be_replaced(django_capture_on_commit_callbacks):
    client = browser()
    token = create(client, django_capture_on_commit_callbacks)
    EmailVerification.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert post(client, "verify", {"token": token}).status_code == 400
    assert User.objects.get().state == "PENDING"
    with django_capture_on_commit_callbacks(execute=True):
        post(client, "resend-verification", {"email": DATA["email"]})
    fresh = mail.outbox[-1].body.split("#token=")[1].split()[0]
    assert post(client, "verify", {"token": fresh}).status_code == 200


@pytest.mark.parametrize(
    "route,data",
    [
        ("register", DATA),
        ("resend-verification", {"email": DATA["email"]}),
        ("verify", {"token": "a" * 43}),
    ],
)
def test_anonymous_csrf_and_origin_enforced(route, data):
    client = browser()
    assert (
        client.post(f"/api/auth/{route}", data, content_type="application/json").status_code == 403
    )
    response = post(client, route, data, HTTP_ORIGIN="https://evil.example")
    assert response.status_code == 403 and response["Cache-Control"] == "no-store"
    assert client.get(f"/api/auth/{route}").status_code == 405


def test_shared_resend_limit_and_fixed_recovery():
    client = browser()
    with override_settings(REGISTRATION_EMAIL_LIMIT=2, REGISTRATION_IP_LIMIT=10):
        first = post(client, "resend-verification", {"email": DATA["email"]})
        assert first.status_code == 202
        assert post(client).status_code == 202
        blocked = post(client, "resend-verification", {"email": " NEW@IUT.EXAMPLE "})
        assert blocked.status_code == 429 and int(blocked["Retry-After"]) > 0
        deadlines = list(LoginAttempt.objects.values_list("resets_at", flat=True))
        assert post(client).status_code == 429
        assert list(LoginAttempt.objects.values_list("resets_at", flat=True)) == deadlines
        LoginAttempt.objects.update(resets_at=timezone.now() - timedelta(seconds=1))
        assert post(client).status_code == 202


def test_peer_budget_covers_variations_and_ignores_forwarded_headers():
    client = browser()
    with override_settings(REGISTRATION_IP_LIMIT=1):
        assert post(client, "resend-verification", {"email": DATA["email"]}).status_code == 202
        count = LoginAttempt.objects.count()
        assert (
            post(
                client,
                data={**DATA, "email": "different@iut.example"},
                HTTP_X_FORWARDED_FOR="198.51.100.3",
            ).status_code
            == 429
        )
        assert LoginAttempt.objects.count() == count
        assert post(client, "verify", {"token": "a" * 43}).status_code == 429


def test_delivery_failure_is_generic_and_recoverable(django_capture_on_commit_callbacks, caplog):
    client = browser()
    with patch(
        "apps.accounts.registration.services.send_mail", side_effect=RuntimeError("smtp-secret")
    ):
        with django_capture_on_commit_callbacks(execute=True):
            response = post(client)
    assert response.status_code == 202 and "smtp-secret" not in caplog.text
    assert User.objects.get().state == "PENDING"
    with django_capture_on_commit_callbacks(execute=True):
        assert post(client, "resend-verification", {"email": DATA["email"]}).status_code == 202
    assert len(mail.outbox) == 1


def test_audit_failure_rolls_back_registration_and_does_not_send(
    django_capture_on_commit_callbacks,
):
    with django_capture_on_commit_callbacks(execute=True):
        with patch(
            "apps.accounts.registration.services.record_event", side_effect=RuntimeError("audit")
        ):
            with pytest.raises(RuntimeError):
                post(browser())
    assert not User.objects.exists() and not EmailVerification.objects.exists() and not mail.outbox


def test_verification_audit_failure_keeps_token_usable(django_capture_on_commit_callbacks):
    client = browser()
    token = create(client, django_capture_on_commit_callbacks)
    with patch(
        "apps.accounts.registration.services.record_event", side_effect=RuntimeError("audit")
    ):
        with pytest.raises(RuntimeError):
            post(client, "verify", {"token": token})
    assert User.objects.get().state == "PENDING"
    assert EmailVerification.objects.get().consumed_at is None
    assert post(client, "verify", {"token": token}).status_code == 200


@pytest.mark.django_db(transaction=True)
def test_concurrent_verification_consumes_once():
    user = User.objects.create_user(DATA["email"], PASSWORD)
    token = "a" * 43
    EmailVerification.objects.create(
        user=user,
        token_digest=token_digest(token),
        account_digest=account_digest(user),
        expires_at=timezone.now() + timedelta(hours=1),
    )
    barrier = Barrier(2)

    def attempt():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return verify(token)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == [False, True]
    assert AuditLog.objects.filter(action="auth.verification.completed").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_resend_budgets_are_shared():
    barrier = Barrier(4)

    def attempt():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return consume_attempt(DATA["email"], "127.0.0.1")
        finally:
            close_old_connections()

    with override_settings(REGISTRATION_EMAIL_LIMIT=2):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: attempt(), range(4)))
    assert results.count(None) == 2


def test_disabled_domain_invalidates_outstanding_link(django_capture_on_commit_callbacks):
    client = browser()
    token = create(client, django_capture_on_commit_callbacks)
    with override_settings(INSTITUTIONAL_EMAIL_DOMAINS=()):
        assert post(client, "verify", {"token": token}).status_code == 400
    assert User.objects.get().email_verified_at is None


def test_verified_and_unknown_resend_have_same_response(django_capture_on_commit_callbacks):
    client = browser()
    token = create(client, django_capture_on_commit_callbacks)
    assert post(client, "verify", {"token": token}).status_code == 200
    with django_capture_on_commit_callbacks(execute=True):
        known = post(client, "resend-verification", {"email": DATA["email"]})
        unknown = post(client, "resend-verification", {"email": "absent@iut.example"})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert len(mail.outbox) == 1


@pytest.mark.parametrize(
    "data",
    [[], {**DATA, "password": 12}, {**DATA, "email": "bad"}, {**DATA, "display_name": "x" * 9000}],
)
def test_malformed_or_oversized_registration_does_not_create(data):
    assert post(browser(), data=data).status_code == 400
    assert not User.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_registration_creates_one_pending_student():
    from apps.accounts.registration.services import register

    barrier = Barrier(2)

    def attempt():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            register(**DATA)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: attempt(), range(2)))
    assert User.objects.count() == EmailVerification.objects.count() == 1
    assert User.objects.get().state == "PENDING"
    assert len(mail.outbox) == 1


@pytest.mark.parametrize("changed", ["email", "password"])
def test_challenge_is_bound_to_original_email_and_password(
    changed, django_capture_on_commit_callbacks
):
    client = browser()
    token = create(client, django_capture_on_commit_callbacks)
    user = User.objects.get()
    if changed == "email":
        user.email = "changed@iut.example"
    else:
        user.set_password("another-synthetic-password-123")
    user.save()
    assert post(client, "verify", {"token": token}).status_code == 400
    user.refresh_from_db()
    assert user.email_verified_at is None and user.state == "PENDING"
