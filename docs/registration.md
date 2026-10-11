# Institutional registration and verification (S009)

Implemented for AUTH-002, SRS 16.1/18/30 and D02. This is self-registration as a
Student. Admin account creation and bulk provisioning remain later work. Password recovery
and lifecycle commands are implemented in [S010](recovery-lifecycle.md). See [authentication](authentication.md) for
the login/session boundary and [S009 evidence](sprints/S009.md) for verification.

## Try it locally

Use the root README's PostgreSQL, migration and two-terminal setup. In your ignored
`.env`, set `INSTITUTIONAL_EMAIL_DOMAINS` to the exact institutional domain(s) you
intend to allow, separated by commas. The empty default disables registration.
Set `PUBLIC_APP_ORIGIN` to your frontend origin, normally `http://127.0.0.1:5173`.
Restart Django after changing configuration and apply migrations.

1. Open `/register`, enter institutional email, display name and password.
2. The development Django terminal prints the verification email. Open its link
   and press **Verify email**. Merely opening a link never changes the account.
3. Sign in at `/login`. With approval enabled, verification leaves the account
   pending until an administrator approves it through the S010 lifecycle service.
4. Use `/resend-verification` if delivery failed or the link expired. A resend
   replaces the previous link. The page handles replacement links opened in the
   same browser tab, clears the URL fragment, and requires explicit confirmation.

No real mail is sent by development/test profiles, and no sample user is created
by migrations. Console verification links are credentials: keep terminal logs
private. Passwords are cleared from the form on submit; tokens remain in memory
only after their URL fragment is removed. Reloading that cleared page requires
reopening the email link. No browser storage is used.

## API contract

Bootstrap CSRF with `GET /api/auth/session`. All routes below require the CSRF
cookie/header, including anonymous requests, and reject foreign Origins. Responses
use `Cache-Control: no-store`; the existing 8 KiB auth JSON parser limit applies.

| POST route | Exact JSON fields | Success |
|---|---|---|
| `/api/auth/register` | `email`, `display_name`, `password`, all strings | 202 generic `{message}` |
| `/api/auth/resend-verification` | `email`, string | 202 with the same generic message |
| `/api/auth/verify` | `token`, 43-character URL-safe string | 200 `{message}` confirming verification, with approval caveat |

Registration/resend return the same status/body for eligible, already existing,
unknown, closed or disallowed addresses. They never return an account ID or token.
Malformed fields, extra fields and invalid password policy return generic 400;
invalid/expired/replayed verification returns 400 `verification_invalid`. A shared
budget rejection returns 429 `registration_limited` with `Retry-After` seconds.
CSRF failures return 403; unsupported methods return 405. Errors use the auth
envelope `{code, message, request_id: null}`. GET never consumes a token.

Email is trimmed/lowercase and must match an explicitly listed domain exactly;
subdomains, suffix matches and wildcards do not confer eligibility. The domain
must still be allowed at verification time. Email is limited to 254 characters,
display name to 200 and password to 1,024. Passwords require at least 12 characters
and pass Django's common-password, numeric-password and user-similarity validators.
Existing accounts are never altered by registration: no password/profile/role
replacement and no implicit resend. Only challenges created by self-registration
can be resent. Administrator invitations are implemented separately in [S011](account-management.md);
import identity matching remains a later workflow.

## Persistence and transactions

The trusted account manager creates a PENDING Student with a hashed password.
Registration snapshots `REGISTRATION_REQUIRE_APPROVAL` onto the new user. Even if
that setting later changes, that user's approval requirement remains in effect.
No role/state/approval/student-ID fields are accepted from self-registration.

`accounts.0003_emailverification` adds `EmailVerification`: one challenge per user,
unique SHA-256 token digest, keyed account digest, indexed expiry and optional consumed timestamp. The
bearer token uses 32 cryptographically random bytes; only its digest is stored.
The keyed account digest binds the challenge to the current email and password
revision; a change to either invalidates an outstanding link.
The token is dedicated to verification and cannot authenticate a session. Resend
rotates the digest/expiry; successful verification consumes it once, under locks.

Registration, resend and verification take the shared privilege lock before user
and challenge locks. Concurrent registration creates only one account; concurrent
verification can succeed only once. Creation/issue/verification and any activation
commit with reviewed audit events. Audit failure rolls back the corresponding
mutation. Events contain UUID targets and fixed state/outcome values; no password,
email, verification token or SMTP secret is logged in audit payloads.

Verification sets `email_verified_at` only on a still-PENDING, unverified user.
It activates only when approval is unnecessary or already recorded. It cannot
restore SUSPENDED, ARCHIVED or ANONYMIZED users and does not log the browser in.
Consumed challenge rows remain bounded to one per user; they are not an audit log.

Registration/resend budgets share `LoginAttempt` storage using separate keyed HMAC
namespaces from login, keyed by normalized email and peer `REMOTE_ADDR`. Forwarded
headers are ignored. Verification uses the same peer budget. Limits are shared
across workers and independent of whether an email exists. Blocked peer requests
cannot allocate more email rows, and blocked retries do not extend expiry.
The existing `clear_expired_login_attempts` command also removes expired signup
counters. Production proxy/IP trust remains S090 work.

## Configuration and mail

| Setting | Default | Allowed values / purpose |
|---|---|---|
| `INSTITUTIONAL_EMAIL_DOMAINS` | Empty | Comma-separated exact DNS domains; empty disables signup |
| `PUBLIC_APP_ORIGIN` | `http://127.0.0.1:5173` | One HTTP(S) origin, no credentials/path/query/fragment; HTTPS required for production signup |
| `REGISTRATION_REQUIRE_APPROVAL` | `false` | Boolean; captured at account creation |
| `VERIFICATION_TOKEN_SECONDS` | 86400 | Integer 1–604800 |
| `REGISTRATION_EMAIL_LIMIT` | 3 | Integer 1–100, shared registration/resend attempts per window |
| `REGISTRATION_IP_LIMIT` | 30 | Integer 1–1000, registration/resend/verification attempts per peer/window |
| `REGISTRATION_WINDOW_SECONDS` | 900 | Integer 1–86400 |
| `DEFAULT_FROM_EMAIL` | `no-reply@archive.example.invalid` | Valid mailbox; production signup requires an explicitly usable sender |
| `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Empty | SMTP host and optional credentials; host required for production signup |
| `EMAIL_PORT` | 587 | Integer 1–65535 |
| `EMAIL_USE_TLS`, `EMAIL_USE_SSL` | `true`, `false` | Mutually exclusive booleans |
| `EMAIL_TIMEOUT` | 10 | Integer 1–60 seconds |

Development uses console mail, unit tests use Django's captured mailbox, production
uses SMTP. These adapters are selected by profile, not arbitrary backend imports
from an environment string. URLs always use the configured origin, never request
Host headers. The verification token goes in the fragment so HTTP access logs do
not receive it. Production settings validate signup origin/mail prerequisites.

Mail is sent only after database commit. Delivery errors produce a fixed safe
server warning and retain the generic API response; the account stays pending
and the user can request a replacement. Delivery is synchronous and has a bounded
SMTP timeout. This sprint does not implement a durable mail queue or automatic
retry; a process failure between commit and delivery is recovered by resend.

The browser runner uses a temporary file mailbox enabled only in test settings by
`AARCHIVE_TEST_MAIL_DIRECTORY`; that directory is owned and removed by the runner.
The browser reads only these synthetic messages. No inbox API is exposed. Run
`scripts/check_auth_browser.py` as documented in the authentication guide; CI also
runs the real desktop/mobile signup, resend, verification and login flow.
