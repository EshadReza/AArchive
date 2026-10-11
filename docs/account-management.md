# Account administration and profiles (S011)

Implemented for AUTH-002, SRS 16.1/20/47/48 and D02. See
[S011 verification](sprints/S011.md), [session authentication](authentication.md),
[authorization services](access.md) and [lifecycle commands](recovery-lifecycle.md).
CSV/XLSX provisioning and academic enrollment belong to later sprints.

## Try it locally

1. Follow the root [local setup](../README.md#local-setup), apply migrations and run
   Django and Vite. No demo accounts are created by migration.
2. Register/verify an eligible local Student, complete required approval and use
   the guarded [first-Administrator command](access.md) as documented there.
3. Sign in and choose **Manage accounts** from `/account`. `/admin/users` provides
   role/state/search filters and pagination. Open an account for its details,
   reviewed role changes, approval, lifecycle commands and pending invitation resend.
4. Choose **Create an account** (`/admin/users/new`), supply identity, explicit roles
   and the separate approval requirement, review, then **Confirm and invite**.
   The initial password is unusable; administrators never set a recipient password.
5. Development mail appears in the Django terminal. Open its `/accept-invitation`
   link in a separate browser context, choose a password and submit. If approval
   is required, use the admin detail screen's `approve` command before signing in.
6. **Edit profile** from `/account` opens `/profile`. Only the display name can
   change. Email, student ID and platform roles are read-only.

Review screens show the target, requested role/state change, reason and consequences
before mutation. Removing Teacher revokes delegated grants; restricting an account
ends all active sessions and expires pending recovery/verification/invitation links.
A failed or stale action requires reloading the account. Server authorization and
last-Administrator protection apply even if the browser is stale or bypassed.

## API contract

Paths have no trailing slash. All responses are `Cache-Control: no-store`. Bootstrap
CSRF using `/api/auth/session`; every write, including anonymous invitation acceptance,
requires the cookie/header. JSON is bounded by the existing 8 KiB auth parser.
Unexpected fields and coercible non-string/non-boolean input are rejected.

| Method and endpoint | Access and request | Success |
|---|---|---|
| `GET /api/users` (also HEAD) | Eligible Administrator; optional `page`, `page_size`, `role`, `state`, `q` | 200 `{count, next, previous, results}` |
| `POST /api/users` | Eligible Administrator; exactly `{email, display_name, student_id, roles, approval_required}` | 201 account projection |
| `GET /api/users/{uuid}` (also HEAD) | Eligible Administrator | 200 account projection |
| `POST /api/users/{uuid}/roles` | Eligible Administrator; exactly `{roles, expected_roles, reason}` | 200 account projection |
| `POST /api/users/{uuid}/invitation` | Eligible Administrator; exactly `{}` | 202 fixed delivery-request message |
| `POST /api/users/{uuid}/lifecycle` | Existing S010 contract: `{command, expected_state, reason}` | 200 `{id, state}` |
| `GET /api/profile` (also HEAD) | Current eligible authenticated actor, selected by the server | 200 own account projection |
| `PATCH /api/profile` | Same actor; exactly `{display_name}` | 200 own account projection |
| `POST /api/auth/invitation/accept` | Public, CSRF protected; exactly `{token, password}` | 200 fixed acceptance/approval message; no login session |

List ordering is email then UUID; default page size 25, maximum 100. `role` uses
STUDENT/TEACHER/ADMINISTRATOR and `state` uses the fixed lifecycle vocabulary.
`q` is at most 100 characters and searches email, student ID and display name.
Duplicate/unknown filter keys and invalid pagination are rejected. Permission checks
precede list counts, search and detail lookups: ordinary Students/Teachers cannot
enumerate users, including by probing nonexistent IDs.

Creation requires a valid email (maximum 254 characters), nonblank display name
(maximum 200), nullable/blank optional student ID (maximum 64), one to three distinct
fixed roles and a literal boolean approval flag. Email/student ID are canonicalized
by the existing manager. A trusted Administrator may invite a valid email outside
the self-registration domain allowlist; the recipient must still prove ownership.
The approval choice is explicit on the review screen. No creation field can mark
an email verified, supply credentials, choose lifecycle state or update an existing
account. Verified identity editing is not exposed by these endpoints.

Account projection keys: `id`, `email`, `display_name`, `student_id`, `roles`,
`state`, `approval_required`, `approved`, `email_verified`, `date_joined` (ISO
string), and `invitation_pending` (boolean). It contains no password/hash, token,
challenge digest or private session data. Invitation pending means a previously
invited, unverified, PENDING account with unusable credentials and an unconsumed
challenge; an expired challenge can be resent.

Role writes require the roles displayed when reviewing in `expected_roles`.
Allowed reasons: `administrative_change`, `user_request`, `security_response`.
Stale roles return 409 `account_conflict`; existing lifecycle stale states return
409 `state_conflict`. Duplicate creation returns a safe 409 without changing the
existing account or sending mail. Invalid fields/prerequisites return 400,
unauthorized users 403, missing accounts 404 only after admin authorization, and
throttles 429 with `Retry-After`. Errors use the shared safe envelope and bounded
field messages, never raw database/mail exceptions.

## Invitation transaction and security

Admin creation uses the existing pending-Student manager, then the audited role
service for the explicitly selected roles. Account, roles, invitation digest and
audit records commit together under the shared privilege lock. Disabled invitation
configuration or audit failure rolls creation back. No existing account is merged
or overwritten. Approval and email verification remain separate gates.

`accounts.0005_invitation` adds one challenge per user: unique SHA-256 token digest,
keyed email/password-revision digest, indexed expiry, consumption time and send time.
A cryptographically random token appears only in email and transient memory. Its
fixed-origin link uses a fragment, which the frontend removes from the address bar;
no browser credential storage or automatic acceptance occurs.

Acceptance rechecks the user and challenge under locks, validates the chosen
password, verifies email ownership, consumes the challenge and activates only if
required approval is already complete or was explicitly not required. It never
changes roles or logs the recipient in. Concurrent/replayed acceptance succeeds
at most once. Expiry, changed email/password, restriction and disabled invitation
configuration reject the link. Password recovery cannot bootstrap an invited
account with unusable credentials. Resending rotates the token after a cooldown;
it cannot reset an already accepted account's password. Restoration does not
revive expired challenges or sessions.

Public acceptance consumes the existing shared PostgreSQL recovery peer budget
(`RECOVERY_IP_LIMIT` / `RECOVERY_WINDOW_SECONDS`); it does not reveal an email
identity through responses. Administrator resend has a per-account cooldown.
Creation, issuance, acceptance and profile updates emit reviewed audit events.
Profile events record a fixed outcome rather than immutable copies of names;
no raw password/token/email/profile text enters these event payloads. Existing role
and lifecycle events retain their own reviewed state/role projections.

## Configuration and operational limits

| Setting | Local/test default | Purpose |
|---|---|---|
| `INVITATIONS_ENABLED` | `true` | Production defaults to `false`; explicitly enable configured delivery |
| `INVITATION_SECONDS` | `86400` | Positive lifetime, maximum 604800 seconds |
| `INVITATION_RESEND_SECONDS` | `60` | Positive cooldown, maximum 86400 seconds |
| `PUBLIC_APP_ORIGIN` | `http://127.0.0.1:5173` | Fixed link origin; HTTPS required for production mail |

Production invitation opt-in requires validated SMTP/from/origin settings as in
[registration mail configuration](registration.md). Development uses console mail;
tests use memory or an isolated temporary mailbox. No external email is needed to
verify the feature. Mail runs synchronously after commit with a bounded timeout;
delivery failure logs a fixed warning and leaves a pending account for admin resend.
There is no durable mail queue yet and 201/202 does not certify mailbox delivery.

Migration reversal removes invitation challenges. It was tested only on a disposable
empty database; use forward repairs and backups for real records. No account deletion,
anonymization, batch upload or enrollment is implemented here.
