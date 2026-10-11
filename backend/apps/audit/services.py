"""Trusted internal logging, not an authorization or mutation service."""

from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AuditLog
from .policy import EVENTS


@dataclass(frozen=True)
class AuditContext:
    # Supply a server-generated correlation UUID and an explicitly approved IP.
    # Never derive these from raw session IDs, cookies or forwarded headers here.
    request_id: UUID | None = None
    ip: str | None = None
    channel: str = ""


def record_event(
    *,
    action,
    target_id,
    actor=None,
    system_actor="",
    previous_value=None,
    new_value=None,
    reason="",
    context=None,
    using="default",
):
    """Append in the caller's business transaction; propagate failures to its owner.

    Authentication/authorization and locks belong to the caller. Failed-login and
    other standalone security events should open their own explicit atomic block.
    """
    if not transaction.get_connection(using).in_atomic_block:
        raise transaction.TransactionManagementError("Audit recording requires an atomic block.")
    if action not in EVENTS:
        raise ValidationError("Unregistered audit action.")
    target_type = EVENTS[action][0]
    if target_type in {
        "accounts.user",
        "access.grant",
        "academics.structure",
        "academics.course",
        "academics.offering",
        "academics.teacher_assignment",
    }:
        try:
            target_id = str(UUID(str(target_id)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValidationError("Invalid audit target identifier.") from exc
    elif target_id != "system":
        raise ValidationError("Invalid system target identifier.")
    if actor is not None and (actor._state.adding or actor._state.db != using):
        raise ValidationError("Audit actor must exist on the transaction database.")
    context = context or AuditContext()
    if not isinstance(context, AuditContext):
        raise ValidationError("Use explicit audit context fields.")
    entry = AuditLog(
        actor=actor,
        system_actor=system_actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        previous_value=previous_value,
        new_value=new_value,
        reason=reason,
        request_id=context.request_id,
        ip=context.ip,
        channel=context.channel,
    )
    entry.save(using=using, force_insert=True)
    return entry
