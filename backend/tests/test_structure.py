from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client
from django.utils import timezone

from apps.academics.models import Batch, Department, Section, Term
from apps.academics.structure import services
from apps.access.models import PrivilegeLock
from apps.accounts.models import User, UserRole
from apps.audit.models import AuditLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    PrivilegeLock.objects.get_or_create(pk=1)
    user = User.objects.create_user("structure-admin@iut.example", "synthetic-structure-password")
    user.email_verified_at = timezone.now()
    user.state = "ACTIVE"
    user.save()
    UserRole.objects.create(user=user, role="ADMINISTRATOR")
    return user


@pytest.fixture
def client(admin):
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(admin, backend="apps.accounts.auth.backend.PlatformBackend")
    browser.get("/api/auth/session")
    return browser


def write(client, path, data, method="post", csrf=True):
    return getattr(client, method)(
        path,
        data,
        content_type="application/json",
        **({"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value} if csrf else {}),
    )


def create(admin, kind="departments", label="CSE", parent=None):
    return services.create(
        actor=admin,
        kind=kind,
        label=label,
        name=f"Name {label}",
        parent_id=parent.pk if parent else None,
    )


@pytest.fixture
def tree(admin):
    department = create(admin)
    batch = create(admin, "batches", "2026", department)
    term = create(admin, "terms", "1", batch)
    return department, batch, term, Section.objects.get(batch=batch, label="ALL")


def test_create_edit_archive_and_historical_projection(client):
    department = write(client, "/api/departments", {"label": " cse ", "name": "Computer Science"})
    assert department.status_code == 201, department.content
    data = department.json()
    assert data["label"] == "CSE" and data["available"] and data["revision"] == 1
    batch = write(
        client, "/api/batches", {"label": "2026", "name": "Class 2026", "department_id": data["id"]}
    )
    assert batch.status_code == 201, batch.content
    sections = client.get(f"/api/sections?batch_id={batch.json()['id']}").json()
    assert sections["count"] == 1 and sections["results"][0]["label"] == "ALL"
    url = f"/api/departments/{data['id']}"
    edited = write(
        client, url, {"label": "CSE", "name": "Computing", "expected_revision": 1}, "patch"
    )
    assert edited.status_code == 200 and edited.json()["revision"] == 2
    assert (
        write(
            client, url, {"label": "CSE", "name": "Stale", "expected_revision": 1}, "patch"
        ).status_code
        == 409
    )
    assert write(client, f"{url}/archive", {"expected_revision": 2}).status_code == 200
    child = client.get(f"/api/batches/{batch.json()['id']}").json()
    assert child["archived"] is False and child["available"] is False
    assert client.get(url).json()["name"] == "Computing"
    assert write(client, url, {}, "delete").status_code == 405
    audit = AuditLog.objects.filter(
        action="academics.structure.changed", target_id=data["id"]
    ).first()
    assert audit.previous_value["status"] == "ACTIVE" and audit.new_value["status"] == "ARCHIVED"


@pytest.mark.parametrize("kind", ["departments", "batches", "terms", "sections"])
@pytest.mark.parametrize("role", ["STUDENT", "TEACHER", "anonymous"])
def test_non_admin_denied_before_lookup(client, admin, kind, role):
    if role == "anonymous":
        client.logout()
        client.get("/api/auth/session")
    else:
        admin.role_assignments.filter(role="ADMINISTRATOR").delete()
        if role == "TEACHER":
            UserRole.objects.create(user=admin, role=role)
    assert client.get(f"/api/{kind}").status_code == 403
    assert client.get(f"/api/{kind}/{uuid4()}").status_code == 403
    assert write(client, f"/api/{kind}", {}).status_code == 403
    assert write(client, f"/api/{kind}/{uuid4()}/archive", {}).status_code == 403
    with pytest.raises(PermissionDenied):
        create(None if role == "anonymous" else admin, kind)


def test_suspended_admin_and_csrf(client, admin, tree):
    d, _, _, _ = tree
    for path, data, method in [
        ("/api/departments", {"label": "X", "name": "X"}, "post"),
        (f"/api/departments/{d.pk}", {"label": "X", "name": "X", "expected_revision": 1}, "patch"),
        (f"/api/departments/{d.pk}/archive", {"expected_revision": 1}, "post"),
    ]:
        assert write(client, path, data, method, csrf=False).status_code == 403
    admin.state = "SUSPENDED"
    admin.save()
    assert client.get("/api/departments").status_code == 403


@pytest.mark.parametrize(
    "changes",
    [
        {"archived": True},
        {"parent_id": "self"},
        {"revision": 4},
        {"label": True},
        {"name": 10},
        {"label": " "},
        {"name": "x\ny"},
    ],
)
def test_strict_creation(client, changes):
    response = write(client, "/api/departments", {"label": "CSE", "name": "Computing", **changes})
    assert response.status_code == 400
    assert not Department.objects.exists()


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page_size=-1",
        "page=last",
        "page=1&page=2",
        "archived=yes",
        "batch_id=bad",
        "q=anything",
    ],
)
def test_invalid_filters(client, query):
    assert client.get(f"/api/terms?{query}").status_code == 400


def test_pagination_scoping_and_no_cache(client, admin, tree):
    d, b, _, _ = tree
    b2 = create(admin, "batches", "2027", d)
    create(admin, "terms", "1", b2)
    page = client.get("/api/batches?page_size=1")
    assert page.status_code == 200 and page.json()["count"] == 2 and page.json()["next"]
    assert page.headers["Cache-Control"] == "no-store"
    assert client.get(f"/api/terms?batch_id={b.pk}").json()["count"] == 1
    assert client.get(f"/api/terms/{uuid4()}").status_code == 404
    assert client.get("/api/terms?archived=true").json()["count"] == 0


@pytest.mark.parametrize("kind", ["departments", "batches", "terms", "sections"])
def test_duplicate_labels_service_and_database(admin, tree, kind):
    d, b, t, s = tree
    row = {"departments": d, "batches": b, "terms": t, "sections": s}[kind]
    parent = None if kind == "departments" else d if kind == "batches" else b
    with pytest.raises(ValidationError):
        create(admin, kind, row.label.lower(), parent)
    fields = {"label": row.label, "name": "Duplicate"}
    if kind in services.PARENTS:
        fields[services.PARENTS[kind][0]] = parent
    with pytest.raises(IntegrityError), transaction.atomic():
        type(row).objects.create(**fields)


@pytest.mark.parametrize("kind", ["batches", "terms", "sections"])
def test_reparenting_rejected_in_api_model_and_database(client, admin, tree, kind):
    d, b, t, s = tree
    other_d = create(admin, label="EEE")
    other_b = create(admin, "batches", "2027", other_d)
    row = {"batches": b, "terms": t, "sections": s}[kind]
    parent_field = services.PARENTS[kind][0]
    new_parent = other_d if kind == "batches" else other_b
    assert (
        write(
            client,
            f"/api/{kind}/{row.pk}",
            {
                "label": row.label,
                "name": row.name,
                "expected_revision": 1,
                f"{parent_field}_id": str(new_parent.pk),
            },
            "patch",
        ).status_code
        == 400
    )
    setattr(row, parent_field, new_parent)
    with pytest.raises(ValidationError):
        row.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        type(row).objects.filter(pk=row.pk).update(**{parent_field: new_parent})


def test_reserved_all_section_and_protected_parents(client, admin, tree):
    d, b, _, s = tree
    assert (
        write(client, f"/api/sections/{s.pk}/archive", {"expected_revision": 1}).status_code == 400
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Section.objects.filter(pk=s.pk).update(label="RENAMED")
    with pytest.raises(ProtectedError):
        d.delete()
    with pytest.raises(ProtectedError):
        b.delete()


@pytest.mark.parametrize("mismatch", ["department", "term", "section"])
def test_assignment_context_rejects_cross_batch(admin, tree, mismatch):
    d, b, t, s = tree
    other_d = create(admin, label="EEE")
    other_b = create(admin, "batches", "2027", other_d)
    other_t = create(admin, "terms", "1", other_b)
    ids = dict(department_id=d.pk, batch_id=b.pk, term_id=t.pk, section_id=s.pk)
    services.require_assignment_context(**ids)
    ids[f"{mismatch}_id"] = {
        "department": other_d.pk,
        "term": other_t.pk,
        "section": other_b.sections.get().pk,
    }[mismatch]
    with pytest.raises(ValidationError):
        services.require_assignment_context(**ids)


@pytest.mark.parametrize("kind", ["departments", "batches", "terms", "sections"])
def test_archive_blocks_new_assignments_and_child_edits(admin, tree, kind):
    d, b, t, _ = tree
    s = create(admin, "sections", "A", b)
    row = {"departments": d, "batches": b, "terms": t, "sections": s}[kind]
    services.change(actor=admin, kind=kind, pk=row.pk, expected_revision=1, archive=True)
    with pytest.raises(ValidationError):
        services.require_assignment_context(
            department_id=d.pk, batch_id=b.pk, term_id=t.pk, section_id=s.pk
        )
    with pytest.raises(ValidationError):
        services.change(
            actor=admin, kind=kind, pk=row.pk, expected_revision=2, label=row.label, name="Edited"
        )
    if kind in {"departments", "batches"}:
        with pytest.raises(ValidationError):
            create(admin, "terms", "2", b)
    assert Term.objects.filter(pk=t.pk).exists() and Section.objects.filter(pk=s.pk).exists()


def test_audit_failure_rolls_back_batch_and_default_section(admin, tree):
    d, _, _, _ = tree
    count = AuditLog.objects.count()
    with patch(
        "apps.academics.structure.services.record_event", side_effect=RuntimeError("failure")
    ):
        with pytest.raises(RuntimeError):
            create(admin, "batches", "2028", d)
    assert not Batch.objects.filter(label="2028").exists()
    assert AuditLog.objects.count() == count


@pytest.mark.django_db(transaction=True)
def test_concurrent_edits_cannot_overwrite_review(admin):
    row = create(admin)
    barrier = Barrier(2)

    def edit(name):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                services.change(
                    actor=admin,
                    kind="departments",
                    pk=row.pk,
                    expected_revision=1,
                    label="CSE",
                    name=name,
                )
                return "saved"
            except services.StructureConflict:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(edit, ["First", "Second"])) == ["conflict", "saved"]
    row.refresh_from_db()
    assert row.revision == 2
    assert AuditLog.objects.filter(action="academics.structure.changed").count() == 2


@pytest.mark.django_db(transaction=True)
def test_assignment_requires_enclosing_transaction():
    with pytest.raises(transaction.TransactionManagementError):
        services.require_assignment_context(
            department_id=uuid4(), batch_id=uuid4(), term_id=uuid4(), section_id=uuid4()
        )
