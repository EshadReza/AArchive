from django.core.exceptions import ValidationError
from django.db import transaction

from apps.access.policy import require_permission
from apps.access.services import lock_privilege_changes
from apps.audit.services import record_event

from .models import Batch, Department, Section, Term

MODELS = {"departments": Department, "batches": Batch, "terms": Term, "sections": Section}
PARENTS = {
    "batches": ("department", Department),
    "terms": ("batch", Batch),
    "sections": ("batch", Batch),
}


class StructureConflict(ValidationError):
    pass


def validate_text(label, name):
    if not isinstance(label, str) or not isinstance(name, str):
        raise ValidationError("Label and name must be text.")
    label, name = label.strip().upper(), name.strip()
    if (
        not 1 <= len(label) <= 64
        or not 1 <= len(name) <= 200
        or any(ord(c) < 32 or ord(c) == 127 for c in label + name)
    ):
        raise ValidationError("Use a label of 1–64 and name of 1–200 printable characters.")
    return label, name


def require_active(row):
    if row.archived:
        raise ValidationError("Archived structure cannot receive new assignments or edits.")
    if isinstance(row, Batch):
        require_active(row.department)
    elif isinstance(row, Term | Section):
        require_active(row.batch)


def snapshot(kind, row):
    parent = PARENTS.get(kind)
    return {
        "kind": kind,
        "label": row.label,
        "name": row.name,
        "parent_id": str(getattr(row, f"{parent[0]}_id")) if parent else "institution",
        "status": "ARCHIVED" if row.archived else "ACTIVE",
        "revision": str(row.revision),
    }


def audit(actor, kind, row, previous=None):
    record_event(
        actor=actor,
        action="academics.structure.changed",
        target_id=row.pk,
        previous_value=previous,
        new_value=snapshot(kind, row),
        reason="administrative_change",
    )


def save(row):
    row.full_clean()
    row.save()


@transaction.atomic
def create(*, actor, kind, label, name, parent_id=None):
    lock_privilege_changes()
    require_permission(actor, "system.manage")
    if kind not in MODELS:
        raise ValidationError("Unknown structure type.")
    label, name = validate_text(label, name)
    fields = {"label": label, "name": name}
    if kind in PARENTS:
        field, model = PARENTS[kind]
        parent = model.objects.select_for_update().get(pk=parent_id)
        require_active(parent)
        fields[field] = parent
    elif parent_id is not None:
        raise ValidationError("Departments belong directly to the institution.")
    row = MODELS[kind](**fields)
    save(row)
    audit(actor, kind, row)
    if kind == "batches":
        section = Section(batch=row, label="ALL", name="Whole batch")
        save(section)
        audit(actor, "sections", section)
    return row


@transaction.atomic
def change(*, actor, kind, pk, expected_revision, label=None, name=None, archive=False):
    lock_privilege_changes()
    require_permission(actor, "system.manage")
    if kind not in MODELS:
        raise ValidationError("Unknown structure type.")
    row = MODELS[kind].objects.select_for_update().get(pk=pk)
    if type(expected_revision) is not int or row.revision != expected_revision:
        raise StructureConflict("Structure changed. Reload before reviewing.")
    if isinstance(row, Section) and row.label == "ALL":
        if archive or label is None or label.strip().upper() != "ALL":
            raise ValidationError(
                "The reserved ALL section is retained; archive its batch instead."
            )
    if archive and row.archived:
        return row
    previous = snapshot(kind, row)
    if archive:
        row.archived = True
    else:
        require_active(row)
        row.label, row.name = validate_text(label, name)
        if isinstance(row, Section) and row.label == "ALL" and previous["label"] != "ALL":
            raise ValidationError("ALL is reserved for the whole-batch section.")
    row.revision += 1
    save(row)
    audit(actor, kind, row, previous)
    return row


def require_assignment_context(*, department_id, batch_id, term_id, section_id):
    """Future assignment writers call inside their transaction before persisting.

    Shares the archive lock until the caller commits. This validates structure,
    not caller permission or an offering/course relation owned by S013/S014.
    """
    if not transaction.get_connection().in_atomic_block:
        raise transaction.TransactionManagementError("An assignment transaction is required.")
    lock_privilege_changes()
    batch = Batch.objects.select_related("department").get(pk=batch_id)
    term = Term.objects.get(pk=term_id)
    section = Section.objects.get(pk=section_id)
    if (
        batch.department_id != department_id
        or term.batch_id != batch.pk
        or section.batch_id != batch.pk
    ):
        raise ValidationError("Department, batch, term and section must share their parents.")
    for row in (batch, term, section):
        require_active(row)
    return batch, term, section
