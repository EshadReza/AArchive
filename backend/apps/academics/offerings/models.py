import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Trim
from django.utils import timezone

from apps.academics.courses.models import Course
from apps.academics.structure.models import Batch, Section, Term


class Offering(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="offerings")
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="offerings")
    term = models.ForeignKey(Term, on_delete=models.PROTECT, related_name="offerings")
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="offerings")
    name = models.CharField(max_length=200)
    archived = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_offerings"
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "batch", "term", "section"], name="offering_unique_tuple"
            ),
            models.CheckConstraint(
                condition=models.Q(name=Trim("name")) & ~models.Q(name=""),
                name="offering_nonblank_name",
            ),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="offering_revision"),
        ]


class TeacherAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offering = models.ForeignKey(
        Offering, on_delete=models.PROTECT, related_name="teacher_assignments"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="offering_assignments"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="made_offering_assignments"
    )
    assigned_at = models.DateTimeField(default=timezone.now, editable=False)
    ended_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ended_offering_assignments",
    )

    class Meta:
        ordering = ["-assigned_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["offering", "teacher"],
                condition=models.Q(ended_at__isnull=True),
                name="offering_one_current_teacher",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(ended_at__isnull=True, removed_by__isnull=True)
                    | models.Q(
                        ended_at__isnull=False,
                        removed_by__isnull=False,
                        ended_at__gte=models.F("assigned_at"),
                    )
                ),
                name="assignment_end_pair",
            ),
        ]
