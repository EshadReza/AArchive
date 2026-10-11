"""Reviewed event schemas. Add fields here with their owning feature's tests.

No arbitrary text/dictionaries are copied into audit payloads. Unknown fields are
omitted, including their names; known fields must match their bounded vocabulary.
"""

import json
import re
from uuid import UUID

from django.core.exceptions import ValidationError

from apps.access.enums import Capability, ResourceKind
from apps.accounts.enums import AccountState, PlatformRole


def canonical_uuid(value):
    try:
        return str(UUID(value)) == value
    except ValueError, TypeError, AttributeError:
        return False


MAX_PAYLOAD_BYTES = 8192
REASONS = frozenset(
    {"", "administrative_change", "user_request", "graduation", "security_response", "scheduled"}
)
CHANNELS = frozenset({"", "browser", "worker", "management_command"})
SYSTEM_ACTORS = frozenset({"maintenance", "scheduler", "bootstrap", "authentication"})
# action -> (target type, field -> (allowed values, is list))
EVENTS = {
    "academics.offering.changed": (
        "academics.offering",
        {
            "course_id": (canonical_uuid, False),
            "batch_id": (canonical_uuid, False),
            "term_id": (canonical_uuid, False),
            "section_id": (canonical_uuid, False),
            "name": (
                lambda v: 1 <= len(v) <= 200 and v == v.strip() and all(ord(c) >= 32 for c in v),
                False,
            ),
            "status": (("ACTIVE", "ARCHIVED"), False),
            "revision": (
                lambda v: len(v) <= 10 and v.isascii() and v.isdigit() and 0 < int(v) <= 2147483647,
                False,
            ),
        },
    ),
    "academics.teacher.changed": (
        "academics.teacher_assignment",
        {
            "offering_id": (canonical_uuid, False),
            "teacher_id": (canonical_uuid, False),
            "status": (("ASSIGNED", "ENDED"), False),
        },
    ),
    "academics.course.changed": (
        "academics.course",
        {
            "department_id": (canonical_uuid, False),
            "code": (
                lambda v: (
                    1 <= len(v) <= 64 and v == v.strip().upper() and all(ord(c) >= 32 for c in v)
                ),
                False,
            ),
            "title": (
                lambda v: 1 <= len(v) <= 200 and v == v.strip() and all(ord(c) >= 32 for c in v),
                False,
            ),
            "credits": (lambda v: re.fullmatch(r"[0-9]{1,2}\.[0-9]{2}", v) is not None, False),
            "description_digest": (lambda v: re.fullmatch(r"[0-9a-f]{64}", v) is not None, False),
            "status": (("ACTIVE", "ARCHIVED"), False),
            "revision": (
                lambda v: len(v) <= 10 and v.isascii() and v.isdigit() and 0 < int(v) <= 2147483647,
                False,
            ),
        },
    ),
    "academics.structure.changed": (
        "academics.structure",
        {
            "kind": (("departments", "batches", "terms", "sections"), False),
            "label": (
                lambda v: (
                    1 <= len(v) <= 64
                    and v == v.strip().upper()
                    and all(ord(c) >= 32 and ord(c) != 127 for c in v)
                ),
                False,
            ),
            "name": (
                lambda v: (
                    1 <= len(v) <= 200
                    and v == v.strip()
                    and all(ord(c) >= 32 and ord(c) != 127 for c in v)
                ),
                False,
            ),
            "parent_id": (lambda v: v == "institution" or canonical_uuid(v), False),
            "status": (("ACTIVE", "ARCHIVED"), False),
            "revision": (lambda v: v.isascii() and v.isdigit() and 0 < int(v) <= 2147483647, False),
        },
    ),
    "accounts.admin.created": ("accounts.user", {"state": (("PENDING",), False)}),
    "accounts.invitation.issued": ("accounts.user", {"outcome": (("issued",), False)}),
    "accounts.invitation.accepted": ("accounts.user", {"outcome": (("accepted",), False)}),
    "accounts.profile.changed": ("accounts.user", {"outcome": (("updated",), False)}),
    "auth.recovery.failed": (
        "system",
        {"outcome": (("invalid_token", "invalid_credentials"), False)},
    ),
    "auth.recovery.limited": ("system", {"outcome": (("temporary_lockout",), False)}),
    "auth.reset.issued": ("accounts.user", {"outcome": (("issued",), False)}),
    "auth.password.changed": ("accounts.user", {"outcome": (("reset", "changed"), False)}),
    "auth.sessions.revoked": (
        "accounts.user",
        {"outcome": (("password_change", "lifecycle"), False)},
    ),
    "accounts.approval.recorded": ("accounts.user", {"outcome": (("approved",), False)}),
    "auth.registration.created": ("accounts.user", {"state": (("PENDING",), False)}),
    "auth.verification.issued": ("accounts.user", {"outcome": (("issued",), False)}),
    "auth.verification.completed": ("accounts.user", {"outcome": (("verified",), False)}),
    "auth.login.failed": ("system", {"outcome": (("invalid_credentials",), False)}),
    "auth.login.locked": ("system", {"outcome": (("temporary_lockout",), False)}),
    "auth.login.succeeded": ("accounts.user", {"outcome": (("succeeded",), False)}),
    "auth.session.ended": ("accounts.user", {"outcome": (("logout", "revoked"), False)}),
    "accounts.state.changed": ("accounts.user", {"state": (AccountState.values, False)}),
    "accounts.roles.changed": ("accounts.user", {"roles": (PlatformRole.values, True)}),
    "access.grant.changed": (
        "access.grant",
        {
            "subject_id": (canonical_uuid, False),
            "capability": (Capability.values, False),
            "scope_kind": (ResourceKind.values, False),
            "scope_id": (canonical_uuid, False),
            "status": (("GRANTED", "REVOKED"), False),
        },
    ),
    "system.maintenance.completed": (
        "system",
        {"operation": (("integrity_check", "retention_review"), False)},
    ),
}


def project_payload(action, value):
    """Return a detached safe projection; never stringify untrusted values/errors."""
    if action not in EVENTS:
        raise ValidationError("Unregistered audit action.")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValidationError("Audit values must be objects or null.")
    result = {}
    for field, (choices, multiple) in EVENTS[action][1].items():
        if field not in value:
            raise ValidationError("Missing required audit field.")
        item = value[field]
        if multiple:
            if (
                not isinstance(item, list)
                or len(item) > len(choices)
                or any(not isinstance(v, str) or v not in choices for v in item)
                or len(set(item)) != len(item)
            ):
                raise ValidationError("Invalid audit field value.")
            result[field] = list(item)
        else:
            if not isinstance(item, str) or not (
                choices(item) if callable(choices) else item in choices
            ):
                raise ValidationError("Invalid audit field value.")
            result[field] = item
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValidationError("Audit payload exceeds its size limit.")
    return result
