# Course offerings and teacher assignments (S014)

Implements ADMIN-010 and COURSE-001, SRS 13/16.2/43/44, D03/D04.
An Offering is one run of a Course for a Batch, Term and Section. The same Course
can be reused in other terms. [Verification](sprints/S014.md) records the checks.

## Try the screens

Apply migrations using the [local setup](../README.md). An administrator first
creates an active department, batch, term and course. New batches already have an
ALL section; add a named section if needed. Sign in as an eligible Teacher or
Administrator, open **Account → Course offerings**, then choose the department,
course, batch, term and section and supply an offering name.

Creation attaches the creator automatically. Open an offering to edit its name
and read assignment history. Administrators can choose additional eligible staff,
review assignment/removal, or review and confirm archive. Removing a teacher takes
effect on their next server action, including an already-open editor. A stale
revision fails and requires reload. All pickers and lists support pagination.

No enrollment, assessment, marks or contest-management screen is included yet.

## Authorization

| Action | Eligible Administrator | Eligible Teacher | Student / anonymous / closed account |
|---|---|---|---|
| Create | Yes; creator assignment retained | Yes; creator assignment retained | Denied |
| List/detail/history | All offerings | Current assignments only | Denied |
| Edit name | Available offerings | Available, currently assigned offerings | Denied |
| Assign/remove staff | Yes | Denied | Denied |
| Archive | Yes | Denied | Denied |
| Eligible staff picker | Yes | Denied | Denied |
| Active academic selection options | Yes | Yes | Denied |

A current assignment has no `ended_at`; account eligibility and platform roles are
reloaded on every authorization call. An Admin-only creator is retained as staff
without receiving the Teacher platform role. Administrators retain global authority
when their own assignment ends. Removing the Teacher role blocks teacher rights,
but does not end its assignment records; restoring that role can restore rights to
still-current assignments. Explicit assignment removal ends that membership.

All current co-teachers have equal offering settings rights. Future assessment
policies must recheck current membership; special marks locking/unlocking still
needs its separate grant. Offering membership confers no global Contest authority,
restricted-source visibility, or enrollment access. These future actions deny until
implemented with their own policies.

Archived offerings and those with any archived course/department/batch/term/section
remain readable to currently assigned Teachers and Administrators. Settings edits,
new offerings and new assignments require active ancestry. Admin removal remains
possible on historical offerings and suspended/deactivated accounts. There is no
last-teacher restriction: an administrator can recover an unstaffed offering.

## API contract

All routes are same-origin, session authenticated, `Cache-Control: no-store`, with
CSRF required for writes. JSON keys are exact; unexpected fields fail. UUIDs are
strings, revisions positive integers, `active` a JSON boolean, names trimmed
nonblank text up to 200 characters with control characters rejected.

| Method | Path | Input / output |
|---|---|---|
| GET/HEAD | `/api/course-offerings` | Paginated scoped offering summaries |
| POST | `/api/course-offerings` | `course_id`, `batch_id`, `term_id`, `section_id`, `name`; 201 detail |
| GET/HEAD | `/api/course-offerings/{id}` | Scoped detail |
| PATCH | `/api/course-offerings/{id}` | `name`, `expected_revision`; updated detail |
| POST | `/api/course-offerings/{id}/archive` | `expected_revision`; updated detail |
| GET/HEAD | `/api/course-offerings/{id}/teachers` | Paginated current and ended assignment history |
| POST | `/api/course-offerings/{id}/teachers` | `teacher_id`, `active`, `expected_revision`; updated offering detail |
| GET/HEAD | `/api/course-offerings/staff-options` | Admin-only eligible Teacher/Admin UUID, email `label`, display `name` |
| GET/HEAD | `/api/course-offering-options/{departments,batches,terms,sections}` | Active academic selection metadata; no management rights |

Offering/history/staff lists accept only `page` and `page_size` (default 25, max
100); unknown or duplicate query keys and malformed positive numbers fail. The
academic options reuse the [structure list contract](academic-structure.md), adding
mandatory active-ancestor filtering. Batches accept `department_id`; Terms/Sections
accept `batch_id`. Course selection uses the existing filtered `/api/courses`.

Offering summaries include `id`, `name`, `course_id`, `course_code`, `course_title`,
`department_label`, `batch_id`, `batch_label`, `term_id`, `term_label`, `section_id`,
`section_label`, `archived`, `revision`, `created_by`. Detail adds `can_manage` and
`can_assign` as current UI hints; every write reauthorizes independently. A direct
archive flag does not describe ancestor availability; use `can_manage` for editing.

Assignment history includes `id`, `teacher_id`, `display_name`, ISO `assigned_at`,
nullable ISO `ended_at`, `assigned_by`, nullable `removed_by`. Emails are excluded
from history; the admin-only staff picker supplies them for selecting accounts.
Names reflect the current profile; immutable identities and effective dates retain
provenance. All text is rendered as text, not HTML.

Successful repeats of assignment/removal/archive with the **current** revision
are no-ops. Real changes increment the offering revision. A stale revision is 409
`offering_conflict`; malformed/domain-invalid input is 400 `offering_invalid`;
a database integrity conflict is 409; denied authority is 403. Missing or
invisible detail/history is 404. No DELETE, restore or tuple-edit operation exists.

## Persistence and transaction boundary

`Offering` holds protected Course/Batch/Term/Section/creator FKs. Its tuple is
unique even after archive. A PostgreSQL trigger checks Course.Department matches
Batch.Department and Term.Batch/Section.Batch match Offering.Batch. Another part of
that trigger makes tuple, UUID, creator and creation time immutable. Existing
academic-parent triggers prevent later reparenting from invalidating the tuple.

`TeacherAssignment` holds protected offering, teacher, assigner and remover FKs,
start/end timestamps, and UUID identity. A partial unique constraint allows only
one current row per offering/teacher. End time/remover must be both null or both
present, with end at/after start. A trigger prevents deletion, provenance edits and
reactivation of ended rows. Reassignment appends a fresh row. Offering deletion is
also protected by its retained assignments; only archive is exposed.

Creation, settings, archive and assignment services acquire the existing shared
privilege lock inside `transaction.atomic`, then refetch permissions, check revision,
validate context, persist and audit together. `require_course_context` runs within
that same transaction. Concurrent reviewed writes serialize; one wins and the
other receives a revision conflict. Audit failures roll back all related writes.
Removal ends the row and revokes active offering-scoped grants in that transaction;
reassignment does not reactivate those grants. S084 account anonymization must
coordinate grant/assignment retirement before making a subject terminal.

`academics.offering.changed` audits the tuple, name, ACTIVE/ARCHIVED status and
revision. `academics.teacher.changed` audits assignment identity and reviewed
`offering_id`, `teacher_id`, ASSIGNED/ENDED state. Actor/time come from the immutable
audit envelope. Grant revocations also have their existing access audit records.

Migrations `0005` and `0006` introduce tables/constraints and integrity/history
triggers. Apply normally; no new environment variables or production backfill are
needed. Reversal removes offering data and is only tested on an empty disposable
database, not offered as a history-preserving recovery procedure.

## Next integration boundary

S015 can anchor enrollments to these stable offerings. It must use the shared
transaction lock, current `course.manage` policy and active context before writes.
S016 ContestTeacher remains separate; offering assignment must not widen global
Contest operations. Do not treat stored assignment history or a cached permission
boolean as current authority. Continue from the ledger selector.
