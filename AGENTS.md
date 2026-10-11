# Developer and AI working instructions

Read `docs/progress.md` and the requested sprint before implementing anything.
The canonical requirements are `docs/requirements.md`; use Markdown, not the
PDF or a copy outside this repository. The plan is `TASKS.md`.

## Short commands mean implementation

When the user says **"next task"**, **"what's next"**, **"whats next"**, or an
equivalent request to continue this project, treat it as authorization to select
and implement the next ready sprint. Do not just name a sprint, offer to start,
or ask the user to repeat its ID. If the user explicitly asks for status only,
planning only, or no edits, honor that narrower request instead.

1. Read the current progress ledger and inspect the working tree. Recheck a known
   blocker when new input or repository evidence could resolve it; update its
   status only when that evidence supports the change.
2. Run `python3 scripts/sprint_context.py --next`. It validates the ledger and
   selects within the earliest unfinished phase: first a ready IN_PROGRESS sprint
   to resume, otherwise the lowest-ID TODO whose prerequisites are all DONE.
   BLOCKED sprints and their unfinished dependents are skipped. The helper prints
   focused context and does not edit files or implement the sprint itself.
3. Verify prerequisite completion against actual code/evidence. Set the selected
   sprint to IN_PROGRESS, then implement, test, and document it without another
   confirmation. Complete one sprint per short-command request, then stop.
4. If a newly discovered external blocker prevents that sprint, record BLOCKED
   with the missing input and select another independent ready sprint in the same
   phase. Do not invent missing data or mark incomplete work DONE. If none is
   ready, report the concrete blockers instead of asking which sprint to choose.
5. After completion, update the ledger and handoff with actual evidence. Future
   selection comes from the ledger/dependencies, not a hardcoded "next ID" note.

The short command does not authorize production deployment, remote pushes,
destructive production changes, or external messages beyond existing explicit
authorization. Work up to an actual required external gate and record it clearly.

## Keep each task focused

- Use `python3 scripts/sprint_context.py --next` for short continuation requests,
  or `python3 scripts/sprint_context.py S001` when an ID is explicitly supplied, to
  read that sprint, its decision notes, and only its referenced SRS sections.
- Inspect the current code and prerequisite completion evidence. Do not assume
  a feature exists because it appears in the plan. Dependency IDs are completion
  gates; paused, blocked, or partially implemented dependencies are not complete.
- Implement one sprint per task. If a concrete obstacle makes it too large,
  finish a coherent safe slice, record the remaining work, and split the card
  before claiming completion. Do not silently defer required acceptance checks.
- Use the stack and contracts in `docs/decisions/README.md`. Preserve public interfaces
  established by completed sprints. Do not change unrelated architecture or add
  future-phase features to make the current task appear complete.
- Product requirements in the SRS take precedence over this plan. Use decision
  notes to clarify unspecified details; record an actual conflict rather than
  inventing a source schema or quietly weakening privacy or data integrity.
- Add focused tests for changed behavior, especially permissions, grades,
  imports, concurrency, and migrations. Run the affected checks and repository
  CI gate required by the card. Record actual commands and results.
- Keep account data, real archives, credentials, uploads, and generated exports
  out of Git. Tiny synthetic fixtures and their generators belong in Git.
- Never execute imported code, inherit platform privileges from source roles,
  or validate a production archive solely against its own schema copies.
- Update the sprint row in `docs/progress.md` with status, evidence, and a concise
  handoff. Link a detailed note only when needed; avoid copying full tool logs.
- Summarize changed behavior, verification, and any remaining blocker. Creating
  these planning documents does not authorize a deployment, remote push, or
  production-data change during a later implementation task.

## Context and collaboration

Use `rg` and targeted reads. Avoid loading the complete SRS, complete plan, or
dependency tree every turn. Load further sections only when the task needs them.
Use `python3 scripts/sprint_context.py --list` for the sprint index. The helper
does not call an API or run an implementation task. A normal sprint is handled
by one agent; use subagents only when the user requests them.
