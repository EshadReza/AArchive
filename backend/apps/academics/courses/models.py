import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Trim, Upper

from apps.academics.structure.models import Department


class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="courses")
    code = models.CharField(max_length=64)
    title = models.CharField(max_length=200)
    credits = models.DecimalField(max_digits=4, decimal_places=2)
    description = models.TextField(blank=True, max_length=4000)
    archived = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department__label", "code", "id"]
        constraints = [
            models.UniqueConstraint(fields=["department", "code"], name="course_department_code"),
            models.CheckConstraint(
                condition=models.Q(code=Upper(Trim("code"))) & ~models.Q(code=""),
                name="course_canonical_code",
            ),
            models.CheckConstraint(
                condition=models.Q(title=Trim("title")) & ~models.Q(title=""),
                name="course_nonblank_title",
            ),
            models.CheckConstraint(
                condition=models.Q(credits__gte=0, credits__lte=99.99), name="course_credit_range"
            ),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="course_revision"),
        ]

    def clean(self):
        super().clean()
        if (
            not self._state.adding
            and type(self).objects.get(pk=self.pk).department_id != self.department_id
        ):
            raise ValidationError("Course department cannot change.")
