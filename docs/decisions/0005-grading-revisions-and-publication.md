# ADR 0005 - Grades, revisions, corrections, and publication

Status: accepted for implementation; Sprint: S001; Date: 2026-10-05.
Requirements: MARK-001 through MARK-006; SRS Sections 19, 42, 44, 50-51.

## Decision

StudentMark has current revision and publication state. Accepted changes append
MarkAdjustment entries containing previous/new values, original calculation,
reason/actor/time, rule version, and previous/new source snapshots when applicable.
No import changes that history or a published value implicitly. Calculation
previews and correction proposals are separate from the currently visible revision.

| From | Command | To / effect |
|---|---|---|
| DRAFT | Save/manual override/apply calculation | DRAFT; append adjustment and increment revision |
| DRAFT | Finalize | FINALIZED |
| FINALIZED | Reopen | DRAFT; audited, no special elevated privilege |
| FINALIZED | Publish | PUBLISHED; set visible revision and emit committed event |
| PUBLISHED | Prepare correction | PUBLISHED unchanged; draft proposal only |
| PUBLISHED | Correct and republish | PUBLISHED; atomically replace visible revision, append adjustment, emit event |
| PUBLISHED | Lock | LOCKED; elevated scoped action |
| LOCKED | Unlock | PUBLISHED; elevated scoped action with reason/audit |

No direct edit to FINALIZED; reopen first. No correction of LOCKED without unlock.
Any currently assigned offering teacher can finalize/publish/correct. Lock/unlock
needs the explicit admin-delegated offering capability (admins have it globally).
A contest assignment alone grants no mark mutation. Bulk commands check all
selected revisions and permissions and either commit all selected changes or none.
Failed/stale correction leaves the previous published revision visible.

The student read projection includes only PUBLISHED and LOCKED revisions. Draft
and finalized values never influence visible totals; incomplete published totals
state their coverage. Source re-application is a distinct reviewed action: DRAFT
may update through the ledger; FINALIZED requires reopen; PUBLISHED requires
correction-and-republish; LOCKED requires unlock first. Mapping correction is a
separate operation and cannot silently transfer a published grade between users.

## Numerical contract

Use Decimal and versioned rules with a declared maximum, input units, precision,
rounding mode, bonus cap, and missing-input policy. The MVP default is two decimal
places with ROUND_HALF_UP at the final academic-mark boundary; preserve full
documented input/calculation precision before that boundary. Allow explicit
assessment configuration to change the default through a new rule version.
Missing/excluded/absent and recorded zero remain distinct. Best-N/drop-N ties use
stable assessment ID; dependency graphs reject cycles. No unsuitable source score
is auto-converted without a declared grading method. Team allocation snapshots
the reviewed membership and per-student rule.

Custom formulas use an allowlisted pure expression language with Decimal values,
bounded input/AST/operation limits, and a stored input/result trace. No host-language
eval/exec or external I/O. Invalid evaluations cannot replace a saved mark.

## Consequences and verification

S053 verifies concurrent revision checks; S055-S059 verify numerical boundaries
and formulas; S061-S063 verify publication/privacy; S067-S068 verify explicit
re-application and preservation. The normal state machine gains a PUBLISHED
self-transition for correction, not an automatic unpublish/regrade path.

## Alternatives

Editing the visible published row while preparing a correction exposes incomplete
work. Reverting every published mark to DRAFT hides a legitimate academic record.
Binary floating-point defaults and implicit missing-as-zero calculations produce
unexplained marks. Immutable revisions and explicit commands keep changes reviewable.
