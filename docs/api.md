# API contract guide

Status: `/api/health` is implemented by S002; S006 adds the protected audit read API.
S008 adds [session login/logout and current-account endpoints](authentication.md).
S009 adds [registration, verification and resend](registration.md#api-contract).
S010 adds [recovery and lifecycle commands](recovery-lifecycle.md); S011 adds
[admin accounts, invitations and own-profile endpoints](account-management.md#api-contract).
S012 adds [academic structure administration](academic-structure.md#api).
S013 adds [course catalog endpoints](course-catalog.md#authorization-and-api).
S014 adds [offering, teacher-history and selection endpoints](offerings.md#api-contract).
Other business routes below remain planned;
individual sprints implement them. Use [progress](progress.md) for actual status and [TASKS](../TASKS.md) for
the detailed work. The SRS's Sections 10, 16, 18, 32, and 46 are the product basis.

S007 adds [shared authorization and audited privilege services](access.md).
The audit routes now use their central guard/filter; no role/grant write HTTP
endpoint was introduced in S007. S011 now exposes audited role changes through
`POST /api/users/{uuid}/roles`; scoped-grant HTTP writes remain pending.
S008 connects real authenticated sessions to these
checks. Domain views must filter lists and recheck details with their registered policy.

## Implemented foundation endpoint

`GET /api/health` returns HTTP 200, JSON `{"status":"ok"}` and
`Cache-Control: no-store`. HEAD returns the same status with no body. Other
methods return 405. Anonymous callers may read it; it exposes no environment,
dependency version, credentials or database information and performs no database
queries. It is process liveness, not dependency readiness. The path has no trailing
slash. Production HTTPS and host checks apply to it like other endpoints.

DRF defaults require an authenticated session. Health explicitly opts into public
reads. S008 installs the platform authentication backend and current-state session
middleware. Auth endpoints explicitly allow anonymous bootstrap/login/logout while
enforcing CSRF on both POST routes, including anonymous requests. The shared conventions
below are contracts for later feature sprints, including the unified error envelope.

## Shared conventions

### Implemented audit reads (S006)

`GET /api/audit` and `GET /api/audit/{id}` (also HEAD) require a current eligible
Administrator. List uses cursor pagination, 50 records by default, maximum 100;
responses contain `results`, `next`, `previous`. No writes or teacher/student
scope exists. Every request rechecks current role/state; errors and results use
`Cache-Control: no-store`. S008 verifies real session access for eligible
Administrators and denial after logout or loss of eligibility. See [audit contracts, examples and coverage](audit.md#read-api).

### Conventions for feature routes

- REST JSON under `/api/`; same-origin Django session authentication and CSRF for
  browser writes. SSO/tokens are later phases, not alternate MVP shortcuts.
- UUID/public opaque identifiers are recommended; secrecy of an ID is never an
  access control. Every fetch/list/action rechecks current scope.
- Paginate lists with a bounded size and stable secondary sort; use cursor-based
  pagination for very large immutable histories where appropriate. Document each
  route's selected style. Permission filtering occurs before counts and facets.
- Return a consistent error object with `code`, safe `message`, optional
  `field_errors`, and `request_id`. Imported raw exception text and internal paths
  must not reach clients. Use 400/401/403/404/409/413/429 consistently; protected
  resource existence must not leak through inconsistent 403/404 behavior.
- Long jobs return 202 with an opaque job identifier and status link. Require a
  current scoped read at every poll. Commands confirm a specific preview/revision;
  stale versions return 409 instead of overwriting concurrent work.
- Explicit command endpoints represent publish, unlock, confirm, retry, restore,
  and reapply; they are not broad PATCH endpoints over all model fields.
- Use idempotency keys and database uniqueness/locking for retryable mutations.
  Repeating a successful confirmation cannot create another live version.
- Apply SRS 1.1 Section 10's common privacy matrix and ADR 0004's assignment
  rules to every route, worker, download, and aggregate. An offering teacher is
  not implicitly a global manager of every contest linked to that offering.
- Serialize Decimal values and source units explicitly. Timestamps use documented
  ISO representations; preserve source timezone metadata. Missing values remain
  distinct from zero and from unavailable/excluded/truncated/corrupted sections.
- Define upload size/time limits and source MIME behavior. Source bytes are never
  executable responses. Assets use an authorized endpoint or scoped expiring URL.

## Frontend client (S003)

`frontend/src/lib/api.ts` implements `request<T>(path, options)` and
`getPage<T>(path, { signal })` independently of feature endpoints:

- Only the current origin's `/api` and `/api/...` paths are permitted, including
  absolute pagination URLs on that origin. Other origins, credentials in URLs,
  fragments and paths escaping the API namespace are rejected before fetch.
- Fetch uses `credentials: same-origin`, `mode: same-origin`, `redirect: error`
  and `cache: no-store`. It has no bearer-token or local/session storage path.
- POST/PUT/PATCH/DELETE read Django's current `csrftoken` cookie and send
  `X-CSRFToken`; missing/malformed cookies fail before a request. GET sends no
  CSRF header and rejects a body. JSON bodies set the content type. S008 provides
  same-origin session/CSRF bootstrap at `GET /api/auth/session`.
- `AbortSignal` is forwarded and cancellation remains cancellation, not a generic
  network error. Network failures become a safe `ApiError` with status 0.
- `ApiError` exposes `code`, `message`, `status`, `fieldErrors` and optional
  `requestId`. The planned structured error envelope is recognized. Non-JSON or
  unrecognized error responses use a generic message without exposing raw HTML
  or exception text. A 204 response returns undefined; malformed successful JSON
  is rejected. Render server-provided text through React, never as raw HTML.
- Pages require `{results, next, previous}` and optionally a nonnegative integer
  `count`. Results must be an array; links are null or permitted API URLs. This
  supports count-based and cursor pagination without assuming a total. Feature
  modules still need to validate their individual record schemas; TypeScript
  generics alone do not validate server data.

The synthetic workshop never invokes the client. S004 connects local routing:
Vite forwards `/api` to Django (default `127.0.0.1:8000`) with the original browser
Host, Origin and cookies. No CORS bypass is configured. `/api/health` can be read
through the frontend port. `scripts/check_dev_proxy.py` proves forwarding and CSRF
enforcement using an isolated test URLconf; its probe is absent from normal routes.
Later endpoint sprints verify integration with real responses and authorization.

## Planned endpoint ownership

| Area and route family | Behavior | Primary sprint |
|---|---|---|
| `/api/auth/login`, `/logout`, `/session` | Implemented session login, logout, current actor; [contract](authentication.md) | S008 |
| `/api/auth/register`, `/api/auth/verify`, `/api/auth/resend-verification` | Implemented Student registration and one-use verification; [contract](registration.md) | S009 |
| `/api/auth/password-reset`, `/api/auth/password-reset/confirm`, `/api/auth/password-change` | Implemented recovery/change with all-session revocation; [contract](recovery-lifecycle.md) | S010 |
| `/api/users/{id}/lifecycle` | Implemented Administrator-only audited lifecycle commands | S010 |
| `/api/users`, `/api/users/{id}`, `/api/users/{id}/roles`, `/api/users/{id}/invitation`, `/api/profile`, `/api/auth/invitation/accept` | Implemented admin accounts, invitations and limited self-profile; [contract](account-management.md#api-contract) | S011 |
| `/api/departments`, `/api/batches`, `/api/terms`, `/api/sections` (plus detail/archive) | Implemented Administrator-only academic structure; [contract](academic-structure.md#api) | S012 |
| `/api/courses`, `/{id}`, `/{id}/archive` | Implemented reusable catalog, admin writes and filtered Teacher reads; [contract](course-catalog.md) | S013 |
| `/api/course-offerings`, `/{id}`, `/{id}/teachers`, `/{id}/archive`, `/staff-options` | Implemented scoped offerings, retained teacher assignments and admin staffing | S014 |
| `/api/course-offering-options/{kind}` | Implemented active academic selectors for Teachers/Admins | S014 |
| `/api/course-offerings/{id}/enrollments` | Planned roster operations | S015 |
| `/api/account-imports` | Admin CSV/XLSX preview and confirmation | S016 |
| `/api/access-groups`, `/{id}/members` | Delegated group management | S018 |
| `/api/visibility`, `/preview` | Scoped policy read/write and effect preview | S020 |
| `/api/assets/{id}` | Individually authorized delivery | S022 |
| `/api/imports`, `/{id}/status`, `/{id}/logs` | Upload and scoped job observation | S027 |
| `/api/imports/{id}/mappings`, `/preview`, `/confirm` | Revisioned mapping and confirmation | S040-S043 |
| `/api/imports/{id}/provision-student` | Separately confirmed accounts command creating only a pending Student under the narrow capability | S041 |
| `/api/imports/{id}/retry`, `/cancel` | Recovery commands | S044 |
| `/api/contests`, `/{id}/offerings`, `/{id}/tags` | Archive views and university overlays | S046 |
| `/api/contests/{id}/standings` | Official current/historical snapshot rows | S047 |
| `/api/submissions`, `/{id}/runs`, `/{id}/source` | Independent metadata/source/log gates | S048-S049 |
| `/api/problems`, `/api/contests/{id}/materials` | Problems and historical content | S050 |
| `/api/assessments` | Manual/contest-derived assessment definitions | S052 |
| `/api/marks`, `/{id}/history` | Scoped assignment and append-only history | S053 |
| `/api/grading-rules`, `/preview`, `/apply` | Versioned typed rule workflows | S055-S059 |
| `/api/marks/finalize`, `/publish`, `/lock`, `/unlock`, `/correct` | Audited state transitions | S061 |
| `/api/feedback`, `/api/my-marks` | Separate private/visible projections | S062-S063 |
| `/api/imports/{id}/diff`, `/confirm-reimport` | Reviewed source-version promotion | S064-S066 |
| `/api/assessments/{id}/reapply` | Separate explicit source-score correction | S067 |
| `/api/reports/student`, `/problem`, `/contest`, `/course`, `/batch` | Scoped summary/detail datasets | S070-S072 |
| `/api/analytics`, `/api/dashboard` | Versioned aggregates and role projections | S073-S074 |
| `/api/exports`, `/{id}/status`, `/{id}/download` | Job-backed CSV/XLSX/PDF export | S078 |
| `/api/search` | Permission-filtered results/facets/counts | S079 |
| `/api/notifications`, `/{id}/read` | Owner-only inbox | S080-S081 |
| `/api/audit`, `/api/audit/{id}` | Implemented Administrator-only audit reads; real session transport implemented in S008 | S006 |
| `/api/admin/settings` | Typed configuration | S082 |
| `/api/contests/{id}/trash`, `/restore`, `/purge-preview`, `/purge` | Governed deletion and recovery | S083-S084 |

Exact route naming, schemas, and methods become concrete in each owning sprint.
Register implemented request/response examples or generated API schema alongside
this table; do not claim these proposed routes are already served.

## Contract rules that cross features

The import preview references the archive digest, validated schema version,
current source version, and mapping revision. Confirmation must reject a stale
preview. The grade editor likewise includes a mark/rule revision. Re-import never
invokes grading corrections implicitly. Report jobs snapshot the requested data
version and reauthorize current access on generation and download.

The source namespace is verified configuration. A repeated accepted payload returns
an exact-duplicate outcome referencing its existing version without changing the
current pointer, including if that version was superseded. Import job state remains
separate from source-version state. Provisioning uses a separate explicit command,
not an implicit effect of preview: users.manage remains admin-only, existing
accounts are never modified, and the pending account/audit survives cancellation.

Published correction commands reference the expected visible mark revision and
the reviewed proposal. They keep the old visible value until an atomic correction
and republish succeeds; stale proposals return conflict. FINALIZED requires reopen,
LOCKED requires an elevated audited unlock, and contest-only assignments cannot
edit grades. Group/report delegation never bypasses individual-mark privacy.

Platform request/response property names are designed here during implementation.
They are separate from exporter JSON properties, which must come from the trusted
archive schemas. No API serializer may pass through an entire imported object or
database model without an explicit field allowlist.
