# Contributing

## Before implementation

Read [AGENTS.md](AGENTS.md), [architecture](ARCHITECTURE.md), and the current
[progress](docs/progress.md). "Next task", "what's next", and "whats next" mean
select and implement one ready sprint, not merely suggest it. Use
`python3 scripts/sprint_context.py --next` to resume ready unfinished work or
select the next TODO with completed prerequisites in the earliest unfinished
phase. Explicit sprint IDs remain supported. Verify prerequisite evidence against
actual repository code, mark the selected sprint IN_PROGRESS, and execute it
without asking the user to repeat or confirm the request.

Follow [README setup](README.md#local-setup), start Compose dependencies, then run
`uv run --locked --env-file .env bash scripts/check_backend.sh` for backend changes.
This requires a disposable PostgreSQL `TEST_DATABASE_URL`; the shared script forces
test settings and runs the same checks as CI. Also run the sprint context check
when changing documentation. From `frontend/`, run `npm ci` and `npm run check`.
For changes to interactive components or routing, install Playwright Chromium and
run `npm run test:e2e` for keyboard, mobile and accessibility checks. Proxy changes
also require `uv run --locked --env-file .env python scripts/check_dev_proxy.py`.
S004 supplies development services and CI; see [connected development](README.md#connected-development-and-ci).

## Implementation and verification

Keep commits/changes focused on the requested sprint. Add migrations with model
changes, input validation with new writes, scoped authorization with every
protected query/action, and audit events with academic/security mutations. Avoid
permissive stubs that a later sprint is expected to secure.

Test observable behavior and concrete failure modes. Database constraints,
transaction rollback, and concurrency need PostgreSQL tests. Components should
cover relevant loading/error/keyboard behavior. Use browser integration tests
for the end-to-end gates and when an actual browser boundary is the risk. Do not
claim a test passed if it was not run. List the missing dependency or environment
when blocked. Do not substitute a mock-only test for actual import compatibility.

Every acceptance criterion is part of completion. If scope becomes too large,
split the sprint into explicit child cards and update dependencies; preserve the
parent gate. Record actual commands/results, changed contracts, and next steps in
`docs/progress.md`. Keep durable decisions in `docs/decisions/` and concise
operational instructions in `docs/runbooks/` when implemented.

## Repository hygiene

Commit source, migrations, lockfiles, tests, safe environment examples, CI,
documentation, trusted redistributable schemas, and tiny synthetic fixtures.
Do not commit credentials, institutional account data, real uploads, private
evidence, generated reports, local databases, dependency directories, or caches.

`.gitignore` deliberately permits legitimate test ZIP/PDF/JSON files. Put private
inputs under ignored `private/`; generate large benchmark fixtures under ignored
`tmp/` or `data/`. Check `git status --short` and `git check-ignore -v PATH` before
staging. A `.gitignore` change cannot remove a secret already tracked by Git.

Use a feature branch if requested or required by repository policy. Do not force
push, rewrite unrelated work, deploy, or send external messages merely because a
sprint card describes a future workflow. A planning task creates no production
authorization. Follow the user's explicit commit/push/deployment instructions.

## Documentation and review

The canonical SRS is [docs/requirements.md](docs/requirements.md). Update API,
database, and security guides as their contracts become implemented; distinguish
planned, implemented, and blocked behavior. Use stable sprint IDs and requirement
IDs instead of copying the full SRS into every implementation conversation.

A review summary should state the user-visible result, important design choices,
tests actually run, migration/compatibility effects, and any unresolved blocker.
Include screenshots or render evidence when a layout change needs visual review.
Keep full private data and noisy tool logs out of review descriptions.
