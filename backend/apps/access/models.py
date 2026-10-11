import uuid

from django.conf import settings
from django.db import models

from .enums import CAPABILITY_SCOPES, Capability, ResourceKind


class PrivilegeLock(models.Model):
    """One seeded row serializes role/grant edits and first-admin bootstrap."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="one_privilege_lock")]


class ScopedGrant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="scoped_grants"
    )
    capability = models.CharField(max_length=40, choices=Capability)
    scope_kind = models.CharField(max_length=20, choices=ResourceKind)
    scope_id = models.UUIDField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "capability", "scope_kind", "scope_id"],
                name="one_scoped_capability",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    *[
                        models.Q(capability=capability, scope_kind=kind)
                        for capability, kind in CAPABILITY_SCOPES.items()
                    ],
                    _connector=models.Q.OR,
                ),
                name="grant_capability_scope_known",
            ),
        ]
        indexes = [
            models.Index(
                fields=["subject", "capability", "active"], name="grant_subject_cap_active"
            )
        ]
