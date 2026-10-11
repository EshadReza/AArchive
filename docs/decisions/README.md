# Implementation decisions and external inputs

These contracts were accepted in S001 on 2026-10-05 and aligned with SRS version
1.1. They specify required behavior, not implemented application code. Use the
accepted defaults without requesting the same confirmation again. Change a
contract through an ADR and matching SRS edit. The [S001 ledger](../sprints/S001.md)
records the reconciliation and verification.

| Accepted ADR | Contract |
|---|---|
| [0001](0001-application-boundaries.md) | Stack and module boundaries |
| [0002](0002-academic-and-team-model.md) | Academic cardinalities, team subjects, source identity |
| [0003](0003-source-versions-and-import-states.md) | Source namespaces, deduplication, import/version states |
| [0004](0004-permissions-and-provisioning.md) | Authority, privacy matrix, narrow provisioning, account states |
| [0005](0005-grading-revisions-and-publication.md) | Mark revisions, corrections, publication, numerical rules |
| [0006](0006-requirement-authority-and-input-gates.md) | SRS authority, accepted defaults, external gates |

## D01 - Stack and repository layout

Accepted in [ADR 0001](0001-application-boundaries.md). Use Django/DRF, React with
TypeScript and Vite, PostgreSQL, Celery/Redis, and private S3-compatible storage
with a local-development adapter. Serve frontend/API under one origin with Django
sessions and CSRF. Pin supported compatible versions/lockfiles in S002-S004; no
model usage quota is asserted by this document. S002 pins Python 3.14.7 and the
Django 5.2 LTS/DRF 3.18 backend dependencies in `uv.lock`; its settings and health
checks are implemented. See [S002 evidence](../sprints/S002.md) and the root README
for actual commands. S003 adds React 19, React Router 7, TypeScript 6 and Vite 8;
exact versions are in `frontend/package-lock.json`. It implements accessible
primitives, a same-origin API client and development-only workshop. See
[S003 evidence](../sprints/S003.md). S004 implements pinned local PostgreSQL/Redis
services, a Host/Origin-preserving Vite proxy and shared CI gates; see
[S004 evidence](../sprints/S004.md). S008 implements [session bootstrap/login/logout](../authentication.md).

Follow ARCHITECTURE.md: backend/config and backend/apps for domain modules,
frontend/src/app/features/components/lib, shared tests/fixtures, scripts, deploy,
and docs. Accounts owns platform identity; academics owns offerings/enrollment;
access owns policies; imports owns staged validation/orchestration; contests owns
source versions; grading owns marks; assets owns storage/delivery; reports owns
scoped datasets; audit owns audit/outbox; notifications consumes committed events;
governance owns settings/retention. Create modules when needed, without fake APIs.

## D02 - Authorization and state

Accepted in [ADR 0004](0004-permissions-and-provisioning.md). Only Administrator,
Teacher, and Student role definitions exist. Admin-managed users may hold multiple
roles; combine scoped grants after account-state and privacy constraints. Source
roles never grant platform authority. Anonymous callers may read genuinely public
components subject to parent gates. Services, querysets, serializers, workers,
exports, and assets share the policy service; caches never preserve revoked access.

States are PENDING, ACTIVE, INACTIVE, GRADUATED, ALUMNI, SUSPENDED, ARCHIVED,
ANONYMIZED. PENDING requires verification/optional approval before activation.
INACTIVE denotes inactivity and may reactivate on successful login. Alumni and
graduates retain permitted history. PENDING/SUSPENDED/ARCHIVED/ANONYMIZED cannot
authenticate; current sessions recheck state. Restricted-state restoration is an
audited admin action; anonymization is terminal. Preserve assignment/enrollment
history when membership ends.

S005 implements the identity foundation: UUID `accounts.User`, minimal display-name
profile, fixed multi-role assignments, and verified/approved state predicates.
Email storage is trimmed/lowercase; optional student IDs are trimmed/uppercase
strings with blanks stored as NULL. Database constraints enforce canonical
uniqueness and eligibility prerequisites. The trusted manager creates pending
Students only. Django Groups/superuser flags are not alternate platform roles;
audited role changes are implemented by S007; authentication is implemented in S008. See
[account storage details](../database.md#implemented-account-foundation-s005) and
[S005 evidence](../sprints/S005.md).

S006 adds an Administrator-only audit read boundary that rechecks current role and
eligibility. Audit writes require the business transaction and reviewed event
schemas; account actors retain protected UUID references through anonymization.
Reason codes and allowlisted metadata/payloads avoid arbitrary secrets in immutable
records. See [audit service and coverage](../audit.md). S007 integrates shared
authorization; S008 integrates session transport without broadening audit reads.

S009 adds [institutional self-registration and single-use email verification](../registration.md).
Empty domain configuration disables signup. Optional approval is captured per user;
verification never bypasses it or changes existing credentials/roles. Password
recovery and lifecycle commands are implemented in [S010](../recovery-lifecycle.md).
Commands preserve the recorded prior state for restoration and protect the last
eligible Administrator. Password changes and restrictions proactively delete
subject sessions under the shared privilege lock; tokens cannot restore access.
S011 adds [Administrator invitations and own-profile editing](../account-management.md).
Trusted admin creation accepts explicit fixed roles and approval choice but always
starts PENDING with unusable credentials. Invitation acceptance proves email
ownership and sets a password without changing roles or bypassing required approval.
Self-profile writes allow only display name; verified identity editing is not exposed.

S007 adds registered model/queryset policy hooks, typed resource references and
explicit scoped capability storage. Unknown kinds/actions deny, including for
Administrator. Role/grant changes serialize on a seeded lock and audit atomically;
Teacher removal revokes delegations, and the last eligible Administrator is
protected. A local first-admin bootstrap requires an existing eligible account and
refuses once any Administrator exists. Scope activation requires a real registered
resource; academic/contest adapters remain their owning sprints' work. See
[access contracts](../access.md) and [S007 evidence](../sprints/S007.md).

## D03 - Academic and team relationships

Accepted in [ADR 0002](0002-academic-and-team-model.md). Department owns reusable
Courses and Batches. Batch owns Terms and Sections. Offering references one Course,
Batch, Term, and Section with matching parent constraints; use an explicit ALL
Section for an unsplit batch. Contest-to-Offering is many-to-many. Each Assessment
belongs to one Offering and references zero/one Contest; a Contest may feed many
independent assessments.

S012 implements Department → Batch → Term/Section with protected UUID references,
canonical parent-scoped labels and archive flags. New batches receive a reserved
ALL section. Parent relationships are immutable; archive retains history and blocks
new assignments through descendants. The admin screen and revisioned APIs are
documented in [academic structure](../academic-structure.md); future offering writes
must use its transaction-scoped same-parent/archive validation.

S013 implements the [reusable course catalog](../course-catalog.md) with immutable
department ownership, no batch/term fields, unique canonical codes per department
and bounded decimal credits (0–99.99, two places). The credit bound is a storage
default, not a claimed institutional rule. Admins manage/archive records; Teachers
read only available catalog entries, without gaining offering assignment rights.

S014 implements [offerings](../offerings.md): matching immutable academic tuples,
creator staff attachment, admin-managed multi-teacher assignments, immutable ended
history, and immediate scope/grant revocation on removal. Current co-teachers share
name-settings rights; admin-only creators receive no implicit Teacher platform role.

Each versioned participant has exactly one individual ImportedUser or Team subject,
with same-version references. TeamMember links Team to ImportedUser with source
membership times. SourceIdentity is stable across ImportedUser snapshots and has
zero/one current mapping to a platform User plus mapping history. Placeholders
have no login account. TEACHERS_AND_OWNER uses verified membership evidenced at
submission time; later joins grant no retroactive private-source access. Team
membership never grants another student's academic marks. Grade allocation needs
a teacher-reviewed membership/input snapshot.

## D04 - Visibility precedence and shared contests

Accepted in [ADR 0004](0004-permissions-and-provisioning.md); SRS Section 10 is the
common privacy matrix. Hard ceilings: owner-only published/locked marks plus
assigned offering staff/admin, staff-only reports/private notes, intended-student
released feedback, and restricted.view for restricted data. PUBLIC source does
not expose hidden tests or bypass hidden parents. HIDDEN denies normal viewers;
admin governance is explicit and audited.

Apply lifecycle/account constraints, privacy ceilings, parent gates, then effective
component rules. More-specific policies replace inherited rules only for that
component. Without an explicit contest/component override, intersect all linked
offering defaults. Missing defaults resolve to PRIVATE. Use OR within group
choices, AND across rule types; deleted groups fail closed.

Current offering teachers manage their assessments; explicit ContestTeacher
assignment is needed for global contest changes/re-import. A new contest's
successful importing creator gets that assignment. Linking/unlinking requires
management of both Contest and target Offering. Batch reports default to admin;
a delegated grant names allowed offerings and grants only the report projection,
not individual marks. Group management also requires explicit delegated scope.

## D05 - Source identity and immutable versions

Accepted in [ADR 0003](0003-source-versions-and-import-states.md). Distinguish
application product, registered namespace/installation, stable contest/user keys,
export ID, format version, and ZIP hash. S025 supplies the actual field mapping;
never guess IDs from names. The namespace is trusted admin/adapter configuration,
not authority supplied by an upload.

Constrain Contest by namespace/stable contest key and committed versions by
(contest_id, zip_sha256). Each job produces zero/one new version; duplicate jobs
may refer to an existing one without promoting it. A duplicate superseded payload
cannot roll back the current pointer. Retain immutable source rows, tombstones,
asset references, and provenance; source keys are unique per version/entity type.
Keep job IMPORTED distinct from version CURRENT/SUPERSEDED and Contest lifecycle.
Content-addressed blobs need reference-safe cleanup. Earlier marks continue to
cite the exact source version used for their calculation.

## D06 - Trusted archive contract (external blocker)

Input gate G01 is recorded in [ADR 0006](0006-requirement-authority-and-input-gates.md).
The supplied tree is preserved verbatim in docs/archive-layout.md. It names files
and record categories but contains no literal JSON Schema definitions. Obtain an
independently trusted complete schema set, concrete field/ID/unit semantics,
format/schema version, provenance/digests, and permitted sample. Record intake in
docs/archive-contract.md. Commit only redistributable schemas/synthetic fixtures;
keep real private archives in ignored private/.

S025 cannot finish without G01. Its dependency descendants cannot claim real-format
support. Independent foundation/accounts/policy/manual-grading/security work can
continue. Test adapters must have a distinct test-only format identifier disabled
in production. Do not promote an archive's own schema copies to trusted authority.

## D07 - Import atomicity and account provisioning

Accepted in [ADR 0003](0003-source-versions-and-import-states.md) and
[ADR 0004](0004-permissions-and-provisioning.md). Persist job/staging/audit metadata
before confirmation; publish no live contest/source rows or confirmed identity
mappings before a current authorized preview is confirmed. Bind that preview to
ZIP digest, schema revision, current source version, and mapping-plan revision.
Validate counts/references before commit. Make assets durable first; commit source
rows/current pointer/mappings/audit/outbox together and reconcile orphans safely.

The separate users.provision_import_student accounts command may create a PENDING
Student with unusable password for a validated unmatched participant in a managed
import. It needs explicit separate confirmation, verification/approval before
activation, idempotency, and audit. It may assign only the fixed Student role;
importer code cannot assign roles or import password hashes. Existing identity
conflicts return to mapping review. users.manage stays admin-only. Canceling the
import preserves the independently created pending account/audit; placeholder and
unmapped choices create no login account.

## D08 - Grades and numerical conventions

Accepted in [ADR 0005](0005-grading-revisions-and-publication.md). Use Decimal,
versioned rule/input snapshots, declared maximum/precision/rounding/bonus/missing
policies. Default final academic marks use two decimals with ROUND_HALF_UP; keep
calculation precision until that boundary. Explicit rule versions may change the
default. Missing/excluded/absent is not zero. Best-N/drop-N ties use stable
assessment ID; reject dependency cycles; disclose report coverage/denominators.

StudentMark source snapshots describe the source used, not the current imported
score. Explicit re-application records old/new values and source versions. State
belongs to each mark, with revision-checked all-or-nothing bulk commands. Current
co-assigned offering teachers may finalize/publish/correct. FINALIZED requires
reopen before editing. PUBLISHED corrections use a separate proposal and atomic
correction-and-republish, retaining the previous visible value until success.
LOCKED needs elevated audited unlock first. Contest-only assignment gives no
grading rights. Students see only published/locked revisions and safe totals.

## D09 - Custom formula language

Accepted boundary in [ADR 0005](0005-grading-revisions-and-publication.md). Use a
small allowlisted expression grammar, Decimal values, pure functions, and bounded
input/AST depth/node count/operations/numeric range. No Python/JavaScript eval,
imports, SQL, network, filesystem, or subprocesses. Store rule version, input
snapshot, bounded trace, and result/error. Failed evaluation cannot replace a
saved mark or published revision. Parser/evaluator implementation belongs to
S058-S059.

## D10 - Retention and erasure

Accepted default in [ADR 0006](0006-requirement-authority-and-input-gates.md).
Soft deletion revokes normal access and is recoverable. Default grace is 30 days;
admin-configurable duration remains positive, with no immediate/emergency bypass.
Hard purge needs explicit admin impact review, audit, and resumable cleanup.
Preserve university marks/adjustments/comments through retained academic tombstones
and provenance; do not cascade them away or delete shared referenced assets.
Anonymization covers source identity projections, mappings, export/search caches,
and personal-data-bearing assets. Define backup expiry and re-erasure on restore.
A public field alone does not make a real archive safe to commit to Git.

## D11 - Measurements and operational dependencies

The SRS has no concrete concurrency/hardware/p95/import-duration targets. S088
names a hardware/dataset/load profile and measures browse/report latency, queue
latency, RSS, import/export duration, and query counts before claiming capacity.
Preserve Section 23 limits; tiny fixtures cannot validate near-limit behavior.
RPO <=24h/RTO <=8h are starting recovery targets subject to documented needs.
Hosting, DNS/TLS, institutional mail, storage, backup access, and live-action
authorization are actual inputs for the deployment cards. They do not block local
scaffolding. See [ADR 0006](0006-requirement-authority-and-input-gates.md).

## D12 - Documentation authority and phase gates

Accepted in [ADR 0006](0006-requirement-authority-and-input-gates.md). The canonical
SRS is docs/requirements.md; parent MD/PDF copies are older handoff exports.
Ordinary code sprints do not regenerate PDF. Historical citations are labeled
External master prompt because that text is unavailable; local Section 48 is
Page Permissions. Never invent missing source decisions. S001's ledger records
corrected references and contracts. Phase 2/Future integration requirements remain
outside MVP launch scope and keep their stated external gates.

### S014 permission clarification (D04)

Assignment changes and archive are Administrator-only; eligible Teachers/Admins
may create and are attached automatically. Current co-assigned Teachers share
name-settings rights on available offerings. Removing a membership retains its
history and authorship while revoking current scope and offering grants. Restoring
membership creates a fresh row without restoring grants. These choices implement
the SRS's co-teacher rights without exposing global Contest operations. See the
[offering authorization matrix](../offerings.md#authorization). Future grading
adapters must use current membership rather than the historical assigner/creator.
