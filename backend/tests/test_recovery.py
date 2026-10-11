from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.sessions.models import Session
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections
from django.test import Client, override_settings
from django.utils import timezone

from apps.access.models import PrivilegeLock
from apps.accounts.models import EmailVerification, LoginAttempt, PasswordReset, User, UserRole
from apps.accounts.recovery.lifecycle import StateConflict, transition
from apps.accounts.recovery.services import confirm_reset
from apps.accounts.recovery.throttle import consume_attempt
from apps.accounts.registration.services import account_digest, token_digest
from apps.audit.models import AuditLog

pytestmark = pytest.mark.django_db
OLD = "synthetic-original-password-123"
NEW = "synthetic-replacement-password-456"


@pytest.fixture(autouse=True)
def configuration():
    PrivilegeLock.objects.get_or_create(pk=1)
    with override_settings(
        PASSWORD_RESET_ENABLED=True,
        PUBLIC_APP_ORIGIN="https://archive.example.invalid",
        INSTITUTIONAL_EMAIL_DOMAINS=("iut.example",),
    ):
        yield


@pytest.fixture
def member():
    return eligible("member@iut.example")


def eligible(email):
    user = User.objects.create_user(email, OLD, display_name="Test Member")
    user.state = "ACTIVE"
    user.email_verified_at = timezone.now()
    user.save()
    return user


@pytest.fixture
def admin():
    user = eligible("admin@iut.example")
    UserRole.objects.create(user=user, role="ADMINISTRATOR")
    return user


def browser():
    client = Client(enforce_csrf_checks=True)
    assert client.get("/api/auth/session").status_code == 200
    return client


def post(client, route, data, **extra):
    return client.post(
        route,
        data,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        **extra,
    )


def login(user):
    client = browser()
    assert (
        post(client, "/api/auth/login", {"email": user.email, "password": OLD}).status_code == 200
    )
    return client


def issue(client, user, callbacks):
    with callbacks(execute=True):
        response = post(client, "/api/auth/password-reset", {"email": user.email})
    assert response.status_code == 202
    return mail.outbox[-1].body.split("#token=")[1].split()[0]


def confirm(client, token, password=NEW):
    return post(client, "/api/auth/password-reset/confirm", {"token": token, "password": password})


def command(admin, user, name, **overrides):
    return transition(
        actor=admin,
        subject_id=user.pk,
        command=name,
        expected_state=user.state,
        reason="administrative_change",
        **overrides,
    )


def test_reset_consumes_once_and_deletes_all_user_sessions(
    member, admin, django_capture_on_commit_callbacks
):
    first, second, unrelated = login(member), login(member), login(admin)
    keys = [first.cookies["sessionid"].value, second.cookies["sessionid"].value]
    unrelated_key = unrelated.cookies["sessionid"].value
    anon = browser()
    token = issue(anon, member, django_capture_on_commit_callbacks)
    row = PasswordReset.objects.get(user=member)
    assert row.token_digest == token_digest(token)
    assert row.account_digest == account_digest(member)
    assert "https://archive.example.invalid/reset-password#token=" in mail.outbox[-1].body
    assert confirm(anon, token).status_code == 200
    assert not Session.objects.filter(pk__in=keys).exists()
    assert Session.objects.filter(pk=unrelated_key).exists()
    assert (
        first.get("/api/auth/session").json()
        == second.get("/api/auth/session").json()
        == {"user": None}
    )
    assert confirm(anon, token).status_code == 400
    assert (
        post(anon, "/api/auth/login", {"email": member.email, "password": OLD}).status_code == 401
    )
    assert (
        post(anon, "/api/auth/login", {"email": member.email, "password": NEW}).status_code == 200
    )
    member.refresh_from_db()
    assert member.state == "ACTIVE" and member.check_password(NEW)
    serialized = str(list(AuditLog.objects.filter(action__startswith="auth.").values()))
    assert all(
        value not in serialized for value in [token, OLD, NEW, member.password, member.email]
    )


def test_password_change_requires_current_password_and_revokes_reset_links(
    member, django_capture_on_commit_callbacks
):
    client, other = login(member), login(member)
    token = issue(browser(), member, django_capture_on_commit_callbacks)
    key = client.cookies["sessionid"].value
    wrong = post(
        client, "/api/auth/password-change", {"current_password": "wrong", "password": NEW}
    )
    assert wrong.status_code == 400 and Session.objects.filter(pk=key).exists()
    good = post(client, "/api/auth/password-change", {"current_password": OLD, "password": NEW})
    assert good.status_code == 200
    assert not Session.objects.filter(pk=key).exists()
    assert other.get("/api/auth/session").json() == {"user": None}
    assert client.get("/api/auth/session").json() == {"user": None}
    assert confirm(browser(), token).status_code == 400


@pytest.mark.parametrize("state", ["PENDING", "SUSPENDED", "ARCHIVED", "ANONYMIZED"])
def test_reset_requests_for_forbidden_or_unknown_accounts_are_generic(
    member, state, django_capture_on_commit_callbacks
):
    User.objects.filter(pk=member.pk).update(state=state)
    client = browser()
    with django_capture_on_commit_callbacks(execute=True):
        known = post(client, "/api/auth/password-reset", {"email": member.email})
        unknown = post(client, "/api/auth/password-reset", {"email": "missing@iut.example"})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert not PasswordReset.objects.exists() and not mail.outbox


@pytest.mark.parametrize("condition", ["unusable", "unapproved", "unverified", "disabled"])
def test_reset_never_bypasses_activation_or_usable_credentials(
    member, condition, django_capture_on_commit_callbacks
):
    if condition == "unusable":
        member.set_unusable_password()
        member.save()
    if condition in {"unapproved", "unverified"}:
        member.state = "PENDING"
        if condition == "unapproved":
            member.approval_required = True
        else:
            member.email_verified_at = None
        member.save()
    with override_settings(PASSWORD_RESET_ENABLED=condition != "disabled"):
        with django_capture_on_commit_callbacks(execute=True):
            assert (
                post(browser(), "/api/auth/password-reset", {"email": member.email}).status_code
                == 202
            )
    assert not PasswordReset.objects.exists() and not mail.outbox


@pytest.mark.parametrize("state", ["INACTIVE", "GRADUATED", "ALUMNI"])
def test_historical_accounts_can_reset_even_without_current_signup_domain(
    member, state, django_capture_on_commit_callbacks
):
    User.objects.filter(pk=member.pk).update(state=state)
    client = browser()
    with override_settings(INSTITUTIONAL_EMAIL_DOMAINS=()):
        token = issue(client, member, django_capture_on_commit_callbacks)
        assert confirm(client, token).status_code == 200
    member.refresh_from_db()
    assert member.state == state
    assert (
        post(client, "/api/auth/login", {"email": member.email, "password": NEW}).status_code == 200
    )


@pytest.mark.parametrize("change", ["expired", "email", "password", "closed", "disabled"])
def test_old_or_changed_account_tokens_fail(member, change, django_capture_on_commit_callbacks):
    client = browser()
    token = issue(client, member, django_capture_on_commit_callbacks)
    if change == "expired":
        PasswordReset.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    elif change == "email":
        member.email = "changed@iut.example"
        member.save()
    elif change == "password":
        member.set_password("different-synthetic-password")
        member.save()
    elif change == "closed":
        member.state = "SUSPENDED"
        member.save()
    with override_settings(PASSWORD_RESET_ENABLED=change != "disabled"):
        assert confirm(client, token).status_code == 400
    member.refresh_from_db()
    assert not member.check_password(NEW)


def test_reissue_replaces_link_and_never_exposes_token(member, django_capture_on_commit_callbacks):
    client = browser()
    first = issue(client, member, django_capture_on_commit_callbacks)
    second = issue(client, member, django_capture_on_commit_callbacks)
    assert first != second and PasswordReset.objects.count() == 1
    assert confirm(client, first).status_code == 400
    assert confirm(client, second).status_code == 200


@pytest.mark.parametrize(
    "password", ["short", "123456789012345", "administrator", OLD, "member@iut.example"]
)
def test_password_policy_failure_preserves_session_and_challenge(
    member, password, django_capture_on_commit_callbacks
):
    client = login(member)
    token = issue(browser(), member, django_capture_on_commit_callbacks)
    key = client.cookies["sessionid"].value
    assert confirm(browser(), token, password).status_code == 400
    assert Session.objects.filter(pk=key).exists()
    assert PasswordReset.objects.get().consumed_at is None
    member.refresh_from_db()
    assert member.check_password(OLD)


@pytest.mark.parametrize(
    "route,data",
    [
        ("/api/auth/password-reset", {"email": "member@iut.example"}),
        ("/api/auth/password-reset/confirm", {"token": "a" * 43, "password": NEW}),
    ],
)
def test_anonymous_csrf_foreign_origin_and_no_get_mutation(route, data):
    client = browser()
    assert client.post(route, data, content_type="application/json").status_code == 403
    assert post(client, route, data, HTTP_ORIGIN="https://evil.example").status_code == 403
    assert client.get(route).status_code == 405


def test_change_and_lifecycle_require_authentication_and_csrf(member, admin):
    assert (
        post(
            browser(), "/api/auth/password-change", {"current_password": OLD, "password": NEW}
        ).status_code
        == 403
    )
    client = login(member)
    payload = {"command": "suspend", "expected_state": "ACTIVE", "reason": "administrative_change"}
    assert post(client, f"/api/users/{admin.pk}/lifecycle", payload).status_code == 403
    assert post(client, f"/api/users/{uuid4()}/lifecycle", payload).status_code == 403
    admin_client = login(admin)
    assert (
        admin_client.post(
            f"/api/users/{member.pk}/lifecycle", payload, content_type="application/json"
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/password-change",
            {"current_password": OLD, "password": NEW},
            content_type="application/json",
        ).status_code
        == 403
    )


def test_lifecycle_http_permission_conflict_validation_and_not_found(member, admin):
    client = login(admin)
    path = f"/api/users/{member.pk}/lifecycle"
    payload = {"command": "suspend", "expected_state": "PENDING", "reason": "administrative_change"}
    assert post(client, path, payload).status_code == 409
    payload["expected_state"] = "ACTIVE"
    assert post(client, path, {**payload, "roles": ["ADMINISTRATOR"]}).status_code == 400
    assert post(client, path, {**payload, "command": "anonymize"}).status_code == 400
    assert post(client, f"/api/users/{uuid4()}/lifecycle", payload).status_code == 404
    result = post(client, path, payload)
    assert result.status_code == 200 and result.json() == {
        "id": str(member.pk),
        "state": "SUSPENDED",
    }


@pytest.mark.parametrize("source", ["ACTIVE", "INACTIVE", "GRADUATED", "ALUMNI", "PENDING"])
def test_restriction_restores_only_recorded_state_and_never_revives_old_sessions(
    member, admin, source, django_capture_on_commit_callbacks
):
    client = login(member)
    key = client.cookies["sessionid"].value
    token = issue(browser(), member, django_capture_on_commit_callbacks)
    member.state = source
    member.save()
    command(admin, member, "suspend")
    member.refresh_from_db()
    assert member.state_before_restriction == source
    assert not Session.objects.filter(pk=key).exists()
    command(admin, member, "archive")
    member.refresh_from_db()
    assert member.state_before_restriction == source
    command(admin, member, "restore")
    member.refresh_from_db()
    assert member.state == source and member.state_before_restriction == ""
    assert client.get("/api/auth/session").json() == {"user": None}
    assert confirm(browser(), token).status_code == 400
    assert member.role_assignments.filter(role="STUDENT").exists()


def test_pending_approval_requires_verification_and_preserves_identity(admin):
    user = User.objects.create_user("pending@iut.example", OLD)
    user.approval_required = True
    user.save()
    result = command(admin, user, "approve")
    assert result.approved_at and result.state == "PENDING" and not result.is_login_eligible
    command(admin, result, "approve")
    assert AuditLog.objects.filter(action="accounts.approval.recorded").count() == 1
    user2 = User.objects.create_user("verified@iut.example", OLD)
    user2.approval_required = True
    user2.email_verified_at = timezone.now()
    user2.save()
    assert command(admin, user2, "approve").state == "ACTIVE"


def test_graduation_and_alumni_preserve_existing_login_history_roles(member, admin):
    client = login(member)
    key = client.cookies["sessionid"].value
    original_pk = member.pk
    joined = member.date_joined
    graduated = command(admin, member, "graduate")
    assert graduated.state == "GRADUATED" and graduated.allows_historical_access
    alumnus = command(admin, graduated, "alumni")
    assert alumnus.pk == original_pk and alumnus.date_joined == joined and alumnus.state == "ALUMNI"
    assert Session.objects.filter(pk=key).exists()
    assert client.get("/api/auth/session").json()["user"]["state"] == "ALUMNI"
    assert alumnus.role_assignments.filter(role="STUDENT").exists()


@pytest.mark.parametrize("name", ["suspend", "archive"])
def test_last_eligible_admin_cannot_be_restricted(admin, name):
    with pytest.raises(ValidationError):
        command(admin, admin, name)
    admin.refresh_from_db()
    assert admin.state == "ACTIVE"


def test_stale_admin_and_terminal_or_unrecorded_states_fail(member, admin):
    UserRole.objects.filter(user=admin, role="ADMINISTRATOR").delete()
    with pytest.raises(PermissionDenied):
        command(admin, member, "suspend")
    UserRole.objects.create(user=admin, role="ADMINISTRATOR")
    for state in ["ANONYMIZED", "SUSPENDED", "ARCHIVED"]:
        member.state = state
        member.save()
        with pytest.raises(ValidationError):
            command(admin, member, "restore")
    member.state = "ACTIVE"
    member.save()
    with pytest.raises(StateConflict):
        transition(
            actor=admin,
            subject_id=member.pk,
            command="suspend",
            expected_state="PENDING",
            reason="administrative_change",
        )


def test_restriction_expires_pending_verification_and_resend_stays_possible(admin):
    user = User.objects.create_user("pending@iut.example", OLD)
    EmailVerification.objects.create(
        user=user,
        token_digest=token_digest("a" * 43),
        account_digest=account_digest(user),
        expires_at=timezone.now() + timedelta(hours=1),
    )
    closed = command(admin, user, "suspend")
    restored = command(admin, closed, "restore")
    row = EmailVerification.objects.get(user=user)
    assert (
        restored.state == "PENDING" and row.expires_at <= timezone.now() and row.consumed_at is None
    )


def test_mail_failure_is_safe_and_recoverable(member, django_capture_on_commit_callbacks, caplog):
    with patch(
        "apps.accounts.recovery.services.send_mail", side_effect=RuntimeError("smtp-secret")
    ):
        with django_capture_on_commit_callbacks(execute=True):
            response = post(browser(), "/api/auth/password-reset", {"email": member.email})
    assert response.status_code == 202 and "smtp-secret" not in caplog.text
    assert PasswordReset.objects.exists()
    issue(browser(), member, django_capture_on_commit_callbacks)
    assert len(mail.outbox) == 1


def test_reset_audit_failure_rolls_back_password_token_and_revocation(
    member, django_capture_on_commit_callbacks
):
    client = login(member)
    key = client.cookies["sessionid"].value
    token = issue(browser(), member, django_capture_on_commit_callbacks)
    with patch("apps.accounts.recovery.services.record_event", side_effect=RuntimeError("audit")):
        with pytest.raises(RuntimeError):
            confirm(browser(), token)
    member.refresh_from_db()
    assert member.check_password(OLD)
    assert (
        PasswordReset.objects.get().consumed_at is None and Session.objects.filter(pk=key).exists()
    )


def test_lifecycle_audit_failure_rolls_back_state_and_sessions(member, admin):
    key = login(member).cookies["sessionid"].value
    with patch("apps.accounts.recovery.lifecycle.record_event", side_effect=RuntimeError("audit")):
        with pytest.raises(RuntimeError):
            command(admin, member, "archive")
    member.refresh_from_db()
    assert member.state == "ACTIVE"
    assert Session.objects.filter(pk=key).exists()


def test_shared_fixed_limits_and_forwarded_header_cannot_bypass():
    client = browser()
    with override_settings(RECOVERY_IDENTITY_LIMIT=2, RECOVERY_IP_LIMIT=3):
        for email in ["unknown@iut.example", " UNKNOWN@IUT.EXAMPLE "]:
            assert post(client, "/api/auth/password-reset", {"email": email}).status_code == 202
        limited = post(client, "/api/auth/password-reset", {"email": "unknown@iut.example"})
        assert limited.status_code == 429 and int(limited["Retry-After"]) > 0
        deadlines = list(LoginAttempt.objects.values_list("resets_at", flat=True))
        assert (
            post(client, "/api/auth/password-reset", {"email": "unknown@iut.example"}).status_code
            == 429
        )
        assert list(LoginAttempt.objects.values_list("resets_at", flat=True)) == deadlines
        assert (
            post(client, "/api/auth/password-reset", {"email": "other@iut.example"}).status_code
            == 202
        )
        count = LoginAttempt.objects.count()
        assert (
            post(
                client,
                "/api/auth/password-reset",
                {"email": "more@iut.example"},
                HTTP_X_FORWARDED_FOR="198.51.100.8",
            ).status_code
            == 429
        )
        assert LoginAttempt.objects.count() == count
        LoginAttempt.objects.update(resets_at=timezone.now() - timedelta(seconds=1))
        assert (
            post(client, "/api/auth/password-reset", {"email": "unknown@iut.example"}).status_code
            == 202
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_reset_consumes_once(member):
    token = "a" * 43
    PasswordReset.objects.create(
        user=member,
        token_digest=token_digest(token),
        account_digest=account_digest(member),
        expires_at=timezone.now() + timedelta(hours=1),
    )
    barrier = Barrier(2)

    def attempt():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return confirm_reset(token, NEW)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == [False, True]


@pytest.mark.django_db(transaction=True)
def test_concurrent_last_admin_restriction_preserves_one(admin):
    other = eligible("other-admin@iut.example")
    UserRole.objects.create(user=other, role="ADMINISTRATOR")
    barrier = Barrier(2)

    def attempt(user):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                command(user, user, "suspend")
                return True
            except ValidationError, PermissionDenied:
                return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [admin, other]))
    assert sorted(results) == [False, True]
    assert (
        User.objects.eligible_for_authentication()
        .filter(role_assignments__role="ADMINISTRATOR")
        .count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_parallel_recovery_budget_is_not_exceeded():
    barrier = Barrier(4)

    def attempt():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return consume_attempt("member@iut.example", "127.0.0.1")
        finally:
            close_old_connections()

    with override_settings(RECOVERY_IDENTITY_LIMIT=2):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: attempt(), range(4)))
    assert results.count(None) == 2


@pytest.mark.parametrize(
    "route,data",
    [
        ("/api/auth/password-reset", {"email": "member@iut.example", "state": "ACTIVE"}),
        (
            "/api/auth/password-reset/confirm",
            {"token": "a" * 43, "password": NEW, "roles": ["ADMINISTRATOR"]},
        ),
        (
            "/api/auth/password-change",
            {"current_password": OLD, "password": NEW, "email": "changed@iut.example"},
        ),
        ("/api/auth/password-reset/confirm", {"token": "a" * 43, "password": "x" * 9000}),
    ],
)
def test_recovery_rejects_extra_fields_and_oversized_bodies(member, route, data):
    client = login(member)
    assert post(client, route, data).status_code == 400
    member.refresh_from_db()
    assert member.email == "member@iut.example" and member.check_password(OLD)
    assert not PasswordReset.objects.exists()


def test_unapproved_legacy_restore_cannot_bypass_eligibility(member, admin):
    member.state = "SUSPENDED"
    member.state_before_restriction = "ACTIVE"
    member.approval_required = True
    member.approved_at = None
    member.save()
    with pytest.raises(ValidationError):
        command(admin, member, "restore")
    member.refresh_from_db()
    assert member.state == "SUSPENDED"


@pytest.mark.django_db(transaction=True)
def test_concurrent_verification_and_approval_activate_once(admin):
    from apps.accounts.registration.services import verify

    user = User.objects.create_user("pending@iut.example", OLD)
    user.approval_required = True
    user.save()
    token = "a" * 43
    EmailVerification.objects.create(
        user=user,
        token_digest=token_digest(token),
        account_digest=account_digest(user),
        expires_at=timezone.now() + timedelta(hours=1),
    )
    barrier = Barrier(2)

    def attempt(kind):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            if kind == "verify":
                return verify(token)
            return command(admin, user, "approve") is not None
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["verify", "approve"]))
    assert results == [True, True]
    user.refresh_from_db()
    assert user.state == "ACTIVE" and user.is_login_eligible
    assert (
        AuditLog.objects.filter(action="accounts.state.changed", target_id=str(user.pk)).count()
        == 1
    )
