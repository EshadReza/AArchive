import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Trim, Upper


class Structure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=64)
    name = models.CharField(max_length=200)
    archived = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["label", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(label=Upper(Trim("label"))) & ~models.Q(label=""),
                name="%(class)s_canonical_label",
            ),
            models.CheckConstraint(
                condition=models.Q(name=Trim("name")) & ~models.Q(name=""),
                name="%(class)s_nonblank_name",
            ),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="%(class)s_revision"),
        ]

    def clean(self):
        super().clean()
        parent_field = "department" if isinstance(self, Batch) else "batch"
        if hasattr(self, f"{parent_field}_id") and not self._state.adding:
            previous = type(self).objects.get(pk=self.pk)
            if getattr(previous, f"{parent_field}_id") != getattr(self, f"{parent_field}_id"):
                raise ValidationError("Academic parents cannot be changed.")


class Department(Structure):
    class Meta(Structure.Meta):
        abstract = False
        constraints = [
            *Structure.Meta.constraints,
            models.UniqueConstraint(fields=["label"], name="department_unique_label"),
        ]


class Batch(Structure):
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="batches")

    class Meta(Structure.Meta):
        abstract = False
        constraints = [
            *Structure.Meta.constraints,
            models.UniqueConstraint(fields=["department", "label"], name="batch_parent_label"),
        ]


class Term(Structure):
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="terms")

    class Meta(Structure.Meta):
        abstract = False
        constraints = [
            *Structure.Meta.constraints,
            models.UniqueConstraint(fields=["batch", "label"], name="term_parent_label"),
        ]


class Section(Structure):
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="sections")

    class Meta(Structure.Meta):
        abstract = False
        constraints = [
            *Structure.Meta.constraints,
            models.UniqueConstraint(fields=["batch", "label"], name="section_parent_label"),
        ]
