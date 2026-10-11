# Password recovery and account lifecycle (S010)

Implemented for AUTH-003, SRS 16.1/18/34 and D02. This extends the existing
[session](authentication.md), [registration](registration.md) and
[authorization](access.md) contracts. Account management/invitations are implemented in
[S011](account-management.md); anonymization is S084. No academic/source records are deleted by these
commands. See [S010 evidence](sprints/S010.md).

## Local browser flow

Use the README's migration and two-terminal setup. On `/login`, select **Forgot
your password?**, or open `/forgot-password`. Submit an existing account email;
development prints its reset email in the Django terminal. Open that link, choose
a different password and submit. The link alone performs no mutation. All sessions
end and the user signs in again with the new password.

The Account page links to `/change-password`. This requires the current password
and a different new password, and also ends all sessions, including the current
one. Both forms clear password fields on submit and keep no credentials in browser
storage. `/reset-password` removes its token fragment from browser history, retains
it only in memory, and handles replacement links opened in the same tab. Reopening
the original email link is necessary after reloading a page whose fragment was
cleared. Reset errors are generic and focus the error summary.

Only verified, approved (when required), eligible accounts with usable passwords
receive reset links. PENDING, SUSPENDED, ARCHIVED, ANONYMIZED and invitation-only
accounts do not. INACTIVE, GRADUATED and ALUMNI can recover their accounts; the
current signup domain allowlist does not remove recovery for existing alumni.
Password reset never changes lifecycle state, verification, approval, roles or
profile. A subsequent successful login may reactivate INACTIVE per S008.

## Recovery endpoints

All are JSON POST endpoints without trailing slashes. Bootstrap CSRF at
`GET /api/auth/session`; anonymous reset requests/confirmations also require the
cookie/header. Foreign Origins fail. The 8 KiB auth body cap, explicit field lists,
1,024-character password cap and `Cache-Control: no-store` apply.

| Route | Exact request fields | Success |
|---|---|---|
| `/api/auth/password-reset` | `email` string | 202 generic `{message}` for known/unknown/ineligible/disabled recovery |
| `/api/auth/password-reset/confirm` | `token`, `password` strings | 200 `{message}`; all account sessions revoked |
| `/api/auth/password-change` | `current_password`, `password` strings | Authenticated 200 `{message}`; all account sessions revoked |

Tokens are 43-character URL-safe random strings. Malformed or extra fields return
400. Invalid/expired/replayed reset tokens and incorrect current passwords return
400 `recovery_invalid`; password-policy rejection returns 400 `password_invalid`
with fixed guidance. Passwords must differ from the current password and pass
S009's Django validators (12 characters minimum, common/numeric/similarity checks).
CSRF or anonymous password-change attempts return 403; unsupported methods return
405. Generic 429 `recovery_limited` includes `Retry-After` seconds. Errors contain
`code`, `message`, and `request_id: null`, without raw validator/SMTP exception text.

The reset-request endpoint returns no account ID, token or account-state details.
It never logs a browser in. Disabled production recovery returns the same generic
response. Reset confirmation also fails while recovery is disabled; authenticated
password change continues to work because it requires no mail delivery.

## Tokens, throttling and email

`PasswordReset` stores one challenge per user: unique SHA-256 token digest, keyed
email/password-revision digest, indexed expiry and optional consumed timestamp.
There is no raw reset token in the database. Reissue rotates the challenge; changed
email/password, expiry, prior consumption or current ineligibility rejects it.
Concurrent confirmation can consume a token only once. Password changes consume
outstanding reset challenges; restrictions expire reset and verification links.

Recovery counters reuse `LoginAttempt` with separate keyed HMAC namespaces.
Reset requests use normalized email; password changes use actor UUID; confirmation
uses the peer budget. All share the recovery peer budget. `REMOTE_ADDR` is used;
forwarded headers are ignored. PostgreSQL row locks enforce finite fixed windows.
Blocked retries do not extend expiry or create extra identity rows for a blocked
peer. Threshold audit events are fixed system outcomes without submitted values.
The existing expired-counter cleanup also covers recovery counters.

| Setting | Default | Range / purpose |
|---|---|---|
| `PASSWORD_RESET_ENABLED` | Development/test: `true`; production: `false` | Explicit production opt-in after configuring mail |
| `PASSWORD_RESET_SECONDS` | 3600 | Integer 1–86400 |
| `RECOVERY_IDENTITY_LIMIT` | 3 | Integer 1–100 attempts per email/actor per window |
| `RECOVERY_IP_LIMIT` | 30 | Integer 1–1000 attempts per peer per window |
| `RECOVERY_WINDOW_SECONDS` | 900 | Integer 1–86400 |

The `.env.example` enables local reset mail. Production opt-in requires HTTPS
`PUBLIC_APP_ORIGIN`, SMTP `EMAIL_HOST` and a configured `DEFAULT_FROM_EMAIL`, even
if self-registration is disabled. S009's SMTP credentials/TLS/timeout settings
apply. Development uses console mail; tests use captured mail only. Links use the
configured origin, never the request Host, with the token in the fragment.

Delivery happens after commit with a bounded SMTP timeout. Failure keeps the
generic response and emits a fixed warning without secrets; request another link
to recover. No durable queue/automatic retry is implemented. Keep console/mailbox
artifacts private. Production trusted proxy/IP configuration remains S090.

## Administrator lifecycle commands

`POST /api/users/{uuid}/lifecycle` requires a current eligible Administrator through
the central `users.manage` policy, rechecked inside the privilege lock. It takes
exactly `{command, expected_state, reason}`, all strings. Reasons are
`administrative_change`, `user_request`, or `security_response`.

Success is 200 `{id, state}`. A stale `expected_state` returns 409 `state_conflict`;
invalid transitions/prerequisites/last-admin restrictions return 400
`transition_invalid`. Missing accounts return 404 only after Administrator
authorization; non-Administrators receive 403 before lookup. Submitted roles,
passwords, arbitrary target states or approval timestamps are rejected. S011 adds an
[admin detail screen](account-management.md) that reviews and calls this command API.

### Allowed transition table

| Command | Source | Result / prerequisites |
|---|---|---|
| `approve` | PENDING with `approval_required=true` | Record approval; ACTIVE only if email already verified, otherwise remain PENDING |
| `activate` | INACTIVE | ACTIVE; verification/approval remain required |
| `inactivate` | ACTIVE | INACTIVE; retains eligibility and historical access |
| `graduate` | ACTIVE or INACTIVE | GRADUATED; identity/history/roles and existing sessions retained |
| `alumni` | ACTIVE, INACTIVE or GRADUATED | ALUMNI; same retained-access boundary |
| `suspend` | PENDING, any eligible state, or ARCHIVED | SUSPENDED; preserve first prior state, revoke sessions and expire recovery/verification links |
| `archive` | PENDING, any eligible state, or SUSPENDED | ARCHIVED; same restriction effects |
| `restore` | SUSPENDED or ARCHIVED with recorded prior state | Restore exactly that recorded state; never revive sessions/tokens |

All other transitions fail. ANONYMIZED is terminal and cannot be entered or exited
by this API. Direct ACTIVE transitions from PENDING cannot bypass email/approval.
Repeated approval of an already-approved PENDING account is a no-op. Switching
between SUSPENDED and ARCHIVED retains the first prior state. Restoring a prior
PENDING state stays pending; restoring an eligible state rechecks prerequisites.

The last eligible Administrator cannot be suspended/archived. Lifecycle edits and
role edits share the S007 singleton lock, so concurrent operations cannot remove
all eligible administrators. Approval and email verification also share it and
can activate only once. User UUID, profile, roles, dates and all existing references
remain intact; historical reads still obey their resource policies.

The new `User.state_before_restriction` field defaults to empty. A pre-existing
closed account without a recorded prior state fails restoration safely; do not
guess an ACTIVE state or use password recovery as a restoration shortcut. Such
legacy data needs an explicit reviewed repair based on authoritative history.

## Session revocation and audit integrity

Credential/lifecycle mutations take the privilege lock, then the current user and
challenge locks, and commit their mutation, revocation and audit in one transaction.
Audit failure rolls all of them back. New sessions are created under the same
privilege lock, preventing login from racing a restriction into a live session.

Revocation decodes active Django database sessions in batches of 200 and deletes
only those belonging to the subject. It covers sessions issued before S010 and
does not wait for a browser request. Restoration cannot revive deleted rows.
Expired rows remain inaccessible and are removed by `clearsessions`. The current
implementation scans active sessions (bounded memory, linear work); a relational
session-owner index may be needed when deployment scale is measured. This is not
a claim of tested high-volume capacity.

S008's current-state middleware remains a defensive check for changes outside the
service. Supported account mutations must use these audited services. Already
executing requests cannot be recalled; sensitive service mutations must recheck
current authorization under the shared lock, as these services do.

Audit schemas include reset issue, password change, session revocation, generic
recovery failure/limit and recorded approval. State changes use the existing event.
Only fixed outcomes/states and stable UUID targets are stored. No passwords,
encoded hashes, reset tokens, emails or arbitrary reasons enter audit payloads.
