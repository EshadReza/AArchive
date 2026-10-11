import hashlib
import re
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.academics.structure.models import Department
from apps.academics.structure.services import (
    StructureConflict,
    require_active,
    require_assignment_context,
    validate_text,
)
from apps.access.policy import current_principal, require_permission
from apps.access.services import lock_privilege_changes
from apps.audit.services import record_event

from .models import Course


def catalog(actor):
    principal = current_principal(actor)
    if principal is None or not principal.roles & {"ADMINISTRATOR", "TEACHER"}:
        raise PermissionDenied("Catalog access is required.")
    rows = Course.objects.select_related("department")
    if "ADMINISTRATOR" not in principal.roles:
        rows = rows.filter(archived=False, department__archived=False)
    return rows


def validated(code, title, credits, description):
    code, title = validate_text(code, title)
    if not isinstance(credits, str) or not re.fullmatch(r"[0-9]{1,2}(?:\.[0-9]{1,2})?", credits):
        raise ValidationError(
            "Credits must be a decimal string from 0 to 99.99 with at most two decimal places."
        )
    if (
        not isinstance(description, str)
        or len(description) > 4000
        or any((ord(c) < 32 and c not in "\n\r\t") or ord(c) == 127 for c in description)
    ):
        raise ValidationError("Description must be at most 4000 characters of plain text.")
    return dict(code=code, title=title, credits=Decimal(credits), description=description.strip())


def snapshot(row):
    return {
        "department_id": str(row.department_id),
        "code": row.code,
        "title": row.title,
        "credits": format(row.credits, ".2f"),
        "description_digest": hashlib.sha256(row.description.encode()).hexdigest(),
        "status": "ARCHIVED" if row.archived else "ACTIVE",
        "revision": str(row.revision),
    }


def audit(actor, row, previous=None):
    record_event(
        actor=actor,
        action="academics.course.changed",
        target_id=row.pk,
        previous_value=previous,
        new_value=snapshot(row),
        reason="administrative_change",
    )


@transaction.atomic
def create(*, actor, department_id, code, title, credits, description):
    lock_privilege_changes()
    require_permission(actor, "system.manage")
    department = Department.objects.select_for_update().get(pk=department_id)
    require_active(department)
    row = Course(department=department, **validated(code, title, credits, description))
    row.full_clean()
    row.save()
    audit(actor, row)
    return row


@transaction.atomic
def change(*, actor, pk, expected_revision, archive=False, **fields):
    lock_privilege_changes()
    require_permission(actor, "system.manage")
    row = Course.objects.select_for_update().get(pk=pk)
    if type(expected_revision) is not int or expected_revision != row.revision:
        raise StructureConflict("Course changed. Reload before reviewing.")
    if archive and row.archived:
        return row
    previous = snapshot(row)
    if archive:
        if fields:
            raise ValidationError("Archive accepts no course fields.")
        row.archived = True
    else:
        require_active(row.department)
        if row.archived:
            raise ValidationError("Archived courses cannot be edited.")
        for key, value in validated(**fields).items():
            setattr(row, key, value)
    row.revision += 1
    row.full_clean()
    row.save()
    audit(actor, row, previous)
    return row


def require_course_context(*, course_id, batch_id, term_id, section_id):
    """Validate future offering writes inside their own authorized transaction."""
    if not transaction.get_connection().in_atomic_block:
        raise transaction.TransactionManagementError("An offering transaction is required.")
    lock_privilege_changes()
    course = Course.objects.select_related("department").get(pk=course_id)
    if course.archived:
        raise ValidationError("Archived courses cannot receive new offerings.")
    require_assignment_context(
        department_id=course.department_id,
        batch_id=batch_id,
        term_id=term_id,
        section_id=section_id,
    )
    return course
