# Audit service and coverage contract

Implemented in S006. Requirements: SRS Sections 18, 20, 42 and 45; D02.
The service records events; each owning feature must authorize its mutation,
lock/read current state, and call the service in that mutation's transaction.
No account mutation, maintenance job, or authentication workflow is implicitly
implemented by defining its event schema.

## Recording contract

Use `apps.audit.services.record_event` inside `transaction.atomic()` on the same
database as the protected mutation. Recording in autocommit is rejected. Propagate
validation/database failures out of the business transaction; never catch and
suppress an audit failure and then commit the business change. Do not use
`on_commit()` to write audit records: that would split their atomicity.

```python
from django.db import transaction
from apps.audit.services import record_event

# Inside an authorized, locked account-state service (owned by S010):
with transaction.atomic():
    # Validate transition, capture previous state, then persist the mutation.
    record_event(
        actor=actor,
        action="accounts.state.changed",
        target_id=subject.pk,
        previous_value={"state": previous_state},
        new_value={"state": subject.state},
        reason="administrative_change",
    )
```

`actor` is a saved platform User on the transaction database. Alternatively pass
no user and one registered `system_actor`: `maintenance`, `scheduler`, or the
S007 operator-only `bootstrap`, or S008 `authentication`. Exactly
one actor form is required, including at the database level. Deleted accounts are
represented by retained ANONYMIZED Users, whose UUID references remain valid.
The actor FK uses PROTECT; logs never copy actor email, name, or credentials.
Targets are typed identifiers rather than cascading foreign keys, so target
removal does not remove the audit record. Account target IDs are canonical UUIDs;
the system target is the literal `system`.

`AuditContext` accepts only an optional server-generated request UUID, an optional
validated IP address, and a channel (`browser`, `worker`, `management_command`,
or blank). IP defaults to NULL: callers must deliberately enable it under the
deployment's privacy policy. No automatic request/header capture occurs. Raw
session IDs, cookies, Authorization, user agents, forwarded headers, request
bodies and query strings are never accepted as metadata. Channel provides coarse
device/execution context without recording arbitrary browser strings.

## Reviewed events and redaction

Use lowercase dotted `domain.subject.past_tense_action` names. Event schemas live
in `backend/apps/audit/policy.py`; unregistered actions are rejected. Current
schemas provide integration points for upcoming features:

| Action | Target type | Allowed before/after fields |
|---|---|---|
| `accounts.state.changed` | `accounts.user` | `state`: one of the eight account states |
| `accounts.roles.changed` | `accounts.user` | `roles`: at most three distinct fixed platform roles |
| `access.grant.changed` (S007) | `access.grant` | `subject_id`, `scope_id`: canonical UUIDs; `capability`, `scope_kind`: fixed vocabularies; `status`: GRANTED/REVOKED |
| `auth.reset.issued` | `accounts.user` | `outcome`: `issued` |
| `auth.password.changed` | `accounts.user` | `outcome`: `reset` or `changed` |
| `auth.sessions.revoked` | `accounts.user` | `outcome`: `password_change` or `lifecycle` |
| `auth.recovery.failed` | `system` | `outcome`: `invalid_token` or `invalid_credentials` |
| `auth.recovery.limited` | `system` | `outcome`: `temporary_lockout` |
| `accounts.approval.recorded` | `accounts.user` | `outcome`: `approved` |
| `auth.registration.created` | `accounts.user` | `state`: `PENDING` |
| `auth.verification.issued` | `accounts.user` | `outcome`: `issued` |
| `auth.verification.completed` | `accounts.user` | `outcome`: `verified` |
| `auth.login.failed` | `system` | `outcome`: `invalid_credentials` |
| `auth.login.locked` | `system` | `outcome`: `temporary_lockout` |
| `auth.login.succeeded` | `accounts.user` | `outcome`: `succeeded` |
| `auth.session.ended` | `accounts.user` | `outcome`: `logout` or `revoked` |
| `system.maintenance.completed` | `system` | `operation`: `integrity_check` or `retention_review` |

Each previous/new value is null or an object containing the schema's required
field. Unknown fields and their names are omitted entirely; nested unknown
objects are not traversed or serialized. Known fields use bounded vocabularies,
not arbitrary text. Wrong types, missing required fields and invalid values fail
the write. Projections are detached copies and capped at 8 KiB each after UTF-8
JSON encoding. Current schemas are substantially smaller than this cap. The API
reapplies the safe projection before serializing historical payloads; malformed
payloads become null rather than echoing unsafe content.

Reasons are controlled codes: blank, `administrative_change`, `user_request`,
`graduation`, `security_response`, or `scheduled`. This avoids copying credentials
embedded in arbitrary text into an immutable log. Future reason/schema expansion
must explicitly define privacy-safe values and tests; do not pass model `__dict__`,
serializer output, imported records or raw exception messages wholesale.
Feature services must provide the required safe change fields deliberately.

## Integrity and migrations

`AuditLog` has an integer sequence ID, actor/system actor, action, target type/ID,
previous/new JSON, reason, explicit context, and timestamp. Indexes cover
target/type/time, actor/time, action/time, and time. IDs are stable and unique;
the read API orders by descending ID rather than relying on tied timestamps.
Sequence order is allocation order, not a guarantee of transaction commit order.
Pagination is a live feed, not a snapshot/export or reliable event-delivery queue.

ORM save/update/delete/bulk-update paths reject mutation; bulk insertion is
disabled in favor of the audited service. PostgreSQL's `audit_append_only` trigger
rejects UPDATE/DELETE even through raw SQL. Corrections must append another
registered event. This is not cryptographic tamper evidence or protection against
a database owner: DDL, trigger disabling and TRUNCATE are privileged operational
capabilities. Production database role restrictions and recovery are S090/S093.

`audit.0001_initial` creates the table, indexes, FK and actor constraint;
`0002_append_only` installs the function/trigger. Both were applied, reversed on
an empty disposable database and reapplied while preserving account tables.
Run the README migration command. After real records exist, use forward repair
migrations and tested backups; reversing audit migrations would remove evidence.

## Read API

`GET /api/audit` and `GET /api/audit/{id}` are implemented; HEAD is also supported.
Only current eligible Administrators may read the global audit scope. Teachers,
Students (even the event actor), anonymous callers and closed accounts receive
403 before any target lookup. The permission queries current database state and
roles, so a stale authenticated User cannot retain a removed role. No source role
or Django staff flag grants access. S007 now uses the shared authorization guard
and queryset filter without widening the scope. See [access integration](access.md).

S008 installs real session authentication and verifies Administrator access,
non-Administrator denial, logout and forbidden-state revocation. Existing policy
tests also use injected actors to exercise the full role/state matrix.
Authentication failure/threshold events use only safe outcomes and the system
actor; they never copy attempted email, password, peer IP or session identifiers.

The list returns `{results, next, previous}` with no expensive total count.
`page_size` defaults to 50 and is capped at 100; `cursor` is opaque, limited to
1024 characters, and its position must fit a positive 64-bit ID. Invalid cursors
return 404. Returned links preserve pagination parameters. There are no client
scope selectors, sorting controls or event filters yet. Detail returns the same
record shape; inaccessible callers cannot distinguish a missing record.

```json
{
  "id": 1,
  "actor_id": "00000000-0000-0000-0000-000000000001",
  "system_actor": "",
  "action": "accounts.state.changed",
  "target_type": "accounts.user",
  "target_id": "00000000-0000-0000-0000-000000000002",
  "previous_value": {"state": "ACTIVE"},
  "new_value": {"state": "ALUMNI"},
  "reason": "graduation",
  "request_id": null,
  "ip": null,
  "channel": "",
  "created_at": "2026-10-07T00:00:00Z"
}
```

POST/PUT/PATCH/DELETE have no handlers and return 405 for permitted readers.
Responses, including permission errors, use `Cache-Control: no-store`. Expected
errors have `{code, message, request_id: null}`; full request correlation middleware
is deferred. These local errors follow the planned API envelope without changing
health or future endpoints. No dashboard or event backfill is included.

## Coverage checklist for feature owners

Register each action and its explicit safe schema in the same sprint as its
mutation. Verify success and failure transactions, current authorization, required
reason, credential exclusion and payload limits. Do not claim an event is emitted
merely because its category is listed below.

| Category | Integration owner | Current status |
|---|---|---|
| Roles, scoped permissions | S007 | Implemented atomic role/grant changes and first-admin bootstrap; S011 exposes reviewed role writes over HTTP |
| Login failures, lockouts, success and session end | S008 | Implemented; failed attempts commit independently, successful login/logout commit with their audit event |
| Registration and email verification | S009 | Implemented transactional account creation, challenge issue/rotation and verification; activation uses state-change event |
| Password reset/change and lifecycle | S010 | Implemented challenge issue, credential change, generic failure/threshold, approval and revocation events; mutations and audit commit atomically |
| Admin creation, invitations and own profile | S011 | Implemented atomic creation, challenge issue/acceptance and fixed-outcome profile audit; credentials and raw profile text excluded |
| Bulk account operations | S016 | Pending |
| Academic structure create/edit/archive | S012 | Implemented atomic before/after bounded academic metadata, parent UUID and revision; includes automatic ALL creation |
| Enrollment/teacher assignment | S014-S016 | Pending |
| Groups and visibility | S018-S020 | Pending |
| Upload/import/re-import and identity mappings | S027-S045, S064-S067 | Pending |
| Mark assignment/override/publish/lock/unlock/correction | S053-S061, S067 | Pending |
| Administrative settings and deletion/anonymization | S082-S084 | Pending |
| Coverage inventory, operational integrity/recovery | S085, S090-S093 | Pending |

The durable outbox/event delivery is S023. Audit rows are not an asynchronous job
queue, and logging a request is not proof its external side effects succeeded.
