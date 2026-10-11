# Progress and handoff

Planning setup is complete: canonical Markdown requirements, the verbatim archive
layout, architecture/contribution/security/API/database guides, a detailed sprint
backlog, and a local context helper exist. S001-S012 are complete: contracts,
backend/frontend foundations, local services, API proxy, CI configuration and
platform account models, immutable audit service/read API, and central role/scope
authorization with audited privilege commands, plus session login/logout and
current-account UI, institutional Student registration and single-use email
verification with optional approval gating, password recovery/change and audited
lifecycle commands with proactive session revocation, administrator account screens,
invitations and restricted self-profile editing, plus academic departments, batches,
terms and sections with protected parents and archival. Account and structure
management are runnable; courses, offerings and contest workflows remain pending.

**Next task:** selected from this ledger and TASKS.md by
`python3 scripts/sprint_context.py --next`; do not maintain a separate fixed ID.
The user can simply say "next task" or "whats next" to have an agent execute it.
**Known external input:** S025 needs literal trusted JSON Schema definitions and
exporter field semantics. The supplied ZIP tree is already saved; it is not lost.
Foundation and independent manual-grading work can proceed per TASKS.md.

Status values: TODO, IN_PROGRESS, BLOCKED, DONE. Change only the relevant rows.
For DONE, record exact check commands/results and a commit or evidence path when
available. Do not mark an unrun check passed. For BLOCKED, name the missing input
and affected downstream cards. Add child-sprint rows when splitting work.

| Sprint | Status | Evidence / handoff |
|---|---|---|
| S001 | DONE | SRS 1.1 and six accepted ADRs; [changes, contract review and verification](sprints/S001.md). Context check and all 9 selector tests passed. |
| S002 | DONE | [Backend foundation and verification](sprints/S002.md): locked fresh install, Django checks, Ruff, 37 tests, PostgreSQL migration/connection and HTTP smoke checks passed. |
| S003 | DONE | [Frontend foundation and verification](sprints/S003.md): clean npm install/build/typecheck/lint, 23 component/API tests, 5 browser checks and desktop/mobile visual review passed. |
| S004 | DONE | [Services, proxy and CI evidence](sprints/S004.md): 38 backend tests, 23 frontend tests, 5 browser checks, CSRF proxy smoke, workflow validation, negative gate and persistence checks passed locally. |
| S005 | DONE | [Account models and migration evidence](sprints/S005.md): 80 backend tests, Ruff/Django checks, migration drift and empty-database apply/reverse/reapply passed. Pending Student creation, canonical unique identities, fixed roles and lifecycle predicates implemented; authentication remains S008. |
| S006 | DONE | [Audit service and verification](sprints/S006.md): 131 backend tests, Ruff/Django/migration checks, schema/trigger apply-reverse-reapply passed. Transactional immutable records, reviewed payloads, protected actors and Administrator-only paginated read API; real sessions remain S008. |
| S007 | DONE | [Authorization and privilege-service evidence](sprints/S007.md): 173 tests, Ruff/Django/migration checks, grant/lock migration apply-reverse-reapply passed. Shared policy/filter hooks, typed scopes, audited admin role/grant edits, concurrent last-admin protection, Teacher grant revocation and guarded CLI bootstrap implemented. |
| S008 | DONE | [Session authentication and verification](sprints/S008.md): 207 backend tests, 27 frontend tests, 5 foundation and 4 real auth browser checks; lint/types/build, migration lifecycle, proxy/CSRF and workflow checks passed. Login/logout, current-account UI, shared limits and detected-state revocation implemented. |
| S009 | DONE | [Registration and verification evidence](sprints/S009.md): 259 backend tests, 32 frontend tests and 11 browser checks; lint/types/build, migration roundtrip/drift and workflow checks passed. Exact domain allowlisting, pending Student creation, approval gating, single-use account-bound verification, resend limits and local/SMTP mail configuration implemented. |
| S010 | DONE | [Recovery and lifecycle evidence](sprints/S010.md): 318 backend tests, 37 frontend tests and 13 browser checks passed, plus lint/types/build, migration roundtrip/drift and workflow validation. One-use resets, password changes, admin approval/lifecycle commands, last-admin protection and proactive subject-session revocation implemented. |
| S011 | DONE | [Account administration and invitation evidence](sprints/S011.md): 369 backend tests, 43 frontend tests, 15 browser checks, lint/types/build, migration roundtrip/drift and workflow validation passed. Admin list/detail/create, reviewed role/lifecycle changes, single-use invitations and display-name-only self-profile implemented. |
| S012 | DONE | [Academic structure evidence](sprints/S012.md): 416 backend tests, 48 frontend tests, 17 browser checks, lint/types/build, migration/trigger roundtrip and workflow checks passed. Admin hierarchy management, atomic ALL creation, protected parents, archive inheritance and assignment-context validation implemented. |
| S013 | TODO |  |
| S014 | TODO |  |
| S015 | TODO |  |
| S016 | TODO |  |
| S017 | TODO |  |
| S018 | TODO |  |
| S019 | TODO |  |
| S020 | TODO |  |
| S021 | TODO |  |
| S022 | TODO |  |
| S023 | TODO |  |
| S024 | TODO |  |
| S025 | TODO | External gate: actual trusted schema contents and format contract are needed. |
| S026 | TODO |  |
| S027 | TODO |  |
| S028 | TODO |  |
| S029 | TODO |  |
| S030 | TODO |  |
| S031 | TODO |  |
| S032 | TODO |  |
| S033 | TODO |  |
| S034 | TODO |  |
| S035 | TODO |  |
| S036 | TODO |  |
| S037 | TODO |  |
| S038 | TODO |  |
| S039 | TODO |  |
| S040 | TODO |  |
| S041 | TODO |  |
| S042 | TODO |  |
| S043 | TODO |  |
| S044 | TODO |  |
| S045 | TODO |  |
| S046 | TODO |  |
| S047 | TODO |  |
| S048 | TODO |  |
| S049 | TODO |  |
| S050 | TODO |  |
| S051 | TODO |  |
| S052 | TODO |  |
| S053 | TODO |  |
| S054 | TODO |  |
| S055 | TODO |  |
| S056 | TODO |  |
| S057 | TODO |  |
| S058 | TODO |  |
| S059 | TODO |  |
| S060 | TODO |  |
| S061 | TODO |  |
| S062 | TODO |  |
| S063 | TODO |  |
| S064 | TODO |  |
| S065 | TODO |  |
| S066 | TODO |  |
| S067 | TODO |  |
| S068 | TODO |  |
| S069 | TODO |  |
| S070 | TODO |  |
| S071 | TODO |  |
| S072 | TODO |  |
| S073 | TODO |  |
| S074 | TODO |  |
| S075 | TODO |  |
| S076 | TODO |  |
| S077 | TODO |  |
| S078 | TODO |  |
| S079 | TODO |  |
| S080 | TODO |  |
| S081 | TODO |  |
| S082 | TODO |  |
| S083 | TODO |  |
| S084 | TODO |  |
| S085 | TODO |  |
| S086 | TODO |  |
| S087 | TODO |  |
| S088 | TODO |  |
| S089 | TODO |  |
| S090 | TODO |  |
| S091 | TODO |  |
| S092 | TODO | External input/authorization gate is specified on the sprint card. |
| S093 | TODO | External input/authorization gate is specified on the sprint card. |
| S094 | TODO | External input/authorization gate is specified on the sprint card. |
| S095 | TODO |  |
| S096 | TODO | External input/authorization gate is specified on the sprint card. |
| S097 | TODO |  |
| S098 | TODO |  |
| S099 | TODO |  |
| S100 | TODO |  |
| S101 | TODO |  |
| S102 | TODO |  |
| S103 | TODO | External input/authorization gate is specified on the sprint card. |
| S104 | TODO |  |
| S105 | TODO | External input/authorization gate is specified on the sprint card. |
| S106 | TODO |  |
| S107 | TODO |  |
| S108 | TODO | External input/authorization gate is specified on the sprint card. |

## Latest handoff

- Completed S012 on 2026-10-09. [Evidence](sprints/S012.md) and the
  [academic structure guide](academic-structure.md) document API/UI, archive policy,
  parent/ALL protections, migrations and future assignment integration.
- `/account` now links Administrators to `/admin/structure`. All four record types
  support paginated admin reads/create/edit/archive, named parent selection and
  filtering. Archive requires review/confirmation; revisions reject stale edits.
- Batch creation atomically creates its reserved ALL section and audits both rows.
  Parent references cannot change, including through direct database updates.
  Archive retains UUIDs/history, blocks new children/assignments and makes descendants
  unavailable. There is no hard-delete, restore or course/offering implementation yet.
- Future assignment writers must authorize the actor and call
  `require_assignment_context` inside the same transaction as their write. It checks
  Department/Batch/Term/Section membership and active ancestors under the shared
  privilege lock. S013/S014 add Course validation and database constraints for their
  new references. Teacher selection reads need an explicitly scoped projection;
  S012 management APIs remain Administrator-only.
- Final checks: 416 backend tests (77.84s), 48 frontend tests, 5 foundation browser
  checks (7.1s), 12 real application browser checks (1.3m), lint/types/build,
  academic schema/trigger apply/reverse/reapply/no-op, migration drift, workflow
  syntax, runner compilation and desktop/mobile visual review passed. Documentation
  links/whitespace, ignore checks and `git diff --check` passed. Browser resources
  and the S012 synthetic Compose service/network/volume were removed.
- No new environment variables are needed; apply migrations before using the page.
  Existing invitation/recovery delivery limitations remain documented. G01 still
  gates S025's exporter schema work; the supplied ZIP layout remains preserved.
- The validated ledger now selects S013 (reusable course catalog). Continue using
  the selector and preserve existing working-tree contents. No commit, push, real
  institutional data, external email or deployment was performed.
