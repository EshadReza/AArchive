from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DataError, IntegrityError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError

from apps.academics.courses import services
from apps.academics.models import Course
from apps.academics.structure import services as structure
from apps.accounts.models import UserRole
from apps.audit.models import AuditLog

from . import test_structure as structure_tests

admin = structure_tests.admin
client = structure_tests.client
tree = structure_tests.tree
write = structure_tests.write

pytestmark = pytest.mark.django_db
FIELDS = dict(
    code="CSE 101",
    title="Introduction to Computing",
    credits="3.50",
    description="A reusable course.\nSecond line.",
)


def make(admin, tree, **changes):
    return services.create(actor=admin, department_id=tree[0].pk, **{**FIELDS, **changes})


def test_create_edit_archive_history(client, admin, tree):
    d = tree[0]
    response = write(
        client, "/api/courses", {"department_id": str(d.pk), **FIELDS, "code": " cse 101 "}
    )
    assert response.status_code == 201, response.content
    row = response.json()
    assert (
        row["code"] == "CSE 101" and row["credits"] == "3.50" and row["department_label"] == d.label
    )
    assert "batch_id" not in row and "term_id" not in row
    path = f"/api/courses/{row['id']}"
    edited = write(client, path, {**FIELDS, "title": "Updated", "expected_revision": 1}, "patch")
    assert edited.status_code == 200 and edited.json()["revision"] == 2
    assert write(client, path, {**FIELDS, "expected_revision": 1}, "patch").status_code == 409
    assert write(client, f"{path}/archive", {"expected_revision": 2}).status_code == 200
    history = client.get(path)
    assert (
        history.status_code == 200
        and history.json()["title"] == "Updated"
        and not history.json()["available"]
    )
    assert history.json()["description"] == FIELDS["description"]
    assert history.headers["Cache-Control"] == "no-store"
    assert write(client, path, {}, "delete").status_code == 405
    assert write(client, path, {**FIELDS, "expected_revision": 3}, "patch").status_code == 400
    assert write(client, f"{path}/archive", {"expected_revision": 3}).status_code == 200
    assert Course.objects.count() == 1
    audit = AuditLog.objects.filter(action="academics.course.changed").first()
    assert audit.previous_value["status"] == "ACTIVE" and audit.new_value["status"] == "ARCHIVED"
    assert "description" not in audit.new_value and len(audit.new_value["description_digest"]) == 64


@pytest.mark.parametrize(
    "value", ["-1", "100", "3.555", "NaN", "Infinity", "1e1", " 3 ", 3, 3.5, True, None, ""]
)
def test_invalid_credits(client, tree, value):
    response = write(
        client, "/api/courses", {"department_id": str(tree[0].pk), **FIELDS, "credits": value}
    )
    assert response.status_code == 400
    assert not Course.objects.exists()


@pytest.mark.parametrize(
    "extra",
    [
        {"archived": True},
        {"batch_id": "x"},
        {"term_id": "x"},
        {"revision": 1},
        {"title": " "},
        {"code": "\n"},
        {"description": "x" * 4001},
        {"description": "x\x00y"},
    ],
)
def test_invalid_fields(client, tree, extra):
    assert (
        write(
            client, "/api/courses", {"department_id": str(tree[0].pk), **FIELDS, **extra}
        ).status_code
        == 400
    )
    assert not Course.objects.exists()


def test_duplicates_scoped_and_department_immutable(client, admin, tree):
    course = make(admin, tree)
    with pytest.raises(ValidationError):
        make(admin, tree, code="cse 101")
    other = structure.create(actor=admin, kind="departments", label="EEE", name="Electrical")
    separate = services.create(actor=admin, department_id=other.pk, **FIELDS)
    assert course.pk != separate.pk
    with pytest.raises(IntegrityError), transaction.atomic():
        Course.objects.create(department=tree[0], **FIELDS)
    assert (
        write(
            client,
            f"/api/courses/{course.pk}",
            {**FIELDS, "expected_revision": 1, "department_id": str(other.pk)},
            "patch",
        ).status_code
        == 400
    )
    course.department = other
    with pytest.raises(ValidationError):
        course.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        Course.objects.filter(pk=course.pk).update(department=other)
    with pytest.raises(ProtectedError):
        other.delete()


@pytest.mark.parametrize(
    "fields",
    [
        {"code": "lower"},
        {"title": ""},
        {"credits": "-0.01"},
        {"credits": "100.00"},
        {"revision": 0},
    ],
)
def test_database_constraints(admin, tree, fields):
    error = DataError if fields.get("credits") == "100.00" else IntegrityError
    with pytest.raises(error), transaction.atomic():
        Course.objects.create(department=tree[0], **{**FIELDS, **fields})


@pytest.mark.parametrize("role", ["anonymous", "STUDENT", "TEACHER", "suspended"])
def test_write_permissions_and_filtered_reads(client, admin, tree, role):
    active = make(admin, tree)
    archived = make(admin, tree, code="CSE 102")
    services.change(actor=admin, pk=archived.pk, expected_revision=1, archive=True)
    hidden_dept = structure.create(actor=admin, kind="departments", label="EEE", name="Electrical")
    hidden = services.create(actor=admin, department_id=hidden_dept.pk, **FIELDS)
    structure.change(
        actor=admin, kind="departments", pk=hidden_dept.pk, expected_revision=1, archive=True
    )
    if role == "anonymous":
        client.logout()
        client.get("/api/auth/session")
    elif role == "suspended":
        admin.state = "SUSPENDED"
        admin.save()
    else:
        admin.role_assignments.filter(role="ADMINISTRATOR").delete()
        if role == "TEACHER":
            UserRole.objects.create(user=admin, role=role)
    actor = None if role == "anonymous" else admin
    assert (
        write(client, "/api/courses", {"department_id": str(tree[0].pk), **FIELDS}).status_code
        == 403
    )
    assert (
        write(
            client, f"/api/courses/{active.pk}", {**FIELDS, "expected_revision": 1}, "patch"
        ).status_code
        == 403
    )
    assert (
        write(client, f"/api/courses/{uuid4()}/archive", {"expected_revision": 1}).status_code
        == 403
    )
    with pytest.raises(PermissionDenied):
        make(actor, tree)
    if role == "TEACHER":
        result = client.get("/api/courses").json()
        assert result["count"] == 1 and result["results"][0]["id"] == str(active.pk)
        assert client.get(f"/api/courses/{active.pk}").status_code == 200
        assert client.get(f"/api/courses/{archived.pk}").status_code == 404
        assert client.get(f"/api/courses/{hidden.pk}").status_code == 404
        assert client.get("/api/courses?archived=true").json()["count"] == 0
        assert client.get(f"/api/courses?department_id={hidden_dept.pk}").json()["count"] == 0
    else:
        assert client.get("/api/courses").status_code == 403
        assert client.get(f"/api/courses/{uuid4()}").status_code == 403


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page_size=no",
        "q=" + "x" * 101,
        "q=a&q=b",
        "department_id=bad",
        "archived=1",
        "batch_id=x",
    ],
)
def test_invalid_filters(client, query):
    assert client.get(f"/api/courses?{query}").status_code == 400


def test_filters_pagination_csrf(client, admin, tree):
    course = make(admin, tree)
    make(admin, tree, code="CSE 102")
    assert client.get("/api/courses?page_size=1").json()["next"]
    assert client.get("/api/courses?q=101").json()["count"] == 1
    assert client.get(f"/api/courses?department_id={uuid4()}").json()["count"] == 0
    assert client.get(f"/api/courses/{uuid4()}").status_code == 404
    for path, data, method in [
        ("/api/courses", {**FIELDS, "department_id": str(tree[0].pk)}, "post"),
        (f"/api/courses/{course.pk}", {**FIELDS, "expected_revision": 1}, "patch"),
        (f"/api/courses/{course.pk}/archive", {"expected_revision": 1}, "post"),
    ]:
        assert write(client, path, data, method, csrf=False).status_code == 403


def test_one_course_reused_across_terms_and_context_gates(admin, tree):
    d, batch, term, section = tree
    course = make(admin, tree, credits="0")
    second = structure.create(
        actor=admin, kind="terms", label="2", name="Second", parent_id=batch.pk
    )
    for t in [term, second]:
        assert (
            services.require_course_context(
                course_id=course.pk, batch_id=batch.pk, term_id=t.pk, section_id=section.pk
            ).pk
            == course.pk
        )
    assert Course.objects.count() == 1
    other_d = structure.create(actor=admin, kind="departments", label="EEE", name="Electrical")
    other_batch = structure.create(
        actor=admin, kind="batches", label="2026", name="Batch", parent_id=other_d.pk
    )
    with pytest.raises(ValidationError):
        services.require_course_context(
            course_id=course.pk, batch_id=other_batch.pk, term_id=term.pk, section_id=section.pk
        )
    services.change(actor=admin, pk=course.pk, expected_revision=1, archive=True)
    with pytest.raises(ValidationError):
        services.require_course_context(
            course_id=course.pk, batch_id=batch.pk, term_id=term.pk, section_id=section.pk
        )
    assert Course.objects.get(pk=course.pk).description == FIELDS["description"]


def test_department_archive_blocks_creation_edit_and_context(admin, tree):
    d, b, t, s = tree
    course = make(admin, tree)
    structure.change(actor=admin, kind="departments", pk=d.pk, expected_revision=1, archive=True)
    with pytest.raises(ValidationError):
        make(admin, tree, code="NEW")
    with pytest.raises(ValidationError):
        services.change(actor=admin, pk=course.pk, expected_revision=1, **FIELDS)
    with pytest.raises(ValidationError):
        services.require_course_context(
            course_id=course.pk, batch_id=b.pk, term_id=t.pk, section_id=s.pk
        )
    assert services.catalog(admin).filter(pk=course.pk).exists()


def test_audit_failure_rolls_back_create_and_edit(admin, tree):
    course = make(admin, tree)
    before = AuditLog.objects.count()
    with patch("apps.academics.courses.services.record_event", side_effect=RuntimeError("fail")):
        with pytest.raises(RuntimeError):
            make(admin, tree, code="NEW")
        with pytest.raises(RuntimeError):
            services.change(
                actor=admin, pk=course.pk, expected_revision=1, **{**FIELDS, "title": "Changed"}
            )
    course.refresh_from_db()
    assert course.title == FIELDS["title"] and course.revision == 1
    assert Course.objects.count() == 1 and AuditLog.objects.count() == before


@pytest.mark.django_db(transaction=True)
def test_concurrent_reviews_one_writer(admin, tree):
    row = make(admin, tree)
    barrier = Barrier(2)

    def edit(title):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                services.change(
                    actor=admin, pk=row.pk, expected_revision=1, **{**FIELDS, "title": title}
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


@pytest.mark.django_db(transaction=True)
def test_context_requires_outer_transaction():
    with pytest.raises(transaction.TransactionManagementError):
        services.require_course_context(
            course_id=uuid4(), batch_id=uuid4(), term_id=uuid4(), section_id=uuid4()
        )
