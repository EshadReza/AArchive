# Reusable course catalog (S013)

Implemented for ADMIN-010, SRS 13/16.2/44/47 and D03. See [S013 evidence](sprints/S013.md).
A Course belongs to one Department and has no Batch, Term or Section relationship.
[S014 offerings](offerings.md) now reference the same Course UUID across terms.
Enrollment and grading remain future work.

## Local use

Apply migrations and run the backend/frontend using the root
[setup guide](../README.md#local-setup). Sign in as an Administrator and choose
**Manage course catalog** from `/account`, or open `/admin/courses`.

Choose a department using the paginated picker, then enter code, title, credits and
optional plain-text description. Codes are trimmed and stored in uppercase. The
list shows department context, credits and availability, with search, department
filtering and archive filters. Edit keeps the department fixed. Archive requires a
review and explicit confirmation; the record and its descriptive data remain stored.
Archived courses or courses under archived departments cannot be edited or selected
for new offerings. There is no hard-delete or restore endpoint.

## Authorization and API

Eligible Administrators can read all catalog records and create/edit/archive them.
Eligible Teachers can read only available courses whose departments are also active.
List counts, filters, pagination and detail reads use the same current-role selector;
archived Teacher detail requests return 404. Anonymous/Student/closed-account requests
are denied before lookup. The current management screen is Administrator-only;
Teacher catalog API reads support later offering selection and confer no offering
management or grading rights. Student course pages will use enrollment permissions
in their owning sprint rather than expose this management catalog.

| Method and path | Exact input | Result |
|---|---|---|
| GET / HEAD `/api/courses` | Optional query filters below | 200 `{count, next, previous, results}` |
| POST `/api/courses` | `{department_id, code, title, credits, description}` | 201 course |
| GET / HEAD `/api/courses/{uuid}` | None | 200 permitted course |
| PATCH `/api/courses/{uuid}` | `{code, title, credits, description, expected_revision}` | 200 updated course |
| POST `/api/courses/{uuid}/archive` | `{expected_revision}` | 200 archived course |

All paths omit trailing slashes. Writes require current Administrator permission
and same-origin session/CSRF, rechecked inside the transaction. Responses have
`Cache-Control: no-store` and safe errors; request JSON uses the existing 8 KiB limit.
Unexpected fields, including department changes, batch/term fields, archive flags,
credentials and client-controlled revisions, are rejected. There is no broad model
serializer or raw exception response.

Filters: `department_id` UUID, `q` (code/title substring, maximum 100 characters),
`archived=true|false`, `page` positive integer, `page_size` positive integer (default
25, capped at 100). Order is department label, code, UUID. Unknown/duplicate filters
are rejected. Teacher filters can only narrow their available catalog; they cannot
reveal hidden record counts. `archived` filters the direct flag, while `available`
also reflects department archival.

Projection: `id`, `department_id`, `department_label`, `department_name`, `code`,
`title`, `credits`, `description`, `archived`, `available`, `revision`.
Credits are always decimal **strings**, e.g. `"3.50"`, to avoid float rounding.
Codes are 1–64 characters, titles 1–200, both nonblank printable text. Description
is optional text but the key is required (use `""`), at most 4000 characters; line
breaks/tabs are permitted. The browser escapes descriptions and never renders them
as HTML. Credits accept decimal strings from `"0"` through `"99.99"` with at most
two decimal places; signs, exponents, whitespace, NaN, numeric JSON values and
booleans are rejected. This is a documented storage bound, not an institutional
rule about approved credit values. The SRS specifies no narrower credit policy.

`expected_revision` is a positive JSON integer (not a boolean/string). Stale edits
or archives return 409 `course_conflict`; current invalid fields, duplicate codes
caught during validation and archive prerequisites return 400 `course_invalid`.
Database conflicts return safe 409. Missing authorized resources return 404;
unauthorized writes/reads return 403. Unsupported methods return 405 after applicable
authentication/CSRF checks. Errors require reload/review before retrying stale writes.

## Storage, audit and future integration

`academics.0003_course` adds UUID Course with protected Department FK, code/title,
Decimal(4,2) credits, description, archive flag, revision and timestamps. Database
constraints enforce `(department, code)` uniqueness, canonical nonblank code,
nonblank title, credit range and positive revision. Same codes in distinct departments
are allowed; archived codes stay reserved. `0004_course_department_immutable` rejects
parent reassignment even through direct queryset updates. Stable IDs survive edits
and archive; Department deletion is protected by Course references.

Create/edit/archive transactions acquire the shared privilege lock before row locks,
recheck permission and archive/revision state, and commit reviewed audit with the
business change. A failed audit rolls back creation/edit. Concurrent edits based on
the same revision cannot both succeed. Repeating archive with the current revision
is a no-op; using an old revision still conflicts.

`academics.course.changed` records previous/new Department UUID, code, title, credits,
status and revision. Descriptions use a SHA-256 digest instead of retaining arbitrary
long text in immutable audit history. The event records that a description changed;
it is not a recoverable historical copy of that description. Archive retains the
actual current description in the Course row.

Future offering writers must authorize the actor and call
`apps.academics.courses.services.require_course_context` inside the same enclosing
transaction as their write. It takes Course/Batch/Term/Section UUIDs and combines
active-course/department checks with S012's same-parent and archive validation. The
shared privilege lock stays held until the outer transaction commits, preventing
archive races. Two Terms can validate the same Course without creating new catalog
rows. The helper does not create an offering or authorize the actor. S014 adds
its own offering uniqueness/FKs and database constraints for the newly introduced
relationships; catalog presence never supplies implicit teacher assignment.

Migration reversal deletes course data and removes its trigger. It was tested only
on an isolated empty database; use forward repairs and backups for real data.
No new environment settings or external services are required.
