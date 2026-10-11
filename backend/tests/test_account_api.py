from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections
from django.test import Client, override_settings
from django.utils import timezone

from apps.access.models import PrivilegeLock
from apps.accounts.api.services import accept_invitation, create_account
from apps.accounts.models import Invitation, User, UserRole
from apps.accounts.recovery.lifecycle import transition
from apps.accounts.registration.services import account_digest, token_digest
from apps.audit.models import AuditLog

pytestmark = pytest.mark.django_db
PASSWORD = "synthetic-account-password-123"
NEW = {
    "email": "invited@iut.example",
    "display_name": "Invited Member",
    "student_id": "001x",
    "roles": ["TEACHER"],
    "approval_required": True,
}


@pytest.fixture(autouse=True)
def configure():
    PrivilegeLock.objects.get_or_create(pk=1)
    with override_settings(
        INVITATIONS_ENABLED=True, PUBLIC_APP_ORIGIN="https://archive.example.invalid"
    ):
        yield


def eligible(email, role="STUDENT"):
    user = User.objects.create_user(email, PASSWORD, display_name="Test Member")
    user.state = "ACTIVE"
    user.email_verified_at = timezone.now()
    user.save()
    if role != "STUDENT":
        UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def admin():
    return eligible("admin@iut.example", "ADMINISTRATOR")


@pytest.fixture
def member():
    return eligible("member@iut.example")


def browser():
    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/session")
    return client


def post(client, path, data, method="post", **extra):
    return getattr(client, method)(
        path,
        data,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        **extra,
    )


def login(user):
    client = browser()
    assert (
        post(client, "/api/auth/login", {"email": user.email, "password": PASSWORD}).status_code
        == 200
    )
    return client


def invite(admin, callbacks, **changes):
    with callbacks(execute=True):
        response = post(login(admin), "/api/users", {**NEW, **changes})
    assert response.status_code == 201, response.content
    return User.objects.get(pk=response.json()["id"]), mail.outbox[-1].body.split("#token=")[
        1
    ].split()[0]


def accept(client, token, password=PASSWORD):
    return post(client, "/api/auth/invitation/accept", {"token": token, "password": password})


def test_admin_creation_invitation_approval_and_login(admin, django_capture_on_commit_callbacks):
    user, token = invite(admin, django_capture_on_commit_callbacks)
    assert user.state == "PENDING" and not user.has_usable_password()
    assert user.student_id == "001X" and list(
        user.role_assignments.values_list("role", flat=True)
    ) == ["TEACHER"]
    assert Invitation.objects.get(user=user).token_digest == token_digest(token)
    assert "https://archive.example.invalid/accept-invitation#token=" in mail.outbox[-1].body
    client = browser()
    assert accept(client, token).status_code == 200
    user.refresh_from_db()
    assert user.state == "PENDING" and user.email_verified_at and user.check_password(PASSWORD)
    assert (
        post(client, "/api/auth/login", {"email": user.email, "password": PASSWORD}).status_code
        == 401
    )
    transition(
        actor=admin,
        subject_id=user.pk,
        command="approve",
        expected_state="PENDING",
        reason="administrative_change",
    )
    assert (
        post(client, "/api/auth/login", {"email": user.email, "password": PASSWORD}).status_code
        == 200
    )
    assert accept(client, token).status_code == 400
    serialized = str(list(AuditLog.objects.values()))
    assert all(value not in serialized for value in [PASSWORD, token, user.email, user.password])


def test_creation_without_extra_approval_activates_only_after_acceptance(
    admin, django_capture_on_commit_callbacks
):
    user, token = invite(
        admin,
        django_capture_on_commit_callbacks,
        approval_required=False,
        roles=["STUDENT", "ADMINISTRATOR"],
    )
    assert not user.is_login_eligible
    client = browser()
    assert accept(client, token).status_code == 200
    user.refresh_from_db()
    assert user.state == "ACTIVE" and user.is_login_eligible
    assert client.get("/api/auth/session").json() == {"user": None}
    assert set(user.role_assignments.values_list("role", flat=True)) == {"STUDENT", "ADMINISTRATOR"}


@pytest.mark.parametrize("role", ["STUDENT", "TEACHER"])
def test_non_admin_cannot_enumerate_or_mutate_accounts(role, admin):
    client = login(eligible(f"{role.lower()}@iut.example", role))
    for path in [
        "/api/users",
        f"/api/users/{admin.pk}",
        f"/api/users/{uuid4()}",
        "/api/users?q=admin",
    ]:
        response = client.get(path)
        assert response.status_code == 403 and "admin@iut.example" not in response.content.decode()
    for path, data in [
        ("/api/users", NEW),
        (
            f"/api/users/{admin.pk}/roles",
            {
                "roles": ["STUDENT"],
                "expected_roles": ["STUDENT", "ADMINISTRATOR"],
                "reason": "administrative_change",
            },
        ),
        (f"/api/users/{admin.pk}/invitation", {}),
    ]:
        assert post(client, path, data).status_code == 403
    assert not Invitation.objects.exists()


def test_anonymous_and_stale_admin_deny_before_lookup(admin):
    assert browser().get("/api/users").status_code == 403
    client = login(admin)
    UserRole.objects.filter(user=admin, role="ADMINISTRATOR").delete()
    assert client.get("/api/users").status_code == 403
    assert post(client, "/api/users", NEW).status_code == 403
    with pytest.raises(PermissionDenied):
        create_account(actor=admin, **NEW)


def test_list_filters_pagination_and_safe_projection(admin, member):
    teacher = eligible("teacher@iut.example", "TEACHER")
    client = login(admin)
    page = client.get("/api/users?page_size=1").json()
    assert (
        page["count"] == 3
        and len(page["results"]) == 1
        and page["next"]
        and page["previous"] is None
    )
    assert "password" not in page["results"][0] and "token_digest" not in page["results"][0]
    teachers = client.get("/api/users?role=TEACHER").json()["results"]
    assert [x["id"] for x in teachers] == [str(teacher.pk)]
    assert client.get("/api/users?state=PENDING").json()["results"] == []
    assert (
        client.get("/api/users?q=member").json()["count"] == 3
    )  # all synthetic names are Test Member
    assert client.get("/api/users?q=teacher%40").json()["count"] == 1
    assert client.get(f"/api/users/{uuid4()}").status_code == 404
    assert client.get("/api/users")["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "query",
    [
        "role=ADMIN",
        "state=DELETED",
        "q=" + ("a" * 101),
        "page=0",
        "page=-1",
        "page_size=NaN",
        "page=1&page=2",
        "unknown=x",
    ],
)
def test_invalid_filters_are_bounded(admin, query):
    assert login(admin).get("/api/users?" + query).status_code == 400


@pytest.mark.parametrize(
    "extra",
    [
        {"state": "ACTIVE"},
        {"password": PASSWORD},
        {"email_verified_at": "now"},
        {"approved_at": "now"},
        {"id": str(uuid4())},
    ],
)
def test_admin_creation_rejects_unsafe_fields(admin, extra):
    assert post(login(admin), "/api/users", {**NEW, **extra}).status_code == 400
    assert not Invitation.objects.exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"roles": ["ROOT"]},
        {"roles": []},
        {"roles": ["TEACHER", "TEACHER"]},
        {"approval_required": "false"},
        {"display_name": 12},
        {"email": "bad"},
    ],
)
def test_admin_creation_field_validation(admin, changes):
    response = post(login(admin), "/api/users", {**NEW, **changes})
    assert response.status_code == 400
    assert not Invitation.objects.exists()


def test_duplicate_identity_is_conflict_and_does_not_mutate(
    admin, member, django_capture_on_commit_callbacks
):
    original = member.password
    with django_capture_on_commit_callbacks(execute=True):
        response = post(login(admin), "/api/users", {**NEW, "email": " MEMBER@IUT.EXAMPLE "})
    assert response.status_code == 409
    member.refresh_from_db()
    assert member.password == original and not mail.outbox


def test_profile_only_updates_own_display_name(member, admin):
    client = login(member)
    before = User.objects.values().get(pk=member.pk)
    response = post(client, "/api/profile", {"display_name": "Updated Name"}, method="patch")
    assert response.status_code == 200 and response.json()["display_name"] == "Updated Name"
    assert User.objects.values().get(pk=member.pk) == before
    assert User.objects.get(pk=admin.pk).profile.display_name == "Test Member"
    assert AuditLog.objects.filter(action="accounts.profile.changed", actor=member).count() == 1
    assert "Updated Name" not in str(list(AuditLog.objects.values()))


@pytest.mark.parametrize(
    "extra",
    [
        {"roles": ["ADMINISTRATOR"]},
        {"student_id": "OTHER"},
        {"state": "ACTIVE"},
        {"email": "other@iut.example"},
        {"id": str(uuid4())},
        {"user_id": str(uuid4())},
        {"approved_at": "now"},
    ],
)
def test_profile_mass_assignment_is_denied(member, extra):
    client = login(member)
    assert (
        post(
            client, "/api/profile", {"display_name": "Changed", **extra}, method="patch"
        ).status_code
        == 400
    )
    assert User.objects.get(pk=member.pk).profile.display_name == "Test Member"


def test_profile_closed_and_anonymous_deny(member):
    assert browser().get("/api/profile").status_code == 403
    client = login(member)
    User.objects.filter(pk=member.pk).update(state="SUSPENDED")
    assert client.get("/api/profile").status_code == 403
    assert post(client, "/api/profile", {"display_name": "No"}, method="patch").status_code == 403


def test_role_service_last_admin_and_stale_review(admin, member):
    client = login(admin)
    payload = {
        "roles": ["TEACHER"],
        "expected_roles": ["STUDENT"],
        "reason": "administrative_change",
    }
    assert post(client, f"/api/users/{member.pk}/roles", payload).status_code == 200
    assert post(client, f"/api/users/{member.pk}/roles", payload).status_code == 409
    assert (
        post(
            client,
            f"/api/users/{admin.pk}/roles",
            {
                "roles": ["STUDENT"],
                "expected_roles": ["ADMINISTRATOR", "STUDENT"],
                "reason": "administrative_change",
            },
        ).status_code
        == 400
    )


@pytest.mark.parametrize("change", ["expired", "email", "password", "closed", "disabled"])
def test_invalid_invitation_never_activates(admin, change, django_capture_on_commit_callbacks):
    user, token = invite(admin, django_capture_on_commit_callbacks, approval_required=False)
    if change == "expired":
        Invitation.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    elif change == "email":
        user.email = "changed@iut.example"
        user.save()
    elif change == "password":
        user.set_password("another-synthetic-password")
        user.save()
    elif change == "closed":
        user.state = "SUSPENDED"
        user.save()
    with override_settings(INVITATIONS_ENABLED=change != "disabled"):
        assert accept(browser(), token).status_code == 400
    user.refresh_from_db()
    assert user.email_verified_at is None


def test_invitation_resend_rotates_after_cooldown_and_restriction_expires(
    admin, django_capture_on_commit_callbacks
):
    user, token = invite(admin, django_capture_on_commit_callbacks)
    client = login(admin)
    path = f"/api/users/{user.pk}/invitation"
    assert post(client, path, {}).status_code == 429
    Invitation.objects.update(sent_at=timezone.now() - timedelta(hours=1))
    with django_capture_on_commit_callbacks(execute=True):
        assert post(client, path, {}).status_code == 202
    new = mail.outbox[-1].body.split("#token=")[1].split()[0]
    assert new != token and accept(browser(), token).status_code == 400
    transition(
        actor=admin,
        subject_id=user.pk,
        command="suspend",
        expected_state="PENDING",
        reason="administrative_change",
    )
    transition(
        actor=admin,
        subject_id=user.pk,
        command="restore",
        expected_state="SUSPENDED",
        reason="administrative_change",
    )
    assert accept(browser(), new).status_code == 400


def test_csrf_on_all_writes_and_no_get_acceptance(admin, member):
    client = login(admin)
    for path, data in [
        ("/api/users", NEW),
        (f"/api/users/{member.pk}/roles", {}),
        (f"/api/users/{member.pk}/invitation", {}),
        ("/api/auth/invitation/accept", {"token": "a" * 43, "password": PASSWORD}),
    ]:
        assert client.post(path, data, content_type="application/json").status_code == 403
        assert post(client, path, data, HTTP_ORIGIN="https://evil.example").status_code == 403
    assert (
        client.patch(
            "/api/profile", {"display_name": "Changed"}, content_type="application/json"
        ).status_code
        == 403
    )
    assert client.get("/api/auth/invitation/accept").status_code == 405


def test_invitation_password_validation_preserves_challenge(
    admin, django_capture_on_commit_callbacks
):
    user, token = invite(admin, django_capture_on_commit_callbacks)
    assert accept(browser(), token, "short").status_code == 400
    user.refresh_from_db()
    assert not user.has_usable_password() and Invitation.objects.get().consumed_at is None


def test_failure_rolls_back_account_and_delivery(admin, django_capture_on_commit_callbacks):
    client = login(admin)
    with django_capture_on_commit_callbacks(execute=True):
        with patch("apps.accounts.api.services.record_event", side_effect=RuntimeError("audit")):
            with pytest.raises(RuntimeError):
                post(client, "/api/users", NEW)
    assert not User.objects.filter(email=NEW["email"]).exists() and not mail.outbox


def test_disabled_delivery_rolls_back_and_smtp_failure_is_safe(
    admin, django_capture_on_commit_callbacks, caplog
):
    client = login(admin)
    with override_settings(INVITATIONS_ENABLED=False):
        assert post(client, "/api/users", NEW).status_code == 400
    assert not User.objects.filter(email=NEW["email"]).exists()
    with patch("apps.accounts.api.services.send_mail", side_effect=RuntimeError("smtp-secret")):
        with django_capture_on_commit_callbacks(execute=True):
            assert post(client, "/api/users", NEW).status_code == 201
    assert "smtp-secret" not in caplog.text
    assert Invitation.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_invitation_concurrent_consumption_once(admin):
    user = User.objects.create_user("invite@iut.example")
    token = "a" * 43
    Invitation.objects.create(
        user=user,
        token_digest=token_digest(token),
        account_digest=account_digest(user),
        expires_at=timezone.now() + timedelta(hours=1),
        sent_at=timezone.now(),
    )
    barrier = Barrier(2)

    def attempt():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return accept_invitation(token=token, password=PASSWORD)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == [False, True]
