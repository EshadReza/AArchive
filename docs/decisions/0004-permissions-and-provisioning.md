# ADR 0004 - Scoped authority, visibility, and import account provisioning

Status: accepted for implementation; Sprint: S001; Date: 2026-10-05.
Requirements: AUTH-002/003, COURSE-001, IMPORT-001/006/007, VISIBILITY-001/002/003;
SRS Sections 9-10, 16, 18-19, 21, 48.

## Ownership and roles

The only role definitions are Administrator, Teacher, and Student. Admin-managed
assignments may include more than one role; combine their scoped grants after
applying account-state and privacy constraints. Source roles never contribute.
Public viewing is evaluated identically for anonymous and authenticated callers;
a Teacher role does not create global private-contest access.

Any currently assigned offering teacher may manage that Offering's assessments,
marks, feedback, and permitted course reports. “Owning teacher” means such an
assignment, not an exclusive founder. Global contest mutation/re-import requires
an explicit ContestTeacher assignment or Administrator. On first successful
import, the teacher creator receives that explicit assignment. Other offering
teachers do not receive contest-management rights just because a contest is linked.
Linking/unlinking an Offering requires both contest management and authority over
that Offering, or an Administrator. Preserve audit when assignments are removed.

Batch-report permission defaults to admin-only. A delegated teacher grant specifies
the allowed offerings within a batch and authorizes only that report projection;
it does not grant individual mark access or silently include other offerings.
Access Group management likewise requires an explicit scoped delegation.

## Policy order and privacy matrix

Resolve account/lifecycle restrictions, hard privacy limits, parent gates, and
then the effective component policy. Inheritance is System → Course → Contest →
Component override. An explicit more-specific policy replaces the inherited rule
set for that component, but cannot override hard ceilings or hidden parent gates.
If several linked offerings supply defaults and there is no contest/component
override, require all applicable offering policies to pass (intersection).
Missing policies fall back to system default PRIVATE; deleted groups fail closed.
Within a rule's group list use OR; across rule types use AND.

| Resource | Normal permitted audience | Authority to widen configuration |
|---|---|---|
| Contest overview/standings/statements/editorials | Audience admitted by parent and effective policy | Assigned contest manager/admin, within component limits |
| Submission metadata/verdict/source/log/test result | Per-field PUBLIC, TEACHERS_ONLY, TEACHERS_AND_OWNER, or HIDDEN, plus parent gates; Teacher means assigned contest teacher | Assigned contest manager/admin; PUBLIC never exposes hidden test content |
| Personal academic mark | Owning student for PUBLISHED/LOCKED; assigned offering teachers/admin for draft and published work | Cannot widen to public, groups, or other students |
| Teacher report | Assigned offering/report staff for explicit scope, or admin | Delegated report scope only; no private-note or individual-grade privilege by implication |
| Private teacher note | Assigned offering teachers/admin | Cannot expose through student/API/export projections |
| Student feedback | Intended student when released with a published/locked mark, plus assigned offering teachers/admin | No other student access |
| Restricted evidence | Admin with built-in restricted.view or a teacher with explicit admin-granted restricted.view and resource scope | Never Student-role/public access; log governance reads |

TEACHERS_ONLY refers to staff assigned to the relevant resource, not every Teacher.
TEACHERS_AND_OWNER adds verified individual/team ownership from ADR 0002. HIDDEN
denies normal viewing; admin governance access is explicit and audited. A user who
also holds a Student role may use an authorized staff grant; a Student grant alone
never unlocks staff/restricted content. Deletion/archive lifecycle gates cannot be
bypassed through a public URL, cached report, or notification.

## Narrow account provisioning

`users.manage` and `roles.manage` remain admin-only. Add
`users.provision_import_student`: a teacher may invoke it only in an import they
can manage, for a validated unmatched participant, with an explicit separate
confirmation. The accounts service creates a PENDING Student with unusable
password and verification/approval requirements. Importer code does not set roles,
copy source password hashes, or modify existing credentials/roles. Existing-email
or identity conflicts return to mapping review; an invitation proves institutional
ownership before activation. Requests are idempotent and audited.

This separate provisioning can occur before final import confirmation and is an
explicit exception to the broad “no production data before confirm” wording.
Job/staging/audit records are also allowed; live Contest, Submission, StandingEntry,
and confirmed identity mappings are not. Cancellation preserves the independently
created pending account and its audit; it never silently deletes an account.
Placeholder/unmapped choices create no login account.

## Account states

Use PENDING, ACTIVE, INACTIVE, GRADUATED, ALUMNI, SUSPENDED, ARCHIVED, ANONYMIZED.
PENDING requires verified institutional ownership and optional admin approval
before ACTIVE. ACTIVE may become INACTIVE through recorded inactivity; successful
login reactivates it. GRADUATED/ALUMNI retain historical login. SUSPENDED and
ARCHIVED deny login and invalidate existing sessions; only an audited admin
action restores a recorded prior eligible state. ANONYMIZED is terminal and
denies authentication; “deleted account” refers to this erasure outcome, not a
second slash-separated enum. Admin graduation/alumni/restriction changes are
audited, and authentication always checks current state.

## Verification and alternatives

S005-S011 test lifecycle, verification, and non-escalation. S014/S019-S020 test
shared-contest conflicts and immediate revocation. S041 tests four mapping choices
and the provisioning exception. S061/S085 test all privacy projections. Granting
every offering teacher global contest rights would expose other offerings; allowing
generic teacher user creation would exceed the account-management contract.
