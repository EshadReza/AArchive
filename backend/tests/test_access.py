from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.access import policy
from apps.access.enums import Capability, ResourceKind
from apps.access.models import PrivilegeLock, ScopedGrant
from apps.access.permissions import PolicyPermission
from apps.access.policy import (
    ResourcePolicy,
    ResourceRef,
    allows,
    granted_scope_ids,
    scope_queryset,
)
from apps.access.services import bootstrap_administrator, set_grant, set_roles
from apps.accounts.models import User, UserProfile, UserRole
from apps.audit.models import AuditLog

pytestmark = pytest.mark.django_db


def account(name, roles=("STUDENT",)):
    user = User.objects.create_user(f"{name}@iut.example", display_name="not-a-mark")
    User.objects.filter(pk=user.pk).update(state="ACTIVE", email_verified_at=timezone.now())
    user.role_assignments.all().delete()
    for role in roles:
        UserRole.objects.create(user=user, role=role)
    user.refresh_from_db()
    return user


@pytest.fixture
def actors():
    # Transaction tests flush the seed row; ordinary migrated databases already have it.
    PrivilegeLock.objects.get_or_create(pk=1)
    return {
        "anonymous": None,
        "owner": account("owner"),
        "other": account("other"),
        "assigned": account("assigned", ("TEACHER",)),
        "unassigned": account("unassigned", ("TEACHER",)),
        "admin": account("admin", ("ADMINISTRATOR",)),
    }


@pytest.fixture
def resources(actors, monkeypatch):
    """Synthetic adapter proving hooks; no real academic/contest policy is shipped.

    Existing profiles stand in for resource rows. Only this test registers these
    models; the assignment map is synthetic trusted fixture data, never request input.
    """
    owner, other = actors["owner"], actors["other"]
    UserProfile.objects.filter(pk=owner.pk).update(display_name="published")
    UserProfile.objects.filter(pk=other.pk).update(display_name="draft")
    assignments = {actors["assigned"].pk: {owner.pk, other.pk}}

    def selected(principal, action):
        ceiling = Q(display_name__in=["published", "draft"])
        if "ADMINISTRATOR" in principal.roles:
            return ceiling
        assigned = (
            assignments.get(principal.user_id, set()) if "TEACHER" in principal.roles else set()
        )
        if action == "marks.lock":
            return (
                ceiling
                & Q(pk__in=assigned)
                & Q(
                    pk__in=granted_scope_ids(
                        principal, Capability.MARKS_LOCK, ResourceKind.OFFERING
                    )
                )
            )
        staff = Q(pk__in=assigned)
        if action == "marks.view" and "STUDENT" in principal.roles:
            return ceiling & (staff | Q(pk=principal.user_id, display_name="published"))
        return ceiling & staff

    monkeypatch.setitem(
        policy._policies,
        ResourceKind.MARK,
        ResourcePolicy(
            UserProfile,
            {
                action: (lambda principal, action=action: selected(principal, action))
                for action in ["marks.view", "marks.assign", "marks.lock"]
            },
        ),
    )
    monkeypatch.setitem(policy._policies, ResourceKind.OFFERING, ResourcePolicy(UserProfile, {}))
    return assignments


@pytest.mark.parametrize("name", ["anonymous", "owner", "other", "assigned", "unassigned", "admin"])
@pytest.mark.parametrize("action", ["marks.view", "marks.assign"])
def test_matrix_list_and_detail_agree(actors, resources, name, action):
    actor = actors[name]
    expected = {actors["owner"].pk, actors["other"].pk} if name in {"admin", "assigned"} else set()
    if name == "owner" and action == "marks.view":
        expected = {actors["owner"].pk}
    visible = scope_queryset(actor, action, UserProfile.objects.all(), kind=ResourceKind.MARK)
    assert set(visible.values_list("pk", flat=True)) == expected
    for target in [actors["owner"], actors["other"]]:
        assert allows(actor, action, ResourceRef(ResourceKind.MARK, target.pk)) == (
            target.pk in expected
        )


def test_source_admin_unknown_actions_and_unregistered_resources_fail_closed(actors):
    source = SimpleNamespace(pk=actors["admin"].pk, roles=["ADMINISTRATOR"], is_authenticated=True)
    assert not allows(source, "roles.manage")
    for actor in [source, actors["admin"], actors["unassigned"]]:
        assert not allows(actor, "invented.permission")
        assert not allows(actor, "contest.manage", ResourceRef(ResourceKind.CONTEST, uuid4()))
        assert not allows(actor, "marks.view", {"owner": True, "source_role": "administrator"})
    assert not scope_queryset(
        actors["admin"], "audit.view", User.objects.all(), kind=ResourceKind.AUDIT
    ).exists()


@pytest.mark.parametrize("state", ["PENDING", "SUSPENDED", "ARCHIVED", "ANONYMIZED"])
def test_current_state_overrides_cached_privileges(actors, resources, state):
    admin = actors["admin"]
    User.objects.filter(pk=admin.pk).update(state=state)
    assert not allows(admin, "roles.manage")
    assert not scope_queryset(
        admin, "marks.view", UserProfile.objects.all(), kind=ResourceKind.MARK
    ).exists()


def test_multirole_and_assignment_removal_are_fresh(actors, resources):
    user = actors["owner"]
    UserRole.objects.create(user=user, role="TEACHER")
    resources[user.pk] = {actors["other"].pk}
    assert allows(user, "marks.assign", ResourceRef(ResourceKind.MARK, actors["other"].pk))
    resources.pop(user.pk)
    assert not allows(user, "marks.assign", ResourceRef(ResourceKind.MARK, actors["other"].pk))
    assert allows(user, "marks.view", ResourceRef(ResourceKind.MARK, user.pk))


def test_role_changes_are_admin_only_audited_and_noop_is_idempotent(actors):
    target = actors["owner"]
    for actor in [None, actors["unassigned"], target]:
        with pytest.raises(PermissionDenied):
            set_roles(
                actor=actor,
                subject_id=target.pk,
                roles=["ADMINISTRATOR"],
                reason="administrative_change",
            )
    set_roles(
        actor=actors["admin"],
        subject_id=target.pk,
        roles=["STUDENT", "TEACHER"],
        reason="administrative_change",
    )
    entry = AuditLog.objects.get(action="accounts.roles.changed")
    assert entry.previous_value == {"roles": ["STUDENT"]}
    assert entry.new_value == {"roles": ["STUDENT", "TEACHER"]}
    assert entry.actor_id == actors["admin"].pk
    set_roles(
        actor=actors["admin"],
        subject_id=target.pk,
        roles=["TEACHER", "STUDENT"],
        reason="administrative_change",
    )
    assert AuditLog.objects.count() == 1


@pytest.mark.parametrize(
    "roles", [[], ["TA"], ["SOURCE_ADMIN"], ["TEACHER", "TEACHER"], "ADMINISTRATOR"]
)
def test_invalid_roles_cannot_be_assigned(actors, roles):
    with pytest.raises(ValidationError):
        set_roles(
            actor=actors["admin"],
            subject_id=actors["owner"].pk,
            roles=roles,
            reason="administrative_change",
        )
    assert not AuditLog.objects.exists()


def test_role_changes_require_reason_and_do_not_mass_assign(actors):
    args = {"actor": actors["admin"], "subject_id": actors["owner"].pk, "roles": ["TEACHER"]}
    with pytest.raises(ValidationError):
        set_roles(**args, reason="")
    with pytest.raises(TypeError):
        set_roles(**args, reason="administrative_change", source_roles=["ADMINISTRATOR"])
    with pytest.raises(TypeError):
        set_roles(**args, reason="administrative_change", password="secret")


def test_last_eligible_admin_cannot_be_removed(actors):
    admin = actors["admin"]
    with pytest.raises(ValidationError, match="last eligible"):
        set_roles(
            actor=admin, subject_id=admin.pk, roles=["TEACHER"], reason="administrative_change"
        )
    set_roles(
        actor=admin,
        subject_id=actors["owner"].pk,
        roles=["ADMINISTRATOR"],
        reason="administrative_change",
    )
    set_roles(actor=admin, subject_id=admin.pk, roles=["TEACHER"], reason="administrative_change")
    assert not allows(admin, "roles.manage")


def test_audit_failure_rolls_back_privileges(actors, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("apps.access.services.record_event", fail)
    with pytest.raises(RuntimeError):
        set_roles(
            actor=actors["admin"],
            subject_id=actors["owner"].pk,
            roles=["TEACHER"],
            reason="administrative_change",
        )
    assert list(actors["owner"].role_assignments.values_list("role", flat=True)) == ["STUDENT"]


def grant(actors, **kwargs):
    return set_grant(
        **{
            "actor": actors["admin"],
            "subject_id": actors["assigned"].pk,
            "capability": Capability.MARKS_LOCK,
            "scope": ResourceRef(ResourceKind.OFFERING, actors["owner"].pk),
            "active": True,
            "reason": "administrative_change",
            **kwargs,
        }
    )


def test_scoped_grant_intersects_assignment_and_revokes_immediately(actors, resources):
    teacher = actors["assigned"]
    target = ResourceRef(ResourceKind.MARK, actors["owner"].pk)
    assert not allows(teacher, "marks.lock", target)
    row = grant(actors)
    assert allows(teacher, "marks.lock", target)
    assert not allows(teacher, "marks.lock", ResourceRef(ResourceKind.MARK, actors["other"].pk))
    grant(actors, subject_id=actors["unassigned"].pk)
    assert not allows(actors["unassigned"], "marks.lock", target)
    entry = AuditLog.objects.filter(target_id=str(row.pk)).get()
    assert entry.new_value["scope_id"] == str(actors["owner"].pk)
    assert entry.new_value["status"] == "GRANTED"
    grant(actors, active=False)
    assert not allows(teacher, "marks.lock", target)
    row.refresh_from_db()
    assert not row.active
    assert AuditLog.objects.filter(target_id=str(row.pk)).count() == 2
    grant(actors, active=False)
    assert AuditLog.objects.filter(target_id=str(row.pk)).count() == 2
    grant(actors)
    teacher.role_assignments.filter(role="TEACHER").delete()
    assert not allows(teacher, "marks.lock", target)


def test_grant_cannot_broaden_marks_view_or_wrong_capability(actors, resources):
    grant(actors, capability=Capability.BATCH_REPORTS, subject_id=actors["unassigned"].pk)
    assert not allows(
        actors["unassigned"], "marks.view", ResourceRef(ResourceKind.MARK, actors["owner"].pk)
    )
    assert not allows(
        actors["unassigned"], "marks.lock", ResourceRef(ResourceKind.MARK, actors["owner"].pk)
    )


@pytest.mark.parametrize(
    "case",
    [
        "student",
        "wrong_scope",
        "unknown_capability",
        "missing_scope",
        "unregistered_scope",
        "not_bool",
    ],
)
def test_invalid_grants_fail_without_rows(actors, resources, case):
    kwargs = {
        "student": {"subject_id": actors["owner"].pk},
        "wrong_scope": {"scope": ResourceRef(ResourceKind.CONTEST, actors["owner"].pk)},
        "unknown_capability": {"capability": "roles.manage"},
        "missing_scope": {"scope": ResourceRef(ResourceKind.OFFERING, uuid4())},
        "unregistered_scope": {
            "capability": Capability.RESTRICTED_VIEW,
            "scope": ResourceRef(ResourceKind.CONTEST, uuid4()),
        },
        "not_bool": {"active": "true"},
    }[case]
    with pytest.raises(ValidationError):
        grant(actors, **kwargs)
    assert not ScopedGrant.objects.exists()


def test_grant_requires_admin_and_audit_failure_rolls_back(actors, resources, monkeypatch):
    with pytest.raises(PermissionDenied):
        grant(actors, actor=actors["assigned"])

    def fail(**kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("apps.access.services.record_event", fail)
    with pytest.raises(RuntimeError):
        grant(actors)
    assert not ScopedGrant.objects.exists()


def test_removing_teacher_revokes_delegations_before_role_can_be_restored(actors, resources):
    row = grant(actors)
    teacher = actors["assigned"]
    set_roles(
        actor=actors["admin"], subject_id=teacher.pk, roles=["STUDENT"], reason="security_response"
    )
    row.refresh_from_db()
    assert not row.active
    assert AuditLog.objects.filter(target_id=str(row.pk), new_value__status="REVOKED").count() == 1
    set_roles(
        actor=actors["admin"],
        subject_id=teacher.pk,
        roles=["TEACHER"],
        reason="administrative_change",
    )
    assert not allows(teacher, "marks.lock", ResourceRef(ResourceKind.MARK, actors["owner"].pk))


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_delegation_creates_one_grant_and_event(actors, resources):
    barrier = Barrier(2)

    def delegate(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return grant(actors).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        ids = list(executor.map(delegate, range(2)))
    assert ids[0] == ids[1]
    assert ScopedGrant.objects.count() == 1
    assert AuditLog.objects.filter(action="access.grant.changed").count() == 1


def test_database_grant_uniqueness_and_capability_scope_constraints(actors, resources):
    row = grant(actors)
    with pytest.raises(IntegrityError), transaction.atomic():
        ScopedGrant.objects.create(
            subject=row.subject,
            capability=row.capability,
            scope_kind=row.scope_kind,
            scope_id=row.scope_id,
        )
    for fields in [{"capability": "roles.manage"}, {"scope_kind": ResourceKind.CONTEST}]:
        with pytest.raises(IntegrityError), transaction.atomic():
            ScopedGrant.objects.filter(pk=row.pk).update(**fields)


def test_bootstrap_is_once_only_audited_and_requires_existing_eligible_account():
    PrivilegeLock.objects.get_or_create(pk=1)
    user = User.objects.create_user("bootstrap@iut.example")
    with pytest.raises(CommandError):
        call_command("bootstrap_administrator", email=user.email, stdout=StringIO())
    User.objects.filter(pk=user.pk).update(state="ACTIVE", email_verified_at=timezone.now())
    call_command("bootstrap_administrator", email=user.email.upper(), stdout=StringIO())
    assert allows(user, "roles.manage")
    event = AuditLog.objects.get()
    assert event.system_actor == "bootstrap"
    assert event.actor_id is None
    with pytest.raises(PermissionDenied):
        bootstrap_administrator(subject_id=user.pk)
    User.objects.filter(pk=user.pk).update(state="SUSPENDED")
    with pytest.raises(PermissionDenied):
        bootstrap_administrator(subject_id=user.pk)


def test_rest_permission_uses_shared_current_role_gate(actors):
    class View(APIView):
        permission_classes = [PolicyPermission]
        policy_action = "roles.manage"

        def get(self, request):
            return Response({"ok": True})

    for name, expected in [("admin", 200), ("assigned", 403), ("owner", 403)]:
        request = APIRequestFactory().get("/synthetic-policy-check")
        force_authenticate(request, user=actors[name])
        assert View.as_view()(request).status_code == expected


@pytest.mark.django_db(transaction=True)
def test_concurrent_self_demotions_leave_an_eligible_admin(actors):
    second = account("second-admin", ("ADMINISTRATOR",))
    first = actors["admin"]
    barrier = Barrier(2)

    def demote(user_id):
        close_old_connections()
        try:
            user = User.objects.get(pk=user_id)
            barrier.wait(timeout=10)
            try:
                set_roles(
                    actor=user,
                    subject_id=user.pk,
                    roles=["TEACHER"],
                    reason="administrative_change",
                )
                return "changed"
            except ValidationError:
                return "protected"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(demote, [first.pk, second.pk]))
    assert sorted(results) == ["changed", "protected"]
    assert (
        User.objects.eligible_for_authentication()
        .filter(role_assignments__role="ADMINISTRATOR")
        .count()
        == 1
    )
    assert AuditLog.objects.filter(action="accounts.roles.changed").count() == 1
