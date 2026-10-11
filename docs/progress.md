# Progress and handoff

Planning setup is complete: canonical Markdown requirements, the verbatim archive
layout, architecture/contribution/security/API/database guides, a detailed sprint
backlog, and a local context helper exist. S001-S014 are complete: contracts,
backend/frontend foundations, local services, API proxy, CI configuration and
platform account models, immutable audit service/read API, and central role/scope
authorization with audited privilege commands, plus session login/logout and
current-account UI, institutional Student registration and single-use email
verification with optional approval gating, password recovery/change and audited
lifecycle commands with proactive session revocation, administrator account screens,
invitations and restricted self-profile editing, plus academic departments, batches,
terms and sections with protected parents and archival, and a reusable department
course catalog, course offerings and retained multiple teacher assignments. Account,
academic and offering management are runnable; enrollment and contest workflows
remain pending.

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
| S013 | DONE | [Reusable catalog evidence](sprints/S013.md): 460 backend tests, 53 frontend tests, 19 browser checks, lint/types/build and migration/trigger roundtrip passed. Department-owned Course, decimal credits, filtered Teacher reads, admin catalog UI, audited revisions/archive and future offering-context validation implemented. |
| S014 | DONE | [Offering evidence](sprints/S014.md): 489 backend tests, 58 frontend tests, 21 browser checks, lint/types/build and migration/trigger roundtrip passed. Matching immutable offering tuples, audited creator/co-teacher assignments, retained history, immediate scope/grant revocation and responsive editor implemented. |
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

- Completed S014 on 2026-10-11, resuming the interrupted sprint. The
  [evidence](sprints/S014.md) and [offering guide](offerings.md) document API
  payloads, permissions, persistence, migration checks and local use.
- Account links eligible Teachers/Admins to `/offerings`. Create by selecting a
  matching Course/Batch/Term/Section; the creator is attached automatically. The
  tuple and original creator remain immutable. Administrators see all offerings;
  Teachers see only current assignments, with equal name-settings rights.
- Administrator assignment/removal/archive controls require review. Removal ends
  a membership, revokes scoped grants and denies the removed Teacher's next read
  or write. Historical authorship and dated assignments remain. Reassignment
  creates a new history row without restoring old grants. Global Administrator
  authority remains independent of assignment.
- Archived offerings/ancestry block settings and new assignments; current staff
  can still read history, and admins can remove memberships. There is no restore
  or delete endpoint. Teacher academic selectors expose only active metadata;
  staff email selection remains Administrator-only.
- Final gates passed: 489 backend tests (143.49s), 58 frontend tests, 5 foundation
  browser checks (5.6s), 16 real application browser checks (1.6m), lint/types/build,
  no migration drift, migration/trigger apply-reverse-reapply/no-op and all 108
  ledger references. The mobile selector overflow found during browser testing
  was fixed and reverified; desktop/mobile screenshots were reviewed. The S014
  disposable services/volume were removed; documentation links and ignore checks
  passed.
- Apply migrations before opening offerings. No new environment variables or
  dependencies are needed. S015 should reuse stable Offering IDs, current scoped
  permissions and the transaction lock for enrollment. S016 ContestTeacher remains
  separate; offering membership gives no global contest authority or implemented
  grading workflow. G01 exporter schemas/semantics still gates S025.
- The selector chooses S015 (enrollment and historical membership). Keep using
  the ledger. S013 and S014 are included together in the user-requested main-branch
  commit following baseline `2894f44` (S001-S012). The checkout contains source,
  migrations, tests and developer documentation needed to continue from a clone.
  Local credentials, databases, dependencies and generated artifacts stay ignored.
  No deployment, real institutional data or external messages are included.
