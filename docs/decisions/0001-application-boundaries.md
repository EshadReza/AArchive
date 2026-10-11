# ADR 0001 - Application stack and module boundaries

Status: accepted for implementation; Sprint: S001; Date: 2026-10-05.
Requirements: SRS Sections 12, 17, 26, 32, 33, 56 and Appendix A.

## Decision

Use Django/DRF, React/TypeScript with Vite, PostgreSQL, Celery/Redis, and private
S3-compatible storage with a local adapter. Deploy the frontend and API under one
origin with Django sessions and CSRF. Select supported compatible dependency
versions and commit lockfiles in S002-S004; this ADR does not claim current
version numbers or provide a runnable scaffold.

Use the module paths in [ARCHITECTURE.md](../../ARCHITECTURE.md). Accounts owns
platform identity and role assignment; academics owns offering/enrollment;
access owns policy evaluation; contests owns versioned source evidence; imports
owns staging/validation/orchestration; grading owns academic values; assets owns
bytes/delivery; reports owns scoped projections; audit owns append-only events
and the transactional outbox; notifications consumes committed events; governance
owns settings and retention operations.

All entry points call these domain services. Workers do not bypass authorization,
and serializers do not independently calculate grades. A mutation, its audit,
and outbox event share a PostgreSQL transaction. Object storage does not join
that transaction; durable assets precede publication, and idempotent cleanup
reconciles orphaned writes. Report caches never become the primary grade store.

## Consequences and verification

REST views and workers use the same service contracts. S002-S004 supply runnable
commands/CI; S021-S023 verify storage/outbox failure boundaries. Runtime tests
belong to those sprints, not this documentation acceptance. No new service split,
authentication mechanism, or frontend framework is needed for later cards.

## Alternatives

A TypeScript backend is viable in the original SRS, but keeping one selected
stack prevents conflicting scaffolds across agents. Microservices and a separate
JWT browser identity system add boundaries without a current project need.
