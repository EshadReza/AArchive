from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError

from apps.academics.models import Offering, TeacherAssignment
from apps.academics.offerings import services
from apps.academics.structure import services as structure
from apps.access.enums import Capability, ResourceKind
from apps.access.models import ScopedGrant
from apps.access.policy import ResourceRef, allows
from apps.access.services import set_grant
from apps.audit.models import AuditLog

from . import test_courses as courses
from . import test_structure as fixtures
from .test_access import account

admin = fixtures.admin
client = fixtures.client
tree = fixtures.tree
write = fixtures.write
pytestmark = pytest.mark.django_db
BASE = "/api/course-offerings"


def fields(admin, tree):
    course = courses.make(admin, tree)
    return dict(
        course_id=course.pk,
        batch_id=tree[1].pk,
        term_id=tree[2].pk,
        section_id=tree[3].pk,
        name="Computing 2026",
    )


def login(client, actor):
    client.force_login(actor, backend="apps.accounts.auth.backend.PlatformBackend")
    client.get("/api/auth/session")


def test_creation_creator_and_admin_roles(client, admin, tree):
    data = fields(admin, tree)
    teacher = account("creator", ("TEACHER",))
    login(client, teacher)
    response = write(client, BASE, {key: str(value) for key, value in data.items()})
    assert response.status_code == 201, response.content
    row = Offering.objects.get()
    assert row.created_by == teacher and response.json()["can_manage"]
    assert TeacherAssignment.objects.get().teacher == teacher
    assert AuditLog.objects.filter(action="academics.teacher.changed").count() == 1
    assert AuditLog.objects.filter(action="academics.offering.changed").count() == 1
    second = fixtures.create(admin, "terms", "2", tree[1])
    row2 = services.create(actor=admin, **{**data, "term_id": second.pk})
    assert row2.teacher_assignments.get().teacher == admin
    assert not admin.role_assignments.filter(role="TEACHER").exists()
    assert client.get(BASE).json()["count"] == 1


def test_multi_teacher_removal_reassignment_and_grants(client, admin, tree):
    teacher = account("creator", ("TEACHER",))
    other = account("co-teacher", ("TEACHER",))
    row = services.create(actor=teacher, **fields(admin, tree))
    path = f"{BASE}/{row.pk}"
    services.assign(actor=admin, pk=row.pk, teacher_id=other.pk, expected_revision=1, active=True)
    login(client, other)
    assert client.get(path).status_code == 200
    assert (
        write(
            client, path, {"name": "Co-teacher edit", "expected_revision": 2}, "patch"
        ).status_code
        == 200
    )
    assert (
        write(
            client,
            path + "/teachers",
            {"teacher_id": str(teacher.pk), "active": False, "expected_revision": 3},
        ).status_code
        == 403
    )
    scope = ResourceRef(ResourceKind.OFFERING, row.pk)
    set_grant(
        actor=admin,
        subject_id=teacher.pk,
        capability=Capability.MARKS_LOCK,
        scope=scope,
        active=True,
        reason="administrative_change",
    )
    removed = services.assign(
        actor=admin, pk=row.pk, teacher_id=teacher.pk, expected_revision=3, active=False
    )
    assert removed.revision == 4
    assert not ScopedGrant.objects.get().active
    login(client, teacher)
    assert client.get(BASE).json()["count"] == 0
    assert client.get(path).status_code == 404
    assert client.get(path + "/teachers").status_code == 404
    assert (
        write(client, path, {"name": "Forbidden", "expected_revision": 4}, "patch").status_code
        == 403
    )
    assert not allows(teacher, "course.manage", scope)
    assert allows(other, "course.manage", scope)
    services.assign(actor=admin, pk=row.pk, teacher_id=teacher.pk, expected_revision=4, active=True)
    assert TeacherAssignment.objects.filter(teacher=teacher).count() == 2
    assert TeacherAssignment.objects.filter(teacher=teacher, ended_at__isnull=False).count() == 1
    assert not ScopedGrant.objects.get().active
    row.refresh_from_db()
    assert row.created_by == teacher and row.name == "Co-teacher edit"
    history = client.get(path + "/teachers").json()
    assert history["count"] == 3 and all("email" not in link for link in history["results"])
    assert client.get(BASE + "/staff-options").status_code == 403
    assert write(client, path + "/archive", {"expected_revision": 5}).status_code == 403


@pytest.mark.parametrize("mismatch", ["department", "term", "section"])
def test_mismatches_at_service_api_and_database(client, admin, tree, mismatch):
    data = fields(admin, tree)
    other_d = fixtures.create(admin, label="EEE")
    other_b = fixtures.create(admin, "batches", "2026", other_d)
    other_t = fixtures.create(admin, "terms", "1", other_b)
    if mismatch == "department":
        data.update(
            batch_id=other_b.pk, term_id=other_t.pk, section_id=other_b.sections.get(label="ALL").pk
        )
    elif mismatch == "term":
        data["term_id"] = other_t.pk
    else:
        data["section_id"] = other_b.sections.get(label="ALL").pk
    with pytest.raises(ValidationError):
        services.create(actor=admin, **data)
    assert write(client, BASE, {k: str(v) for k, v in data.items()}).status_code == 400
    with pytest.raises(IntegrityError), transaction.atomic():
        Offering.objects.create(created_by=admin, **data)
    assert not Offering.objects.exists()


def test_duplicates_archived_and_immutable_tuple(admin, tree):
    data = fields(admin, tree)
    row = services.create(actor=admin, **data)
    services.change(actor=admin, pk=row.pk, expected_revision=1, archive=True)
    with pytest.raises(ValidationError):
        services.create(actor=admin, **data)
    with pytest.raises(IntegrityError), transaction.atomic():
        Offering.objects.create(created_by=admin, **data)
    term = fixtures.create(admin, "terms", "2", tree[1])
    for changes in ({"term_id": term.pk}, {"created_by": account("someone")}, {"id": uuid4()}):
        with pytest.raises(IntegrityError), transaction.atomic():
            Offering.objects.filter(pk=row.pk).update(**changes)
    with pytest.raises(ProtectedError):
        tree[1].delete()
    with pytest.raises(ProtectedError):
        row.delete()


def test_assignment_history_database_guards(admin, tree):
    row = services.create(actor=admin, **fields(admin, tree))
    link = row.teacher_assignments.get()
    with pytest.raises(IntegrityError), transaction.atomic():
        TeacherAssignment.objects.create(offering=row, teacher=admin, assigned_by=admin)
    with pytest.raises(IntegrityError), transaction.atomic():
        TeacherAssignment.objects.filter(pk=link.pk).delete()
    services.assign(actor=admin, pk=row.pk, teacher_id=admin.pk, active=False, expected_revision=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        TeacherAssignment.objects.filter(pk=link.pk).update(ended_at=None, removed_by=None)
    assert allows(admin, "course.manage", ResourceRef(ResourceKind.OFFERING, row.pk))


@pytest.mark.parametrize("role", ["anonymous", "STUDENT", "TEACHER", "suspended"])
def test_unassigned_and_lifecycle_denial(client, admin, tree, role):
    row = services.create(actor=admin, **fields(admin, tree))
    if role == "anonymous":
        client.logout()
        client.get("/api/auth/session")
    else:
        actor = account("outside", ("TEACHER",) if role == "suspended" else (role,))
        if role == "suspended":
            actor.state = "SUSPENDED"
            actor.save()
        login(client, actor)
    result = client.get(BASE)
    assert result.status_code == (200 if role == "TEACHER" else 403)
    if role == "TEACHER":
        assert result.json()["count"] == 0
    assert client.get(f"{BASE}/{row.pk}").status_code == (404 if role == "TEACHER" else 403)
    assert (
        write(
            client, f"{BASE}/{row.pk}", {"name": "No", "expected_revision": 1}, "patch"
        ).status_code
        == 403
    )
    assert client.get(BASE + "/staff-options").status_code == 403


@pytest.mark.parametrize("parent", ["department", "batch", "term", "section", "course", "offering"])
def test_archive_gates_and_retained_reads(client, admin, tree, parent):
    teacher = account("teacher", ("TEACHER",))
    data = fields(admin, tree)
    if parent == "section":
        section = fixtures.create(admin, "sections", "A", tree[1])
        tree = (*tree[:3], section)
        data["section_id"] = section.pk
    row = services.create(actor=teacher, **data)
    if parent == "offering":
        services.change(actor=admin, pk=row.pk, expected_revision=1, archive=True)
    elif parent == "course":
        courses.services.change(actor=admin, pk=row.course_id, expected_revision=1, archive=True)
    else:
        index = ["department", "batch", "term", "section"].index(parent)
        structure.change(
            actor=admin,
            kind=["departments", "batches", "terms", "sections"][index],
            pk=tree[index].pk,
            expected_revision=1,
            archive=True,
        )
    login(client, teacher)
    response = client.get(f"{BASE}/{row.pk}")
    assert response.status_code == 200 and not response.json()["can_manage"]
    with pytest.raises(PermissionDenied):
        services.change(actor=teacher, pk=row.pk, expected_revision=1, name="No")
    row.refresh_from_db()
    with pytest.raises(ValidationError):
        services.assign(
            actor=admin, pk=row.pk, teacher_id=admin.pk, expected_revision=row.revision, active=True
        )
    services.assign(
        actor=admin, pk=row.pk, teacher_id=teacher.pk, expected_revision=row.revision, active=False
    )
    assert client.get(f"{BASE}/{row.pk}").status_code == 404


def test_revision_csrf_payload_options(client, admin, tree):
    data = fields(admin, tree)
    row = services.create(actor=admin, **data)
    path = f"{BASE}/{row.pk}"
    for suffix, payload in [
        ("", {"name": "New", "expected_revision": 1}),
        ("/teachers", {"teacher_id": str(admin.pk), "active": False, "expected_revision": 1}),
        ("/archive", {"expected_revision": 1}),
    ]:
        method = "patch" if not suffix else "post"
        assert write(client, path + suffix, payload, method, csrf=False).status_code == 403
        assert (
            write(client, path + suffix, {**payload, "expected_revision": 999}, method).status_code
            == 409
        )
        assert (
            write(client, path + suffix, {**payload, "unexpected": True}, method).status_code == 400
        )
    for query in ["page=0", "page=1&page=2", "page_size=x", "unknown=true"]:
        assert client.get(BASE + "?" + query).status_code == 400
    assert client.get(BASE).headers["Cache-Control"] == "no-store"
    assert client.get(BASE + "/staff-options").json()["count"] == 1
    teacher = account("teacher", ("TEACHER",))
    login(client, teacher)
    assert client.get("/api/course-offering-options/departments").json()["count"] == 1
    assert (
        client.get(f"/api/course-offering-options/batches?department_id={uuid4()}").json()["count"]
        == 0
    )
    assert write(client, "/api/course-offering-options/departments", {}).status_code == 405
    structure.change(
        actor=admin, kind="departments", pk=tree[0].pk, expected_revision=1, archive=True
    )
    for kind in ["departments", "batches", "terms", "sections"]:
        assert client.get("/api/course-offering-options/" + kind).json()["count"] == 0


def test_eligibility_and_audit_rollback(admin, tree):
    data = fields(admin, tree)
    with patch("apps.academics.offerings.services.record_event", side_effect=RuntimeError("fail")):
        with pytest.raises(RuntimeError):
            services.create(actor=admin, **data)
    assert not Offering.objects.exists() and not TeacherAssignment.objects.exists()
    row = services.create(actor=admin, **data)
    student = account("student")
    with pytest.raises(ValidationError):
        services.assign(
            actor=admin, pk=row.pk, teacher_id=student.pk, expected_revision=1, active=True
        )
    teacher = account("teacher", ("TEACHER",))
    for subject, active in [(teacher, True), (admin, False)]:
        with patch(
            "apps.academics.offerings.services.record_event", side_effect=RuntimeError("fail")
        ):
            with pytest.raises(RuntimeError):
                services.assign(
                    actor=admin,
                    pk=row.pk,
                    teacher_id=subject.pk,
                    expected_revision=1,
                    active=active,
                )
        row.refresh_from_db()
        assert row.revision == 1 and row.teacher_assignments.count() == 1
        assert row.teacher_assignments.get().ended_at is None


@pytest.mark.django_db(transaction=True)
def test_concurrent_edits_one_revision(admin, tree):
    row = services.create(actor=admin, **fields(admin, tree))
    barrier = Barrier(2)

    def edit(name):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                services.change(actor=admin, pk=row.pk, expected_revision=1, name=name)
                return "saved"
            except services.StructureConflict:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(edit, ["A", "B"])) == ["conflict", "saved"]


@pytest.mark.parametrize(
    "changes",
    [
        {"name": ""},
        {"name": "x" * 201},
        {"name": "\x00"},
        {"name": True},
        {"course_id": "bad"},
        {"batch_id": None},
        {"created_by": "spoofed"},
    ],
)
def test_creation_strict_payload(client, admin, tree, changes):
    data = {k: str(v) for k, v in fields(admin, tree).items()}
    assert write(client, BASE, {**data, **changes}).status_code == 400
    assert not Offering.objects.exists()


def test_creation_permissions_csrf_and_current_role(client, admin, tree):
    data = fields(admin, tree)
    payload = {k: str(v) for k, v in data.items()}
    assert write(client, BASE, payload, csrf=False).status_code == 403
    student = account("student")
    login(client, student)
    assert write(client, BASE, payload).status_code == 403
    teacher = account("teacher", ("TEACHER",))
    row = services.create(actor=teacher, **data)
    scope = ResourceRef(ResourceKind.OFFERING, row.pk)
    assert allows(teacher, "course.manage", scope)
    teacher.role_assignments.all().delete()
    assert not allows(teacher, "course.view", scope)
    with pytest.raises(PermissionDenied):
        services.change(actor=teacher, pk=row.pk, expected_revision=1, name="No")
    assert row.teacher_assignments.get().ended_at is None


def test_assignment_noop_and_pagination(client, admin, tree):
    row = services.create(actor=admin, **fields(admin, tree))
    teacher = account("teacher", ("TEACHER",))
    for subject, active in [(admin, True), (teacher, False)]:
        result = services.assign(
            actor=admin, pk=row.pk, teacher_id=subject.pk, expected_revision=1, active=active
        )
        assert result.revision == 1
    services.assign(actor=admin, pk=row.pk, teacher_id=teacher.pk, expected_revision=1, active=True)
    path = f"{BASE}/{row.pk}/teachers"
    page = client.get(path + "?page_size=1").json()
    assert page["count"] == 2 and page["next"] and len(page["results"]) == 1
    assert client.get(path + "?page_size=1&page=2").json()["previous"]
    assert client.get(BASE + "/staff-options?page_size=1").json()["next"]
    assert (
        write(
            client, path, {"teacher_id": str(teacher.pk), "active": "false", "expected_revision": 2}
        ).status_code
        == 400
    )
    assert (
        write(
            client, f"{BASE}/{row.pk}", {"name": "No", "expected_revision": True}, "patch"
        ).status_code
        == 400
    )
