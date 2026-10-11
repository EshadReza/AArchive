# ADR 0002 - Academic relationships, team participants, and assessments

Status: accepted for implementation; Sprint: S001; Date: 2026-10-05.
Requirements: ADMIN-010, COURSE-001, CONTEST-002, MARK-003; SRS Sections 13, 40-44.

## Decision

Department owns reusable Courses and Batches. Batch owns Terms and Sections.
Offering references exactly one Course, Batch, Term, and Section. Term/Section
must belong to that Batch and Course to its Department. Use a real `ALL` Section
for an unsplit batch. Preserve effective-dated enrollment and teacher assignments.

Contest links to zero or more Offerings. Each Offering defines many Assessments;
each Assessment references zero or one Contest; one Contest may therefore feed
many Assessments, including independent scales/rules for different Offerings.
The relationship cannot be represented by the former one-assessment ER edge.

A versioned ContestParticipant has a discriminator and exactly one subject:
an ImportedUser for an individual, or a Team for team participation. TeamMember
links a versioned Team to an ImportedUser with source membership times. Source
records and referenced subjects must agree on import version. Where the trusted
format allows a missing optional user profile, preserve a source-identity stub
with availability metadata; a required unresolved reference still fails import.

SourceIdentity is the stable `(source_namespace, source_user_key)` concept.
Versioned ImportedUser snapshots refer to it. At most one current
StudentIdentityMapping maps a SourceIdentity to a platform User; append-only
mapping history preserves corrections. A placeholder is a non-login identity
resolution state, not a fabricated institutional User with a fake email.

StudentMark always belongs to one actual enrolled platform student and one
Assessment. A team score requires a teacher-reviewed allocation and membership
snapshot. Team membership grants no access to another member's academic mark.
For TEACHERS_AND_OWNER source viewing, a verified mapping to a member recorded
at the submission's source time counts as team ownership; insufficient historical
membership evidence cannot grant access. Adding a current member later does not
grant retroactive access to earlier private submissions.

## Consequences and verification

S012-S015 test matching-parent constraints; S024/S034 test individual/team XOR
and version integrity; S040-S041 test namespace-safe mappings; S052/S054 test
independent offering assessments and reviewed team grade allocation. No exporter
property names are inferred by these platform concepts.

## Alternatives

Duplicating Courses per term would fragment the catalog. Choosing a captain as
the owner of all team submissions would lose team evidence. Automatically copying
a team score to every enrollee would create academic records without a valid basis.
