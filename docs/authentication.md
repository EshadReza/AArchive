# Session authentication (S008)

Implemented against AUTH-001, SRS Sections 16.1, 18 and 46, and D01/D02.
See [verification evidence](sprints/S008.md). Registration and verification are implemented in [S009](registration.md); password recovery, lifecycle commands
and proactive session revocation are implemented in [S010](recovery-lifecycle.md).
[S011](account-management.md) adds Manage accounts for Administrators and Edit
profile for signed-in users, plus invitation acceptance.

## Browser and API contract

Run migrations and both development servers using the root README. Open `/login`
or `/account` through Vite. Both routes bootstrap the session, show a sign-in form
when anonymous, and show the current account with Refresh session and Sign out
when authenticated. An existing eligible, verified account with a usable password
is required; required approval must also be complete. Migrations create no demo
accounts. Use the [registration flow](registration.md) to create a new Student
when institutional domains are configured. The first-Administrator command promotes an existing eligible account;
it does not create one. Django `createsuperuser` is not a supported provisioning
workflow for this custom model.

All paths below omit a trailing slash. All responses use `Cache-Control: no-store`.

| Endpoint | Request | Result |
|---|---|---|
| `GET /api/auth/session` (also HEAD) | No body; allowed anonymously | 200 with `{user: null}` or current user; sets/refreshes the CSRF cookie |
| `POST /api/auth/login` | JSON containing exactly string `email` and `password`; CSRF cookie/header | 200 with current user; 401 generic invalid credentials; 429 generic attempt limit with `Retry-After` seconds |
| `POST /api/auth/logout` | CSRF cookie/header; no body needed | 204, including an already anonymous session |

The user projection contains only `id`, `email`, `display_name`, `state`, and
`roles`. The frontend validates this shape and the fixed state/role vocabulary.
Malformed login input returns 400; missing/invalid CSRF or foreign Origin returns
403. Errors contain `code`, a safe `message`, and `request_id: null`. Unsupported
methods/media types retain their HTTP status with a generic error envelope.
The JSON parser reads at most 8,193 bytes and rejects bodies over 8,192 bytes;
email is limited to 254 characters and password to 1,024, without trimming passwords.

Fetch the session before the first POST. Login rotates Django's CSRF token and
uses Django session rotation/identity replacement; the client reads the current
CSRF cookie for each subsequent mutation. CSRF is required even for anonymous
login/logout. The session cookie is HttpOnly, SameSite=Lax, and Secure in
production; CSRF is SameSite=Lax and Secure in production. No credentials or
session tokens are stored in browser storage. Password input is cleared on submit.

## Eligibility and transactions

The custom backend uses Django password hashing and current platform eligibility.
Unknown/unusable credentials still perform dummy hashing. Wrong passwords, unknown
accounts and forbidden states return the same invalid-credential response.
INACTIVE reactivates to ACTIVE on successful login with an audited state change;
GRADUATED and ALUMNI retain their states. Source roles and framework Groups or
Permissions confer no platform authority.

After hashing, login takes the shared privilege lock then the user row lock and
rechecks eligibility and password revision. Session persistence, last-login and
success audit commit together. Logout deletes the session with its audit event.
On subsequent requests, middleware refetches the actor and deletes a session if
a forbidden state is detected, recording revocation. Restoring the account cannot
revive that deleted session. Password changes and expiry also invalidate access.
Health bypasses session evaluation to remain independent of database availability.
S010 shares the privilege lock and proactively deletes all active subject sessions
on password changes and restriction transitions. S008 also detects a forbidden
state on request as a defensive check. See [revocation contract](recovery-lifecycle.md#session-revocation-and-audit-integrity).

## Configuration and maintenance

These environment settings accept integers from 1 through the stated maximum:

| Setting | Default | Maximum | Meaning |
|---|---:|---:|---|
| `AUTH_SESSION_SECONDS` | 43200 | 604800 | Absolute session lifetime, not extended by reads |
| `AUTH_LOGIN_ATTEMPT_LIMIT` | 5 | 100 | Attempts per normalized email per window |
| `AUTH_LOGIN_IP_LIMIT` | 30 | 1000 | Attempts per peer IP per window |
| `AUTH_LOGIN_WINDOW_SECONDS` | 900 | 86400 | Fixed attempt window in seconds |

PostgreSQL rows hold keyed SHA-256 HMACs of normalized email and peer address,
counts and expiry. Row locking shares budgets across workers. Peer rows are locked
first; a blocked peer cannot allocate new identifier rows by varying email.
The peer is `REMOTE_ADDR`; forwarded headers are ignored. Deployment proxy/IP
trust and shared-network tuning must be verified in S090.

These are attempt budgets, including successful attempts. Success clears the
identifier count but keeps the peer budget. Known and unknown accounts use the
same limits. Reaching a threshold records one safe lockout event; blocked retries
do not extend expiry or repeat that event. Expiry permits retry automatically.
Failure audit contains only a fixed outcome, never the supplied email/password/IP.

Run maintenance against the intended environment:

```sh
uv run --locked --env-file .env python backend/manage.py clearsessions
uv run --locked --env-file .env python backend/manage.py clear_expired_login_attempts
```

These delete expired sessions/counters only. Scheduling belongs to operations;
no scheduler is installed by this sprint. No session signing secret or real
account credentials should be committed.

## Real browser checks

Install frontend dependencies and Playwright Chromium using the root README.
From the repository root, with a dedicated `TEST_DATABASE_URL` configured:

```sh
uv run --locked --env-file .env python scripts/check_auth_browser.py
```

The database role needs permission to create/drop a test database. The runner
creates a uniquely named `test_auth_browser_*` database, applies migrations, seeds
two synthetic users, starts Django/Vite on ephemeral ports, and removes its
servers/database in a finally block. The suspend/restore fixture refuses other
settings/databases and accepts only the synthetic identities. It is not an API.
CI runs this helper. Desktop/mobile flows cover real login, persistence, logout,
CSRF, forbidden-state deletion, finite lockout recovery, accessibility and layout.
Screenshots/reports in `frontend/test-results/` remain ignored.
