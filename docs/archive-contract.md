# Archive contract intake

Status: file inventory supplied; exact field-level contract pending.

This is input gate **G01**, recorded in
[ADR 0006](decisions/0006-requirement-authority-and-input-gates.md). It gates S025
and its dependent production-format work; it does not block independent foundation
or manual-grading sprints.

The owner's complete tree is preserved in [archive-layout.md](archive-layout.md).
It specifies manifest/checksums/README, schema filenames, record families, paths,
and intended content. It includes optional restricted evidence and derived human
reports. This is enough to plan modules and implement adapter-independent ZIP
security, staging, jobs, and UI workflows.

It does not include the contents of `manifest.schema.json` or the other schema
files. For example, a comment saying “Stable IDs” does not establish whether the
property is `id`, `userId`, a string or an integer, or unique per installation.
That information is needed before a production adapter can claim compatibility.

## S025 intake checklist

- Complete independently trusted schema definitions, including their JSON Schema
  draft, supported format-version value, and digest/provenance information.
- Exporter README with concrete field names, units, timestamps/timezones, nullable
  versus absent semantics, enum meanings, and record/file relationship rules.
- Stable source installation, contest, participant/user, export/version identifiers
  and how they behave when a contest is exported again or rejudged.
- Exact file-to-schema mapping, including final/frozen/snapshot standings,
  JSONL row schemas, and `files/revisions/.../problem.json`.
- Required versus optional paths and how manifest counts, availability,
  exclusions, truncation, and inventory are encoded.
- Checksum line format, normalized path rules, Unicode/case behavior, and archive
  schema-copy comparison semantics.
- A small permitted/anonymized sample and expected interpretation, plus permission
  to commit schema definitions or generated synthetic fixtures if applicable.

Store schema provenance and the finalized adapter mapping here once obtained.
Keep real private ZIPs under ignored `private/`. Do not put fabricated “official”
schema files in a production registry. Test-only adapters use a separate format
identifier that production configuration refuses.

## Inventory disposition

| Archive family | Planned treatment | Sprint |
|---|---|---|
| manifest/checksums/schemas/README | Bounded validation, trusted version registry, provenance | S025, S030-S032 |
| contest and problems | Versioned source metadata and inert assets | S033 |
| people | Source users/teams/participants, separate identity mapping | S034, S040-S041 |
| judging and submissions | Streamed historical execution evidence; never run code | S035 |
| results | Official final/frozen/history and derived source statistics | S036 |
| communication/materials/history/presentation | Historical evidence with original audience metadata | S037 |
| files and referenced revisions | Preserved bytes, opaque storage IDs, per-component gates | S021-S022, S033-S038 |
| restricted | Separately protected structured data and evidence | S038 |
| reports | Optional non-authoritative derived artifacts; never overwrite JSON facts | S037 |

The full tree remains the source for individual filenames. This table is a routing
index, not a replacement or an invented field schema.
