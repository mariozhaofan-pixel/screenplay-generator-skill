# Asset and Scene Master Locks

Use this reference when the user supplies character images, wardrobe/period looks, locations, scene plates, props, audio, approved frames, or downstream production assets. This file owns authoritative Asset/SCN registries, path verification, scene-master geometry, deprecation, and downstream layer boundaries.

## Contents

- Asset authority and registry
- Path status and deprecation
- Character-period locks
- Scene master versus master shot
- SCN mapping and allowed additions
- Reference-role boundaries
- Post-production layers
- Validation

## Asset Authority and Registry

Register authoritative assets once:

```text
Asset-ID | type | character period/look | absolute path or external ID |
applicable Scene/CUT/GEN | locked facts | status | deprecated paths
```

Use `ASSET-001`, `ASSET-002`, and so on. CUTs and GENs should cite Asset-IDs instead of repeating absolute paths throughout the document.

An Asset-ID is authoritative only for the dimensions explicitly locked: identity, face, hairstyle, wardrobe, prop state, location geometry, position, action phase, or another named role.

For a pending `AUTHORIZED-ASSET`, lock only facts supported by the current
brief or inspected reference. A named but unseen costume/prop does not establish
wearability, pockets, dimensions, weight, articulation, hand use, storage
capacity, or suitability as a plot mechanism. Keep those dimensions
`pending-source` until the asset is supplied or verified.

When a recognizable protected prop is visually required but the story also
needs a precise physical function, separate the roles when necessary: the
protected visual asset preserves recognition, while an original or controlled
functional prop performs storage, concealment, interaction, or causal work.
Do not make the story depend on unknown protected-asset geometry.

## Path Status and Deprecation

- In a local environment, verify that required paths exist and record a hash when production integrity needs it.
- In an environment that cannot access the path, mark it `user-supplied/unverified`; do not claim the file was checked.
- A deprecated path must appear only in the registry's dedicated deprecation/validation sidecar, not in active CUTs or canon prose.
- Scan the full delivery for deprecated paths after replacement.
- Do not copy private asset paths into public Skill references, examples, README content, or tests.

## Character-Period Locks

- One character period/look has one authoritative active asset unless the user explicitly defines variants.
- Distinguish current, past, future, work, home, injury, disguise, or costume states with explicit look IDs.
- Reject phrases such as `use the existing look` when more than one candidate exists.
- A position reference cannot silently replace the identity/wardrobe authority.

## Scene Master Versus Master Shot

`SCN master` means the authoritative spatial geometry and set identity for a story location. It is not the film-language `master shot`.

Register:

```text
SCN-ID | location/event identity | master asset | geometry locks |
allowed additions | prohibited alternate spaces | applicable Scene/CUT/GEN
```

A camera may create many shots inside one SCN master without creating another location.

## SCN Mapping and Allowed Additions

- Every CUT resolves to one SCN-ID.
- The first SCN-ID in the CUT's `场景` field is its active scene master. SCN-IDs
  named only as transition destinations or next-CUT handoffs are references, not
  additional masters for the current CUT.
- CUTs in the same continuous event use one SCN-ID unless the screenplay visibly moves to another space.
- Add user-approved crew, equipment, furniture, weather, crowd, or life detail inside the locked geometry when they do not create a second room, stage, backstage, monitor zone, or alternate topology.
- A new angle, lens, or composition does not create a new SCN master.
- A scene plate controls only the dimensions declared in its Asset-ID/SCN-ID role.

## Reference-Role Boundaries

Separate control dimensions:

- character asset: identity and approved look
- scene master: topology, material, fixed architecture, and approved dressing
- final frame: character world position, facing, spacing, and action phase only when declared
- action reference: route, rhythm, contact, or camera timing only when declared
- current CUT: camera, lens, framing, focus, blocking, and story action

Do not let one reference overwrite dimensions owned by another.

## Post-Production Layers

Mark assets and text that must not leak automatically into generation prompts:

- licensed song or BGM
- lyrics and lyric subtitles
- audio paths
- theme/title cards
- ordinary post subtitles
- editorial overlays or screen replacements

If exact UI text, indicator state, signature order, warning/permission sequence, or screen animation is decisive story evidence, register each required state under an Asset-ID and set `layer=post/screen-replacement`. Generate a stable clean display surface, then apply the exact evidence in post. Organic model rendering is not an authoritative source for causal screen facts.

Use `layer=post` in the registry or downstream contract. Sound design may remain in the screenplay delivery while BGM is conditional on the brief and rights plan.

When an Asset-ID depends on a named third-party clip, character/likeness,
costume, prop, artwork, logo, or other protected source, link it to a
`RIGHTS-ID`. Rights status, replication level, source-state tokens, and
authorization scope are owned by `open-source-research.md`; this file only keeps
the Asset-ID mapping and continuity facts. `rights-asserted` does not block
planning, but it must not be relabeled as an inspected asset or verified license.

## Validation

Before production handoff, verify:

- every cited Asset-ID and SCN-ID exists in its registry
- required local paths exist or are honestly marked unverified
- one active authority per character period/look
- deprecated paths have zero active-document hits
- every continuous event resolves to one SCN master
- allowed additions remain inside locked geometry
- CUT and GEN references agree
- post-production layers are excluded from image/video generation inputs unless explicitly authorized
- every causal screen state has a numbered authority and a declared transition order
- every Asset state change has one explicit before/action/after chain; no field
  simultaneously claims `fixed/unchanged` and moved, removed, opened, or
  relocated
- pending authorized assets are not assigned unsupported functional geometry

This Skill outputs canonical asset/space facts and a downstream handoff contract. Model-specific image-reference ranges and Seedance prompt compilation remain the responsibility of the directing/prompt Skill.
