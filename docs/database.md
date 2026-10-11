# Database model and integrity guide

Status: PostgreSQL connection configuration is implemented in S002; S005 adds
the custom User, UserProfile and UserRole models with `accounts.0001_initial`.
S006 adds AuditLog and its PostgreSQL mutation-rejection trigger.
S007 adds ScopedGrant and a seeded singleton PrivilegeLock; see
[access schema and mutation contract](access.md).
SRS 1.1 Sections 13-16 and 33/40-45 define the domain; accepted ADRs 0002-0005
resolve its cardinality, identity, and publication contracts. Other domain models
remain planned; each owning sprint implements and tests their constraints.

S002 uses Psycopg 3 and rejects non-PostgreSQL database URLs in every profile.
Development/production use `DATABASE_URL`; tests use a separate `TEST_DATABASE_URL`
and never inherit the developer's database. `AUTH_USER_MODEL=accounts.User` is set
before the first migration. S008 installs auth/contenttypes/sessions; admin remains
uninstalled and no default `auth_user` table exists. The S002 health
endpoint is independent of database availability. PostgreSQL 17 is the initial
verification baseline; S004 supplies the shared development service configuration.

The S004 backend gate now requires real PostgreSQL and exercises transaction
rollback in pytest's disposable test database. Compose stores local data in a
project-scoped named volume; `down` preserves it, while `down --volumes` deletes
it. CI creates its own PostgreSQL service. No account/domain migration is added by
the infrastructure sprint.

## Academic structure storage (S012)

`academics.0001_initial` creates Department, Batch, Term and Section with protected
typed parents, canonical labels, parent-scoped uniqueness, archive flags and revisions.
`0002_protect_structure_parents` prevents parent changes and protects reserved ALL
section identity via PostgreSQL triggers. Batch creation and automatic ALL creation
commit with audit; ancestor archive blocks new associations without deleting history.
See [structure integrity and assignment contract](academic-structure.md#integrity-and-transactions).
Courses/offerings/enrollment remain future models.

## Invitation storage (S011)

`accounts.0005_invitation` adds one `Invitation` per user, with unique token digest,
account-revision digest, indexed expiry, consumed timestamp and send timestamp.
Acceptance is atomic and single-use; resend rotates the challenge after a cooldown.
Suspension/archive expire it alongside verification/reset challenges. No raw token
is stored. See [account management](account-management.md) for transactions and
configuration. Existing account/profile/role schemas are unchanged.

## Recovery and lifecycle storage (S010)

`accounts.0004_passwordreset_user_state_before_restriction_and_more` adds one
`PasswordReset` per user (unique token digest, account-revision digest, indexed
expiry, consumed timestamp) and `User.state_before_restriction` (empty, PENDING
or an eligible state). A database CHECK fixes the prior-state vocabulary. Legacy
closed accounts start with no recorded prior state and cannot be restored by
guessing an eligible state. The service keeps the first prior state across nested
restrictions and clears it on restoration; no roles/history are deleted.
Recovery counters reuse LoginAttempt with separate namespaces. Active Django
session rows are proactively deleted for the affected user on password changes
and restrictions. See [transaction and session contract](recovery-lifecycle.md).

## Email verification (S009)

`accounts.0003_emailverification` adds one `EmailVerification` challenge per user
with a unique 64-character SHA-256 token digest, a keyed email/password-revision
digest, indexed expiry and nullable consumption
time. No raw token is stored. Registration/resend counters reuse LoginAttempt with
separate HMAC namespaces. See [registration transactions](registration.md#persistence-and-transactions).
Self-registration creates only pending Students and captures required approval;
verification activates only when that approval gate is satisfied.

## Session storage (S008)

`accounts.0002_loginattempt` adds `LoginAttempt`: a 64-character keyed HMAC primary
key, nonnegative attempt count and indexed `resets_at`. Separate namespaces hash
normalized email and peer IP; raw identifiers are not stored in these rows. Atomic
row locks enforce shared fixed windows across workers. Django `sessions.0001_initial`
adds `django_session` with encoded session data and indexed expiry; the cookie
holds an opaque key. See [authentication](authentication.md) for expiry and cleanup.
Django Group/Permission tables are framework storage, not platform roles.

## Implemented account foundation (S005)

- `User`: stable UUID primary key, unique email, optional unique student ID,
  lifecycle state, verification/approval timestamps and approval-required flag,
  join/update times, and Django password/last-login fields. No source identity or
  archive credentials are stored here.
- Email is stripped and lowercased in full. A database CHECK requires canonical,
  nonempty, whitespace-free storage; uniqueness also applies to direct writes.
  The manager validates email syntax. Institutional domain allow-listing is implemented
  by registration in S009; the manager does not guess domains.
- Student ID is a string up to 64 characters, stripped and uppercased, preserving
  leading zeroes. Blank input becomes SQL NULL. CHECK/UNIQUE constraints reject
  noncanonical or duplicate stored IDs while allowing multiple NULLs. The SRS
  supplies no institution-specific format, so none is invented.
- `UserProfile`: one-to-one protected reference, display name (up to 200 characters),
  creation/update times. Academic affiliations belong to future academic models.
- `UserRole`: protected user reference, one of ADMINISTRATOR/TEACHER/STUDENT,
  assignment time; UNIQUE(user, role) permits several distinct fixed roles.
  There is no user-defined role table or source-role-to-platform-role conversion.
- Lifecycle CHECKs reject unknown states and require email verification plus any
  required approval for ACTIVE/INACTIVE/GRADUATED/ALUMNI. Remaining states deny
  authentication. `ANONYMIZED` represents deletion; there is no DELETED enum.
  State CHECKs do not enforce transition history or terminality: S010 implements
  guarded, audited transitions; S084 owns actual data anonymization.

`User.objects.create_user(email, password=None, *, display_name="", student_id=None)`
atomically creates a PENDING Student and profile. Omitted passwords are unusable;
raw passwords are hashed by Django. Known encoded Django hashes and unexpected
privilege/source fields are rejected. Callers must supply explicit validated
fields; direct ORM writes are trusted internal operations, not an import API.
Role mutation/bootstrap is implemented in S007; authentication is implemented in S008; public registration in S009 adds domain/password-policy checks and audit controls.
S011 implements administrator invitations; future bulk/import provisioning must
retain its separately authorized, idempotent creation contracts.

`is_login_eligible`, `is_active`, `allows_authenticated_session`, and
`allows_historical_access` require an eligible state and verification/approval.
`User.objects.eligible_for_authentication()` queries those conditions in current
database rows. Session handlers must fetch current state, never retain a cached
User after suspension. History eligibility does not authorize particular records.
Profile/role references use PROTECT; PostgreSQL FKs also prevent orphaning through
raw deletion. Future academic FKs must preserve this stable identity.

Apply with the README's `manage.py migrate --noinput` command. The backend gate
checks migration drift and runs integrity tests on PostgreSQL. Initial forward,
empty-database rollback, and reapplication were verified; see [S005 evidence](sprints/S005.md).
Reversing this migration drops account data: use forward corrective migrations
once real users exist, with a tested backup/recovery procedure.

## Domain ownership

S006 audit schema and recovery details are in [audit integrity](audit.md#integrity-and-migrations).
Audit actors use protected account references (or explicit system actors); target
identifiers survive entity removal. User anonymization preserves the actor UUID
without copying names or credentials into audit rows. Prior audit records cannot
be updated or deleted through the ORM or ordinary SQL UPDATE/DELETE.

| Module | Planned model families | Owning sprints |
|---|---|---|
| accounts | User, profile, platform roles/grants, lifecycle, invitation | S005-S011 |
| audit | AuditLog, durable outbox, event-delivery state | S006, S023 |
| academics | Department, Batch, Term, Section, Course, Offering, teacher assignment, enrollment | S012-S016 |
| access | AccessGroup, membership, VisibilityPolicy, typed policy rules | S018-S020 |
| assets | FileAsset, restricted classification, blob references, staging leases | S021-S022 |
| contests/imports | Contest, ContestTeacher, ContestImport, ContestImportVersion, SourceIdentity, versioned ImportedUser, mapping/history, source records and overlays | S024-S045 |
| grading | Assessment, rule/version, StudentMark, MarkAdjustment, MarkCorrectionProposal, private note, visible feedback | S052-S063 |
| reports | Aggregate snapshot, report/export job, later saved filters | S069-S078 |
| notifications | Owner notification and delivery/deduplication state | S080-S081 |
| governance | Settings, deletion/tombstone/anonymization ledger | S082-S084 |

## Academic relationships

Department owns reusable Courses and Batches. Batch owns its Terms and Sections.
Each Offering references one Course, Batch, Term, and Section with matching parent
constraints. An unsplit batch uses an explicit ALL Section. Teacher assignments
and enrollment retain history and effective state; removal never deletes marks.

Contest-to-Offering is many-to-many. An Offering defines assessments; an assessment
optionally references a Contest. Thus the same Contest can feed several distinct
offering assessments. Participants may be individuals or teams with time-aware
membership. Participant has a discriminator and exactly one ImportedUser or Team
subject; subject/membership references must match the import version. Team
submissions do not require choosing an arbitrary user as owner. Verified source
membership at submission time controls team source ownership; later membership
cannot grant retroactive access or access to another member's academic mark.

## Source versions and academic provenance

Source rows are version-scoped. Stable keys include source installation/namespace
and source ID; archive/export ID and upload hash are separate concepts. Source
application name alone is not sufficient to isolate multiple installations.
The trusted format contract supplies concrete field names and ID semantics.

SourceIdentity is the stable namespace/user key. Versioned ImportedUser snapshots
refer to it; one current StudentIdentityMapping optionally maps it to a platform
User, with immutable mapping history. Placeholder resolution creates no fabricated
User/login. Namespace registration is trusted configuration, not an upload claim.
Each import job produces zero/one committed version; each version has one producing
job. Duplicate jobs may separately reference an existing version without promotion.

Keep previous version rows and source-side rejudge/deletion history. One current
pointer on Contest selects the active source version. Switch it transactionally
under a contest lock. University overlays, identity mappings, publication state,
marks, and feedback live separately and survive pointer changes.

StudentMark identifies the source snapshot/version used for its calculation.
Explicit re-application creates an adjustment containing old/new source values
and versions; it never erases provenance. Published corrections and rule changes
retain prior values and the calculation trace. Decimal precision and rounding are
declared per rule/domain contract. Default final marks use two decimal places and
ROUND_HALF_UP; preserve source/calculation precision until the final boundary.
Track current and visible mark revisions separately from an uncommitted correction
proposal. Correction-and-republish atomically advances the visible revision; failed
or stale proposals leave it intact. FINALIZED requires reopen and LOCKED requires
elevated audited unlock before correction.

## Constraints and transaction boundaries

- Normalize institutional email and constrain unique student ID when present.
- Constrain department/course-code, batch/section-label, and offering tuple.
  Validate matching parents using suitable composite FKs or transaction-safe
  database/service constraints; a normal row CHECK cannot query another table.
- Constrain one mark per assessment/student, one group membership per group/user,
  and source-key uniqueness within a source version. Constrain Contest by
  (source_namespace, stable_contest_key) and committed versions by
  (contest_id, zip_sha256). Keep duplicate attempt jobs without duplicate versions.
  Replaying a superseded payload must not change the current pointer.
- Use foreign keys and deletion restriction for academic references. Model the
  retained tombstone explicitly for source purge; no cascading deletion of marks.
- Row CHECKs validate allowed state values; guarded transitions need old/new
  state-aware services or triggers. Lock/read current revisions before mutations.
- Commit business mutation, audit, and outbox together. Object storage is outside
  the database transaction: make blobs durable before publishing references, then
  clean tracked orphans through retry-safe recovery.
- Preserve unavailable, excluded, empty, truncated, and corrupted states with
  typed metadata. Nullable values must not be interpreted as recorded zeros.
- Model multi-rule visibility explicitly; one `visibility_type` plus an array
  cannot express every AND-across-types policy without a typed rule relation.

## Indexing and growth

Index foreign keys and measured query paths: contest/version/source key,
submission participant/problem/time, standing snapshot/rank, mark assessment/user,
audit actor/target/time, membership user/group, and worker status/heartbeat.
Use bounded batch writes, streaming JSONL, and staging reference indexes. Query
plans and RSS/latency benchmarks in S088-S089 determine additional indexes.
Do not add speculative partitions or a second primary database before evidence.

## Migration evidence

Each owning sprint adds migrations, database integrity tests, and a rollback or
forward-recovery note when needed. Verify constraints/concurrency on PostgreSQL.
Archive schema definitions are not database migrations. Production credentials,
dumps, and real archive payloads remain outside Git.
