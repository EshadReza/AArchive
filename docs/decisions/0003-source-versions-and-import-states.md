# ADR 0003 - Source namespaces, deduplication, and import publication

Status: accepted for implementation; Sprint: S001; Date: 2026-10-05.
Requirements: IMPORT-001 through IMPORT-009, MARK-006; SRS Sections 15, 33, 40-45, 51.

## Decision

Distinguish source application product, source installation/namespace, stable
contest key, source user key, export identifier, format version, and ZIP digest.
These are platform concepts; S025 must establish their concrete exporter mapping.
The namespace is registered/verified by an admin or trusted adapter configuration;
an upload cannot select another installation's identity solely by declaring it.

Contest identity is `(source_namespace, stable_contest_key)`. Deduplicate accepted
payloads by `(contest_id, zip_sha256)` on ContestImportVersion. Repeated uploads
may have separate job/audit rows but cannot produce duplicate committed versions.
The same bytes from a previous superseded version classify as an exact duplicate;
they never implicitly roll the current pointer back. A differently packaged ZIP
with identical logical data may be a no-change re-import; it is not falsely called
a byte-for-byte duplicate. Classify only after scoped identity validation.

Source entity keys are unique within version and entity type. Retain previous
version values and tombstones; no in-place source overwrite on re-import.
Every committed version has one producing import job; a job has zero or one
committed version, since uploads can fail or be duplicates. Every live Contest
has exactly one current-version pointer whose target belongs to that Contest.

### Separate state machines

| Object | States and transitions |
|---|---|
| Import job | UPLOADED → VALIDATING → VALIDATION_FAILED / MAPPING_REQUIRED / CONFLICT_REVIEW_REQUIRED / READY_TO_IMPORT; resolved mappings can require conflict review; both reviews must finish before READY_TO_IMPORT |
| Confirmed job | READY_TO_IMPORT → IMPORTING → IMPORTED / IMPORT_FAILED |
| Recovery/cancel | Retry VALIDATION_FAILED only for a transient failure of unchanged bytes; changed bytes require a new upload. IMPORT_FAILED can return to READY_TO_IMPORT only after recovery and a fresh preview/authorization. Pre-commit jobs may become CANCELLED after stopping work and cleanup; cancellation cannot undo a committed import. |
| Source version | Created CURRENT at commit; prior current version becomes SUPERSEDED atomically. Job success remains IMPORTED when its version is superseded. |
| Contest lifecycle | ACTIVE ↔ ARCHIVED; either can become SOFT_DELETED; restore returns to the stored previous state; explicit eligible purge leaves an academic tombstone under Section 34. |

Persist upload/job metadata before validation so worker failure is observable.
Staging records and a revisioned mapping plan are not live contest data. Bind
confirmation to upload digest, schema registry revision, current version, mapping
plan revision, and current permission. Validate counts/references before commit.
Make required immutable assets durable first, then commit source rows, the pointer,
confirmed mappings, audit, and outbox in one database transaction.

An exact duplicate may finish IMPORTED with `outcome=EXACT_DUPLICATE` and a
reference to an existing version, but it has no newly produced version and emits
no new academic/contest publication event. Job outcome is distinct from source
version state. Recovery checks commit evidence before labeling a crashed job
failed or retrying it.

Re-import promotes source evidence only. A separate reviewed action changes
university mappings or marks; published marks follow ADR 0005. Content-addressed
blobs retain reference accounting so deleting one version does not remove another
version's evidence. Academic tombstones retain necessary citations after purge.

## Consequences and verification

S024/S039 test namespace isolation, accepted-payload uniqueness, and job/version
cardinality. S043-S044 test rollback/crash recovery and duplicate confirmation.
S064-S068 test immutable prior evidence and academic preservation. Schema contents
are an external S025 dependency, not an invented part of this decision.

## Alternatives

Product name plus local contest ID collides across installations. A fresh job ID
plus ZIP hash never detects repeat jobs. Overwriting rows destroys the evidence
used by past grades. Combining job and version states obscures recovery semantics.
