from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.courses.services import require_course_context
from apps.academics.structure.services import StructureConflict, validate_text
from apps.access.enums import ResourceKind
from apps.access.models import ScopedGrant
from apps.access.policy import ResourceRef, require_permission
from apps.access.services import lock_privilege_changes, set_grant
from apps.accounts.models import User
from apps.audit.services import record_event

from .models import Offering, TeacherAssignment


def value(row):
    return {
        "course_id": str(row.course_id),
        "batch_id": str(row.batch_id),
        "term_id": str(row.term_id),
        "section_id": str(row.section_id),
        "name": row.name,
        "status": "ARCHIVED" if row.archived else "ACTIVE",
        "revision": str(row.revision),
    }


def audit(actor, row, previous=None):
    record_event(
        actor=actor,
        action="academics.offering.changed",
        target_id=row.pk,
        previous_value=previous,
        new_value=value(row),
        reason="administrative_change",
    )


def assignment_value(link):
    return {
        "offering_id": str(link.offering_id),
        "teacher_id": str(link.teacher_id),
        "status": "ENDED" if link.ended_at else "ASSIGNED",
    }


def assignment_audit(actor, link, previous=None):
    record_event(
        actor=actor,
        action="academics.teacher.changed",
        target_id=link.pk,
        previous_value=previous,
        new_value=assignment_value(link),
        reason="administrative_change",
    )


def require_available(row):
    if row.archived:
        raise ValidationError("Archived offerings cannot receive changes.")
    require_course_context(
        course_id=row.course_id,
        batch_id=row.batch_id,
        term_id=row.term_id,
        section_id=row.section_id,
    )


def check_revision(row, expected_revision):
    if type(expected_revision) is not int or expected_revision != row.revision:
        raise StructureConflict("Offering changed; reload and review.")


def attach_creator(actor, row):
    # Creation already authorizes a current Admin/Teacher under the privilege lock.
    # An Admin-only creator gets a retained staff assignment, not a new platform role.
    link = TeacherAssignment.objects.create(offering=row, teacher=actor, assigned_by=actor)
    assignment_audit(actor, link)


@transaction.atomic
def create(*, actor, course_id, batch_id, term_id, section_id, name):
    lock_privilege_changes()
    require_permission(actor, "course.create")
    require_course_context(
        course_id=course_id, batch_id=batch_id, term_id=term_id, section_id=section_id
    )
    _, name = validate_text("OFFERING", name)
    row = Offering(
        course_id=course_id,
        batch_id=batch_id,
        term_id=term_id,
        section_id=section_id,
        name=name,
        created_by=actor,
    )
    row.full_clean()
    row.save()
    audit(actor, row)
    attach_creator(actor, row)
    return row


@transaction.atomic
def change(*, actor, pk, expected_revision, name=None, archive=False):
    lock_privilege_changes()
    if archive:
        require_permission(actor, "system.manage")
    else:
        require_permission(actor, "course.manage", ResourceRef(ResourceKind.OFFERING, pk))
    row = Offering.objects.select_for_update().get(pk=pk)
    check_revision(row, expected_revision)
    if archive and row.archived:
        return row
    previous = value(row)
    if archive:
        row.archived = True
    else:
        require_available(row)
        _, row.name = validate_text("OFFERING", name)
    row.revision += 1
    row.full_clean()
    row.save()
    audit(actor, row, previous)
    return row


@transaction.atomic
def assign(*, actor, pk, teacher_id, expected_revision, active):
    lock_privilege_changes()
    require_permission(actor, "system.manage")
    row = Offering.objects.select_for_update().get(pk=pk)
    check_revision(row, expected_revision)
    if type(active) is not bool:
        raise ValidationError("Choose assignment or removal.")
    link = TeacherAssignment.objects.filter(
        offering=row, teacher_id=teacher_id, ended_at__isnull=True
    ).first()
    if active:
        require_available(row)
        teacher = User.objects.select_for_update().get(pk=teacher_id)
        if (
            not teacher.is_login_eligible
            or not teacher.role_assignments.filter(role__in=["TEACHER", "ADMINISTRATOR"]).exists()
        ):
            raise ValidationError("Choose an eligible Teacher or Administrator.")
        if link:
            return row
        link = TeacherAssignment.objects.create(offering=row, teacher=teacher, assigned_by=actor)
        assignment_audit(actor, link)
    else:
        # Removal remains possible on historical offerings and closed accounts.
        if link is None:
            return row
        previous = assignment_value(link)
        link.ended_at = timezone.now()
        link.removed_by = actor
        link.full_clean()
        link.save(update_fields=["ended_at", "removed_by"])
        assignment_audit(actor, link, previous)
        for grant in ScopedGrant.objects.filter(
            subject_id=teacher_id, scope_kind=ResourceKind.OFFERING, scope_id=pk, active=True
        ):
            set_grant(
                actor=actor,
                subject_id=teacher_id,
                capability=grant.capability,
                scope=ResourceRef(ResourceKind.OFFERING, pk),
                active=False,
                reason="administrative_change",
            )
    previous = value(row)
    row.revision += 1
    row.save(update_fields=["revision", "updated_at"])
    audit(actor, row, previous)
    return row
