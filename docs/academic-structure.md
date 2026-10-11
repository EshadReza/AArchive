# Academic structure (S012)

Implemented for ADMIN-010, SRS 13/16.2/43/44 and D03/ADR 0002.
[S012 evidence](sprints/S012.md) records verification. Courses and offerings remain
S013/S014; this feature introduces no enrollment, course catalog or contest links.

## Browser walkthrough

Apply migrations and run Django/Vite using the root [local setup](../README.md#local-setup).
Sign in as an eligible Administrator and choose **Manage academic structure** from
`/account`, or open `/admin/structure`.

1. Under **Departments**, create a label and name, for example `CSE` / `Computing`.
2. Switch to **Batches**, choose that department and create `2026` / `Class 2026`.
   Every batch automatically receives a reserved `ALL` / `Whole batch` section.
3. Switch to **Terms** or **Sections**, choose the batch, and create its semester or
   named subdivision. Labels are unique within each parent, case-insensitively
   through canonical uppercase storage. Sections belong to batches across terms.
4. Choose **Edit** to change a label/name. Parent links are fixed after creation.
5. Choose **Archive**, review the affected record and consequences, then confirm.
   The record remains visible. Descendants show **Parent archived** and cannot
   receive new assignments or edits. No academic records are deleted.

Lists and parent pickers are paginated. Select **Limit to selected parent** and
apply filters to narrow a child list. Archive filtering distinguishes a record's
own flag from inherited unavailability. Reserved `ALL` cannot be renamed or archived
individually; archive its batch to retire it. Additional named sections do not delete
`ALL`, which may already be referenced by historical whole-batch offerings later.
There is no restore or hard-delete endpoint in this sprint.

## API

The four route families are `/api/departments`, `/api/batches`, `/api/terms` and
`/api/sections`. They all require a current eligible Administrator through the
central `system.manage` guard, including reads. Teacher offering selection can gain
an explicitly scoped projection in its own sprint; these management APIs do not
implicitly become public. Unknown IDs do not bypass authorization.

| Method | Path (replace `{family}`) | Exact JSON input / result |
|---|---|---|
| GET / HEAD | `/api/{family}` | Paginated `{count, next, previous, results}` |
| POST | `/api/{family}` | `{label, name}` plus `department_id` for batches or `batch_id` for terms/sections; 201 record |
| GET / HEAD | `/api/{family}/{uuid}` | 200 record, including archived history |
| PATCH | `/api/{family}/{uuid}` | `{label, name, expected_revision}`; 200 updated record |
| POST | `/api/{family}/{uuid}/archive` | `{expected_revision}`; 200 archived record |

A record contains `id`, `label`, `name`, `archived`, `available`, `revision`, and for
children the appropriate parent UUID and `parent_label` (department label, or
`department / batch`). `available` is false if this record or an ancestor is archived.
No user credentials, roles or source data appear in these projections.

List parameters: `page` (positive integer), `page_size` (default 25, maximum 100),
`archived=true|false` and the family's parent UUID field where applicable. Stable
ordering is label then UUID. Unknown/duplicate parameters, invalid UUIDs, negative
or malformed pagination and unexpected body fields return 400. All responses use
`Cache-Control: no-store`; all writes use existing same-origin session/CSRF protection
and the bounded 8 KiB JSON parser. Read paths have no trailing slash.

Labels are trimmed, converted to uppercase, 1–64 characters; names are trimmed,
1–200 characters. Control characters are rejected. Labels are unique institution-wide
for departments, department-wide for batches, and batch-wide independently for terms
and sections. Archived labels remain reserved. `expected_revision` must be a positive
JSON integer, not a boolean/string. Parent/state/revision mass assignment is rejected.

Stale review revisions return 409 `structure_conflict`. Invalid input, duplicate
labels detected during validation, reserved-ALL operations and archived structure
edits return safe 400 `structure_invalid`; database conflicts return safe 409.
Unauthorized requests return 403 before lookup, missing authorized resources 404,
and unsupported methods 405 after authentication/CSRF checks. Errors never contain
raw SQL, database exceptions or server paths. Reload after a conflict before retrying.

## Integrity and transactions

`academics.0001_initial` creates UUID Department, Batch, Term and Section rows with
label/name, direct archive flag, positive revision and creation/update timestamps.
Canonical/nonblank checks and parent-scoped uniqueness are database enforced.
Batch→Department and Term/Section→Batch use protected foreign keys. Department is
a root under the single institution; typed parent relationships cannot form cycles.

`academics.0002_protect_structure_parents` installs PostgreSQL update triggers that
reject any parent reassignment, including direct queryset updates, and protect the
reserved ALL label/archive state. Parents are immutable even before offerings exist,
so later references cannot silently move across departments or batches. Name/label
changes retain UUIDs. The trusted batch-creation service creates ALL and audits both
rows in the same transaction; failure rolls both back. Raw ORM insertion is a trusted
implementation/migration path, not the public provisioning interface.

All writes take the existing singleton privilege lock before row locks, recheck
Administrator permission, validate current archive/revision state and commit audit
with the mutation. Archive does not cascade flags or delete descendants. Availability
is derived through ancestors, so historical rows stay readable without enabling new
assignments. This intentionally serializes low-volume structure/privilege writes.

Future assignment services **must call**
`apps.academics.structure.services.require_assignment_context` inside their enclosing
transaction before persisting a structural association. It requires department,
batch, term and section UUIDs, checks same-parent membership and all archive gates,
and takes the same privilege lock until the outer transaction commits. Calling it
outside a transaction fails. It does not authorize the actor or validate a Course;
S013/S014 must add those requirements and their database relationship constraints.
Returning validated IDs and committing before writing would lose the archive-race
protection and is not supported. Historical reads do not call this active-only gate.

`academics.structure.changed` audit events retain explicit previous/new kind,
label/name, parent UUID, ACTIVE/ARCHIVED status and revision, with the actor and fixed
administrative reason. This is reviewed bounded academic metadata, not arbitrary
request JSON. Every creation/edit/archive and automatic ALL creation is audited;
audit failure rolls back business writes. Repeating archive with the current revision
is a no-op; stale archive reviews still conflict.

## Migration and operational boundaries

Reversal drops academic rows and then their triggers; it was verified only against
an empty disposable database. Use forward repairs and backups once real records or
future offering references exist. Archiving is the supported retirement operation.
No new environment variables, external services, real institutional records, or
production deployment are required for this sprint.
