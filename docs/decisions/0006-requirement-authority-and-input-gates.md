# ADR 0006 - Requirement authority and external inputs

Status: accepted for implementation; Sprint: S001; Date: 2026-10-05.
Requirements: SRS Sections 11, 14, 23, 34, 52-54 and Appendix C.

## Decision

The repository [requirements.md](../requirements.md) is authoritative. Keep its
numbered sections and existing requirement IDs stable. ADRs clarify its contracts;
they do not silently override it. Parent-directory Markdown/PDF copies remain
older handoff artifacts; ordinary sprints do not regenerate them.

The original master prompt is unavailable. References labeled “External master
prompt” are historical attributions, not local section links or evidence that
missing text was verified. Replace an ambiguous internal citation with the actual
local section when the SRS contains the relevant requirement. Local Section 48
means Page Permissions only.

The supplied [archive-layout.md](../archive-layout.md) is a verbatim known file
inventory. Missing field-level schemas, units, enum/ID semantics, schema draft,
and stable source identity mapping remain input gate G01. A trusted adapter must
not be fabricated from the tree. Record the actual intake in
[archive-contract.md](../archive-contract.md); S025 is the direct affected sprint,
and its dependency descendants cannot claim real-format support until it is DONE.
S001 and independent foundation/security/manual-grading work remain executable.

## Defaults and external gates

| Topic | Accepted rule / missing input | Effect |
|---|---|---|
| Institutional hierarchy | No Faculty layer; Department is the top unit | Implement now; a later institutional change requires a documented schema change |
| Access Groups | OR within a group's rule; AND across rule types | Implement now under ADR 0004 |
| Deletion grace | Default 30 days; admin-configurable positive duration, no immediate bypass | Implement now; preserve academic tombstones/history and shared asset references |
| G01 exporter definitions | Independently trusted schemas and concrete ID/version/unit semantics | Blocks S025 completion and dependent production adapters; tree already supplied |
| Workload targets | Named hardware/concurrency/latency/import budgets | Established/measured in S088 before release claims |
| Staging/production services | Host, DNS/TLS, mail, storage, backup access and live-action authorization | S090 can package locally; S092/S093 block on missing required access |
| Later integrations | Provider/vendor/feed/signing/retention contracts | Gate the specific Phase 2/Future cards, not MVP foundation work |

Institutions can amend accepted defaults later; they are not unanswered questions
that every future agent must ask again. Retention has no grace-period emergency
bypass. Purge removes eligible source data while preserving required academic
records via tombstones; anonymization follows the separate governed erasure path.

## Verification and alternatives

S001's change ledger maps each ambiguity to an ADR, SRS section, and later behavior
test. The context helper validates references/dependencies. S025 must demonstrate
format support from actual trusted definitions. Treating guessed definitions as
confirmed or repeatedly blocking unrelated tasks on optional defaults would make
the backlog unreliable.
