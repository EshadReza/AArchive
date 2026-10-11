# Security and privacy implementation guide

Status: required controls and verification plan. This file does not certify that
an unbuilt application is secure. See SRS Sections 10/16.5/18-20/23-25/31/34/55 and
the implementing sprint evidence in [progress](progress.md).

## Implemented foundation controls (S002)

Production settings require an explicit generated secret, allowed hosts and
PostgreSQL credentials, reject debug mode/example credentials, enable secure
cookies/HTTPS redirects, and do not automatically trust proxy headers. Tests use
a separate PostgreSQL URL rather than inheriting a developer's database. The
health endpoint exposes only a fixed liveness result; new DRF views deny access
by default unless an endpoint explicitly allows anonymous access. S005 supplies
account-state predicates and S007 supplies central authorization. S008 implements
[database sessions, CSRF and login limits](authentication.md); S010 implements [password recovery, lifecycle
commands and proactive session revocation](recovery-lifecycle.md). S090 must test the deployment's
trusted TLS proxy boundary. See [backend setup](../README.md#local-setup).

S004's local PostgreSQL/Redis ports bind only to loopback and use project-scoped
Docker volumes. `.env` is ignored; CI service credentials are synthetic and scoped
to its disposable database. The Vite development proxy preserves Host and Origin
without adding trusted origins or disabling CSRF. The automated proxy smoke check
verifies missing-token and foreign-origin rejection. Its test-only URLconf never
replaces normal application routes. CI has read-only permissions and pinned
action/image references; production network/service configuration remains separate.

## Identity and access

S007's [central policy interface](access.md) refetches platform state/roles, denies
unknown actions/resources, and uses the same selector for list/detail checks.
Privilege mutations serialize on a database lock, reauthorize the Administrator,
and commit changes with audit. Removing Teacher revokes delegated grants; removing
the last eligible Administrator is rejected. S010 lifecycle/recovery services share this lock order.
The audit API uses the central guard and scoped queryset. Scope adapters are
trusted server code, never uploaded or request-provided policies.

S005's trusted account manager accepts only explicit identity/profile fields and
an optional raw password. It creates PENDING Students atomically; missing passwords
are unusable, supplied raw passwords use Django hashing, known Django encoded
hashes are rejected, and source roles/credential fields cannot be mass-assigned.
Unknown password strings are hashed as raw input, never adopted as serialized
credentials. Importers must never pass source credential values to this manager.
The database fixes role/state vocabularies and enforces identity uniqueness and
activation prerequisites. S007 implements audited role/grant services; S008 adds
the authentication backend, audited login/logout, bounded sessions, shared attempt
limits and revocation on detected forbidden states. S009 implements [registration and verification](registration.md), including exact
domain allowlisting, password validation, single-use token digests, approval gating,
shared resend limits and safe mail failure handling. S010 implements password recovery/change and audited lifecycle commands, with
account-bound expiring one-use tokens, shared attempt limits, atomic all-session
revocation and last-eligible-Administrator protection.
S011 implements [account administration and invitations](account-management.md):
admin-only enumeration/create/role commands, expected-role conflicts, explicit
review screens, single-use account-bound invitation acceptance and a strict
display-name-only self-profile endpoint. Existing identity/role/state fields cannot
be mass-assigned. Mail is post-commit; production invitations require explicit
opt-in and validated SMTP/HTTPS configuration.
S012 [academic structure](academic-structure.md) management uses current
Administrator checks before lists/counts/lookups and again under the privilege lock
for writes. Strict fields, expected revisions, immutable parents, protected foreign
keys and ancestor-aware archive gates prevent accidental reassignment or loss of
history. Academic changes and reviewed metadata audit records commit atomically.
Current-state predicates are tested for every state; they are eligibility ceilings,
not resource permissions. ANONYMIZED denies eligibility, but actual erasure and
terminal transition enforcement belong to their later services.

The S003 browser client confines cookies and CSRF headers to the same-origin API,
rejects redirects, and reads the current CSRF cookie for each mutation. It stores
no credentials in localStorage/sessionStorage. Its development workshop persists
no data and is excluded from production builds. S008 connects this client to real
server-side session/CSRF bootstrap and sign-in/account screens; passwords are
cleared on submit and the account projection remains in memory only.

Use institutional session login with CSRF, secure cookies, strong framework
password hashing, bounded sessions, reset/verification token expiry, and rate
limits. PENDING, SUSPENDED, ARCHIVED, and ANONYMIZED deny authentication; active
sessions check current state. INACTIVE denotes inactivity, not suspension, and
alumni retain permitted historical access. Source roles, imported password hashes, and source admission grants never
authorize platform operations. Registration and import provisioning cannot choose
Teacher/Admin roles or overwrite an existing account's credentials. The separate
users.provision_import_student capability invokes the accounts service for a
validated unmatched participant in a managed import. Explicit confirmation creates
only a PENDING Student; invitation/verification/approval precede activation. The
importer itself never writes roles or credential fields. Cancellation preserves
the independently provisioned account/audit, while confirmed mappings still await
import confirmation.

The shared policy service authorizes querysets, individual resources, actions,
field projections, jobs, and file delivery. Apply current assignments/membership
at access time. A cached report or old notification is not a permanent grant.
Check role/object matrices for anonymous, owning student, unrelated student,
assigned teacher, unrelated teacher, and administrator.

SRS 1.1 Section 10 and ADR 0004 define the shared privacy matrix. All current
co-assigned offering teachers may grade their assessments; global contest changes
need explicit contest assignment. Shared-offering inherited policies intersect
until an explicit authorized component rule replaces them. Hard ceilings and
hidden parent gates remain. Team source ownership needs verified membership
evidence at submission time; later joins confer no retroactive private-source
access or access to another student's marks.

Hard ceilings: personal academic marks are owner-only after publication plus
authorized staff; teacher reports are staff-only; restricted evidence requires
restricted.view. Group membership and PUBLIC source policy cannot override these
ceilings or reveal hidden tests. Draft/finalized grades must not leak via totals,
statistics, notifications, search, or exports. Private teacher notes and visible
feedback use separate projections.

## Untrusted archives

The uploaded ZIP tree is a known inventory, not a trustworthy validator. Pin the
actual format schemas independently and reject unknown versions or modified
archive schema copies. Disable untrusted external schema references. Self-contained
checksums detect corruption; they do not prove who created the archive.

Check path traversal, absolute paths, symlinks, entry type/encryption, duplicate or
colliding paths, file count, depth, individual size, total extraction, and runtime
compression expansion. Enforce limits while streaming as well as from metadata.
Never execute source, checkers, generators, validators, reference solutions,
compiler commands, or archived scripts. Do not fetch archive-specified URLs.

Validate manifest, complete checksum coverage, pinned JSON/JSONL schemas,
cross-record references, and record counts before publication. No teacher can
waive an integrity failure. Preview and confirmation bind the file digest,
schema/source versions, and mapping revision, and recheck authorization.

## Content and file delivery

Sanitize imported HTML with an allowlist; output-escape everything else. Deliver
source/log content as inert text or attachments with safe MIME/disposition and
nosniff behavior. Do not adopt imported branding/navigation as application code.
Store restricted structured fields and blobs under enforced access controls;
directory names alone provide no security.

Object storage is private. Return only opaque application links or scoped
short-lived signed URLs after permission checks; do not expose raw filesystem
paths. Expiry and permission/cache invalidation behavior must be documented and
tested. Keep secrets, raw exception traces, restricted filenames, and credential
hashes out of normal UI, events, and logs.

## Academic integrity and operations

S006 implements the [audit service](audit.md): reviewed event projections,
bounded JSON, controlled reason codes and explicit metadata, a transaction-required
writer, ORM mutation guards and a PostgreSQL UPDATE/DELETE rejection trigger.
Audit reads require a freshly checked eligible Administrator; source headers/roles
and stale role assignments confer no authority. S008 verifies these checks through real database sessions.
Logging is integrated into each feature by its owning sprint; defining event
schemas does not automatically audit all database writes. Database-owner DDL and
TRUNCATE are outside the app's immutability boundary; production privilege
separation and retention/recovery remain operational sprint responsibilities.

Use revision checks/locks for marks and source-version promotion. Persist mutation,
audit, and durable events atomically. Audit reads are scoped; application APIs
cannot alter prior entries. Preserve source and university data separately.
Custom formulas use the bounded pure expression language, never host-language
eval/exec. Record formula version, inputs, result/error, and bounded trace.

CSV/XLSX serializers neutralize untrusted spreadsheet formulas. PDF/XLSX/CSV
exports use the same scoped datasets and reauthorize download. Revoked users
cannot retrieve stale private files because they previously requested the job.

Production configuration must reject missing secrets, unsafe hosts/origins, debug
mode, and public private-data storage. Secrets are environment-managed. Backups
include both database and required files, have restricted access, and are tested
through actual restore drills. Purge/anonymization is explicitly authorized,
audited, reference-safe, and reconciled with backup restoration.

## Evidence owners

S008-S011 verify authentication and account management; S019-S022 verify policy and file controls;
S026-S045 verify hostile archives and recovery; S053-S068 verify grades/re-import;
S075-S085 verify exports/revocation/governance; S088-S093 verify production limits
and recovery. S085 maintains an endpoint authorization inventory. Passing a local
test suite is not a claim of an independent penetration assessment.
