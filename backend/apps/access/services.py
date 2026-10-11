"""Explicit admin commands. All privilege edits take the singleton lock first."""

from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.enums import AccountState, PlatformRole
from apps.accounts.models import User, UserRole
from apps.audit.services import record_event

from .enums import CAPABILITY_SCOPES
from .models import PrivilegeLock, ScopedGrant
from .policy import ResourceRef, require_permission, scope_exists

MUTATION_REASONS = frozenset({"administrative_change", "user_request", "security_response"})


def lock_privilege_changes():
    """Inside atomic(), acquire this BEFORE account/resource locks (also for S010)."""
    PrivilegeLock.objects.select_for_update().get(pk=1)


def _reason(reason):
    if not isinstance(reason, str) or reason not in MUTATION_REASONS:
        raise ValidationError("A supported nonempty reason is required.")


def _subject(subject_id):
    subject = User.objects.select_for_update().get(pk=subject_id)
    if subject.state == AccountState.ANONYMIZED:
        raise ValidationError("Anonymized account privileges cannot be changed.")
    return subject


@transaction.atomic
def set_roles(*, actor, subject_id, roles, reason, context=None):
    lock_privilege_changes()
    require_permission(actor, "roles.manage")
    _reason(reason)
    if (
        not isinstance(roles, (list, tuple, set, frozenset))
        or not roles
        or len(roles) > 3
        or any(not isinstance(r, str) or r not in PlatformRole.values for r in roles)
        or len(set(roles)) != len(roles)
    ):
        raise ValidationError("Choose one or more distinct fixed platform roles.")
    subject = _subject(subject_id)
    previous = set(subject.role_assignments.values_list("role", flat=True))
    selected = set(roles)
    if previous == selected:
        return subject
    if PlatformRole.ADMINISTRATOR in previous and PlatformRole.ADMINISTRATOR not in selected:
        if (
            not User.objects.eligible_for_authentication()
            .filter(
                role_assignments__role=PlatformRole.ADMINISTRATOR,
            )
            .exclude(pk=subject.pk)
            .exists()
        ):
            raise ValidationError("The last eligible Administrator cannot be removed.")
    subject.role_assignments.exclude(role__in=selected).delete()
    for role in selected - previous:
        UserRole.objects.create(user=subject, role=role)
    record_event(
        actor=actor,
        action="accounts.roles.changed",
        target_id=subject.pk,
        previous_value={"roles": sorted(previous)},
        new_value={"roles": sorted(selected)},
        reason=reason,
        context=context,
    )
    if PlatformRole.TEACHER in previous and PlatformRole.TEACHER not in selected:
        for grant in subject.scoped_grants.filter(active=True):
            before = _grant_value(grant)
            grant.active = False
            grant.save(update_fields=["active", "updated_at"])
            record_event(
                actor=actor,
                action="access.grant.changed",
                target_id=grant.pk,
                previous_value=before,
                new_value=_grant_value(grant),
                reason=reason,
                context=context,
            )
    return subject


def _grant_value(grant):
    return {
        "subject_id": str(grant.subject_id),
        "capability": grant.capability,
        "scope_kind": grant.scope_kind,
        "scope_id": str(grant.scope_id),
        "status": "GRANTED" if grant.active else "REVOKED",
    }


@transaction.atomic
def set_grant(*, actor, subject_id, capability, scope, active, reason, context=None):
    lock_privilege_changes()
    require_permission(actor, "roles.manage")
    _reason(reason)
    if (
        not isinstance(capability, str)
        or not isinstance(scope, ResourceRef)
        or CAPABILITY_SCOPES.get(capability) != scope.kind
        or type(active) is not bool
    ):
        raise ValidationError("Invalid capability, scope or activation flag.")
    if not isinstance(scope.pk, UUID):
        raise ValidationError("Delegated scope identifiers must be UUIDs.")
    subject = _subject(subject_id)
    if active and not subject.role_assignments.filter(role=PlatformRole.TEACHER).exists():
        raise ValidationError("Delegated capabilities require the Teacher role.")
    if active and not scope_exists(scope):
        raise ValidationError("Delegated scope must be registered and exist.")
    grant = ScopedGrant.objects.filter(
        subject=subject, capability=capability, scope_kind=scope.kind, scope_id=scope.pk
    ).first()
    if grant is None and not active:
        return None
    if grant is not None and grant.active == active:
        return grant
    previous = _grant_value(grant) if grant else None
    if grant is None:
        grant = ScopedGrant(
            subject=subject, capability=capability, scope_kind=scope.kind, scope_id=scope.pk
        )
    grant.active = active
    grant.full_clean()
    grant.save()
    record_event(
        actor=actor,
        action="access.grant.changed",
        target_id=grant.pk,
        previous_value=previous,
        new_value=_grant_value(grant),
        reason=reason,
        context=context,
    )
    return grant


@transaction.atomic
def bootstrap_administrator(*, subject_id):
    """Local operator only; never expose this function through a request handler."""
    lock_privilege_changes()
    if UserRole.objects.filter(role=PlatformRole.ADMINISTRATOR).exists():
        raise PermissionDenied("An Administrator already exists; use the authorized role service.")
    subject = _subject(subject_id)
    if not subject.is_login_eligible:
        raise ValidationError("Bootstrap requires an already verified, approved eligible account.")
    previous = list(subject.role_assignments.values_list("role", flat=True))
    UserRole.objects.create(user=subject, role=PlatformRole.ADMINISTRATOR)
    record_event(
        system_actor="bootstrap",
        action="accounts.roles.changed",
        target_id=subject.pk,
        previous_value={"roles": sorted(previous)},
        new_value={"roles": sorted([*previous, PlatformRole.ADMINISTRATOR])},
        reason="administrative_change",
    )
    return subject
