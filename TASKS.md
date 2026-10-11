# AArchive implementation plan

This is the detailed sprint backlog for the full project. The canonical SRS is
[docs/requirements.md](docs/requirements.md). The user-supplied ZIP inventory is
[docs/archive-layout.md](docs/archive-layout.md). Follow the repository layout in
[ARCHITECTURE.md](ARCHITECTURE.md) and working rules in [AGENTS.md](AGENTS.md).

## How to use this plan with GPT 6-Astra at High effort

A sprint means one bounded implementation task, not a calendar week. Start one
fresh task per sprint, with the same repository and the previous completed work
available. The cards are sized around one service, workflow step, screen family,
or verification gate; complex import and grading work is deliberately separated.
This is a sizing target, not a guarantee of one-shot success, a fixed token cost,
or a claim about the Plus plan's changing usage limits. Hardware access, schema
availability, unforeseen integration bugs, and external approvals can prevent a
sprint from finishing in one run.

Say either of these to an agent working in this repository:

```text
next task

whats next
```

Both mean **select and implement one ready sprint**, including its verification
and progress update. No sprint ID or extra confirmation is needed. AGENTS.md
defines the selection rules: resume a ready IN_PROGRESS card first, otherwise
take the lowest-ID TODO with all prerequisites DONE, within the earliest
unfinished phase. Skip BLOCKED cards and dependent work. If new evidence removes
a blocker, update that status before selection. If a selected card encounters an
external blocker, record it and continue to an independent ready card; if none
exists, report the actual missing input. Explicit status-only/no-edit requests
remain read-only. The helper prints context; the agent carries out the work.

Use `docs/progress.md` and the actual code for current implementation status.
Do not mark an implementation sprint complete based on planning files alone;
the helper selects from verified completion recorded in the ledger.

### Read only the context needed

- `python3 scripts/sprint_context.py --next` selects the next ready card and
  prints its focused context. Use `--next --brief` for only that card.
- `python3 scripts/sprint_context.py --list` prints the ID/title/dependency index.
- `python3 scripts/sprint_context.py S042` prints one card, referenced decision
  notes, and the relevant SRS sections, with overlapping sections deduplicated.
- `python3 scripts/sprint_context.py S042 --brief` prints the card only.
- `python3 scripts/sprint_context.py --check` checks IDs, dependencies, cycles,
  SRS/decision references, and progress rows. It does not run application tests.
- Read the API/database/security guide only when the card touches that concern.
  Read archive-layout.md for a mapper's specific paths. Do not repeatedly load the
  entire SRS, this complete backlog, a PDF, or all prior tool logs.

### Common implementation contract for every card

1. Check prerequisite statuses and inspect actual code. An earlier ID is not
   automatically completed. Keep the working tree's unrelated changes intact.
2. Establish the interface before internals: validate inputs, typed output/error
   shape, object scope, pagination, idempotency, and transaction boundary as
   applicable. Extend `docs/api.md` and `docs/database.md` when contracts change.
3. Implement the listed steps in the named areas; include migrations, serializers,
   policies, and UI behavior only as needed for this card. Named paths are target
   boundaries, not a claim that all files already exist.
4. Add behavior-focused tests for the card's risks and acceptance checks. Use
   PostgreSQL for constraints/concurrency. Use synthetic fixtures. Do not create
   snapshots/tests that merely repeat implementation text.
5. Run the touched backend/frontend gates and relevant integration checks. Run
   the broader CI gate at integration/release checkpoints or when a shared change
   requires it. Record actual commands, result, and environment; never claim an
   unrun check passed. A blocked required check means the sprint is not done.
6. Update `docs/progress.md`: status, evidence location/commit if one exists,
   concise handoff, and exact remaining blocker. Update architecture/decision
   records when behavior changes; document a migration or compatibility effect.

A normal implementation card should usually touch one module plus its tests/UI
and documentation. If it expands into unrelated services or multiple independent
features, split it into child IDs such as `S043A` and `S043B`, update dependencies
and the progress ledger, and retain the parent acceptance gate. Do not weaken the
acceptance checks to fit a single run. Schema intake, infrastructure integration,
and release cards are external gates and can be blocked despite correct work.

### Scope and ordering

- S001-S093 cover the entire MVP, including safe imports, all grading methods,
  non-contest assessments, reports in all three formats, visibility, governance,
  search, notifications, and operational readiness.
- S094-S103 implement Phase 2 after MVP. Provider-specific integrations require
  their actual contracts/credentials and authorization where data leaves IUT.
- S104-S108 implement Future scope after the stated institutional decisions.
- Default to ascending ID order, but the explicit dependency list is authoritative.
  If S025 is blocked by missing field-level schemas, S026-S029 archive-safety work,
  the account/course/policy lane, and S052-S053/S055-S062 manual-grading work can
  continue once their own prerequisites are done. S025-dependent adapters and a
  real-format release remain blocked. The pasted layout itself is already saved.
- Optional platform-side recalculated standings are not required for the MVP;
  the MVP reconstructs the imported official snapshots for display. If later
  requested, add a scoring-format-specific card after S047 with known expected
  rankings; never silently replace imported official standings.

## Phase index

| Range | Deliverable | Gate |
|---|---|---|
| S001-S011 | Contracts, reproducible app foundations, accounts, audit, roles | Real login and tested scope boundaries |
| S012-S020 | Academic structure, enrollment, groups, visibility | Course navigation and deny-by-default policy |
| S021-S032 | Storage, workers, schema intake, secure staged validation | No live rows before confirmation |
| S033-S045 | Archive mappers, identity review, commit and recovery | Verified UC-01/UC-02 with a trusted format |
| S046-S051 | Browsable archive and independently gated content | Official evidence accessible by policy |
| S052-S063 | Gradebook and publication | Traceable marks with correct student visibility |
| S064-S068 | Re-import and explicit re-application | University data survives new source versions |
| S069-S081 | Reports, analytics, exports, search, notifications | Scoped data across screens/files/jobs |
| S082-S093 | Governance, acceptance, performance, operations, release | Measured and rehearsed MVP release |
| S094-S103 | Phase 2 | Integration-specific acceptance |
| S104-S108 | Future scope | Institutional contracts and policies supplied |

## Sprint index


| Sprint | Outcome | Prerequisites |
|---|---|---|
| [S001](#s001) | Freeze implementation contracts and resolve remaining SRS ambiguities | None |
| [S002](#s002) | Create the backend skeleton and reproducible Python environment | S001 |
| [S003](#s003) | Create the frontend shell and shared interaction primitives | S001 |
| [S004](#s004) | Wire development services and continuous integration | S002, S003 |
| [S005](#s005) | Define platform users and account states | S002 |
| [S006](#s006) | Create the append-only audit service | S005 |
| [S007](#s007) | Implement the central role and scope policy interface | S005, S006 |
| [S008](#s008) | Implement session login and logout | S004, S005, S006, S007 |
| [S009](#s009) | Implement institutional registration and email verification | S008 |
| [S010](#s010) | Implement password recovery and lifecycle transitions | S008, S009 |
| [S011](#s011) | Build account administration and profile screens | S007, S009, S010 |
| [S012](#s012) | Model departments, batches, terms, and sections | S003, S005, S006, S007 |
| [S013](#s013) | Implement the reusable course catalog | S012 |
| [S014](#s014) | Implement offerings and multiple teacher assignments | S007, S012, S013 |
| [S015](#s015) | Implement enrollment and historical membership | S014 |
| [S016](#s016) | Implement CSV/XLSX account and enrollment import | S011, S015 |
| [S017](#s017) | Build course and roster navigation | S003, S014, S015 |
| [S018](#s018) | Implement Access Groups and delegated management | S007, S011 |
| [S019](#s019) | Implement component visibility resolution | S007, S014, S015, S018 |
| [S020](#s020) | Build visibility administration and preview | S019, S003 |
| [S021](#s021) | Implement storage adapters and asset metadata | S002, S006 |
| [S022](#s022) | Implement authorized asset delivery and HTML sanitization | S019, S021 |
| [S023](#s023) | Implement background job and transactional event foundations | S004, S006 |
| [S024](#s024) | Implement contests, import versions, and provenance models | S006, S014, S021 |
| [S025](#s025) | Onboard the supplied archive layout and actual format contract | S001 |
| [S026](#s026) | Create deterministic synthetic archive fixtures | S021, S024 |
| [S027](#s027) | Implement upload staging and import job creation | S008, S021, S023, S024 |
| [S028](#s028) | Implement ZIP inventory and path safety checks | S026, S027 |
| [S029](#s029) | Implement bounded extraction and recovery cleanup | S028, S021 |
| [S030](#s030) | Implement manifest parsing and the trusted schema registry | S025, S029 |
| [S031](#s031) | Implement checksum and streaming record validation | S030, S026 |
| [S032](#s032) | Implement reference and completeness validation | S031 |
| [S033](#s033) | Map contest and problem source records | S032, S024 |
| [S034](#s034) | Map users, participants, teams, and source access records | S032, S024 |
| [S035](#s035) | Map judging, submissions, and execution evidence | S032, S033, S034 |
| [S036](#s036) | Map official results and historical snapshots | S032, S033, S034 |
| [S037](#s037) | Map communication, materials, history, and presentation evidence | S032, S033, S034 |
| [S038](#s038) | Map restricted source data into isolated storage | S022, S032, S034 |
| [S039](#s039) | Classify new imports, duplicates, and existing contests | S024, S030 |
| [S040](#s040) | Implement deterministic identity candidates | S015, S034 |
| [S041](#s041) | Implement all four identity resolution choices | S011, S040 |
| [S042](#s042) | Build import validation and confirmation preview | S003, S027, S032, S039, S041 |
| [S043](#s043) | Commit a fully validated contest version atomically | S033, S034, S035, S036, S037, S038, S042, S023 |
| [S044](#s044) | Recover interrupted imports and clean staging safely | S043 |
| [S045](#s045) | Verify the complete first-import user journey | S025, S043, S044 |
| [S046](#s046) | Build contest overview and course associations | S019, S024, S033, S043 |
| [S047](#s047) | Build official standings and snapshot navigation | S036, S046 |
| [S048](#s048) | Build submission browsing and judging history | S035, S046 |
| [S049](#s049) | Build source and log inspection with field gates | S022, S048 |
| [S050](#s050) | Build problems, editorials, materials, and historical content pages | S022, S033, S037, S046 |
| [S051](#s051) | Complete personal archive navigation and history views | S017, S046, S047, S048, S050 |
| [S052](#s052) | Model manual and contest-derived assessments | S014, S024, S006 |
| [S053](#s053) | Implement marks, manual entry, and immutable adjustment history | S052 |
| [S054](#s054) | Assign draft marks from an imported version | S034, S036, S043, S053 |
| [S055](#s055) | Implement proportional, percentage, and threshold grading | S053 |
| [S056](#s056) | Implement weighted assessment aggregation | S052, S055 |
| [S057](#s057) | Implement best-N, drop-lowest, and bonus rules | S056 |
| [S058](#s058) | Define and parse the custom grading expression language | S055 |
| [S059](#s059) | Evaluate custom formulas with bounded traces | S058, S053 |
| [S060](#s060) | Build assessment setup and gradebook editing UI | S017, S053, S055, S056, S057, S059 |
| [S061](#s061) | Implement finalize, publish, lock, unlock, and correction | S053, S060, S023 |
| [S062](#s062) | Implement private notes and student-visible feedback | S053, S061 |
| [S063](#s063) | Build student marks and explainable totals | S054, S061, S062, S051 |
| [S064](#s064) | Compute immutable re-import differences | S035, S036, S037, S038, S039, S043 |
| [S065](#s065) | Build re-import review and conflict resolution UI | S042, S064 |
| [S066](#s066) | Promote re-import versions while preserving university data | S044, S064, S065 |
| [S067](#s067) | Implement explicit source-score re-application and remapping | S054, S061, S066 |
| [S068](#s068) | Verify re-import and academic preservation journeys | S063, S066, S067 |
| [S069](#s069) | Define report datasets, metric semantics, and permissions | S047, S048, S063 |
| [S070](#s070) | Implement the student performance report | S069 |
| [S071](#s071) | Implement problem and contest reports | S069 |
| [S072](#s072) | Implement course and batch reports | S069, S070, S071 |
| [S073](#s073) | Materialize analytics and invalidate stale aggregates | S023, S068, S069 |
| [S074](#s074) | Build role dashboards from existing datasets | S051, S063, S070, S072, S073 |
| [S075](#s075) | Implement safe CSV report serialization | S069, S070, S071, S072 |
| [S076](#s076) | Implement XLSX report serialization | S075 |
| [S077](#s077) | Implement paginated PDF reports | S069, S070, S071, S072 |
| [S078](#s078) | Wire asynchronous export jobs and download history | S023, S022, S075, S076, S077 |
| [S079](#s079) | Implement permission-filtered global and contextual search | S046, S050, S051, S072 |
| [S080](#s080) | Implement in-app notification storage and inbox | S005, S023 |
| [S081](#s081) | Connect required notification events and admin alerts | S044, S061, S062, S078, S080 |
| [S082](#s082) | Build governance, audit, and operational settings screens | S011, S020, S044, S073, S081 |
| [S083](#s083) | Implement recoverable contest deletion and restore | S046, S082 |
| [S084](#s084) | Implement controlled purge and account anonymization | S083, S068, S078 |
| [S085](#s085) | Verify cross-cutting authorization and concurrency | S068, S078, S079, S082, S084 |
| [S086](#s086) | Complete accessibility and responsive workflow checks | S060, S063, S074, S078, S082 |
| [S087](#s087) | Run MVP acceptance journeys and requirement coverage | S045, S068, S072, S078, S079, S081, S082, S084, S085, S086 |
| [S088](#s088) | Build repeatable scale benchmarks and agree budgets | S045, S073, S078, S079 |
| [S089](#s089) | Fix measured performance bottlenecks | S088 |
| [S090](#s090) | Package production services and safe deployment configuration | S004, S022, S023, S082, S087 |
| [S091](#s091) | Implement backup, restore, and disaster-recovery rehearsal | S084, S090 |
| [S092](#s092) | Deploy to staging and perform an operator rehearsal | S087, S089, S090, S091 |
| [S093](#s093) | Complete the MVP release and handover | S092 |
| [S094](#s094) | Implement one institutional SSO provider adapter | S093 |
| [S095](#s095) | Build SSO enrollment and account-linking UI | S094 |
| [S096](#s096) | Implement one enrollment synchronization adapter | S093, S016 |
| [S097](#s097) | Improve identity matching with reviewed suggestions | S093, S040, S041 |
| [S098](#s098) | Implement term archiving and course-structure cloning | S093, S014, S015, S052 |
| [S099](#s099) | Implement reusable grading templates | S093, S055, S056, S057, S059 |
| [S100](#s100) | Implement saved report filters and anonymized standings toggle | S093, S047, S072 |
| [S101](#s101) | Implement configurable branding and dark mode | S093, S086 |
| [S102](#s102) | Implement scoped public API tokens | S093, S085 |
| [S103](#s103) | Implement one code-similarity integration hook | S093, S038, S049 |
| [S104](#s104) | Implement integrity review workflow | S103 |
| [S105](#s105) | Implement formal signed contest-performance transcripts | S093, S063, S077, S091 |
| [S106](#s106) | Implement contest bookmarks and basic comparison dashboards | S093, S070, S071, S073 |
| [S107](#s107) | Implement advanced course and problem comparisons | S106, S072 |
| [S108](#s108) | Implement policy-driven retention automation | S093, S084, S091 |

## Detailed sprint cards

<a id="s001"></a>

### S001 - Freeze implementation contracts and resolve remaining SRS ambiguities

**Phase:** MVP
**Prerequisites:** None
**SRS sections:** 10, 13, 16.5, 40, 44, 50, Appendix C
**Decisions:** D01, D03, D04, D05, D07, D08, D12
**Work areas:** `docs/decisions/, docs/requirements.md, docs/decisions/README.md`
**Requirement focus:** Contract clarification

**Implementation steps**

1. Record the selected stack and module boundaries in short ADRs; list supported workflow states and ownership rules.
2. Reconcile team participants, multi-offering assessments, source namespace/contest identity, duplicate uniqueness, published corrections, and scoped account provisioning against D03-D08; update the repository SRS and a change note together.
3. Distinguish real-format schema input still needed from the supplied archive tree; keep unavailable master-prompt references explicitly external.
4. Record policy inheritance for shared contests and the privacy matrix used by all later endpoints. Choose routine defaults in DECISIONS; preserve unresolved external facts as named blockers.

**Acceptance checks**

- Every listed contradiction has one written implementation rule or an explicit blocking input with affected sprint IDs.
- SRS, decisions, ER cardinalities, and requirement IDs agree after the edits; no invented exporter field names.

**Boundary:** No application implementation, PDF regeneration, or schema fabrication.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s002"></a>

### S002 - Create the backend skeleton and reproducible Python environment

**Phase:** MVP
**Prerequisites:** S001
**SRS sections:** 17, 33, 56.1
**Decisions:** D01
**Work areas:** `backend/config/, backend/apps/, pyproject.toml, Python lockfile`

**Implementation steps**

1. Create a minimal Django/DRF project with development, test, and production settings split and environment-based configuration.
2. Configure PostgreSQL from environment variables and a health endpoint that reveals no secret settings.
3. Pin supported compatible dependencies in a lockfile; add formatter/linter and test runner configuration.
4. Write exact local install, migrate, run, and test commands in README; include a safe .env.example.

**Acceptance checks**

- A fresh environment installs from the lockfile and runs framework checks and the health test.
- Missing production secrets fail startup clearly; no SQLite-only assumptions enter production settings.

**Boundary:** No account migrations until S005; no business APIs.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s003"></a>

### S003 - Create the frontend shell and shared interaction primitives

**Phase:** MVP
**Prerequisites:** S001
**SRS sections:** 27, 28, 47, Appendix A
**Decisions:** D01
**Work areas:** `frontend/src/app/, frontend/src/components/, frontend/package.json`

**Implementation steps**

1. Create React/TypeScript/Vite with router, strict type checking, linting, component tests, and a committed lockfile.
2. Build a responsive shell, navigation slot, page heading, labeled form field, error summary, loading state, and empty-state components.
3. Add an API client wrapper for same-origin sessions, CSRF, typed errors, cancellation, and paginated responses.
4. Add a clearly synthetic development page demonstrating the primitives without pretending the backend features exist.

**Acceptance checks**

- Install, build, type check, and component tests pass from a clean checkout.
- Keyboard focus and error labels work at desktop and mobile widths; no credentials are stored in browser localStorage.

**Boundary:** No feature dashboards, generated production data, or second authentication scheme.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s004"></a>

### S004 - Wire development services and continuous integration

**Phase:** MVP
**Prerequisites:** S002, S003
**SRS sections:** 17, 55, 56
**Decisions:** D01
**Work areas:** `compose.yaml, .github/workflows/, scripts/, README.md`

**Implementation steps**

1. Add local PostgreSQL/Redis services with health checks and ignored persistent volumes; keep secrets in example-only configuration.
2. Make frontend development proxy /api to Django without disabling CSRF protections.
3. Add CI jobs for backend checks/tests with PostgreSQL and frontend lint/typecheck/build/tests using locked installs.
4. Document common start/stop/reset commands and a smoke route through the frontend proxy.

**Acceptance checks**

- CI configuration runs the actual repository commands and catches a deliberately failing local check during verification.
- Clean development startup reaches the backend through the frontend without cross-origin session hacks.

**Boundary:** No cloud deployment or external credentials required.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s005"></a>

### S005 - Define platform users and account states

**Phase:** MVP
**Prerequisites:** S002
**SRS sections:** 9, 16.1, 19, 44
**Decisions:** D02
**Work areas:** `backend/apps/accounts/models/, migrations/, tests/`
**Requirement focus:** AUTH-002, AUTH-003

**Implementation steps**

1. Create the custom User before the first account migration; normalize institutional email and constrain student IDs.
2. Define the fixed platform-role vocabulary, profile fields, lifecycle states, and minimal account manager.
3. Separate source identity from platform identity; prohibit source roles or imported hashes entering authentication fields.
4. Define state predicates for login, historical access, and suspension without deleting academic references.

**Acceptance checks**

- Database tests reject duplicate normalized emails/student IDs and preserve distinct NULL student IDs.
- Alumni remain eligible for login; suspended/archived/deleted accounts fail the active-session predicate.

**Boundary:** No registration UI or identity-import matching yet.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s006"></a>

### S006 - Create the append-only audit service

**Phase:** MVP
**Prerequisites:** S005
**SRS sections:** 18, 20, 42, 45
**Decisions:** D02
**Work areas:** `backend/apps/audit/, tests/`

**Implementation steps**

1. Add indexed audit entries for actor, action, target, before/after, reason, time, and safe request metadata.
2. Create a service used in the same transaction as protected mutations; redact secrets and bound stored payload sizes.
3. Support system actors and deleted-user references without losing history.
4. Expose an admin-scoped paginated read API only; document action naming and a coverage checklist for future modules.

**Acceptance checks**

- Rollback of a business transaction rolls back its audit entry; successful changes retain both.
- API callers cannot update/delete audit rows or read another scope; secret fields never appear in serialized audit data.

**Boundary:** No log dashboard or bulk event backfill.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s007"></a>

### S007 - Implement the central role and scope policy interface

**Phase:** MVP
**Prerequisites:** S005, S006
**SRS sections:** 9, 10, 18, 48
**Decisions:** D02, D04
**Work areas:** `backend/apps/access/, backend/apps/accounts/, tests/`

**Implementation steps**

1. Implement explicit role/grant checks and object-policy hooks with deny-by-default outcomes.
2. Provide shared authorization helpers for REST views, services, querysets, and future workers; use typed resource contexts.
3. Add admin role/grant mutation service with audit and no mass-assignment shortcut.
4. Create a role/object test matrix fixture including anonymous, owner student, other student, assigned teacher, unassigned teacher, and admin.

**Acceptance checks**

- An unassigned teacher and imported source administrator gain no object rights by default.
- List filtering and detail checks return consistent denial; privilege edits require authorized admin actions.

**Boundary:** No complete contest visibility resolver until S019.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s008"></a>

### S008 - Implement session login and logout

**Phase:** MVP
**Prerequisites:** S004, S005, S006, S007
**SRS sections:** 16.1, 18, 46
**Decisions:** D01, D02
**Work areas:** `backend/apps/accounts/auth/, frontend/src/features/auth/`
**Requirement focus:** AUTH-001

**Implementation steps**

1. Add login, current-session, and logout endpoints with Django session rotation, CSRF, and secure production cookie settings.
2. Build login and signed-in account UI using the shared API client.
3. Return generic invalid-credential errors and apply configurable rate limiting/temporary lockout with safe recovery.
4. Invalidate sessions when a forbidden account state is detected on an authenticated request.

**Acceptance checks**

- Valid login/logout works through a real browser flow; invalid login does not reveal account existence.
- CSRF, session fixation, lockout, and suspended-session cases are covered; passwords never reach audit payloads.

**Boundary:** No OAuth, registration, or password reset in this card.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s009"></a>

### S009 - Implement institutional registration and email verification

**Phase:** MVP
**Prerequisites:** S008
**SRS sections:** 16.1, 18, 30
**Decisions:** D02
**Work areas:** `backend/apps/accounts/registration/, frontend/src/features/auth/`
**Requirement focus:** AUTH-002

**Implementation steps**

1. Add domain allowlisting, verification token lifetime, optional admin approval, and a non-privileged pending Student state.
2. Implement registration and verify-email screens with generic responses, resend throttling, and one-use tokens.
3. Use console/test mail delivery locally and an environment-configured mail adapter for deployment.
4. Keep role selection and existing-account mutation outside the self-registration payload.

**Acceptance checks**

- Unapproved or unverified registrations cannot authenticate as an active account.
- Expired/replayed tokens, disallowed domains, and attempts to request Teacher/Admin roles fail without privilege escalation.

**Boundary:** No institutional SSO or bulk invitations.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s010"></a>

### S010 - Implement password recovery and lifecycle transitions

**Phase:** MVP
**Prerequisites:** S008, S009
**SRS sections:** 16.1, 18, 34
**Decisions:** D02
**Work areas:** `backend/apps/accounts/recovery/, frontend/src/features/auth/`
**Requirement focus:** AUTH-003

**Implementation steps**

1. Add generic password-reset request, expiring single-use reset confirmation, and password-change flow.
2. Implement audited admin lifecycle transitions with retained identity/history and session revocation.
3. Document the allowed state-transition table and how graduates/alumni retain access.
4. Connect the reset UI and account-state errors without disclosing whether an email exists.

**Acceptance checks**

- Tokens cannot be replayed; resetting a password invalidates required sessions and never exposes imported credential hashes.
- Graduation preserves historical login, while suspension immediately revokes authenticated access.

**Boundary:** No anonymization implementation until S084.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s011"></a>

### S011 - Build account administration and profile screens

**Phase:** MVP
**Prerequisites:** S007, S009, S010
**SRS sections:** 16.1, 20, 47, 48
**Decisions:** D02
**Work areas:** `backend/apps/accounts/api/, frontend/src/features/accounts/`
**Requirement focus:** AUTH-002

**Implementation steps**

1. Add paginated admin account list/detail/create and role/lifecycle actions, using existing services.
2. Build student/teacher filters, validation messages, explicit destructive-action review, and self-profile editing.
3. Restrict self-profile writable fields and prevent reassignment of verified identity/roles through profile endpoints.
4. Add invitation delivery for admin-created accounts with unusable initial passwords.

**Acceptance checks**

- Admin creation and invitation work end-to-end; ordinary users cannot enumerate the admin account list.
- Profile mass assignment cannot change role, student ID, lifecycle, or another account.

**Boundary:** No batch CSV upload or academic enrollment.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s012"></a>

### S012 - Model departments, batches, terms, and sections

**Phase:** MVP
**Prerequisites:** S003, S005, S006, S007
**SRS sections:** 13, 16.2, 43, 44
**Decisions:** D03
**Work areas:** `backend/apps/academics/structure/, migrations/, tests/`
**Requirement focus:** ADMIN-010

**Implementation steps**

1. Add Department, Batch, batch-scoped Term, and batch-scoped Section with archive flags and uniqueness constraints.
2. Provide admin CRUD/archive APIs and a minimal management page using shared form/table components.
3. Create an explicit ALL section for unsplit batches; preserve references when structural records are archived.
4. Validate parent membership and reject cycles or reparenting that would invalidate existing academic records.

**Acceptance checks**

- Cross-batch term/section assignments and duplicate labels fail at the data/service boundary.
- Archiving blocks new assignments while historical references remain readable; non-admin mutations are denied.

**Boundary:** No offerings or duplicate course catalogs per term.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s013"></a>

### S013 - Implement the reusable course catalog

**Phase:** MVP
**Prerequisites:** S012
**SRS sections:** 13, 16.2, 44, 47
**Decisions:** D03
**Work areas:** `backend/apps/academics/courses/, frontend/src/features/courses/`
**Requirement focus:** ADMIN-010

**Implementation steps**

1. Create department-owned Course with code, title, credits, description, and archive state.
2. Add admin create/edit/archive and permission-filtered catalog endpoints.
3. Build catalog list and edit screens with clear department context and validation.
4. Keep course identity independent of a batch/term so later offerings reuse the same record.

**Acceptance checks**

- Duplicate codes within a department fail; the same course can be referenced from multiple terms.
- Archiving a catalog course does not delete historical course data.

**Boundary:** No per-student grades or offering creation.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s014"></a>

### S014 - Implement offerings and multiple teacher assignments

**Phase:** MVP
**Prerequisites:** S007, S012, S013
**SRS sections:** 13, 16.2, 43, 44
**Decisions:** D03, D04
**Work areas:** `backend/apps/academics/offerings/, frontend/src/features/offerings/`
**Requirement focus:** ADMIN-010, COURSE-001

**Implementation steps**

1. Create Offering referencing Course, Batch, Term, and Section with matching-parent validation and uniqueness.
2. Allow authorized teachers/admins to create offerings; attach the creator through an audited assignment service.
3. Implement multi-teacher assignment/removal, detail/settings APIs, and a small offering editor.
4. Retain assignment history and revoke removed teachers scope immediately without rewriting authorship.

**Acceptance checks**

- Mismatched department/batch/term/section tuples and duplicate offerings are rejected.
- Removing a teacher revokes writes immediately; a second assigned teacher has the documented co-teacher rights.

**Boundary:** No enrollment import or contest-level global permission inheritance.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s015"></a>

### S015 - Implement enrollment and historical membership

**Phase:** MVP
**Prerequisites:** S014
**SRS sections:** 13, 20, 38, 43
**Decisions:** D02, D03
**Work areas:** `backend/apps/academics/enrollment/, frontend/src/features/offerings/`

**Implementation steps**

1. Add enrollment with effective dates/status and stable links to user and offering.
2. Implement add/remove/restore enrollment services, audit, scoped APIs, and roster UI.
3. Define active versus historical roster queries so past marks and participation remain attributable.
4. Prevent a teacher from enrolling or mutating students in an unassigned offering.

**Acceptance checks**

- Withdrawal revokes current course access as documented without deleting prior marks/participation references.
- Duplicate enrollments and unauthorized roster mutations fail; date boundaries are tested.

**Boundary:** No bulk spreadsheet ingestion.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s016"></a>

### S016 - Implement CSV/XLSX account and enrollment import

**Phase:** MVP
**Prerequisites:** S011, S015
**SRS sections:** 16.1, 20, 52, 53
**Decisions:** D02, D03
**Work areas:** `backend/apps/accounts/bulk/, frontend/src/features/accounts/`
**Requirement focus:** AUTH-002

**Implementation steps**

1. Publish exact CSV/XLSX templates for account and enrollment fields with header mapping and size/row limits.
2. Implement admin-only parse, preview, row-level validation, deterministic duplicate handling, and explicit confirmation.
3. Reuse account-provisioning and enrollment services; do not overwrite existing roles/passwords or silently merge ambiguous identities.
4. Build upload/preview/result UI and document partial-row failure versus all-or-nothing batch behavior.

**Acceptance checks**

- Mixed new/existing users and invalid offering rows produce a deterministic preview and matching commit result.
- Formula-like spreadsheet strings are treated as values, macros are not executed, and repeat confirmation is idempotent.

**Boundary:** No automatic institutional synchronization until Phase 2.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s017"></a>

### S017 - Build course and roster navigation

**Phase:** MVP
**Prerequisites:** S003, S014, S015
**SRS sections:** 27, 28, 47, 48
**Decisions:** D02, D03
**Work areas:** `frontend/src/features/courses/, frontend/src/features/offerings/`

**Implementation steps**

1. Build My Courses, Course Details, offering selector, assigned teachers, and roster screens.
2. Use server-authorized datasets; keep teacher-only controls separate from student-readable fields.
3. Add pagination, loading/empty/denied states, accessible labels, and mobile overflow behavior.
4. Link future contest/gradebook slots only when their routes exist; do not show fabricated statistics.

**Acceptance checks**

- Teachers see only assigned scope; students see active/historical access according to the membership policy.
- Keyboard navigation and a narrow viewport work without exposing hidden roster fields.

**Boundary:** No analytics dashboards or gradebook implementation.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s018"></a>

### S018 - Implement Access Groups and delegated management

**Phase:** MVP
**Prerequisites:** S007, S011
**SRS sections:** 11, 16.5, 20, 38
**Decisions:** D02, D04
**Work areas:** `backend/apps/access/groups/, frontend/src/features/access/`
**Requirement focus:** VISIBILITY-002

**Implementation steps**

1. Add AccessGroup and membership with uniqueness, audited mutations, and explicit manager grants.
2. Build scoped list/create/member add/remove/archive APIs and a simple management UI.
3. Allow teacher management only through the documented delegation capability.
4. Preserve a deleted/archived group reference for fail-closed policy evaluation; invalidate membership cache after changes.

**Acceptance checks**

- Removing membership or archiving a referenced group never opens access to everyone.
- An unrelated teacher cannot manage members; duplicate memberships are rejected.

**Boundary:** No component-policy inheritance editor yet.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s019"></a>

### S019 - Implement component visibility resolution

**Phase:** MVP
**Prerequisites:** S007, S014, S015, S018
**SRS sections:** 11, 16.5, 18, 19, 48
**Decisions:** D04
**Work areas:** `backend/apps/access/policies/, tests/`
**Requirement focus:** VISIBILITY-001, VISIBILITY-002, VISIBILITY-003

**Implementation steps**

1. Define policies/rules for system, course, contest, and component overrides with parameterized department/batch/course/group scopes.
2. Implement one resolver that applies hard privacy ceilings, parent gates, inheritance, group OR, and cross-rule AND.
3. Handle shared-contest inheritance conservatively and distinguish HIDDEN/ARCHIVED/access lifecycle from public data.
4. Expose a pure decision/explanation interface for services and admin previews; do not reveal explanations to unauthorized viewers.

**Acceptance checks**

- Matrix tests cover all policy types, anonymous access, unrelated teachers, hidden tests, and own versus others marks.
- Deleted groups and conflicting inherited policies fail closed; role/group union cannot bypass a privacy ceiling.

**Boundary:** No frontend policy editor or raw policy bypass in serializers.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s020"></a>

### S020 - Build visibility administration and preview

**Phase:** MVP
**Prerequisites:** S019, S003
**SRS sections:** 16.5, 20, 28
**Decisions:** D04
**Work areas:** `backend/apps/access/api/, frontend/src/features/access/`
**Requirement focus:** VISIBILITY-001

**Implementation steps**

1. Add authorized policy read/write APIs with schema validation and audited before/after values.
2. Build component tabs, inheritance explanation, allowed audience controls, and a simulated-viewer preview.
3. Reject impossible settings such as PUBLIC marks, public teacher reports, or group access overriding restricted.view.
4. Show policy effects on shared contests and require scoped contest-management rights for global changes.

**Acceptance checks**

- UI and API both reject invalid widening; saving an override changes the same resolver used for requests.
- Unauthorized users cannot enumerate membership or preview another users hidden data.

**Boundary:** No new permission semantics hidden inside frontend code.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s021"></a>

### S021 - Implement storage adapters and asset metadata

**Phase:** MVP
**Prerequisites:** S002, S006
**SRS sections:** 18, 25, 31
**Decisions:** D05, D07
**Work areas:** `backend/apps/assets/storage/, tests/`

**Implementation steps**

1. Create local-development and S3-compatible storage adapters with opaque object keys and streaming upload/download interfaces.
2. Add asset metadata for digest, bytes, MIME, visibility classification, version references, and retention status.
3. Implement immutable staging/final object naming and reference tracking without storing large blobs in PostgreSQL.
4. Provide fake storage and failure injection for import tests; document private bucket configuration.

**Acceptance checks**

- Adapter contract tests cover missing objects, interrupted writes, duplicate content, and reference-safe cleanup.
- API-facing metadata never contains raw filesystem paths, credentials, or permanent public bucket URLs.

**Boundary:** No public asset routes or production bucket creation.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s022"></a>

### S022 - Implement authorized asset delivery and HTML sanitization

**Phase:** MVP
**Prerequisites:** S019, S021
**SRS sections:** 18, 19, 31
**Decisions:** D04, D07
**Work areas:** `backend/apps/assets/serving/, backend/apps/assets/sanitization/`

**Implementation steps**

1. Route file reads through current policy checks or short-lived scoped signed URLs; enforce expiry and safe filenames.
2. Implement allowlist HTML sanitization and isolated rendering rules for imported descriptions/statements.
3. Serve executable/source content as inert text or attachment with appropriate content type and nosniff; never execute it.
4. Keep hidden tests, restricted evidence, and logs in separately classified access paths.

**Acceptance checks**

- Stored-XSS, MIME spoofing, path traversal, expired URL, and hidden-test access cases fail safely.
- Changing permissions prevents newly issued access and invalidates cached delivery metadata as designed.

**Boundary:** No browser rendering of arbitrary imported scripts or branding.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s023"></a>

### S023 - Implement background job and transactional event foundations

**Phase:** MVP
**Prerequisites:** S004, S006
**SRS sections:** 15, 20, 26, 30
**Decisions:** D07
**Work areas:** `backend/apps/imports/jobs/, backend/apps/audit/outbox/, backend/config/`

**Implementation steps**

1. Configure Celery/Redis and define job status, heartbeat, bounded retry, cancellation, and correlation-ID conventions.
2. Add a transactional outbox for durable post-commit work and a deduplicating dispatcher.
3. Provide worker health/status API accessible only in scope, and a fake task runner for tests.
4. Document failure recovery and ensure task payloads contain IDs rather than large archives or secrets.

**Acceptance checks**

- A crash after commit but before queue publication is recovered by the outbox dispatcher.
- Repeated delivery invokes an idempotent handler and does not create duplicate completion events.

**Boundary:** No import business mappings or notification UI.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s024"></a>

### S024 - Implement contests, import versions, and provenance models

**Phase:** MVP
**Prerequisites:** S006, S014, S021
**SRS sections:** 14, 15.4, 33, 40, 43, 44
**Decisions:** D03, D05, D07
**Work areas:** `backend/apps/contests/models/, backend/apps/imports/models/, migrations/`

**Implementation steps**

1. Add Contest, ContestImport job, immutable ContestImportVersion, current-version pointer, and contest/offering association.
2. Define stable source-key namespaces, unique version references, and distinct university-owned overlay fields.
3. Add source-record base interfaces and version-keyed asset relationships; keep source and platform audit models separate.
4. Create synthetic factories for a two-version contest without enabling real-format imports.

**Acceptance checks**

- Constraints prevent two current versions and duplicate stable source identities within the documented namespace.
- A source-version change cannot overwrite a university overlay or orphan existing referenced assets.

**Boundary:** No guessed concrete JSON field adapter or transaction orchestration.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s025"></a>

### S025 - Onboard the supplied archive layout and actual format contract

**Phase:** MVP
**Prerequisites:** S001
**SRS sections:** 11, 14, 16.3, 23, Appendix C
**Decisions:** D05, D06
**Work areas:** `docs/archive-layout.md, docs/archive-contract.md, backend/apps/imports/schemas/`
**Requirement focus:** IMPORT-002, IMPORT-003

**Implementation steps**

1. Use the owners verbatim tree as the file inventory: contest, people, problems, judging, submissions, results, communication, materials, history, presentation, files, restricted, and reports.
2. Obtain literal independently trusted schema definitions and exporter field documentation; record version, JSON Schema draft, hashes, provenance, units, IDs, optionality, and redistribution status.
3. Build a file-to-schema mapping including standings snapshots, revision problem.json files, and every JSONL row type; resolve ambiguities with exporter evidence.
4. If definitions are unavailable, write the exact missing-input checklist and mark this sprint blocked; do not guess a schema and call it production support.

**Acceptance checks**

- Every documented structured file maps to a trusted schema or an explicitly documented version-specific exclusion.
- A sample validates against pinned schemas and stable source IDs are understood; otherwise completion remains blocked while independent sprints proceed.

**Boundary:** The pasted directory tree alone is not a field-level schema. No live judge integration.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s026"></a>

### S026 - Create deterministic synthetic archive fixtures

**Phase:** MVP
**Prerequisites:** S021, S024
**SRS sections:** 14, 23, 24, 55
**Decisions:** D05, D06
**Work areas:** `tests/fixtures/archives/, scripts/generate_test_archives.py`

**Implementation steps**

1. Build a deterministic tiny fixture generator with a clearly test-only format identifier and test-only schema adapter.
2. Represent individual/team contests, excluded/empty/truncated sections, multi-file source, nested revision files, and two import versions.
3. Generate corrupt checksums, duplicate paths, traversal names, oversized counters, and dangling references without committing huge malicious binaries.
4. Keep fixture seeds, expected summaries, and generated tiny ZIPs redistributable; production settings must reject this test format.

**Acceptance checks**

- Two runs with the same seed produce the same logical payload and checksums.
- Fixtures contain no real people, passwords, or private evidence; production format allowlist excludes the test adapter.

**Boundary:** No claim of compatibility with the actual exporter; S025 remains a separate gate.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s027"></a>

### S027 - Implement upload staging and import job creation

**Phase:** MVP
**Prerequisites:** S008, S021, S023, S024
**SRS sections:** 15, 16.3, 18, 23
**Decisions:** D07
**Work areas:** `backend/apps/imports/upload/, tests/`
**Requirement focus:** IMPORT-001

**Implementation steps**

1. Add scoped streaming ZIP upload with maximum request size, type checks, rate limits, and random isolated staging keys.
2. Compute the ZIP digest incrementally and persist uploader/context/job metadata before queue dispatch.
3. Authorize assigned-offering imports and teacher-created unassociated contests without granting global course rights.
4. Return a job ID and bounded status endpoint; clean abandoned uploads by an explicit TTL policy.

**Acceptance checks**

- Oversized/non-ZIP requests and unauthorized course contexts fail without production contest rows.
- Interrupted upload cleanup and queued-job retry preserve a recoverable status without loading the full archive into RAM.

**Boundary:** No extraction or live Contest creation.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s028"></a>

### S028 - Implement ZIP inventory and path safety checks

**Phase:** MVP
**Prerequisites:** S026, S027
**SRS sections:** 16.3, 18, 23, 55
**Decisions:** D06, D07
**Work areas:** `backend/apps/imports/security/zip_inventory.py, tests/`
**Requirement focus:** IMPORT-SEC-001

**Implementation steps**

1. Inspect archive metadata before extraction; reject absolute paths, traversal, symlink-like entries, duplicate/colliding normalized paths, unsupported encryption, and unsupported entry types.
2. Enforce entry count, declared sizes, nesting depth, and compression-ratio limits with configurable safe defaults.
3. Normalize separator/Unicode/case behavior consistently with the storage destination and record precise stage errors.
4. Treat reported sizes as untrusted hints and pass a validated inventory to the extractor.

**Acceptance checks**

- Adversarial path fixtures never create files outside staging; duplicate names cannot shadow manifest or schema files.
- Limit boundaries and deceptive metadata are tested; no checksum failure can be waived by a teacher.

**Boundary:** No extraction, JSON parsing, or source data mappings.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s029"></a>

### S029 - Implement bounded extraction and recovery cleanup

**Phase:** MVP
**Prerequisites:** S028, S021
**SRS sections:** 15, 16.3, 23, 24, 39
**Decisions:** D07
**Work areas:** `backend/apps/imports/security/extract.py, tests/`
**Requirement focus:** IMPORT-SEC-001

**Implementation steps**

1. Extract only validated inventory entries into an isolated staging directory using safe path resolution.
2. Enforce actual expanded byte, per-file, ratio, and time/resource budgets while streaming; do not trust ZIP headers.
3. Persist stage progress and make retry cleanup safe after worker interruption.
4. Retain the original ZIP only for the documented success/failure retention period; separate diagnostic logs from private content.

**Acceptance checks**

- Runtime counters stop a deceptive compressed fixture before crossing configured limits.
- A simulated crash leaves no path escape and a retry safely recreates only its own staging directory.

**Boundary:** No arbitrary subprocess calls or execution of archived checkers/validators.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s030"></a>

### S030 - Implement manifest parsing and the trusted schema registry

**Phase:** MVP
**Prerequisites:** S025, S029
**SRS sections:** 11, 14, 16.3, 23
**Decisions:** D05, D06
**Work areas:** `backend/apps/imports/validation/manifest.py, schema_registry.py`
**Requirement focus:** IMPORT-002

**Implementation steps**

1. Parse a size-bounded manifest using pinned bootstrap rules; use the declared supported format version to select the trusted registry entry.
2. Validate file inventory, expected counts, availability/exclusion declarations, timestamps, and known version-specific requirements.
3. Compare archive schema copies to the pinned trusted definitions using the documented comparison rule.
4. Disable network/filesystem resolution of untrusted schema references and bound validator recursion/resource usage.

**Acceptance checks**

- Unknown versions, modified schema copies, remote references, and missing required files fail closed.
- An explicitly excluded optional area differs from empty, unavailable, truncated, and corrupted data.

**Boundary:** No best-effort parsing of unsupported production formats.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s031"></a>

### S031 - Implement checksum and streaming record validation

**Phase:** MVP
**Prerequisites:** S030, S026
**SRS sections:** 14, 16.3, 23, 24, 26
**Decisions:** D06, D07
**Work areas:** `backend/apps/imports/validation/checksums.py, records.py`
**Requirement focus:** IMPORT-003, IMPORT-SEC-001

**Implementation steps**

1. Require one checksum entry for every regular file except the checksum file itself; reject omitted/extra/duplicate entries.
2. Stream file hashing and JSONL validation against the pinned record schemas with line-numbered errors and bounded line size.
3. Validate JSON files with a size-aware parser; handle large results arrays without unbounded memory assumptions.
4. Keep imported values and unavailable-state metadata intact; return validated staging records, not live model rows.

**Acceptance checks**

- A one-byte change, missing checksum entry, invalid JSONL line, or weakened supplied schema blocks confirmation.
- Validation of a generated large stream demonstrates bounded memory; checksums are not presented as proof of origin.

**Boundary:** No teacher exclusion override for integrity errors.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s032"></a>

### S032 - Implement reference and completeness validation

**Phase:** MVP
**Prerequisites:** S031
**SRS sections:** 16.3, 24, 38, 39
**Decisions:** D05, D07
**Work areas:** `backend/apps/imports/validation/references.py, tests/`
**Requirement focus:** IMPORT-004, IMPORT-009

**Implementation steps**

1. Build disk/database-backed staging indexes for source IDs and file references to avoid retaining millions of keys in process memory.
2. Validate required and optional cross-record references, per-version uniqueness, asset references, and declared record counts.
3. Specify which dangling references block import and how tolerated missing optional data is represented without dropping records.
4. Produce deterministic warning/error summaries and a normalized validation report for preview.

**Acceptance checks**

- An unresolved required submission participant/problem blocks import; optional missing evidence stays visibly unavailable.
- Count mismatches and duplicate source IDs fail before commit; staging indexes survive retry cleanly.

**Boundary:** No live record insertion or silent repair of source evidence.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s033"></a>

### S033 - Map contest and problem source records

**Phase:** MVP
**Prerequisites:** S032, S024
**SRS sections:** 14, 33, 40
**Decisions:** D05, D06
**Work areas:** `backend/apps/imports/adapters/contest.py, problems.py, backend/apps/contests/`

**Implementation steps**

1. Implement validated adapter mappings for contest identity/settings/schedule/scoring/access/organizers and problem metadata.
2. Map tests, test groups, checker/validator/generator/reference-solution/editorial/attachment metadata and revision references.
3. Keep schedule units, pauses, source rules, visibility evidence, and raw provenance without converting source policies into platform permissions.
4. Produce version-scoped normalized batches and asset references through a stable adapter interface.

**Acceptance checks**

- Golden fixtures round-trip meaningful source values and retain excluded/truncated markers.
- Checker commands and source roles remain inert data; applying the adapter cannot publish files or execute code.

**Boundary:** No final standings calculation or platform visibility changes.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s034"></a>

### S034 - Map users, participants, teams, and source access records

**Phase:** MVP
**Prerequisites:** S032, S024
**SRS sections:** 11, 14, 16.3, 40
**Decisions:** D03, D05, D07
**Work areas:** `backend/apps/imports/adapters/people.py, backend/apps/contests/people/`

**Implementation steps**

1. Map imported users, individual/team participants, teams, time-aware membership, registrations, source access grants, and source role assignments.
2. Keep source identities namespaced and separate from platform Users and platform grants.
3. Handle a team participant without inventing an individual owner, and preserve participants whose optional profile record is missing.
4. Emit identity candidates for later mapping without creating or altering accounts.

**Acceptance checks**

- Team submissions resolve to a team participant and preserve all memberships.
- A source administrator and source account-migration data cannot change platform role or password fields.

**Boundary:** No automatic account creation, mapping confirmation, or team grade assignment.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s035"></a>

### S035 - Map judging, submissions, and execution evidence

**Phase:** MVP
**Prerequisites:** S032, S033, S034
**SRS sections:** 14, 26, 40, 45
**Decisions:** D05, D06
**Work areas:** `backend/apps/imports/adapters/submissions.py, judging.py`

**Implementation steps**

1. Map judge environment/languages/configurations/profiles/dependency inventory as historical snapshots.
2. Stream submissions, judging runs, test results, score adjustments, rejudge history, and deletion history into bounded normalized batches.
3. Preserve multi-file sources, skipped tests, truncated outputs, time/memory units, active state, and multiple rejudge attempts.
4. Define version-scoped uniqueness and indexes for contest/participant/problem/run queries.

**Acceptance checks**

- Fixture tests preserve every judging attempt and distinguish missing output from empty output.
- Bulk mapping has bounded memory and never executes compile/run commands or opens arbitrary archive paths.

**Boundary:** No live judging or recomputed verdicts.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s036"></a>

### S036 - Map official results and historical snapshots

**Phase:** MVP
**Prerequisites:** S032, S033, S034
**SRS sections:** 14, 16.7, 24, 40
**Decisions:** D05, D06
**Work areas:** `backend/apps/imports/adapters/results.py, backend/apps/contests/results/`

**Implementation steps**

1. Map final/frozen standings, timestamped snapshots, participant results, statistics, awards, and certificates.
2. Retain rank, ties, penalties, per-problem results, inclusion/disqualification flags, source rule versions, and snapshot times.
3. Represent missing/excluded standings explicitly and preserve source-calculated statistics separately from platform aggregates.
4. Attach source and asset provenance so an official row can be traced to its import version.

**Acceptance checks**

- Frozen and final tables remain distinct; ties and disqualified/unofficial participants retain source semantics.
- Missing final standings produce unavailable data rather than fabricated zero participants.

**Boundary:** No recalculated ranking engine or report UI.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s037"></a>

### S037 - Map communication, materials, history, and presentation evidence

**Phase:** MVP
**Prerequisites:** S032, S033, S034
**SRS sections:** 14, 18, 31
**Decisions:** D05, D06
**Work areas:** `backend/apps/imports/adapters/history.py, communication.py, materials.py`

**Implementation steps**

1. Map announcements, clarifications and edits, historical notifications, materials, contest events, configuration changes, problem revisions, admin actions, and source audit events.
2. Preserve audiences and private clarification visibility; do not replay historical notifications as new platform messages.
3. Store presentation/branding/navigation/localization and asset references as inert source snapshots; platform navigation remains separately configured.
4. Classify reports/*.csv and PDF as derived non-authoritative artifacts, and document their retention choice without importing them as facts.

**Acceptance checks**

- Private clarification bodies remain protected and imported audit records stay separate from platform AuditLog.
- Changing imported navigation or source branding cannot change application routes, permissions, or trusted HTML.

**Boundary:** No live clarification system, notification resend, or platform rebranding.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s038"></a>

### S038 - Map restricted source data into isolated storage

**Phase:** MVP
**Prerequisites:** S022, S032, S034
**SRS sections:** 14, 18, 19, 31
**Decisions:** D04, D05, D06
**Work areas:** `backend/apps/imports/adapters/restricted.py, backend/apps/assets/`

**Implementation steps**

1. Map optional account-migration, contest credentials, workstation records, integrity reports, administrative notes, and evidence as restricted evidence.
2. Protect structured fields as well as files with restricted.view and omit them from public/student serializers, search, and diagnostics.
3. Keep credential hashes inert, inaccessible to authentication logic, and redacted from import summaries.
4. Preserve absence/exclusion indicators and restricted asset references without revealing sensitive filenames to normal viewers.

**Acceptance checks**

- A teacher without restricted.view and every student/anonymous viewer are denied across detail, files, exports, and errors.
- Imported passwords/roles do not affect login or platform privileges; missing restricted data is handled distinctly from empty data.

**Boundary:** No credential migration, integrity adjudication, or automatic account merge.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s039"></a>

### S039 - Classify new imports, duplicates, and existing contests

**Phase:** MVP
**Prerequisites:** S024, S030
**SRS sections:** 15.4, 16.3, 44, 51
**Decisions:** D05, D07
**Work areas:** `backend/apps/imports/classification.py, tests/`
**Requirement focus:** IMPORT-005

**Implementation steps**

1. Use verified source installation plus stable contest ID for existing-contest detection; keep export ID separate.
2. Compare content hashes under a well-defined contest scope and classify new/re-import/exact duplicate before preview.
3. Create race-safe database constraints and a scoped advisory/row-lock strategy for competing imports.
4. Expose classification and previous version metadata without exposing contests the uploader cannot manage.

**Acceptance checks**

- Two exports of one contest classify as re-import, while equal local IDs from different source installations remain distinct.
- Concurrent duplicate uploads cannot create duplicate live contests; unassigned uploaders cannot infer private contest existence.

**Boundary:** No full field diff or version promotion yet.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s040"></a>

### S040 - Implement deterministic identity candidates

**Phase:** MVP
**Prerequisites:** S015, S034
**SRS sections:** 16.3, 19, 36, 38
**Decisions:** D02, D05
**Work areas:** `backend/apps/imports/identity/candidates.py, tests/`
**Requirement focus:** IMPORT-006

**Implementation steps**

1. Generate deterministic candidate matches using verified student IDs and documented source namespace mappings; treat email/username heuristics conservatively.
2. Persist reusable source-to-platform mapping metadata with method, actor, time, and confidence as explanation only.
3. Detect one-to-many/many-to-one ambiguity and conflicting existing mappings without auto-assignment.
4. Return scoped candidate summaries that do not leak unrelated student profiles.

**Acceptance checks**

- Two plausible students or duplicate source users require manual resolution and never pick the first database row.
- A prior deterministic mapping is reused only for the same trusted namespace and stable source identity.

**Boundary:** No user creation or production mapping mutation during automatic preview.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s041"></a>

### S041 - Implement all four identity resolution choices

**Phase:** MVP
**Prerequisites:** S011, S040
**SRS sections:** 16.3, 20, 36
**Decisions:** D05, D07
**Work areas:** `backend/apps/imports/identity/resolution.py, frontend/src/features/imports/`
**Requirement focus:** IMPORT-006

**Implementation steps**

1. Implement placeholder, remain-unmapped, map-existing, and request-full-account resolution with bulk defaults and per-row override.
2. Provide a scoped candidate picker and explanations for unresolved/ambiguous identities.
3. Delegate explicit full-account requests to the narrow provisioning service from D07; never update an existing account role/password.
4. Persist a revisioned staging mapping plan, audit changes, and block stale confirmation when the plan changes.

**Acceptance checks**

- Each of the four strategies has a tested resulting state, including team members and unverified new accounts.
- An unauthorized account/role mutation is rejected; canceling the import cannot leave hidden live mappings.

**Boundary:** No forced mapping for every participant or automatic privilege transfer.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s042"></a>

### S042 - Build import validation and confirmation preview

**Phase:** MVP
**Prerequisites:** S003, S027, S032, S039, S041
**SRS sections:** 15, 16.3, 24, 28, 36
**Decisions:** D06, D07
**Work areas:** `frontend/src/features/imports/, backend/apps/imports/preview/`
**Requirement focus:** IMPORT-007

**Implementation steps**

1. Build upload progress, validation status, stage-tagged error/warning list, counts, availability states, identity decisions, and classification views.
2. Bind preview to ZIP digest, validation result, source version, and mapping-plan revision.
3. Create a confirmation command contract that rechecks current authority and the preview fingerprint.
4. Display hard failures as non-confirmable; show missing trusted format definitions as an actionable format-support limitation.

**Acceptance checks**

- No production Contest/Submission/StandingEntry exists before confirmation; stale preview confirmation is rejected.
- Private paths and stack traces stay out of UI; a corrected upload can be retried through the same guided flow.

**Boundary:** No live commit until S043 or checksum waiver control.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s043"></a>

### S043 - Commit a fully validated contest version atomically

**Phase:** MVP
**Prerequisites:** S033, S034, S035, S036, S037, S038, S042, S023
**SRS sections:** 15, 16.3, 33, 39
**Decisions:** D05, D07
**Work areas:** `backend/apps/imports/commit.py, backend/apps/contests/`
**Requirement focus:** IMPORT-008, IMPORT-009

**Implementation steps**

1. Compose the completed mappers into bounded database batch inserts under one logical import transaction.
2. Verify staging fingerprint, current permission, durable asset existence, all required references, and declared counts before publication.
3. Atomically create the version, switch the current pointer, apply explicitly confirmed mappings, append audit, and write outbox events.
4. Make confirmation/job retries idempotent and preserve separately authorized account-provisioning provenance.

**Acceptance checks**

- Injected failure halfway through inserts or at the pointer switch leaves the prior live state unchanged.
- A successful commit exposes all expected rows/assets exactly once and refuses unexplained count differences.

**Boundary:** No re-import diff acceptance or automatic overwrite of existing academic records.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s044"></a>

### S044 - Recover interrupted imports and clean staging safely

**Phase:** MVP
**Prerequisites:** S043
**SRS sections:** 15, 25, 31, 39
**Decisions:** D05, D07
**Work areas:** `backend/apps/imports/recovery.py, cleanup.py, tests/`

**Implementation steps**

1. Implement heartbeat timeout/retry handling for validation and import workers with clear terminal states.
2. Reconcile committed versions, staged blobs, outbox records, and orphaned objects after crashes at each boundary.
3. Apply success ZIP purge and configurable failed-upload retention while preserving useful redacted logs.
4. Add operational status/actions for retry and cancel without reusing an invalid preview authorization.

**Acceptance checks**

- Crash injection before/after object persistence, DB commit, and queue dispatch converges to one complete version or no live change.
- Cleanup never deletes assets referenced by another import/version and never removes a still-active upload.

**Boundary:** No generic storage purge or production-wide repair scripts.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s045"></a>

### S045 - Verify the complete first-import user journey

**Phase:** MVP
**Prerequisites:** S025, S043, S044
**SRS sections:** 36, 37, 39, 55
**Decisions:** D06, D07
**Work areas:** `tests/integration/imports/, frontend/e2e/imports/, docs/runbooks/`

**Implementation steps**

1. Run upload through validation, all mapping choices, preview, confirmation, and completion using an approved-format synthetic archive.
2. Exercise validation failure, stale preview, worker restart, and exact-duplicate paths in integration tests.
3. Write a concise operator import/retry guide and record actual supported archive versions.
4. Fix only failures in this end-to-end path; split unrelated issues into named follow-up cards.

**Acceptance checks**

- UC-01 and UC-02 pass with the real trusted format adapter, and failed imports preserve existing records.
- All supported record categories, asset counts, and missing-data states match expected fixtures; test-only adapters alone cannot satisfy this gate.

**Boundary:** No MVP launch claim or unsupported-format compatibility claim.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s046"></a>

### S046 - Build contest overview and course associations

**Phase:** MVP
**Prerequisites:** S019, S024, S033, S043
**SRS sections:** 16.4, 27, 28, 47
**Decisions:** D03, D04, D05
**Work areas:** `backend/apps/contests/api/, frontend/src/features/contests/`
**Requirement focus:** CONTEST-001, CONTEST-002

**Implementation steps**

1. Add permission-filtered contest list/detail APIs and pages for title, schedule, source, tags, organizers, overview, and availability.
2. Allow authorized management of university tags, offering associations, and overlay corrections with audit.
3. Keep imported source text/evidence immutable and show current-version provenance.
4. Respect public/academic/group gates and unassociated-contest ownership in lists and details.

**Acceptance checks**

- A public contest appears to anonymous users only for permitted components; private contests leave no list/count leak.
- Changing tags or associations does not overwrite imported fields or expose another offering grades.

**Boundary:** No standings, source-code viewer, or report aggregation in this card.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s047"></a>

### S047 - Build official standings and snapshot navigation

**Phase:** MVP
**Prerequisites:** S036, S046
**SRS sections:** 16.7, 24, 27, 47
**Decisions:** D04, D05
**Work areas:** `backend/apps/contests/standings/, frontend/src/features/standings/`
**Requirement focus:** STANDING-001

**Implementation steps**

1. Expose paginated official standings by contest/version/snapshot with stable tie handling and per-problem detail.
2. Build final/frozen/historical snapshot selector, labels, sortable permitted fields, and responsive table behavior.
3. Render unavailable/excluded/empty/truncated states distinctly and preserve unofficial/disqualified status.
4. Ensure identities and fields follow current contest policy and row-level privacy decisions.

**Acceptance checks**

- Final and frozen views never overwrite each other; imported rank/score values match fixtures.
- A missing final snapshot has an explanation rather than a fabricated zero table, and unauthorized users cannot fetch alternate snapshots.

**Boundary:** No independent recalculated scoring algorithm.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s048"></a>

### S048 - Build submission browsing and judging history

**Phase:** MVP
**Prerequisites:** S035, S046
**SRS sections:** 16.5, 16.7, 26, 47
**Decisions:** D04, D05
**Work areas:** `backend/apps/contests/submissions/, frontend/src/features/submissions/`
**Requirement focus:** SUBMISSION-001

**Implementation steps**

1. Add paginated contest/personal submission lists with filters, stable sorting, and scope-aware totals.
2. Expose submission detail and multiple judging attempts with independent field checks for metadata, verdict, and test result summaries.
3. Show source times, languages, rejudge/deletion history, truncation, and unavailable fields clearly.
4. Avoid N+1 queries and use the versioned source indexes established in the mapper sprint.

**Acceptance checks**

- Changing a submission ID cannot expose another students hidden data; list counts apply the same scope.
- A rejudged submission displays all preserved attempts without inventing current verdicts or hidden test content.

**Boundary:** No source-file/log content delivery until S049.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s049"></a>

### S049 - Build source and log inspection with field gates

**Phase:** MVP
**Prerequisites:** S022, S048
**SRS sections:** 16.5, 16.7, 18, 36
**Decisions:** D04, D05
**Work areas:** `frontend/src/features/submissions/, backend/apps/assets/`
**Requirement focus:** VISIBILITY-003, SUBMISSION-001

**Implementation steps**

1. Add inert syntax-highlighted source display, multi-file source navigation, compiler output, judge logs, and test output tabs.
2. Request each field/asset through its own authorization boundary and bound large log previews.
3. Offer authorized downloads with safe filenames; display HIDDEN/unavailable/truncated explanations without leaking sensitive filenames.
4. Log sensitive restricted access when policy requires it and sanitize all rendering.

**Acceptance checks**

- PUBLIC source does not expose hidden tests/logs, while TEACHERS_AND_OWNER permits only the documented owners/staff.
- Stored HTML/script-like source remains text; direct URL/API downloads cannot bypass the page policy.

**Boundary:** No code execution, submission editor, or live debugger.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s050"></a>

### S050 - Build problems, editorials, materials, and historical content pages

**Phase:** MVP
**Prerequisites:** S022, S033, S037, S046
**SRS sections:** 14, 16.4, 16.5, 31, 47
**Decisions:** D04, D05
**Work areas:** `frontend/src/features/problems/, frontend/src/features/contests/`

**Implementation steps**

1. Build problem list/detail with statements/translations, attachments, editorial release state, and provenance.
2. Add contest materials, certificate links, and read-only announcements/clarifications using their original audience constraints.
3. Route all HTML/assets through the sanitizer and serving service; keep source checker/test metadata staff-scoped as required.
4. Provide version/availability context and preserve original files without adopting imported navigation as app navigation.

**Acceptance checks**

- A private clarification and unreleased editorial are absent from unauthorized page/API responses.
- Statement assets render safely and a missing translation falls back with an explicit availability message.

**Boundary:** No live announcements/clarifications or public test-data exposure.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s051"></a>

### S051 - Complete personal archive navigation and history views

**Phase:** MVP
**Prerequisites:** S017, S046, S047, S048, S050
**SRS sections:** 16.1, 27, 28, 47
**Decisions:** D02, D04
**Work areas:** `frontend/src/features/archive/, backend/apps/contests/queries/`

**Implementation steps**

1. Build student My Contests/My Submissions and teacher My Contests entry points with current and historical context.
2. Add stable links from courses to contest/problem/submission history using permission-filtered datasets.
3. Preserve alumni access and distinguish an archived course from a deleted/hidden contest.
4. Add empty-state guidance and basic sorting/pagination without calculating advanced dashboard metrics.

**Acceptance checks**

- An alumnus can reach permitted past work; teacher removal removes edit affordances and backend rights.
- Cross-user navigation and stale deep links reveal no protected information.

**Boundary:** No cross-contest analytics or gradebook totals.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s052"></a>

### S052 - Model manual and contest-derived assessments

**Phase:** MVP
**Prerequisites:** S014, S024, S006
**SRS sections:** 16.6, 33, 43, 44
**Decisions:** D03, D08
**Work areas:** `backend/apps/grading/assessments/, migrations/, tests/`
**Requirement focus:** MARK-003

**Implementation steps**

1. Add AcademicAssessment owned by one Offering, optional Contest reference, assessment type, max mark, dates, and rule version.
2. Allow multiple offering-specific assessments to reference one contest with independent grading context.
3. Implement scoped CRUD/archive service and API for attendance/viva/quiz/assignment/midterm/final/manual types.
4. Define roster snapshot and eligibility behavior without creating marks for every archive participant automatically.

**Acceptance checks**

- Multiple offerings grade the same contest independently; invalid maximum marks and foreign-offering links fail.
- Manual assessment creation works with no imported archive, allowing this lane to progress while schemas are missing.

**Boundary:** No grade calculations, publication, or assessment builder UI.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s053"></a>

### S053 - Implement marks, manual entry, and immutable adjustment history

**Phase:** MVP
**Prerequisites:** S052
**SRS sections:** 16.6, 19, 20, 42
**Decisions:** D08
**Work areas:** `backend/apps/grading/marks/, migrations/, tests/`
**Requirement focus:** MARK-004

**Implementation steps**

1. Add StudentMark uniqueness per assessment/student with Decimal values, nullable missing state, source snapshot fields, and revision number.
2. Implement manual assign/override service with original calculation, before/after, delta, reason, actor, and append-only history.
3. Use row locks or optimistic version checks to prevent concurrent overwrite and audit mutation atomically.
4. Keep manual value, calculated value, and final value separate and validate mark bounds/bonus policy explicitly.

**Acceptance checks**

- Two concurrent edits cannot silently lose one teachers change; history preserves every accepted prior value.
- Missing is not zero; unauthorized teacher/student writes and out-of-bound unapproved values fail.

**Boundary:** No import-triggered auto-update or publication actions.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s054"></a>

### S054 - Assign draft marks from an imported version

**Phase:** MVP
**Prerequisites:** S034, S036, S043, S053
**SRS sections:** 16.6, 19, 42, 51
**Decisions:** D03, D05, D08
**Work areas:** `backend/apps/grading/source_assignment.py, tests/`
**Requirement focus:** MARK-001

**Implementation steps**

1. Preview eligible source-to-student score assignments using verified identity mapping, enrollment, assessment, and source version.
2. Require an explicit direct-score suitability/method choice and preserve blank marks when the archive lacks usable evidence.
3. Handle team scores through a teacher-reviewed membership snapshot and per-student allocation rule.
4. Create initial DRAFT values with source provenance; preserve existing marks on repeat invocation.

**Acceptance checks**

- A second import or replay cannot overwrite any existing draft/manual/published mark by default.
- Unmapped participants, absent scores, and changed team memberships produce review items instead of fabricated grades.

**Boundary:** No automatic assignment across unrelated offerings or re-application of existing marks.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s055"></a>

### S055 - Implement proportional, percentage, and threshold grading

**Phase:** MVP
**Prerequisites:** S053
**SRS sections:** 16.6, 55
**Decisions:** D08
**Work areas:** `backend/apps/grading/rules/basic.py, tests/`
**Requirement focus:** MARK-002

**Implementation steps**

1. Define versioned typed rule configuration for proportional conversion, percentage, and fixed thresholds.
2. Implement pure Decimal evaluators with explicit scale, inclusive/exclusive boundaries, rounding, missing inputs, and maximum handling.
3. Add preview endpoint returning inputs, rule version, output, and explanation without mutating marks.
4. Persist an applied calculation through the mark service only after an explicit confirmed action.

**Acceptance checks**

- Golden cases cover threshold boundaries, zero denominators, fractional marks, rounding, and missing scores.
- Preview does not write marks; changing rule configuration never silently changes a published value.

**Boundary:** No weighted cross-assessment aggregation or arbitrary formulas.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s056"></a>

### S056 - Implement weighted assessment aggregation

**Phase:** MVP
**Prerequisites:** S052, S055
**SRS sections:** 16.6, 21, 43
**Decisions:** D08
**Work areas:** `backend/apps/grading/rules/weighted.py, tests/`
**Requirement focus:** MARK-002

**Implementation steps**

1. Add typed weighted-assessment rules referencing explicit assessment revisions and weights.
2. Build dependency validation with cycle detection, same-offering scope checks, and documented normalization behavior.
3. Implement deterministic aggregation and a preview that states denominator/missing-input handling.
4. Persist a calculation trace so a final course value can be explained from its component marks.

**Acceptance checks**

- Cyclic references, foreign-offering inputs, invalid weights, and ambiguous missing-input handling are rejected.
- A known weighted example and changed-source-version example produce expected Decimal results without altering published marks.

**Boundary:** No best-N/drop-N/bonus/custom expression support in this card.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s057"></a>

### S057 - Implement best-N, drop-lowest, and bonus rules

**Phase:** MVP
**Prerequisites:** S056
**SRS sections:** 16.6, 35, 55
**Decisions:** D08
**Work areas:** `backend/apps/grading/rules/selection.py, tests/`
**Requirement focus:** MARK-002

**Implementation steps**

1. Add explicit best-N-of-M and drop-lowest-N selection rules with stable tie-breaking and insufficient-input behavior.
2. Implement bounded bonus rules with a declared cap and ordered composition with aggregation.
3. Return selected/dropped inputs and bonus adjustments in the calculation preview.
4. Validate graph dependencies and ensure selection cannot silently convert missing assessments to zero.

**Acceptance checks**

- Golden tests cover ties, N=0/invalid N, fewer than N eligible marks, all missing values, bonus caps, and Decimal rounding.
- The same versioned inputs always select the same assessments and produce the same trace.

**Boundary:** No implicit bonus policy or custom code evaluator.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s058"></a>

### S058 - Define and parse the custom grading expression language

**Phase:** MVP
**Prerequisites:** S055
**SRS sections:** 16.6, 57
**Decisions:** D08, D09
**Work areas:** `backend/apps/grading/formula/parser.py, docs/grading-formulas.md`
**Requirement focus:** MARK-002

**Implementation steps**

1. Document a small grammar, allowed variables/functions/operators, Decimal literal syntax, and error locations.
2. Implement a parser that produces a typed AST without using host-language eval/exec.
3. Apply limits to expression bytes, AST node count, nesting, literal magnitude, and function arity.
4. Add a validate-only API for editor feedback and examples that match the written grammar.

**Acceptance checks**

- Allowed expressions parse deterministically; imports, attribute access, comprehensions, assignments, and external calls fail.
- Oversized/deep expressions fail quickly with a bounded error and no process execution.

**Boundary:** No evaluation, mark mutation, or sandboxed arbitrary Python/JavaScript.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s059"></a>

### S059 - Evaluate custom formulas with bounded traces

**Phase:** MVP
**Prerequisites:** S058, S053
**SRS sections:** 16.6, 20, 55, 57
**Decisions:** D08, D09
**Work areas:** `backend/apps/grading/formula/evaluator.py, tests/`
**Requirement focus:** MARK-002

**Implementation steps**

1. Implement an allowlisted pure evaluator over the AST with Decimal context, operation budget, numeric range, and missing-input rules.
2. Record rule version, input snapshot, evaluation trace, result/error, and actor through existing grading/audit services.
3. Add preview/apply service integration so failed formulas cannot replace saved marks.
4. Use deterministic function implementations and guard division by zero, overflow, and expensive nested evaluation.

**Acceptance checks**

- Resource-limit, malicious-expression, zero-division, and reproducibility tests pass without external I/O.
- A failed preview or apply leaves previous marks/publication unchanged and records a safe explanation.

**Boundary:** No filesystem/network access, arbitrary libraries, or code execution workers.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s060"></a>

### S060 - Build assessment setup and gradebook editing UI

**Phase:** MVP
**Prerequisites:** S017, S053, S055, S056, S057, S059
**SRS sections:** 16.6, 27, 28, 47
**Decisions:** D08, D09
**Work areas:** `frontend/src/features/gradebook/, backend/apps/grading/api/`
**Requirement focus:** MARK-002, MARK-003, MARK-004

**Implementation steps**

1. Build assessment creation, rule configuration, calculation preview, roster grid, manual override, and mark history screens.
2. Use revision-aware saves and present a conflict response instead of overwriting another teachers edit.
3. Keep private notes/feedback controls reserved until S062 and publication actions reserved until S061.
4. Support accessible keyboard editing, bounded batch updates, pagination, missing-value labels, and clear source/version explanations.

**Acceptance checks**

- A teacher can configure a manual and calculated assessment and apply a reviewed calculation end-to-end.
- Stale saves are rejected visibly; a student cannot use gradebook write APIs or view draft aggregate values.

**Boundary:** No automatic publication or spreadsheet-style arbitrary formulas.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s061"></a>

### S061 - Implement finalize, publish, lock, unlock, and correction

**Phase:** MVP
**Prerequisites:** S053, S060, S023
**SRS sections:** 16.6, 19, 20, 50
**Decisions:** D08
**Work areas:** `backend/apps/grading/publication.py, frontend/src/features/gradebook/`
**Requirement focus:** MARK-005

**Implementation steps**

1. Implement the documented state machine, explicit FINALIZED-to-DRAFT reopen, audited lock/unlock, and correction-and-republish revision.
2. Authorize all transitions against current offering assignment and the configured elevated lock capability.
3. Make bulk assessment actions transactionally consistent and write durable marks-published events only after successful commit.
4. Keep previously published values visible during correction preparation and block locked edits until unlock.

**Acceptance checks**

- Invalid/stale/concurrent transitions fail without partial publication; unauthorized teachers cannot unlock.
- DRAFT and FINALIZED marks never appear in student APIs or totals; LOCKED published marks remain readable.

**Boundary:** No multi-stage coordinator approval or hidden bypass for re-import.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s062"></a>

### S062 - Implement private notes and student-visible feedback

**Phase:** MVP
**Prerequisites:** S053, S061
**SRS sections:** 19, 20, 30
**Decisions:** D04, D08
**Work areas:** `backend/apps/grading/feedback.py, frontend/src/features/gradebook/`
**Requirement focus:** MARK-004

**Implementation steps**

1. Store private teacher notes and student feedback in separate typed fields/records with separate serializers.
2. Add audited scoped create/edit/history services and gradebook controls.
3. Emit feedback-added events only for actual student-visible changes and respect publication/access rules.
4. Ensure report/export serializers explicitly choose permitted feedback fields instead of serializing entire models.

**Acceptance checks**

- Private notes never appear in student responses, totals, notifications, or export datasets.
- A removed teacher cannot edit feedback, and edits preserve authorship/history.

**Boundary:** No broad messaging system or public comments.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s063"></a>

### S063 - Build student marks and explainable totals

**Phase:** MVP
**Prerequisites:** S054, S061, S062, S051
**SRS sections:** 16.6, 19, 35, 47
**Decisions:** D04, D08
**Work areas:** `frontend/src/features/marks/, backend/apps/grading/student_queries.py`
**Requirement focus:** MARK-005

**Implementation steps**

1. Expose owner-scoped published/locked marks, permitted feedback, calculation explanations, and assessment totals.
2. Build My Marks and course mark breakdown views with unavailable/missing/pending states.
3. Compute student-visible totals only from permitted published inputs; label incomplete totals rather than leaking draft components.
4. Provide teacher/admin scoped preview using the same data projection and current permissions.

**Acceptance checks**

- Student A cannot retrieve Student B marks by changing IDs; FINALIZED data and private notes are absent from serialized payloads.
- An alumnus retains permitted published history and a correction updates only after republish succeeds.

**Boundary:** No formal signed transcript or public mark distribution.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s064"></a>

### S064 - Compute immutable re-import differences

**Phase:** MVP
**Prerequisites:** S035, S036, S037, S038, S039, S043
**SRS sections:** 15.5, 38, 51
**Decisions:** D05, D07, D08
**Work areas:** `backend/apps/imports/diff.py, tests/`
**Requirement focus:** MARK-006

**Implementation steps**

1. Compare staged new version with the current version using stable source keys and normalized values.
2. Report added/changed/removed participants, problems, submissions, judging records, standings, assets, and restricted summary counts.
3. Keep removed records as versioned tombstones/evidence and identify academic records whose source inputs changed without updating them.
4. Generate a deterministic diff fingerprint tied to both versions and the staging plan.

**Acceptance checks**

- Synthetic v1/v2 cases identify every intended change, including deletion/restoration and changed source scores.
- Private restricted fields do not leak into normal diff summaries and unchanged rows are not reported as changes.

**Boundary:** No production version switch or mark recalculation.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s065"></a>

### S065 - Build re-import review and conflict resolution UI

**Phase:** MVP
**Prerequisites:** S042, S064
**SRS sections:** 15.5, 28, 36, 51
**Decisions:** D05, D07, D08
**Work areas:** `frontend/src/features/imports/reimport/, backend/apps/imports/preview/`

**Implementation steps**

1. Build summary counts, paginated per-entity diffs, affected-mark notices, and mapping-conflict review.
2. Require a reviewed diff fingerprint and current contest-management authority before accepting the new version.
3. Separate source-version confirmation from later university-data re-application actions.
4. Provide cancel/discard behavior that removes only the staged version and keeps current data intact.

**Acceptance checks**

- A changed current version or edited mapping invalidates the displayed confirmation token.
- Review never silently opts into overwriting marks/comments/mappings/publication, including bulk UI actions.

**Boundary:** No combined source import and automatic grade overwrite.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s066"></a>

### S066 - Promote re-import versions while preserving university data

**Phase:** MVP
**Prerequisites:** S044, S064, S065
**SRS sections:** 15.5, 33, 38, 51
**Decisions:** D05, D07, D08
**Work areas:** `backend/apps/imports/reimport_commit.py, tests/`
**Requirement focus:** MARK-006

**Implementation steps**

1. Reuse the import transaction to persist the new source version and atomically switch the current pointer under a contest lock.
2. Mark the old version superseded while keeping its rows/assets and stable academic provenance references.
3. Preserve every university-owned field by construction; do not mass-update shared source/university columns.
4. Emit idempotent refresh events and reconcile interrupted promotion using the recovery service.

**Acceptance checks**

- Failure at each transaction boundary leaves one coherent current version and unchanged academic data.
- Published/manual marks, feedback, overlays, mappings, and visibility policies survive a successful re-import unchanged.

**Boundary:** No automatic purging of old versions or automatic grade re-application.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s067"></a>

### S067 - Implement explicit source-score re-application and remapping

**Phase:** MVP
**Prerequisites:** S054, S061, S066
**SRS sections:** 16.6, 20, 42, 51
**Decisions:** D05, D07, D08
**Work areas:** `backend/apps/grading/reapply.py, backend/apps/imports/identity/`
**Requirement focus:** MARK-006

**Implementation steps**

1. Add a separate preview/apply action for changed source scores showing old/new source version, calculation, and impacted student marks.
2. Require explicit teacher selection and current mark revision; follow locked/published correction rules.
3. Support separately reviewed identity mapping corrections with attribution and affected-record preview.
4. Record complete old/new snapshots and reasons; invalidate dependent calculations only through explicit workflow.

**Acceptance checks**

- Re-import alone never calls this service; a locked mark cannot be changed without authorized unlock.
- An explicit reapply updates the intended marks once, preserves history, and cannot transfer another students published record silently.

**Boundary:** No blanket overwrite of every mark or automatic reassignment of historical ownership.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s068"></a>

### S068 - Verify re-import and academic preservation journeys

**Phase:** MVP
**Prerequisites:** S063, S066, S067
**SRS sections:** 36, 37, 38, 55
**Decisions:** D05, D07, D08
**Work areas:** `tests/integration/reimport/, frontend/e2e/reimport/`
**Requirement focus:** MARK-006

**Implementation steps**

1. Build UC-05 tests covering changed source score, removed submission, changed problem/team membership, new participant, and preserved overlays.
2. Exercise diff cancellation, stale confirmation, duplicate jobs, concurrent teachers, and explicit mark correction.
3. Verify the student sees stable published values until a separate correction publishes.
4. Document supported recovery steps and source-versus-university ownership guarantees with actual test evidence.

**Acceptance checks**

- Every university-owned field has a preservation assertion across successful and failed re-import.
- The previously used source version remains inspectable for an academic mark after later versions are current.

**Boundary:** No release beyond the re-import feature gate.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s069"></a>

### S069 - Define report datasets, metric semantics, and permissions

**Phase:** MVP
**Prerequisites:** S047, S048, S063
**SRS sections:** 19, 21, 22, 26
**Decisions:** D02, D04, D08
**Work areas:** `backend/apps/reports/datasets/, docs/report-metrics.md`

**Implementation steps**

1. Define reusable typed datasets and metric formulas for participation, attempts, solve rate/time, mark totals, and coverage.
2. Specify denominators, missing/excluded/truncated behavior, team counting, current versus historical source version, and enrollment eligibility.
3. Apply requester scope before aggregation and attach the scope/version/publication fingerprint to cached or exported results.
4. Build fixtures with two offerings and hidden/unpublished records to anchor expected numbers.

**Acceptance checks**

- Aggregation over unauthorized rows is impossible through the public dataset interface.
- Known fixture totals and missing-data coverage match documented formulas; no metric invents absent source data.

**Boundary:** No report UI or expensive cross-contest comparison engine.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s070"></a>

### S070 - Implement the student performance report

**Phase:** MVP
**Prerequisites:** S069
**SRS sections:** 21, 27, 28, 47
**Decisions:** D04, D08
**Work areas:** `backend/apps/reports/student.py, frontend/src/features/reports/student/`

**Implementation steps**

1. Build student summary/detail datasets for attended/missed contests, attempts/solves, verdicts, language use, scores, marks, and time trends.
2. Expose problem-category performance only when category metadata actually exists; show unavailable otherwise.
3. Add authorized student/course/contest drill-down, filters, and accessible report tables/charts.
4. Keep staff report permissions distinct from the students own performance projection.

**Acceptance checks**

- Report numbers match fixture calculations and never include draft marks/private notes in a student projection.
- A teacher cannot use the student report to inspect unrelated course history.

**Boundary:** No export file generation or formal transcript.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s071"></a>

### S071 - Implement problem and contest reports

**Phase:** MVP
**Prerequisites:** S069
**SRS sections:** 21, 22, 27, 47
**Decisions:** D04, D08
**Work areas:** `backend/apps/reports/problem.py, contest.py, frontend/src/features/reports/`

**Implementation steps**

1. Build problem attempts/solvers/solve-rate/time/verdict/language/score summaries and detailed authorized rows.
2. Build contest participation, score/penalty distributions, per-problem outcomes, and staff-only academic mark distributions.
3. Provide Summary/Detailed views with explicit formula/coverage labels and source snapshot selection.
4. Only show a derived difficulty measure if its documented formula and inputs are present.

**Acceptance checks**

- Golden report fixtures handle ties, partial scores, unofficial participants, excluded tests, and empty contests.
- A public contest does not make academic mark distributions or teacher reports public.

**Boundary:** No export generation, benchmarking, or invented problem tags.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s072"></a>

### S072 - Implement course and batch reports

**Phase:** MVP
**Prerequisites:** S069, S070, S071
**SRS sections:** 21, 27, 28, 48
**Decisions:** D03, D04, D08
**Work areas:** `backend/apps/reports/course.py, batch.py, frontend/src/features/reports/`

**Implementation steps**

1. Build course roster/participation/missed-contest/gradebook/progression summaries and detailed course-to-submission drill-down.
2. Add batch cross-course/semester summaries with admin-only default and explicit optional delegated scope.
3. Use enrollment history and versioned assessments to avoid counting unrelated contests or double-counting shared contests.
4. Expose pagination/filtering and coverage labels consistently with other reports.

**Acceptance checks**

- An assigned teacher sees only permitted offerings and cannot widen batch scope through query parameters.
- Shared contest and withdrawn-student fixtures produce the documented denominators and preserved history.

**Boundary:** No institution-wide student ranking or advanced comparison dashboards.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s073"></a>

### S073 - Materialize analytics and invalidate stale aggregates

**Phase:** MVP
**Prerequisites:** S023, S068, S069
**SRS sections:** 22, 26, 45
**Decisions:** D04, D05, D08
**Work areas:** `backend/apps/reports/aggregates/, tests/`

**Implementation steps**

1. Add background aggregate jobs for committed contest/problem/course metrics using the typed report datasets.
2. Key results by source version, grading/publication revision, and permission-relevant context; track freshness and calculation coverage.
3. Consume import/re-import/publication/correction/enrollment events idempotently and coalesce repeated refresh requests.
4. Recheck current viewer authority on reads even when an aggregate is cached.

**Acceptance checks**

- Re-import and mark correction cannot leave a current dashboard silently serving previous-version totals.
- Revoked membership does not retain cached access; duplicate events do not duplicate aggregates.

**Boundary:** No cache as the authoritative grade store or unscoped shared student reports.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s074"></a>

### S074 - Build role dashboards from existing datasets

**Phase:** MVP
**Prerequisites:** S051, S063, S070, S072, S073
**SRS sections:** 22, 27, 28, 47
**Decisions:** D02, D04
**Work areas:** `frontend/src/features/dashboard/, backend/apps/reports/dashboard/`

**Implementation steps**

1. Build student, teacher, and admin dashboard projections from already-tested dataset services.
2. Show only available performance, course work, import status, and governance counts appropriate to the role.
3. Add accessible trend summaries with table alternatives, freshness indicators, and navigation to existing detail pages.
4. Keep empty states truthful; avoid synthetic success metrics on an empty installation.

**Acceptance checks**

- Dashboard numbers match underlying reports and contain no draft/unrelated student marks.
- Role switching/removal and small-screen navigation respect current permissions without stale cached panels.

**Boundary:** No new analytics formulas or advanced cross-contest comparisons.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s075"></a>

### S075 - Implement safe CSV report serialization

**Phase:** MVP
**Prerequisites:** S069, S070, S071, S072
**SRS sections:** 18, 21, 31
**Decisions:** D04, D08
**Work areas:** `backend/apps/reports/exporters/csv.py, tests/`

**Implementation steps**

1. Define stable CSV columns for each existing report/gradebook dataset with documented units and availability labels.
2. Implement streaming serialization, correct quoting/encoding, and spreadsheet-formula injection protection for untrusted strings.
3. Include report filters, source/publication version metadata in a companion or header convention without changing numeric meaning.
4. Reuse permission-filtered datasets and exclude private notes/restricted fields by explicit field selection.

**Acceptance checks**

- Round-trip tests cover commas, newlines, Unicode, formula-like strings, missing values, and Decimal precision.
- Unauthorized fields cannot appear through a generic model serializer; large row iteration stays bounded.

**Boundary:** No XLSX/PDF implementation or asynchronous download UI yet.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s076"></a>

### S076 - Implement XLSX report serialization

**Phase:** MVP
**Prerequisites:** S075
**SRS sections:** 21, 27, 31
**Decisions:** D04, D08
**Work areas:** `backend/apps/reports/exporters/xlsx.py, tests/`

**Implementation steps**

1. Create workbook serializers for the same approved report/gradebook datasets and column contract.
2. Use explicit text/number/date types, frozen headers, sensible widths, filters, and an information sheet with scope/version/coverage.
3. Treat untrusted formula-like strings as text; do not insert macros or external workbook links.
4. Bound workbook memory using streaming mode and split oversized data into documented sheets/files rather than dropping rows.

**Acceptance checks**

- Reopen generated workbooks and verify cell types, counts, precision, metadata, and absence of executable formulas in user fields.
- Large fixtures complete within the defined memory budget and preserve all eligible rows.

**Boundary:** No interactive Excel integration or new report metrics.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s077"></a>

### S077 - Implement paginated PDF reports

**Phase:** MVP
**Prerequisites:** S069, S070, S071, S072
**SRS sections:** 21, 27, 31
**Decisions:** D04, D08
**Work areas:** `backend/apps/reports/exporters/pdf.py, tests/`

**Implementation steps**

1. Create a consistent server-generated PDF layout for existing report summary/detail datasets with repeated table headers and page numbers.
2. Include report title, filters, generation time, data versions, units, and missing-data coverage.
3. Handle long names, narrow columns, large tables, and Unicode; render content from escaped trusted templates.
4. Add a repeatable render inspection command and small representative output fixtures without committing private generated reports.

**Acceptance checks**

- Text extraction verifies required rows/values and rendered pages have no clipping, overlaps, missing glyphs, or blank overflow pages.
- PDF generation uses the same scoped dataset as the screen/CSV and excludes private fields.

**Boundary:** No formal signed transcript, PDF upload processing, or publication to public storage.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s078"></a>

### S078 - Wire asynchronous export jobs and download history

**Phase:** MVP
**Prerequisites:** S023, S022, S075, S076, S077
**SRS sections:** 21, 26, 30, 31
**Decisions:** D04, D07
**Work areas:** `backend/apps/reports/jobs/, frontend/src/features/exports/`

**Implementation steps**

1. Add scoped export request/status/cancel APIs with immutable filter and source/publication snapshots.
2. Generate CSV/XLSX/PDF through background jobs and private asset storage with expiry and cleanup.
3. Build request/progress/result/download UI and useful retry messages.
4. Reauthorize both generation and download; changed membership must prevent retrieval even if the job completed earlier.

**Acceptance checks**

- Large exports return a job promptly and finish without blocking request handlers.
- A revoked teacher cannot download a previously generated report; repeated jobs/cleanup cannot expose or orphan sensitive artifacts.

**Boundary:** No permanent public export URLs or email attachments by default.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s079"></a>

### S079 - Implement permission-filtered global and contextual search

**Phase:** MVP
**Prerequisites:** S046, S050, S051, S072
**SRS sections:** 18, 26, 29
**Decisions:** D02, D04
**Work areas:** `backend/apps/contests/search/, frontend/src/features/search/`

**Implementation steps**

1. Add search for contests, students, teachers, courses, and problems using indexed PostgreSQL queries and pagination.
2. Implement documented academic/date/tag/type/group filters and context constraints through the shared policy querysets.
3. Apply visibility before counts, suggestions, facets, and snippets so hidden resources cannot be discovered.
4. Build search UI with stable links, empty states, and bounded query inputs.

**Acceptance checks**

- Private contest titles, unrelated students, hidden source snippets, and restricted filenames do not leak through results or counts.
- Representative query plans use appropriate indexes and invalid filters fail clearly.

**Boundary:** No external search cluster or full-text indexing of private source code by default.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s080"></a>

### S080 - Implement in-app notification storage and inbox

**Phase:** MVP
**Prerequisites:** S005, S023
**SRS sections:** 18, 30, 47
**Decisions:** D02, D04
**Work areas:** `backend/apps/notifications/, frontend/src/features/notifications/`

**Implementation steps**

1. Add notification recipient, type, safe payload, read state, deduplication key, and retention fields.
2. Expose owner-only paginated list/unread-count/mark-read APIs and a keyboard-accessible inbox.
3. Resolve deep links through current permissions and avoid embedding private marks/notes in generic notification previews.
4. Provide idempotent notification creation service and an optional disabled email adapter interface.

**Acceptance checks**

- User A cannot enumerate or mark User B notifications; counts are owner-scoped.
- Duplicate event delivery creates one notification and a now-forbidden target reveals no hidden content.

**Boundary:** No mass email or imported historical-notification replay.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s081"></a>

### S081 - Connect required notification events and admin alerts

**Phase:** MVP
**Prerequisites:** S044, S061, S062, S078, S080
**SRS sections:** 20, 30, 52
**Decisions:** D04, D07
**Work areas:** `backend/apps/notifications/handlers/, tests/`

**Implementation steps**

1. Connect import success/failure/mapping-required, contest availability, marks publication, visible feedback, and enrollment changes to the outbox.
2. Add configurable failed-import/storage-threshold admin alerts with deduplication and recovery behavior.
3. Notify only affected permitted recipients after committed state changes; retain historical imported notifications as source evidence.
4. Document event ownership and optional per-type email configuration without enabling unsolicited external delivery.

**Acceptance checks**

- Rolled-back changes send nothing; retries do not duplicate notifications.
- Private-note edits, hidden contests, and failed draft publication do not generate student disclosures.

**Boundary:** No live contest feed or automatic bulk outbound email.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s082"></a>

### S082 - Build governance, audit, and operational settings screens

**Phase:** MVP
**Prerequisites:** S011, S020, S044, S073, S081
**SRS sections:** 20, 23, 25, 34, 47, 48
**Decisions:** D02, D10, D11
**Work areas:** `backend/apps/governance/, frontend/src/features/admin/`

**Implementation steps**

1. Add admin settings for import limits, retention floors, lockout/session behavior, notification thresholds, and defaults with typed validation.
2. Build imports/failures/storage/job status and audit-log query pages using existing scoped APIs.
3. Audit settings changes and show effective values; enforce safe minima rather than accepting nonsensical limits.
4. Keep role names fixed and make delegated grants explicit in the permissions UI.

**Acceptance checks**

- Non-admins cannot change system limits or enumerate global audits; invalid settings cannot disable mandatory integrity checks.
- Audit filters and pagination work over representative data without exposing redacted secrets.

**Boundary:** No schema trust upload by an ordinary teacher or destructive purge action.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s083"></a>

### S083 - Implement recoverable contest deletion and restore

**Phase:** MVP
**Prerequisites:** S046, S082
**SRS sections:** 11, 20, 34, 38
**Decisions:** D04, D10
**Work areas:** `backend/apps/governance/trash/, frontend/src/features/admin/`

**Implementation steps**

1. Add scoped soft-delete, trash listing, restore, deleted-at, and hard-delete eligibility calculations.
2. Revoke normal contest access immediately while retaining source versions, assets, marks, and audit evidence.
3. Build clear restore/grace-period UI with authorized teacher/admin actions.
4. Invalidate search/export/dashboard caches and avoid altering the original source evidence for a platform deletion.

**Acceptance checks**

- A soft-deleted contest disappears from normal public/student access but can be restored with identical academic data.
- Teacher deletion is scoped, audit is complete, and grace-period time boundaries are deterministic.

**Boundary:** No immediate hard purge or academic-record cascade deletion.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s084"></a>

### S084 - Implement controlled purge and account anonymization

**Phase:** MVP
**Prerequisites:** S083, S068, S078
**SRS sections:** 19, 20, 25, 34, 44
**Decisions:** D05, D10
**Work areas:** `backend/apps/governance/purge/, anonymize/, tests/`

**Implementation steps**

1. Build admin-only impact preview and explicit resumable hard-purge command after the grace period.
2. Preserve academic marks/history via tombstones or retained provenance, and delete source/assets only when no surviving references require them.
3. Implement account anonymization across source identity projections, mappings, cached exports/search, and owned sensitive assets according to the documented policy.
4. Record an immutable deletion ledger and document backup retention/re-erasure after restore; verify eligibility again when the worker executes.

**Acceptance checks**

- Purge before the grace deadline, teacher-triggered hard delete, and shared-asset removal are rejected.
- A crash resumes safely; surviving marks retain history and erased identities are not rediscovered through alternate endpoints.

**Boundary:** No automatic retention sweeper or institutional legal-policy invention.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s085"></a>

### S085 - Verify cross-cutting authorization and concurrency

**Phase:** MVP
**Prerequisites:** S068, S078, S079, S082, S084
**SRS sections:** 18, 19, 20, 55
**Decisions:** D02, D04, D07, D08
**Work areas:** `tests/security/, tests/integration/concurrency/`

**Implementation steps**

1. Build an endpoint inventory and parameterized role/object matrix covering reads, writes, exports, assets, jobs, and administrative actions.
2. Exercise revocation after caching/job submission, source-role non-escalation, CSRF, mass assignment, and hidden-resource enumeration.
3. Test simultaneous mark edits, re-import confirmation, mapping changes, and permission removal at transaction boundaries.
4. Fix specific failing checks and update the security guide with actual enforcement locations and residual issues.

**Acceptance checks**

- Every protected route is tied to a tested policy entry; targeted IDOR and revocation cases pass.
- No accepted concurrent workflow silently loses academic data or produces two current source versions.

**Boundary:** No claim that passing these tests is an independent penetration test.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s086"></a>

### S086 - Complete accessibility and responsive workflow checks

**Phase:** MVP
**Prerequisites:** S060, S063, S074, S078, S082
**SRS sections:** 27, 28, 47
**Decisions:** D01
**Work areas:** `frontend/src/, frontend/e2e/accessibility/, docs/`

**Implementation steps**

1. Check login, course navigation, import wizard, standings, gradebook, reports, and admin forms with keyboard and representative viewport sizes.
2. Fix focus order, modal focus return, labeled controls, error summaries, table semantics, contrast, and chart alternatives.
3. Add focused automated accessibility checks for stable critical screens and document manual observations.
4. Preserve data-dense desktop behavior while providing usable scrolling/stacking on mobile/tablet.

**Acceptance checks**

- Critical flows complete without a mouse and errors are announced near the relevant controls.
- No inaccessible hidden action or clipped primary control prevents a task on a narrow screen.

**Boundary:** No broad visual redesign or dark mode until its phase-specific sprint.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s087"></a>

### S087 - Run MVP acceptance journeys and requirement coverage

**Phase:** MVP
**Prerequisites:** S045, S068, S072, S078, S079, S081, S082, S084, S085, S086
**SRS sections:** 35, 36, 37, 52, 55
**Decisions:** D12
**Work areas:** `tests/e2e/, docs/acceptance.md`

**Implementation steps**

1. Run UC-01 through UC-05 plus manual assessment, group gating, alumni access, all report exports, and admin recovery journeys.
2. Map every MVP requirement ID and unnumbered mandatory behavior to completed sprint evidence and a meaningful check.
3. Resolve integration defects only; record larger defects as explicit blocking follow-up sprints instead of calling the MVP complete.
4. Rehearse a clean install/seed with synthetic data and document supported archive versions and known constraints.

**Acceptance checks**

- All mandatory MVP coverage rows have passing evidence; an unimplemented feature cannot be marked done because a placeholder page exists.
- The platform completes import-to-published-mark-to-export and preserves marks across a re-import.

**Boundary:** No launch approval based solely on unit-test success.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s088"></a>

### S088 - Build repeatable scale benchmarks and agree budgets

**Phase:** MVP
**Prerequisites:** S045, S073, S078, S079
**SRS sections:** 17, 23, 26, 45, 55
**Decisions:** D11
**Work areas:** `tests/performance/, scripts/benchmarks/, docs/performance.md`

**Implementation steps**

1. Define named hardware/storage/network profiles and deterministic generators for large submissions/tests/history and near-limit archive files.
2. Measure browse/report p95 latency, queue delay, worker RSS, import/export duration, and query counts under a documented concurrent load.
3. Record provisional pass/fail budgets with evidence and note which need institutional workload confirmation.
4. Keep generated large archives and measurements with personal data ignored; commit generator seeds and sanitized summaries.

**Acceptance checks**

- Benchmarks are rerunnable and report dataset size, concurrency, hardware, and all relevant limits.
- A small unit fixture is never reported as validating the 2 GB/8 GB/200,000-file operating envelope.

**Boundary:** No invented production capacity guarantees or arbitrary benchmark pass claims.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s089"></a>

### S089 - Fix measured performance bottlenecks

**Phase:** MVP
**Prerequisites:** S088
**SRS sections:** 26, 45, 55
**Decisions:** D11
**Work areas:** `backend/apps/ affected modules, migrations/, docs/performance.md`

**Implementation steps**

1. Select the highest-impact measured bottleneck and record the failing baseline/query plan.
2. Apply a focused index, batching, pagination, streaming, or materialization fix that preserves policy and calculation behavior.
3. Rerun the same benchmark and correctness cases; record before/after results and remaining failed budgets.
4. If multiple unrelated bottlenecks remain, split S089 into named child cards with their own gates before marking this sprint complete.

**Acceptance checks**

- The selected change improves the measured bottleneck without changing authorized rows or academic results.
- All launch budgets have evidence or explicit open blockers; no broad unmeasured rewrite is introduced.

**Boundary:** No premature sharding/microservices or disabling integrity checks to improve timing.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s090"></a>

### S090 - Package production services and safe deployment configuration

**Phase:** MVP
**Prerequisites:** S004, S022, S023, S082, S087
**SRS sections:** 18, 25, 56
**Decisions:** D01, D11
**Work areas:** `deploy/, container definitions, .env.example, docs/runbooks/deploy.md`

**Implementation steps**

1. Package web/API, static frontend, worker, scheduler/outbox dispatcher, and proxy using the same locked application revision.
2. Configure TLS termination assumptions, trusted hosts/origins, secure cookies, request limits/timeouts, private storage, and environment-based secrets.
3. Provide migration/static-asset/startup procedures, liveness/readiness checks, and rollback-compatible versioning.
4. Document external prerequisites for DNS, mail, storage, database, and backup services; validate configuration in an isolated environment.

**Acceptance checks**

- Production checks reject debug mode, missing secrets, unsafe host configuration, and public storage defaults.
- Containers/services start with health checks and serve the built frontend/API without relying on development tools.

**Boundary:** No production credentials committed or live deployment performed by creating this plan.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s091"></a>

### S091 - Implement backup, restore, and disaster-recovery rehearsal

**Phase:** MVP
**Prerequisites:** S084, S090
**SRS sections:** 25, 31, 34, 55
**Decisions:** D10, D11
**Work areas:** `deploy/backup/, docs/runbooks/recovery.md, tests/operations/`

**Implementation steps**

1. Document and configure PostgreSQL full/PITR backups and compatible private object-storage/version backups with retention floors.
2. Implement a restore sequence preserving database-to-asset references and reapplying erasure/deletion ledger entries.
3. Rehearse restoration into an isolated environment and verify counts, source versions, marks, audit, and asset availability.
4. Measure recovery point/time against documented targets and record access controls, key ownership, scheduling, and failure alerts.

**Acceptance checks**

- A real isolated restore succeeds; the SRS starting RPO<=24h/RTO<=8h targets have measured evidence or a documented blocker.
- Backup errors alert operators and restoration cannot silently resurrect data scheduled for erasure.

**Boundary:** No destructive restore into production or deletion of the only known-good backup.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s092"></a>

### S092 - Deploy to staging and perform an operator rehearsal

**Phase:** MVP
**Prerequisites:** S087, S089, S090, S091
**SRS sections:** 25, 52, 55, 56
**Decisions:** D06, D11, D12
**Work areas:** `deploy/, docs/runbooks/, docs/acceptance.md`

**Implementation steps**

1. With supplied staging access, deploy the exact tested revision and run migrations/health checks/seed through documented commands.
2. Rehearse import, mapping, grading, re-import, exports, revocation, restart recovery, and backup using anonymized or synthetic data.
3. Check mail deliverability, TLS, storage isolation, observability, and rollback of an application release.
4. Record operator sign-off items and a precise remaining-blocker list; if infrastructure access is missing, mark this sprint blocked rather than claiming deployment.

**Acceptance checks**

- Staging acceptance passes against the deployed revision and a rollback rehearsal preserves data.
- Operators can follow the runbooks without undocumented local knowledge.

**Boundary:** No production launch or actual student records until separately authorized.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s093"></a>

### S093 - Complete the MVP release and handover

**Phase:** MVP
**Prerequisites:** S092
**SRS sections:** 52, 55, 56, 59
**Decisions:** D11, D12
**Work areas:** `docs/releases/, docs/runbooks/, release checklist`

**Implementation steps**

1. Prepare a release manifest with revision, dependency locks, supported archive versions, migration plan, acceptance evidence, and rollback steps.
2. Resolve all MVP blockers and identify operational owners, backup schedule, admin bootstrap, and support escalation.
3. After explicit production authorization and required credentials, execute the reviewed deployment and bounded smoke checks.
4. Record the released revision and operational handover; stop if migrations, health, integrity, or backup gates fail.

**Acceptance checks**

- The release has no unfinished mandatory MVP sprint or unverified archive-format claim.
- Production actions are actually authorized and verified; otherwise deliver the ready release package with deployment marked blocked.

**Boundary:** No Phase 2 scope folded into the launch or automatic remote publishing.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s094"></a>

### S094 - Implement one institutional SSO provider adapter

**Phase:** Phase 2
**Prerequisites:** S093
**SRS sections:** 4.2, 53
**Decisions:** D01, D02
**Work areas:** `backend/apps/accounts/sso/, docs/security.md`

**Implementation steps**

1. Obtain the selected institutional provider/protocol/tenant configuration and approved account-linking policy.
2. Implement one provider adapter with validated issuer/audience, redirect state/nonce, tenant restrictions, and secure token handling.
3. Map authenticated identities to existing verified platform accounts without automatically trusting role claims.
4. Document local-password fallback and revocation behavior; keep provider secrets in deployment configuration.

**Acceptance checks**

- Wrong tenant/audience/issuer, replayed callback, and email-only account takeover attempts fail.
- An existing users history remains attached to the correct account after the approved link flow.

**Boundary:** No second provider until the first adapter contract is verified; blocked without institutional provider details.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s095"></a>

### S095 - Build SSO enrollment and account-linking UI

**Phase:** Phase 2
**Prerequisites:** S094
**SRS sections:** 53, 27, 28
**Decisions:** D02
**Work areas:** `frontend/src/features/auth/sso/, backend/apps/accounts/sso/`

**Implementation steps**

1. Build SSO login, explicit link/unlink, collision review, and operator recovery screens.
2. Require proof/control appropriate to both identities before linking accounts; audit administrative recovery.
3. Show actionable provider failure messages without exposing tokens or tenant secrets.
4. Add a second provider only as a separate adapter child sprint if the institution requires Google and Microsoft simultaneously.

**Acceptance checks**

- Linking cannot hijack an account by presenting a matching unverified email.
- Users can recover through the documented fallback and do not lose historical enrollments/marks.

**Boundary:** No public social-login rollout without the chosen institutional policy.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s096"></a>

### S096 - Implement one enrollment synchronization adapter

**Phase:** Phase 2
**Prerequisites:** S093, S016
**SRS sections:** 53, 20
**Decisions:** D02, D03
**Work areas:** `backend/apps/academics/sync/, docs/decisions/`

**Implementation steps**

1. Obtain an institutional roster feed contract and decide which fields it owns versus local corrections.
2. Implement one adapter with dry-run diff, reviewed conflict handling, stable external keys, and idempotent apply.
3. Preserve enrollment history and teacher-entered academic records when an upstream membership disappears.
4. Add scoped scheduling/status and audit for synchronization runs, with a manual stop/retry mechanism.

**Acceptance checks**

- Repeated feed delivery does not duplicate accounts/enrollment; unexpected removals require the documented review gate.
- A corrupt or unavailable feed leaves previous academic state intact.

**Boundary:** No guessed institution API or automatic role escalation from feed fields.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s097"></a>

### S097 - Improve identity matching with reviewed suggestions

**Phase:** Phase 2
**Prerequisites:** S093, S040, S041
**SRS sections:** 53, 16.3
**Decisions:** D05
**Work areas:** `backend/apps/imports/identity/suggestions/, frontend/src/features/imports/`

**Implementation steps**

1. Add explainable suggested matches from approved secondary signals without replacing deterministic mapping rules.
2. Rank candidates with documented scoring and expose the evidence used, bounded to authorized student scope.
3. Support bulk review of suggestions while retaining explicit per-row choice and ambiguity handling.
4. Evaluate suggestions against a redistributable labeled synthetic/anonymized set and record false-match behavior.

**Acceptance checks**

- An uncertain suggestion never commits a mapping automatically.
- Namespace collisions and similar names do not overwrite an existing confirmed identity mapping.

**Boundary:** No unreviewed fuzzy auto-merge or externally sourced personal profiling.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s098"></a>

### S098 - Implement term archiving and course-structure cloning

**Phase:** Phase 2
**Prerequisites:** S093, S014, S015, S052
**SRS sections:** 53, 34
**Decisions:** D03, D08
**Work areas:** `backend/apps/academics/term_tools/, frontend/src/features/offerings/`

**Implementation steps**

1. Archive a term while retaining historical course/contest/mark access and restricting new edits as documented.
2. Preview cloning offerings, teacher assignments, and empty assessment structure into a target term/batch/section.
3. Explicitly exclude student marks, submissions, publication state, and prior audit from cloning.
4. Apply the reviewed clone atomically with deterministic conflict handling and audit.

**Acceptance checks**

- A cloned course begins with no copied academic results and valid target parent relationships.
- Repeated confirmation does not create duplicate offerings; archived historical records remain readable.

**Boundary:** No cross-institution migration or automatic enrollment copy without review.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s099"></a>

### S099 - Implement reusable grading templates

**Phase:** Phase 2
**Prerequisites:** S093, S055, S056, S057, S059
**SRS sections:** 53, 16.6
**Decisions:** D08, D09
**Work areas:** `backend/apps/grading/templates/, frontend/src/features/gradebook/`

**Implementation steps**

1. Create versioned templates for assessment/rule configuration with named parameters and explicit sharing scope.
2. Preview applying a template to a target offering and map assessment references without copying values or publication state.
3. Validate the resulting dependency graph and custom expression budgets through existing rule services.
4. Preserve the previous applied rule version so later template edits never silently regrade students.

**Acceptance checks**

- Template updates do not mutate existing published grades.
- Invalid target assessment mappings/cycles and unauthorized template sharing fail before apply.

**Boundary:** No automatic cross-course grade normalization.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s100"></a>

### S100 - Implement saved report filters and anonymized standings toggle

**Phase:** Phase 2
**Prerequisites:** S093, S047, S072
**SRS sections:** 53, 19, 29
**Decisions:** D04
**Work areas:** `backend/apps/reports/saved_filters/, frontend/src/features/reports/`

**Implementation steps**

1. Persist user-owned named filter presets with schema/version and current permission validation on every use.
2. Add an authorized contest anonymization toggle with stable public pseudonyms and scoped staff identity reveal.
3. Ensure all standings API fields, exports, search snippets, and asset links respect the anonymized projection.
4. Document identifier leakage limitations and avoid exposing a hidden real identity through alternate endpoints.

**Acceptance checks**

- A saved preset cannot preserve revoked access or broaden query scope.
- An anonymized public standings view and its export reveal no real names/IDs through linked payloads.

**Boundary:** No anonymization of the authoritative academic identity store.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s101"></a>

### S101 - Implement configurable branding and dark mode

**Phase:** Phase 2
**Prerequisites:** S093, S086
**SRS sections:** 53, 27
**Decisions:** D01, D04
**Work areas:** `frontend/src/theme/, backend/apps/governance/branding/`

**Implementation steps**

1. Add admin-managed platform name/logo/theme tokens with safe asset validation, independent of imported contest branding.
2. Implement light/dark/system preference using shared design tokens and persist the user preference.
3. Audit branding changes and preview the configuration before activation.
4. Verify charts, dense tables, forms, focus indicators, and report entry points in both themes.

**Acceptance checks**

- Both themes pass the existing accessibility checks and preserve readable contrast.
- Imported branding/navigation cannot alter global settings or execute content.

**Boundary:** No arbitrary CSS/HTML upload or layout redesign of every feature.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s102"></a>

### S102 - Implement scoped public API tokens

**Phase:** Phase 2
**Prerequisites:** S093, S085
**SRS sections:** 53, 18, 32
**Decisions:** D02, D04
**Work areas:** `backend/apps/accounts/api_tokens/, docs/api.md`

**Implementation steps**

1. Define explicit allowed token scopes, owner/object restrictions, expiry, revocation, and per-token rate limits.
2. Store only token digests, reveal a new token once, and audit creation/use/revocation safely.
3. Expose supported integration endpoints through the same policies and versioned documented contracts.
4. Add token-management UI with clear scope/expiry and revoke controls.

**Acceptance checks**

- A token cannot exceed its owners current rights and becomes unusable immediately on revoke/suspension.
- Tokens and secrets never appear in query strings, audit payloads, or logs.

**Boundary:** No unrestricted admin API key or replacement of browser session authentication.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s103"></a>

### S103 - Implement one code-similarity integration hook

**Phase:** Phase 2
**Prerequisites:** S093, S038, S049
**SRS sections:** 4.2, 53
**Decisions:** D04, D05
**Work areas:** `backend/apps/contests/integrity_adapter/, docs/decisions/`

**Implementation steps**

1. Obtain the selected vendor/input/output contract and approval for sending source/evidence to that service.
2. Implement an adapter that imports or retrieves findings without treating them as a final academic decision.
3. Store provenance, source/version links, and restricted evidence using existing restricted-data controls.
4. Handle failed/duplicate callbacks and vendor outages with idempotent jobs and explicit review status.

**Acceptance checks**

- Unauthorized source sharing and public/student access to restricted findings are prevented.
- A vendor failure or duplicate result cannot change marks or create a misconduct decision automatically.

**Boundary:** No homegrown similarity engine or external data transmission without explicit authorization.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s104"></a>

### S104 - Implement integrity review workflow

**Phase:** Future
**Prerequisites:** S103
**SRS sections:** 54, 14, 19, 20
**Decisions:** D04, D05
**Work areas:** `backend/apps/contests/integrity_review/, frontend/src/features/integrity/`

**Implementation steps**

1. Define documented review states, authorized reviewers, evidence links, notes, and decision history.
2. Build restricted case list/detail, assignment, response recording, and explicit decision transitions.
3. Preserve imported findings as evidence while storing university review decisions separately.
4. Require an independent explicit grading workflow for any resulting mark adjustment.

**Acceptance checks**

- Every case transition is audited and review evidence cannot leak through student/public reports.
- Changing a finding or review state cannot silently modify a mark or source record.

**Boundary:** No automatic misconduct determination or legal-policy automation.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s105"></a>

### S105 - Implement formal signed contest-performance transcripts

**Phase:** Future
**Prerequisites:** S093, S063, S077, S091
**SRS sections:** 54, 19, 25
**Decisions:** D04, D08, D10
**Work areas:** `backend/apps/reports/transcripts/, docs/runbooks/`

**Implementation steps**

1. Obtain the institution-approved transcript contents, signer authority, signature format, and key-management process.
2. Create a versioned transcript snapshot from published permitted academic records with provenance and issue date.
3. Generate the signed document through protected signing infrastructure and store issuance/revocation metadata.
4. Provide owner-authorized download and a verification mechanism that reveals only approved information.

**Acceptance checks**

- A changed PDF fails signature verification and signing keys never enter repository/logs.
- Draft/private data are excluded; reissued/revoked transcripts follow the approved institutional policy.

**Boundary:** No self-invented institutional signature or signing before signer/key approval.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s106"></a>

### S106 - Implement contest bookmarks and basic comparison dashboards

**Phase:** Future
**Prerequisites:** S093, S070, S071, S073
**SRS sections:** 54, 29
**Decisions:** D04, D08
**Work areas:** `backend/apps/contests/bookmarks/, frontend/src/features/comparisons/`

**Implementation steps**

1. Add private per-user contest bookmarks with current-access checks and owner-only management.
2. Build a bounded compare-two-contests/performance view using existing documented report metrics.
3. Display differences in scoring rules, coverage, and participant cohorts so incompatible scores are not treated as directly equivalent.
4. Add stable saved selection URLs that reauthorize every referenced resource.

**Acceptance checks**

- A bookmarked contest becoming private no longer reveals its content/title to an unauthorized user.
- Comparison values match the underlying reports and explicitly mark incomparable or unavailable metrics.

**Boundary:** No unexplained universal ranking across scoring systems.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s107"></a>

### S107 - Implement advanced course and problem comparisons

**Phase:** Future
**Prerequisites:** S106, S072
**SRS sections:** 54, 21, 22
**Decisions:** D04, D08, D11
**Work areas:** `backend/apps/reports/comparisons/, frontend/src/features/comparisons/`

**Implementation steps**

1. Select one documented comparison question and define cohort/normalization/missing-data semantics before implementing it.
2. Build a bounded query/materialization and visual/table view using versioned report datasets.
3. Expose formula, source coverage, filters, and uncertainty/limits of comparisons in the UI.
4. Benchmark the new query and preserve staff/academic scope when joining across courses.

**Acceptance checks**

- An approved example dataset produces independently checked comparison values.
- Small/hidden cohorts and unauthorized courses cannot leak through aggregate differences.

**Boundary:** No unlimited analytics builder or unsupported causal/difficulty claims; split each additional metric into a child sprint.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

<a id="s108"></a>

### S108 - Implement policy-driven retention automation

**Phase:** Future
**Prerequisites:** S093, S084, S091
**SRS sections:** 54, 19, 25, 34
**Decisions:** D10
**Work areas:** `backend/apps/governance/retention/, docs/runbooks/`

**Implementation steps**

1. Obtain the institution-approved retention policy, exclusions, academic holds, and backup-expiry requirements.
2. Implement a dry-run planner showing eligible objects, dependencies, holds, and estimated effects.
3. Add explicit approval/scheduling, resumable execution, audit, stop controls, and restore/re-erasure integration.
4. Keep academic retention floors and shared-asset references enforced independently of configuration.

**Acceptance checks**

- Dry-run and execution agree on a versioned policy snapshot; held/ineligible records cannot be deleted.
- Interrupted execution resumes safely and a restored backup cannot silently resurrect erased identities.

**Boundary:** No default automatic purge or deletion based solely on storage pressure.

**Completion evidence:** Apply the common completion contract; record changed interfaces, exact verification results, and the next ready sprint in `docs/progress.md`.

## SRS coverage and release gates

The references on each card are the detailed reading instructions. This table is
an independent coverage index so unnumbered requirements are not lost. All MVP
rows require implementation evidence before S093; a future-only item is not an
MVP launch blocker.

| SRS requirement or area | Owning sprints |
|---|---|
| AUTH-001/002/003, institutional login, bulk accounts/enrollment, lifecycle | S005, S008-S011, S016 |
| ADMIN-010, COURSE-001, academic hierarchy and multiple teachers | S012-S017 |
| IMPORT-001 through IMPORT-009 | S025, S027, S030-S032, S039-S045 |
| IMPORT-SEC-001 and all Section 23 size/path/count limits | S026-S032, S085, S088 |
| Complete supplied ZIP inventory, all structured/source/restricted areas | S025, S033-S038; archive-layout.md is the inventory |
| Four mapping strategies, placeholders, unmapped identities, teams | S034, S040-S041, S054 |
| CONTEST-001/002, source overlays, course associations | S024, S046, S050 |
| VISIBILITY-001/002/003, independent fields, Access Groups, restricted.view | S007, S018-S022, S038, S049, S085 |
| MARK-001 through MARK-006, all grading methods, non-contest assessments | S052-S068 |
| STANDING-001, SUBMISSION-001, historical snapshots/attempts | S035-S036, S047-S049 |
| Section 17 maintainability/scalability/observability/portability | S002-S004, S021, S023, S082, S088-S091 |
| Sections 18-20 authorization, privacy, audit integrity and categories | S006-S010, S019, S022, every mutating feature, S085 |
| Sections 21-22 student/problem/contest/course/batch reports, summary/detail | S069-S074 |
| CSV/XLSX/PDF exports and async generation | S075-S078 |
| Sections 24/38/39 availability states, import errors, recovery | S026-S045, S047-S050, S064-S068 |
| Sections 25/31/34 backup, files, retention, grace period, erasure | S021-S022, S044, S078, S083-S084, S091 |
| Section 26 streaming, batching, pagination, caches and indexing | S027-S035, S048, S073, S078-S079, S088-S089 |
| Sections 27-28 usability, keyboard, mobile, guided workflows | S003, feature UI cards, S086 |
| Section 29 global/contextual permission-filtered search | S079 |
| Section 30 required in-app notifications and operator alerts | S023, S080-S082 |
| Sections 32-33/40-46 API, DB, constraints, relationships, indexes | S001-S002, S005-S024, each mapper/service card |
| Sections 35-37 use cases and acceptance | S045, S049, S061, S063, S068, S087 |
| Sections 47-48 all role pages and permissions | S003, S008-S020, S042, S046-S051, S060-S063, S070-S082 |
| Sections 49-51 import/marks/re-import workflows | S042-S045, S060-S068 |
| Sections 52/55-59 MVP, tests, deployment, risks, milestones | S001-S093 and release gates S087-S093 |
| Section 53 SSO, synchronization, matching, term cloning, templates | S094-S099 |
| Section 53 saved filters/anonymized standings, branding/dark, API tokens, similarity | S100-S103 |
| Section 54 integrity workflow, signed transcript, bookmarks/comparisons, retention | S104-S108 |
| Appendices A-C stack choices and external schema/policy inputs | S001-S004, S025, S088, S090-S093 |

## Repository and completion policy

Commit the Markdown guides, plan, progress ledger, safe configuration examples,
lockfiles, migrations, trusted redistributable schemas, synthetic fixtures, test
code, and CI configuration when the user requests a commit. Keep real archives,
credentials, local environments, database/storage data, private exports, caches,
and generated PDF copies out of Git. `.gitignore` is deliberately scoped: it
must not hide every ZIP, JSON, PDF, or schema, since some are legitimate test
fixtures or project inputs. Ignoring a path does not untrack an already committed
secret. Use `git status --short` and `git check-ignore` before staging new assets.

A sprint is DONE only when its scope, prerequisites, and required checks are
actually satisfied. Status is evidence of implementation, not intent. Existing
planning files are recorded as planning setup in the progress ledger; all sprint
rows start TODO, with schema/provider/infrastructure requirements explicitly
identified as external gates. Never assume all 108 cards must run sequentially
in a single AI task or within one subscription usage window.
