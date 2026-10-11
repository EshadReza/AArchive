import json
import uuid
from base64 import b64encode
from urllib.parse import urlsplit

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.enums import AccountState, PlatformRole
from apps.accounts.models import User, UserRole
from apps.audit.api import AuditSerializer
from apps.audit.models import AppendOnlyError, AuditLog
from apps.audit.policy import MAX_PAYLOAD_BYTES
from apps.audit.services import AuditContext, record_event

pytestmark = pytest.mark.django_db


@pytest.fixture
def student():
    user = User.objects.create_user("audit-student@iut.example")
    User.objects.filter(pk=user.pk).update(
        state=AccountState.ACTIVE, email_verified_at=timezone.now()
    )
    user.refresh_from_db()
    return user


@pytest.fixture
def administrator(student):
    UserRole.objects.create(user=student, role=PlatformRole.ADMINISTRATOR)
    return student


def append(user, **kwargs):
    return record_event(
        **{
            "action": "accounts.state.changed",
            "actor": user,
            "target_id": user.pk,
            "previous_value": {"state": "ACTIVE"},
            "new_value": {"state": "ALUMNI"},
            "reason": "graduation",
            **kwargs,
        }
    )


def authenticated(user):
    client = APIClient()
    client.force_authenticate(user=user)  # Session transport is S008, not this test's subject.
    return client


@pytest.mark.django_db(transaction=True)
def test_mutation_and_audit_commit_or_rollback_together(student):
    with transaction.atomic():
        User.objects.filter(pk=student.pk).update(state=AccountState.GRADUATED)
        entry = append(student, new_value={"state": "GRADUATED"})
    assert AuditLog.objects.filter(pk=entry.pk).exists()
    student.refresh_from_db()
    assert student.state == AccountState.GRADUATED
    with pytest.raises(RuntimeError), transaction.atomic():
        User.objects.filter(pk=student.pk).update(state=AccountState.SUSPENDED)
        append(student, new_value={"state": "SUSPENDED"})
        raise RuntimeError("synthetic business failure")
    student.refresh_from_db()
    assert student.state == AccountState.GRADUATED
    assert AuditLog.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_audit_validation_failure_rolls_back_business_mutation(student):
    with pytest.raises(ValidationError), transaction.atomic():
        User.objects.filter(pk=student.pk).update(state=AccountState.SUSPENDED)
        append(student, new_value={"state": "INVALID"})
    student.refresh_from_db()
    assert student.state == AccountState.ACTIVE
    assert not AuditLog.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_autocommit_is_rejected(student):
    with pytest.raises(transaction.TransactionManagementError):
        append(student)
    assert not AuditLog.objects.exists()


def test_safe_projection_drops_credentials_nested_data_and_unknown_key_names(student):
    secret = "synthetic-secret-must-never-survive"
    entry = append(
        student,
        new_value={
            "state": "ALUMNI",
            "password": secret,
            "accessToken": secret,
            "nested": {"Authorization": secret},
            secret: "also hidden",
        },
    )
    entry.refresh_from_db()
    assert entry.new_value == {"state": "ALUMNI"}
    assert secret not in json.dumps(AuditSerializer(entry).data)
    assert len(json.dumps(entry.new_value).encode()) <= MAX_PAYLOAD_BYTES
    # Even a manually seeded legacy payload is projected again when serialized.
    entry.previous_value = {"state": "ACTIVE", "password_hash": secret}
    assert secret not in json.dumps(AuditSerializer(entry).data)
    entry.new_value = {"state": {"token": secret}}
    assert AuditSerializer(entry).data["new_value"] is None


@pytest.mark.parametrize(
    "value",
    ["secret" * 10000, ["ACTIVE"], {"state": "secret" * 10000}, {"state": {"token": "secret"}}],
)
def test_malformed_or_oversized_known_values_are_rejected(student, value):
    with pytest.raises(ValidationError):
        append(student, new_value=value)
    assert not AuditLog.objects.exists()


def test_large_unknown_fields_are_omitted_and_role_lists_are_bounded(student):
    entry = append(student, new_value={"state": "ALUMNI", "untrusted": "x" * 100000})
    assert entry.new_value == {"state": "ALUMNI"}
    roles = record_event(
        action="accounts.roles.changed",
        actor=student,
        target_id=student.pk,
        new_value={"roles": ["STUDENT", "TEACHER"], "source_role": "admin"},
    )
    assert roles.new_value == {"roles": ["STUDENT", "TEACHER"]}
    for value in [["STUDENT"] * 100, ["SOURCE_ADMIN"], [{"token": "secret"}]]:
        with pytest.raises(ValidationError):
            record_event(
                action="accounts.roles.changed",
                actor=student,
                target_id=student.pk,
                new_value={"roles": value},
            )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"action": "unknown.action"},
        {"target_id": "not-a-uuid"},
        {"reason": "password=secret"},
        {"context": {"cookie": "secret"}},
        {"context": AuditContext(ip="not-an-ip")},
        {"context": AuditContext(channel="raw user agent")},
        {"system_actor": "scheduler"},
        {"actor": None},
    ],
)
def test_invalid_context_action_or_actor_is_rejected(student, kwargs):
    with pytest.raises(ValidationError):
        append(student, **kwargs)
    assert not AuditLog.objects.exists()


def test_metadata_is_explicit_and_system_events_have_no_fabricated_user(student):
    correlation_id = uuid.uuid4()
    entry = append(
        student, context=AuditContext(request_id=correlation_id, ip="192.0.2.1", channel="browser")
    )
    assert entry.request_id == correlation_id
    assert entry.ip == "192.0.2.1"
    system_entry = record_event(
        action="system.maintenance.completed",
        target_id="system",
        system_actor="maintenance",
        new_value={"operation": "integrity_check"},
    )
    assert system_entry.actor_id is None
    assert system_entry.system_actor == "maintenance"
    assert system_entry.ip is None


def test_anonymized_actor_reference_and_target_history_are_retained(student):
    entry = append(student)
    User.objects.filter(pk=student.pk).update(state=AccountState.ANONYMIZED)
    entry.refresh_from_db()
    assert entry.actor_id == student.pk
    assert entry.target_id == str(student.pk)
    # Audit itself protects the user even if other account references are removed.
    student.role_assignments.all().delete()
    student.profile.delete()
    with pytest.raises(ProtectedError):
        student.delete()
    assert AuditLog.objects.filter(pk=entry.pk).exists()


@pytest.mark.parametrize(
    "operation", ["save", "delete", "update", "query_delete", "bulk_update", "bulk_create"]
)
def test_orm_mutation_paths_are_rejected(student, operation):
    entry = append(student)
    entry.reason = "user_request"
    actions = {
        "save": lambda: entry.save(),
        "delete": lambda: entry.delete(),
        "update": lambda: AuditLog.objects.filter(pk=entry.pk).update(reason="user_request"),
        "query_delete": lambda: AuditLog.objects.filter(pk=entry.pk).delete(),
        "bulk_update": lambda: AuditLog.objects.bulk_update([entry], ["reason"]),
        "bulk_create": lambda: AuditLog.objects.bulk_create([entry]),
    }
    with pytest.raises(AppendOnlyError):
        actions[operation]()
    entry.refresh_from_db()
    assert entry.reason == "graduation"


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE audit_auditlog SET reason = 'scheduled' WHERE id = %s",
        "DELETE FROM audit_auditlog WHERE id = %s",
    ],
)
def test_database_trigger_rejects_bypassed_orm_mutations(student, sql):
    entry = append(student)
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(sql, [entry.pk])
    assert AuditLog.objects.filter(pk=entry.pk).exists()


def test_anonymous_and_source_headers_cannot_read_audit(client, student):
    entry = append(student)
    for path in ["/api/audit", f"/api/audit/{entry.pk}", "/api/audit/999999"]:
        response = client.get(
            path, HTTP_X_ROLE="ADMINISTRATOR", HTTP_AUTHORIZATION="Bearer synthetic"
        )
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"
        assert response["Cache-Control"] == "no-store"


def test_admin_response_never_contains_unreviewed_fields(administrator):
    secret = "synthetic-credential-value"
    entry = append(
        administrator,
        new_value={"state": "ALUMNI", "password": secret, "restricted": {"credentials": secret}},
    )
    client = authenticated(administrator)
    for path in ["/api/audit", f"/api/audit/{entry.pk}"]:
        response = client.get(path)
        assert response.status_code == 200
        assert secret.encode() not in response.content
        assert b"password" not in response.content
        assert b"restricted" not in response.content


@pytest.mark.parametrize("with_actor", [False, True])
def test_database_requires_exactly_one_actor(student, with_actor):
    with (
        pytest.raises(IntegrityError) as error,
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "INSERT INTO audit_auditlog (actor_id, system_actor, action, target_type, "
            "target_id, reason, channel, created_at) VALUES (%s, %s, %s, %s, %s, '', '', NOW())",
            [
                student.pk if with_actor else None,
                "scheduler" if with_actor else "",
                "accounts.state.changed",
                "accounts.user",
                str(student.pk),
            ],
        )
    assert error.value.__cause__.diag.constraint_name == "audit_exactly_one_actor"


def test_missing_reviewed_field_does_not_silently_lose_change_history(student):
    with pytest.raises(ValidationError, match="Missing required audit field"):
        append(student, new_value={"misspelled_state": "ALUMNI"})


@pytest.mark.parametrize("role", [PlatformRole.STUDENT, PlatformRole.TEACHER])
def test_nonadmins_cannot_read_even_their_own_events(student, role):
    if role == PlatformRole.TEACHER:
        UserRole.objects.create(user=student, role=role)
    entry = append(student)
    client = authenticated(student)
    for path in ["/api/audit", f"/api/audit/{entry.pk}", "/api/audit/999999"]:
        assert client.get(path).status_code == 403


@pytest.mark.parametrize("state", ["PENDING", "SUSPENDED", "ARCHIVED", "ANONYMIZED"])
def test_closed_admin_state_is_checked_from_database(administrator, state):
    append(administrator)
    client = authenticated(administrator)
    User.objects.filter(pk=administrator.pk).update(state=state)
    assert client.get("/api/audit").status_code == 403


def test_role_revocation_invalidates_stale_authenticated_admin(administrator):
    client = authenticated(administrator)
    assert client.get("/api/audit").status_code == 200
    administrator.role_assignments.filter(role=PlatformRole.ADMINISTRATOR).delete()
    assert client.get("/api/audit").status_code == 403


def test_admin_detail_pagination_and_new_inserts(administrator):
    entries = [append(administrator) for _ in range(4)]
    client = authenticated(administrator)
    first = client.get("/api/audit?page_size=2")
    assert first.status_code == 200
    assert first["Cache-Control"] == "no-store"
    assert [item["id"] for item in first.json()["results"]] == [entries[3].pk, entries[2].pk]
    assert first.json()["previous"] is None
    append(administrator)
    next_url = urlsplit(first.json()["next"])
    second = client.get(f"{next_url.path}?{next_url.query}")
    assert [item["id"] for item in second.json()["results"]] == [entries[1].pk, entries[0].pk]
    assert second.json()["next"] is None
    detail = client.get(f"/api/audit/{entries[0].pk}")
    assert detail.status_code == 200
    assert detail.json()["actor_id"] == str(administrator.pk)
    assert "email" not in detail.json()
    assert client.get("/api/audit/999999").status_code == 404
    assert client.get("/api/audit?cursor=invalid!!").status_code == 404
    assert client.head("/api/audit").content == b""


def test_page_size_is_capped(administrator):
    for _ in range(102):
        append(administrator)
    response = authenticated(administrator).get("/api/audit?page_size=999999")
    assert len(response.json()["results"]) == 100
    assert response.json()["next"] is not None


@pytest.mark.parametrize("position", ["secret-string", "-1", "0", "9" * 100, "١٢٣"])
def test_decodable_but_invalid_cursor_positions_are_safe_errors(administrator, position):
    cursor = b64encode(f"p={position}".encode()).decode()
    response = authenticated(administrator).get("/api/audit", {"cursor": cursor})
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert position not in response.json()["message"]


def test_oversized_cursor_is_rejected(administrator):
    assert authenticated(administrator).get("/api/audit", {"cursor": "x" * 1025}).status_code == 404


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_admin_cannot_write_through_list_or_detail_api(administrator, method):
    entry = append(administrator)
    client = authenticated(administrator)
    for path in ["/api/audit", f"/api/audit/{entry.pk}"]:
        response = getattr(client, method)(path, {"reason": "user_request"}, format="json")
        assert response.status_code == 405
        assert response.json()["code"] == "method_not_allowed"
    assert AuditLog.objects.count() == 1
    entry.refresh_from_db()
    assert entry.reason == "graduation"
