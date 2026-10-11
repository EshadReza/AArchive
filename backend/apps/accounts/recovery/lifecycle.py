"""Administrator-only lifecycle commands. Anonymization belongs to S084."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.access.policy import require_permission
from apps.access.services import MUTATION_REASONS, lock_privilege_changes
from apps.accounts.enums import AUTHENTICATABLE_STATES
from apps.accounts.models import EmailVerification, Invitation, PasswordReset, User
from apps.audit.services import record_event

from .sessions import revoke_sessions

CLOSED = {"SUSPENDED", "ARCHIVED"}
TRANSITIONS = {
    "activate": ({"INACTIVE"}, "ACTIVE"),
    "inactivate": ({"ACTIVE"}, "INACTIVE"),
    "graduate": ({"ACTIVE", "INACTIVE"}, "GRADUATED"),
    "alumni": ({"ACTIVE", "INACTIVE", "GRADUATED"}, "ALUMNI"),
    "suspend": ({"PENDING", *AUTHENTICATABLE_STATES, "ARCHIVED"}, "SUSPENDED"),
    "archive": ({"PENDING", *AUTHENTICATABLE_STATES, "SUSPENDED"}, "ARCHIVED"),
}


class StateConflict(ValidationError):
    pass


@transaction.atomic
def transition(*, actor, subject_id, command, expected_state, reason):
    lock_privilege_changes()
    require_permission(actor, "users.manage")
    if reason not in MUTATION_REASONS:
        raise ValidationError("A supported reason is required.")
    user = User.objects.select_for_update().get(pk=subject_id)
    if user.state != expected_state:
        raise StateConflict("The account state changed. Refresh before retrying.")
    if user.state == "ANONYMIZED":
        raise ValidationError("Anonymized accounts cannot be changed.")
    previous = user.state
    if command == "approve":
        if previous != "PENDING" or not user.approval_required:
            raise ValidationError("This account does not require pending approval.")
        if user.approved_at is not None:
            return user
        user.approved_at = timezone.now()
        if user.email_verified_at is not None:
            user.state = "ACTIVE"
        record_event(
            actor=actor,
            action="accounts.approval.recorded",
            target_id=user.pk,
            new_value={"outcome": "approved"},
            reason=reason,
        )
    elif command == "restore":
        if previous not in CLOSED or user.state_before_restriction not in {
            "PENDING",
            *AUTHENTICATABLE_STATES,
        }:
            raise ValidationError("No restorable prior state is recorded.")
        user.state = user.state_before_restriction
        user.state_before_restriction = ""
    elif command in TRANSITIONS:
        sources, target = TRANSITIONS[command]
        if previous not in sources:
            raise ValidationError("This transition is not allowed.")
        user.state = target
        if target in CLOSED and previous not in CLOSED:
            user.state_before_restriction = previous
    else:
        raise ValidationError("Unknown lifecycle command.")
    if user.state in AUTHENTICATABLE_STATES and not user.is_login_eligible:
        raise ValidationError("Verification and approval must be complete.")
    if user.state in CLOSED:
        if user.role_assignments.filter(role="ADMINISTRATOR").exists() and not (
            User.objects.eligible_for_authentication()
            .filter(role_assignments__role="ADMINISTRATOR")
            .exclude(pk=user.pk)
            .exists()
        ):
            raise ValidationError("The last eligible Administrator cannot be restricted.")
        revoke_sessions(user)
        PasswordReset.objects.filter(user=user).update(expires_at=timezone.now())
        Invitation.objects.filter(user=user).update(expires_at=timezone.now())
        EmailVerification.objects.filter(user=user).update(expires_at=timezone.now())
        record_event(
            actor=actor,
            action="auth.sessions.revoked",
            target_id=user.pk,
            new_value={"outcome": "lifecycle"},
            reason=reason,
        )
    user.save(update_fields=["state", "state_before_restriction", "approved_at", "updated_at"])
    if user.state != previous:
        record_event(
            actor=actor,
            action="accounts.state.changed",
            target_id=user.pk,
            previous_value={"state": previous},
            new_value={"state": user.state},
            reason=reason,
        )
    return user
