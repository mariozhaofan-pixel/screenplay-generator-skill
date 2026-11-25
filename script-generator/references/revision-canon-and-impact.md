# Revision Canon and Impact Control

Use this reference when the user names an existing script, version, canon, sole source, approved draft, locked asset set, or asks to revise production material. This file owns source-canon protection, version allocation, change impact, stale-residue auditing, numbering propagation, and downstream re-baselining.

## Contents

- Revision-mode trigger and preflight
- Source protection and version allocation
- Locked invariants and change requests
- Impact matrix
- Propagation and numbering
- Residue audit
- Downstream production gate
- Revision delivery

## Revision-Mode Trigger and Preflight

Enter revision mode when any of these is true:

- a source document or exact version is named
- the user says canon, sole source, approved draft, locked version, or replace a specific passage
- existing CUTs, dialogue IDs, assets, or downstream production work must remain synchronized

Before editing, read the complete source and record:

`source_canon_path | source_sha256 | parent_version | locked_invariants | explicit_delete | explicit_add | affected_downstream`

Do not infer canon from the newest-looking filename when the user has named another source.

For local production work, run the report-only preflight before creating the candidate:

```text
python scripts/preflight_revision.py --source SOURCE --versions-dir DIR \
  --locked-invariant "..." --explicit-delete "..." --explicit-add "..." \
  --json-out PREFLIGHT.json
```

Exit `0` passes, `1` means a protected constraint failed, and `2` means the input could not be parsed. The script never creates or rewrites the candidate.

## Source Protection and Version Allocation

- Source and output paths must resolve to different files.
- Never overwrite, rename, delete, or silently mutate the source canon.
- Use the next higher unused version unless the user explicitly provides another unused lane.
- Refuse an occupied output path.
- Preserve source hash and report it in the revision manifest.
- Keep rejected and historical versions available as history; do not relabel them as current.
- A candidate becomes canon only after the requested validation and explicit acceptance boundary.

## Locked Invariants and Change Requests

Record:

- `locked_invariants`: facts, lines, ending, IDs, assets, or production decisions that must remain
- `explicit_delete`: facts, events, dialogue, props, transitions, assets, or paths that must disappear
- `explicit_add`: new facts or requirements
- `allowed_side_effects`: consequences the user has approved

Do not widen the rewrite beyond the causal and synchronization impact of the request.

## Impact Matrix

Create before drafting:

```text
Change-ID | deleted/added fact | direct Beat/CUT impact |
propagated surfaces | preserved constraints | acceptance check
```

For each Change-ID, mark every surface whose facts, IDs, assets, or handoffs change:

- version header and source hash
- creative assumptions and contract mode
- event causality and EVT callbacks
- character behavior loops
- complete screenplay
- image/camera style prompts
- scene director maps
- CUTs and viewpoint fields
- screenplay/CUT sync table
- complete dialogue lock
- timing/GEN contract
- sound, BGM, and post layers
- continuity, Asset/SCN registries
- downstream canon notification

## Propagation and Numbering

- If CUT, D-ID, EVT-ID, GEN-ID, Asset-ID, or SCN-ID numbering changes, declare the remap and update every reference.
- If numbering does not change, still validate continuity, uniqueness, order, and reference closure.
- Update derived surfaces from their authority source; do not patch projections independently.
- A changed scene fact must propagate into each listed surface that cites or depends on that fact.

## Residue Audit

Build a deletion manifest covering:

`old dialogue | action | prop | location | transition | event term | continuity description | asset path`

Run two passes:

1. exact/regex scan across the complete document and every table
2. independent semantic red-team looking for the same old event expressed with different words

Static scans are deterministic; semantic residue requires review. Do not mix this audit with `style-contamination.md`, which owns unrelated example/style leakage.

Keep scan patterns and detailed findings in a sidecar validation report. Do not paste forbidden legacy terms into the final canon's self-check section and accidentally recreate the residue.

## Downstream Production Gate

- When downstream image/video/prompt work exists, pause only the affected range while the new canon is unresolved.
- Do not generate or continue affected prompts from a superseded source.
- After acceptance, issue a re-baseline notice containing new canon path/hash, affected IDs, replaced IDs/assets, preserved work, and the next authorized action.
- Do not automatically resume generation unless the user has authorized that stage.

## Revision Delivery

For a production revision, provide:

- version header with parent and source hash
- concise modification request and preserved invariants
- new canon candidate document
- ID remap whenever any existing identifier changes, splits, merges, or shifts
- sidecar impact/residue/validation report
- downstream re-baseline notice whenever affected downstream production exists

Set `revision.impact_report_path` in the delivery contract to that sidecar. The
post-delivery validator rejects revision mode when the report is missing, is the
delivery document itself, lacks a populated impact matrix, or omits source,
delete/add, and residue-audit surfaces.

Do not embed the full impact audit or banned-term list inside the canon document unless the user explicitly requests an annotated diagnostic edition.
