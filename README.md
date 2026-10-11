# AArchive

A permanent archive and academic platform for programming contests exported from
Arbitrator. It preserves contest evidence, links it to courses, and supports
grading, reports, and controlled access. It does not judge or execute submissions.

## Current state

This repository contains the developer handoff and implementation plan.
[S001](docs/sprints/S001.md) establishes the accepted contracts in SRS 1.1 and six
architecture decisions. S002 adds a runnable Django/DRF backend foundation with
PostgreSQL configuration and a health endpoint. S003 adds a React/TypeScript frontend
shell, accessible interaction components, a session/CSRF API client and a development
showcase. Contest features remain pending. Celery/Redis and S3-compatible storage
remain part of the selected architecture. S004 supplies local PostgreSQL/Redis,
the frontend API proxy and CI checks. [S005](docs/sprints/S005.md) adds the custom
platform user, profile, fixed roles, account-state predicates and first migration.
S006 adds an immutable audit service and Administrator-only read API.
[S008](docs/sprints/S008.md) adds session login/logout, current-account UI and
shared login limits. [S009](docs/sprints/S009.md) adds institutional Student
registration, single-use email verification and optional approval gating. Password
recovery and password changes are implemented in [S010](docs/sprints/S010.md),
along with audited lifecycle commands and proactive session revocation.
[S011](docs/sprints/S011.md) adds administrator account lists/details, reviewed
role/lifecycle changes, email invitations and restricted self-profile editing.
See the [account-management guide](docs/account-management.md) to try these screens.
[S012](docs/sprints/S012.md) adds academic departments, batches, terms and sections
with admin management, protected parents, archive rules and a default ALL section.
See [academic structure](docs/academic-structure.md) for a local walkthrough.
[S013](docs/sprints/S013.md) adds the reusable department course catalog, guarded
reads/writes and reviewed archive UI; see [course catalog](docs/course-catalog.md).
[S014](docs/sprints/S014.md) adds course offerings, shared teacher settings rights,
admin assignment review and retained membership history; see [offerings](docs/offerings.md).
S007 adds shared role/scope policy helpers, audited privilege services, scoped-grant
storage and a guarded local first-Administrator command. See [authorization guide](docs/access.md).

## Start here

Tell the agent **"next task"** or **"what's next"** ("whats next" also works).
The repository instructions tell it to select the next ready sprint, implement
it, run the required checks, and update progress. You do not need to remember an
ID or confirm that it should start. Each request completes one sprint; an
interrupted sprint is resumed when its prerequisites are complete.

The agent reads [AGENTS.md](AGENTS.md) and [docs/progress.md](docs/progress.md),
then obtains the selected card and its referenced requirements with:

```sh
python3 scripts/sprint_context.py --next
```

The helper uses Python's standard library and needs no API key, model call,
application dependencies, or PDF parser. Run `--list` for the index, `--brief`
with `--next` or a sprint ID for its card alone, or `--check` to validate planning
references. Selection skips blocked work and stays in the earliest unfinished
phase. The helper is read-only; the agent performs the actual implementation.

## Continuing from a fresh clone

This repository contains the implementation through **S014** and the plan for the
remaining project. Another developer can continue without the original chat:

1. Follow the local setup below: install the pinned runtimes, install dependencies
   from lockfiles, copy `.env.example` to `.env`, set local credentials and start
   PostgreSQL/Redis. Apply migrations and run the backend/frontend servers.
2. Read `AGENTS.md`, `ARCHITECTURE.md` and `docs/progress.md`. The canonical SRS is
   `docs/requirements.md`; detailed completed-sprint evidence is in `docs/sprints/`.
3. Run `python3 scripts/sprint_context.py --next` for the next ready card and its
   focused requirements. At this handoff it selects **S015 — enrollment management**.
4. Use `CONTRIBUTING.md` for checks and update the progress ledger after each sprint.

Local `.env`, databases, account records, installed dependencies, generated builds
and screenshots are deliberately excluded. Set up your own local environment and
accounts using the documented registration/bootstrap flow. No chat attachments or
machine-specific temporary files are required to build the implemented features.
The supplied archive layout is included in `docs/archive-layout.md`; the actual
trusted exporter JSON Schemas and field semantics remain an external input for
S025. They do not block the next academic/catalog sprints.

## Developer documentation

| File | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stack, module boundaries, source layout, runtime flows |
| [TASKS.md](TASKS.md) | 108 detailed sprints: 93 MVP, 10 Phase 2, 5 Future |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development, verification, handoff, and Git practices |
| [.env.example](.env.example) | Safe planned configuration names; placeholders only |
| [docs/requirements.md](docs/requirements.md) | Canonical Markdown SRS copied from the reviewed handoff |
| [docs/api.md](docs/api.md) | Planned API conventions and endpoint ownership |
| [docs/database.md](docs/database.md) | Planned relational model and integrity rules |
| [docs/security.md](docs/security.md) | Permission, privacy, import, and operational controls |
| [docs/audit.md](docs/audit.md) | Implemented audit service, read API and feature coverage checklist |
| [docs/offerings.md](docs/offerings.md) | Offering API/UI, teacher history, permissions and integrity |
| [docs/course-catalog.md](docs/course-catalog.md) | Reusable course catalog API, management UI, permissions and offering integration |
| [docs/academic-structure.md](docs/academic-structure.md) | Academic hierarchy, management API/UI, archive and assignment rules |
| [docs/account-management.md](docs/account-management.md) | Admin accounts, invitations, reviewed access changes and self-profile |
| [docs/recovery-lifecycle.md](docs/recovery-lifecycle.md) | Password reset/change, admin transitions and session revocation |
| [docs/registration.md](docs/registration.md) | Institutional registration, verification links and mail configuration |
| [docs/authentication.md](docs/authentication.md) | Session endpoints, login limits, account UI and browser checks |
| [docs/access.md](docs/access.md) | Shared authorization, grants and audited privilege commands |
| [docs/decisions/](docs/decisions/README.md) | Planning defaults, ADR guidance, external inputs |
| [docs/archive-layout.md](docs/archive-layout.md) | Owner-supplied contest ZIP tree, preserved verbatim |
| [docs/archive-contract.md](docs/archive-contract.md) | Known archive facts and field-level schema intake checklist |
| [docs/progress.md](docs/progress.md) | Sprint status and current handoff |

Use the repository's Markdown SRS for implementation. Parent-directory copies and
PDF exports are reference handoffs, not competing sources of truth. The upload
ZIP layout is separate from the application's source-code layout.

The supplied ZIP tree gives filenames and intended contents. Literal JSON Schema
definitions are still needed before claiming compatibility with the actual
exporter; S025 handles that input. Other independent work can proceed now.

## Local setup

### Backend

Run all commands below from the repository root. Backend runtime is Python
3.14.7 (`.python-version`), Django 5.2 LTS and DRF 3.18. Exact dependency versions
and hashes are in `uv.lock`. Use **uv 0.12.23** (the compatible 0.12 series is
enforced in `pyproject.toml`); see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).
The standard-library planning helper still works on Python 3.10+.

```sh
uv python install 3.14.7
uv sync --locked
# Only when .env does not already exist:
cp .env.example .env
uv run --locked python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Put the generated value in `.env` as `DJANGO_SECRET_KEY`. Keep
`DJANGO_SETTINGS_MODULE=config.settings.development` locally. Set `DATABASE_URL`
to your local PostgreSQL database (PostgreSQL 17 is the verified baseline);
URL-encode special characters in its user/password. The credentials in the example
are placeholders. Set `POSTGRES_PASSWORD` in `.env` and use the same credentials
in `DATABASE_URL` and `TEST_DATABASE_URL`. With Docker and Compose installed,
start the local PostgreSQL/Redis dependencies before running migrations:

```sh
docker compose up -d --wait
```

PostgreSQL listens on loopback port 5432 and Redis on 6379. If those ports are
occupied, change `POSTGRES_PORT`/`REDIS_PORT` in `.env` and update the corresponding
URLs. The Python and frontend processes run on your host, outside Docker.

```sh
uv run --locked --env-file .env python backend/manage.py check
uv run --locked --env-file .env python backend/manage.py migrate --noinput
uv run --locked --env-file .env python backend/manage.py runserver 127.0.0.1:8000
```

`GET http://127.0.0.1:8000/api/health` returns `{"status":"ok"}`. This is process
liveness: it intentionally does not query PostgreSQL or check external services.
The migration command needs a reachable database and creates the account and
audit/access and academic structure tables, integrity triggers and privilege lock. `AUTH_USER_MODEL`
is `accounts.User` from the first migration. Account
creation currently uses a trusted manager that creates only pending Students;
login, registration, invitations, account management and own-profile endpoints
are implemented. Django
`createsuperuser` is not a supported provisioning workflow for this custom model.
S007 provides audited role/grant services and the guarded
[bootstrap command](docs/access.md#first-administrator). Migrations also create
database sessions and login counters. DRF uses session authentication and requires
an authenticated actor by default; health explicitly allows anonymous reads.

### Checks

```sh
uv run --locked --env-file .env bash scripts/check_backend.sh
```

The shared gate installs from the lockfile and runs Ruff, Django checks, migration-drift checks, pytest
and sprint-document validation. It explicitly selects `config.settings.test`
even when `.env` selects development. S004 adds a real PostgreSQL transaction
test, so the full suite now requires the Compose database (or another disposable
PostgreSQL instance). `TEST_DATABASE_URL` must use a role with permission to create
the test database; pytest creates/drops `test_<database-name>`. Never point test
configuration at a production database. Test settings ignore `DATABASE_URL`.

Use `uv sync --locked`/`uv run --locked` for reproducibility. To deliberately
update dependencies, edit constraints as needed, run `uv lock --upgrade-package
PACKAGE`, review the lockfile, and rerun the checks. Commit `uv.lock` with any
dependency change. `.venv`, local secrets, data and tool caches are ignored.

### Production configuration contract

Select `DJANGO_SETTINGS_MODULE=config.settings.production` explicitly for
management commands. WSGI/ASGI entry points default to production. Supply a
generated `DJANGO_SECRET_KEY` (at least 50 characters), explicit
`DJANGO_ALLOWED_HOSTS`, and a PostgreSQL `DATABASE_URL` including a real database
user/password. Missing values, example secrets, SQLite URLs and enabled debug
cause startup failure. `DJANGO_CSRF_TRUSTED_ORIGINS`, if needed, accepts explicit
HTTPS origins only. Production configuration is supplied by the environment;
Django does not silently load `.env` files.

Production enables HTTPS redirects, secure cookies and HSTS for the configured
host. Forwarded headers are not trusted by default; S090 must define the trusted
TLS proxy boundary before deployment. This sprint supplies entry points, not a
production web server or deployment. Later service configuration remains marked
as planned in `.env.example`.

Keep credentials, real archives, database files and generated private reports out
of Git. Commit lockfiles, migrations, safe examples, trusted redistributable
schemas and synthetic fixtures.

## Frontend setup

Use Node **22.23.1** (`frontend/.nvmrc`) and npm **10.9.8**. The compatible Node
22/npm 10 ranges are enforced by `frontend/.npmrc`; all packages are pinned in
`frontend/package-lock.json`.

```sh
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/`. The **Interface workshop** link opens
`/dev/primitives`, a clearly labeled synthetic page for testing forms, validation,
loading and empty states. It sends and saves no data. The workshop route/module
are excluded from production builds. The overview is an honest foundation page;
`/login` and `/account` provide sign-in, session refresh and sign-out. Login needs
an existing verified, approved (when required), eligible account with a usable
password. No demo account is created by migrations. To create an account,
configure the domain allowlist and open `/register`; development verification mail
appears in the Django terminal. See [registration setup](docs/registration.md#try-it-locally).
Dashboards and contest workflows remain pending. See [authentication](docs/authentication.md).

Run from `frontend/`:

```sh
npm run typecheck
npm run lint
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser checks build production assets, start local development/preview servers on
ports **5178/5179**, and stop them afterward. They cover desktop/mobile keyboard
access, error recovery, automated accessibility checks and production exclusion
of the workshop. On a supported Linux host, `npx playwright install --with-deps
chromium` also installs required OS libraries. Screenshots and reports in
`frontend/test-results/` are ignored; regenerate them with the browser checks.

`npm run preview` serves the production output locally. It is not a production
deployment server. Use `npm ci` for clean installs and commit the lockfile with
intentional dependency updates.

The visual workshop still needs no environment file or running backend. API requests
are restricted to the same-origin `/api` namespace. Vite now proxies that namespace
to Django at `http://127.0.0.1:8000`, preserving Host, Origin and cookies. If Django
uses a different port, set the server-only `AARCHIVE_API_TARGET` when starting Vite,
for example `AARCHIVE_API_TARGET=http://127.0.0.1:8001 npm run dev`.
S008 supplies session/CSRF bootstrap and real login/logout through this proxy.
Do not add cross-origin credentials, browser token storage or a second login
scheme to connect future pages. See [API client contract](docs/api.md#frontend-client-s003).

## Connected development and CI

With Compose dependencies running, use two VS Code terminals:

1. Repository root: `uv run --locked --env-file .env python backend/manage.py runserver 127.0.0.1:8000`
2. `frontend/`: `npm run dev`

Open `http://127.0.0.1:5173/`. To verify the connection, open
`http://127.0.0.1:5173/api/health` or run:

```sh
curl --fail http://127.0.0.1:5173/api/health
```

Expect `{"status":"ok"}` from Django through Vite. Use the frontend port printed
by Vite if 5173 is occupied. No cross-origin allowlist or disabled CSRF is needed.
Use the same hostname consistently (for example `127.0.0.1`). Vite's proxy is
development-only; production routing belongs to the deployment sprint.

For an automated isolated health/cookie/CSRF check, run from the repository root:

```sh
uv run --locked --env-file .env python scripts/check_dev_proxy.py
```

This starts its own Django/Vite processes on temporary loopback ports and stops
them afterward. A test-only URLconf checks cookie forwarding, valid CSRF, missing
tokens and foreign-origin rejection. The test endpoint is never mounted in the
normal application. This helper uses POSIX process groups (Linux/macOS); the manual
health check works anywhere the application runs.

### Stop, resume and reset services

Press **Ctrl+C** in each application terminal. From the repository root:

```sh
docker compose stop             # Preserve containers and data
docker compose up -d --wait      # Start or resume healthy services
docker compose down             # Remove containers/network; keep data volumes
```

PostgreSQL and Redis data use project-scoped Docker named volumes, outside the Git
checkout. `/data/`, local `.env`, dependency directories and build/test output are
also ignored. The image digests are pinned in `compose.yaml`.

To intentionally erase **this Compose project's local database and Redis data**:

```sh
docker compose down --volumes
docker compose up -d --wait
uv run --locked --env-file .env python backend/manage.py migrate --noinput
```

Changing PostgreSQL credentials in `.env` does not change an already initialized
volume. Update the local database role deliberately, or reset disposable data as
above when it can be discarded.

### Continuous integration

`.github/workflows/ci.yaml` runs on pushes and pull requests, with manual dispatch
available. The backend job supplies PostgreSQL, runs `bash scripts/check_backend.sh`,
checks the real Vite/Django proxy, and validates Compose. The frontend job runs
`npm ci`, `npm run check` (lint/types/unit tests/build), and `npm run test:e2e`.
Actions and service images are pinned, and workflow permissions are read-only.

These exact commands were verified locally, including rejection of an intentionally
failing test in a temporary copy. GitHub-hosted execution will occur after the
workflow is pushed; it has not been claimed as a completed remote CI run.
