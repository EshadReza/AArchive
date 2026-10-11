# Contest export archive layout

Supplied by the project owner on 2026-10-04. Both attachments contained the same
layout; it is preserved verbatim below. This describes the ZIP uploaded to the
platform, not the application source-code directories. The names and comments are
known. Exact JSON properties, types, enums, required fields, schema draft, and a
concrete format-version value are not specified by this tree. Do not invent them
when claiming compatibility with the external exporter.

See [the SRS](requirements.md), [decisions D05-D07](decisions/README.md), and
[sprint S025](../TASKS.md#s025) for schema onboarding. Implementation
of ZIP safety, staging, and application features can proceed before the literal
schema definitions arrive.

```text
contest-export.zip
├── manifest.json                         # Format version, source, snapshot time, counts, availability, exclusions, file inventory
├── checksums.sha256                      # SHA-256 checksum for every archive file except this checksum file
├── README.md                             # Format documentation, field meanings, units, relationships, import behavior
│
├── schemas/                              # JSON Schemas defining every JSON and JSONL record type
│   ├── manifest.schema.json
│   ├── contest.schema.json
│   ├── settings.schema.json
│   ├── schedule.schema.json
│   ├── scoring-rules.schema.json
│   ├── access-policy.schema.json
│   ├── organizers.schema.json
│   ├── users.schema.json
│   ├── participants.schema.json
│   ├── teams.schema.json
│   ├── team-memberships.schema.json
│   ├── registrations.schema.json
│   ├── access-grants.schema.json
│   ├── contest-role-assignments.schema.json
│   ├── problems.schema.json
│   ├── test-cases.schema.json
│   ├── test-groups.schema.json
│   ├── checkers.schema.json
│   ├── validators.schema.json
│   ├── generators.schema.json
│   ├── reference-solutions.schema.json
│   ├── editorials.schema.json
│   ├── attachments.schema.json
│   ├── environment.schema.json
│   ├── languages.schema.json
│   ├── judge-configurations.schema.json
│   ├── execution-profiles.schema.json
│   ├── dependency-inventory.schema.json
│   ├── submissions.schema.json
│   ├── judging-runs.schema.json
│   ├── test-results.schema.json
│   ├── score-adjustments.schema.json
│   ├── rejudge-history.schema.json
│   ├── deletion-history.schema.json
│   ├── standings.schema.json
│   ├── participant-results.schema.json
│   ├── problem-statistics.schema.json
│   ├── contest-statistics.schema.json
│   ├── awards.schema.json
│   ├── certificates.schema.json
│   ├── announcements.schema.json
│   ├── clarifications.schema.json
│   ├── clarification-history.schema.json
│   ├── notifications.schema.json
│   ├── materials.schema.json
│   ├── contest-events.schema.json
│   ├── configuration-changes.schema.json
│   ├── problem-revisions.schema.json
│   ├── administrative-actions.schema.json
│   ├── audit-events.schema.json
│   ├── branding.schema.json
│   ├── navigation.schema.json
│   ├── page-content.schema.json
│   ├── localization.schema.json
│   ├── asset-references.schema.json
│   ├── account-migration.schema.json
│   ├── contest-credentials.schema.json
│   ├── workstation-records.schema.json
│   ├── integrity-reports.schema.json
│   └── administrative-notes.schema.json
│
├── contest/
│   ├── contest.json                      # Identity, title, slug, description reference, type, state, owner, organization, tags
│   ├── settings.json                     # Feature flags, visibility settings, submission limits, clarification settings
│   ├── schedule.json                     # Scheduled/actual start, duration, end, freeze, pauses, accumulated paused time, timezone
│   ├── scoring-rules.json                # Points, partial credit, penalties, time calculation, tie-breaks, ranking algorithm/version
│   ├── access-policy.json                # Admission requirements, eligibility, permissions, content release rules
│   ├── organizers.json                   # Organizer references, roles, ordering, public contact information
│   ├── rules.html                        # Complete contest rules
│   └── description.html                  # Complete contest description
│
├── people/
│   ├── users.json                        # Stable IDs, usernames, display names, creation times, source roles, profile references
│   ├── participants.json                 # Contest/user/team references, contestant numbers, divisions, eligibility, participation status
│   ├── teams.json                        # Team identities, names, institutions, captain references
│   ├── team-memberships.json             # Team/user relationships, member roles, membership timestamps
│   ├── registrations.json                # Registration timestamps, approval status, approvers, custom answers
│   ├── access-grants.json                # Contest/user admission grants, grant times, revocations if recorded
│   └── contest-role-assignments.json      # Contest-specific roles, permissions, assignment/revocation times
│
├── problems/
│   ├── problems.json                     # IDs, codes, titles, ordering, statement paths, limits, points, attribution, revision references
│   ├── test-cases.json                    # IDs, problem references, indices, input/output paths, checksums, visibility, weights
│   ├── test-groups.json                   # Subtasks/groups, points, dependencies, aggregation and execution rules
│   ├── checkers.json                      # Checker types, source paths, language, commands, tolerances, dependencies
│   ├── validators.json                    # Input validator sources, commands, limits, dependencies, versions
│   ├── generators.json                    # Test generator sources, parameters, seeds, commands, versions
│   ├── reference-solutions.json           # Solution source paths, languages, expected verdicts, authors, visibility
│   ├── editorials.json                    # Editorial content paths, languages, authors, visibility, release times
│   └── attachments.json                   # Problem attachments, file paths, content types, ordering, visibility
│
├── judging/
│   ├── environment.json                  # Judge version, OS, architecture, image digest, locale, isolation configuration
│   ├── languages.json                    # Compiler/runtime versions, extensions, compile/run commands, language-specific limits
│   ├── judge-configurations.json          # Time/memory accounting, output limits, retries, execution order, fail-fast behavior
│   ├── execution-profiles.json            # Process, filesystem, network, resource limits, permitted environment variables
│   └── dependency-inventory.json          # Required libraries, packages, versions, checksums, dependency relationships
│
├── submissions/
│   ├── submissions.jsonl                 # One submission per line; references, source path, timestamps, status, verdict, marks, active flag
│   ├── judging-runs.jsonl                # One judging attempt per line; configuration/revision references, results, logs, trigger
│   ├── test-results.jsonl                # One executed/skipped test result per line; verdict, score, time, memory, outputs, truncation flags
│   ├── score-adjustments.jsonl           # Manual score/penalty adjustments, units, previous/new values, reasons, actors, timestamps
│   ├── rejudge-history.jsonl             # Rejudge requests/actions, submission/run references, reasons, actors, timestamps
│   └── deletion-history.jsonl            # Soft-deletion/restoration events, previous/new active state, reasons, actors, timestamps
│
├── results/
│   ├── final-standings.json               # Final ranks, scores, solved counts, penalties, tie-break values, per-problem results
│   ├── frozen-standings.json              # Standings as visible at the freeze snapshot
│   ├── standings-snapshots.jsonl          # Timestamped historical standings and scoring-rule versions
│   ├── participant-results.json          # Participant totals, per-problem outcomes, first-to-solve flags, inclusion status
│   ├── problem-statistics.json           # Attempts, acceptances, verdict distributions, solve rates, timing statistics
│   ├── contest-statistics.json           # Contest totals, language distributions, calculation times, inclusion rules
│   ├── awards.json                       # Recipients, award names/categories, ranks, issuers, issue dates
│   └── certificates.json                 # Recipient references, certificate paths, issuers, verification references
│
├── communication/
│   ├── announcements.json                # Complete bodies, formats, timestamps, authors, audiences, pinned state, assets
│   ├── clarifications.json               # Questions/answers, asker/problem references, timestamps, privacy, approval state
│   ├── clarification-history.jsonl       # Question/answer edits, visibility/approval changes, actors, timestamps
│   └── notifications.jsonl               # Recorded notifications, related records, audiences, timestamps, delivery states
│
├── materials/
│   └── materials.json                    # Original/stored filenames, archive paths, MIME types, sizes, hashes, upload times, visibility
│
├── history/
│   ├── contest-events.jsonl              # Start, pause, resume, freeze, unfreeze, end and other recorded lifecycle events
│   ├── configuration-changes.jsonl       # Setting changes with previous/new values, actors, reasons, timestamps
│   ├── problem-revisions.jsonl           # Historical problem/test/checker revisions and references to archived revision files
│   ├── administrative-actions.jsonl      # Recorded administrative actions, targets, actors, reasons, timestamps
│   └── audit-events.jsonl                # Recorded audit events, correlation IDs, targets, actors, timestamps
│
├── presentation/
│   ├── branding.json                     # Logo/banner paths, colors, typography settings
│   ├── navigation.json                   # Page/menu ordering, labels, destinations
│   ├── page-content.json                 # Additional public page content and file references
│   ├── localization.json                 # Supported locales, translated labels/content, default locale
│   └── asset-references.json             # Asset IDs, archive paths, original URLs, content types, checksums, visibility
│
├── files/                                # Original file bytes; referenced by archive-relative paths in JSON records
│   ├── statements/
│   │   └── problem-{problemId}/
│   │       ├── statement.html
│   │       ├── statement.pdf
│   │       ├── translations/
│   │       │   └── {locale}/
│   │       │       ├── statement.html
│   │       │       └── statement.pdf
│   │       └── assets/
│   │           └── {assetId}.{extension}
│   │
│   ├── tests/
│   │   └── problem-{problemId}/
│   │       └── test-{testId}/
│   │           ├── input.txt
│   │           └── expected-output.txt
│   │
│   ├── checkers/
│   │   └── checker-{checkerId}/
│   │       ├── source.{extension}
│   │       └── dependencies/
│   │           └── {filename}
│   │
│   ├── validators/
│   │   └── validator-{validatorId}/
│   │       ├── source.{extension}
│   │       └── dependencies/
│   │           └── {filename}
│   │
│   ├── generators/
│   │   └── generator-{generatorId}/
│   │       ├── source.{extension}
│   │       └── dependencies/
│   │           └── {filename}
│   │
│   ├── reference-solutions/
│   │   └── solution-{solutionId}/
│   │       └── source.{extension}
│   │
│   ├── editorials/
│   │   └── editorial-{editorialId}/
│   │       ├── content.{extension}
│   │       └── assets/
│   │           └── {assetId}.{extension}
│   │
│   ├── problem-attachments/
│   │   └── attachment-{attachmentId}/
│   │       └── {originalFilename}
│   │
│   ├── submissions/
│   │   └── submission-{submissionId}/
│   │       ├── source.{extension}
│   │       ├── source-files/              # Additional source files for multi-file submissions, if supported
│   │       │   └── {relativeSourcePath}
│   │       └── runs/
│   │           └── run-{runId}/
│   │               ├── compiler-output.txt
│   │               ├── judge-log.txt
│   │               └── tests/
│   │                   └── test-{testId}/
│   │                       ├── stdout.txt
│   │                       ├── stderr.txt
│   │                       └── checker-output.txt
│   │
│   ├── revisions/
│   │   └── problem-{problemId}/
│   │       └── revision-{revisionId}/
│   │           ├── problem.json
│   │           ├── statement/
│   │           │   └── {filename}
│   │           ├── tests/
│   │           │   └── test-{testId}/
│   │           │       ├── input.txt
│   │           │       └── expected-output.txt
│   │           └── checker/
│   │               └── source.{extension}
│   │
│   ├── materials/
│   │   └── material-{materialId}/
│   │       └── {originalFilename}
│   │
│   ├── communication-assets/
│   │   └── {assetId}.{extension}
│   ├── branding/
│   │   └── {assetId}.{extension}
│   ├── avatars/
│   │   └── {assetId}.{extension}
│   └── certificates/
│       └── certificate-{certificateId}.pdf
│
├── restricted/                           # Optional protected migration/admin data; folder name does not provide encryption
│   ├── README.md                         # Access restrictions, migration instructions, inclusion/exclusion details
│   ├── account-migration.json            # Account references, password hashes/algorithm parameters when explicitly included
│   ├── contest-credentials.json          # Contest password hashes/algorithm parameters when explicitly included
│   ├── workstation-records.jsonl         # Recorded user/submission IP/MAC observations and timestamps
│   ├── integrity-reports.json            # Evidence references, findings, review states, reviewers, decisions
│   ├── administrative-notes.json         # Private notes, target references, authors, timestamps
│   └── evidence/
│       └── evidence-{evidenceId}/
│           └── {filename}
│
└── reports/                              # Optional derived human-readable reports; JSON records remain authoritative
    ├── standings.csv
    ├── submissions.csv
    ├── participant-results.csv
    ├── problem-statistics.csv
    └── contest-summary.pdf
```
