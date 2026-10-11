from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from .policy import CHANNELS, EVENTS, REASONS, SYSTEM_ACTORS, project_payload


class AppendOnlyError(ValueError):
    pass


class AuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AppendOnlyError("Audit entries cannot be updated.")

    def delete(self):
        raise AppendOnlyError("Audit entries cannot be deleted.")

    def bulk_update(self, *args, **kwargs):
        raise AppendOnlyError("Audit entries cannot be updated.")

    def bulk_create(self, *args, **kwargs):
        raise AppendOnlyError("Use the transactional audit service.")


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_entries",
    )
    system_actor = models.CharField(max_length=32, blank=True)
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64)
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    reason = models.CharField(max_length=64, blank=True)
    request_id = models.UUIDField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    channel = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    objects = AuditQuerySet.as_manager()

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(
                fields=["target_type", "target_id", "created_at"], name="audit_target_time"
            ),
            models.Index(fields=["actor", "created_at"], name="audit_actor_time"),
            models.Index(fields=["action", "created_at"], name="audit_action_time"),
            models.Index(fields=["created_at"], name="audit_time"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(actor__isnull=False, system_actor="")
                    | (models.Q(actor__isnull=True) & ~models.Q(system_actor=""))
                ),
                name="audit_exactly_one_actor",
            ),
        ]

    def clean(self):
        super().clean()
        if self.action not in EVENTS or self.target_type != EVENTS[self.action][0]:
            raise ValidationError("Invalid audit action or target type.")
        if self.reason not in REASONS or self.channel not in CHANNELS:
            raise ValidationError("Invalid audit reason or channel.")
        if self.system_actor and self.system_actor not in SYSTEM_ACTORS:
            raise ValidationError("Invalid system actor.")
        self.previous_value = project_payload(self.action, self.previous_value)
        self.new_value = project_payload(self.action, self.new_value)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AppendOnlyError("Audit entries cannot be updated.")
        using = kwargs.get("using") or "default"
        if not transaction.get_connection(using).in_atomic_block:
            raise transaction.TransactionManagementError(
                "Audit recording requires an atomic block."
            )
        # Remove unknown input before Django's JSON validation traverses it.
        self.previous_value = project_payload(self.action, self.previous_value)
        self.new_value = project_payload(self.action, self.new_value)
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyError("Audit entries cannot be deleted.")
