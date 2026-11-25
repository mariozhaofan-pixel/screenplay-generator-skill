# Terminology and Portability Lock

Load this reference for every substantive screenplay, storyboard, revision, or
production task. It owns canonical vocabulary, condition wording, and
cross-model/cross-computer boundaries. It does not replace any domain owner.

## Rule Precedence

Apply rules in this order:

1. safety, originality, copyright, factual honesty, and source-canon protection
2. the current user's explicit project facts, named source, output scope, and hard contract
3. the single domain owner named in `SKILL.md`
4. this terminology lock
5. examples, style references, and low-risk defaults

`owner` means the single authority file for a rule domain, not a copyright or
project owner. A routing file may point to an owner but may not redefine that
owner's rule. File order and filename numbering do not create precedence.

`current brief` means the latest non-conflicting user instructions plus any
source explicitly named for this task. Older examples, tests, chat summaries,
and model memory are excluded unless the user explicitly carries them forward.

`explicit` means stated by the user or measured/read from a named source. It
does not include a model inference, common convention, or remembered example.

`default` means a fallback used only when the user, named source, active
contract, and domain owner provide no conflicting value. A default never carries
facts forward from an older task.

`hard contract` means the user intends a numeric value or bound to be used for
acceptance, such as `must equal`, `must not exceed`, `at least`, or a model unit
limit. Approximate mood language such as `about two minutes` remains soft unless
the user also asks for numeric budgeting or compliance.

`real media` means a source audio/video/frame file that is available to the
current run and has actually been probed. A mentioned but inaccessible file is
not measured media.

`rights evidence` means a license, permission record, contract, platform grant,
or other rights-holder source actually inspected in the current run. A user's
statement that rights exist or can be purchased is explicit project input, but
is not inspected rights evidence.

## Canonical Machine Tokens

Use these exact tokens in contracts, headings, validators, and mode declarations:

| Domain | Canonical token | Meaning |
|---|---|---|
| timing | `silent-default` | no explicit numeric contract and no real-media lock |
| timing | `contract-budget` | explicit numeric production target, bound, or GEN limit |
| timing | `media-frame-lock` | measured real audio/video/timecode/frame synchronization |
| dialogue | `draft-sync` | screenplay and CUT dialogue are synchronized internally |
| dialogue | `production-lock` | stable D-IDs and all three dialogue projections are exact |
| viewpoint | `客观` / `objective` | no character owns the camera's knowledge boundary |
| viewpoint | `角色对齐` / `character-aligned` | perception is aligned with one character without literal eye-camera identity |
| viewpoint | `字面POV` / `literal POV` | camera represents the owner's actual view or verified media memory |
| viewpoint | `临时全知` / `temporary omniscience` | declared information temporarily exceeds one character's knowledge |
| generation | `CUT` | one uninterrupted editorial camera segment |
| generation | `GEN` | one independently generatable and reviewable production unit |
| generation | `SEG` | accepted input alias only; normalize output to `GEN` |
| layers | `layer=post` | post-production content excluded from organic image/video generation |
| layers | `layer=post/screen-replacement` | controlled UI/screen state composited after base generation |
| rights | `rights-unverified` | no permission evidence or usable scope was inspected in the current run |
| rights | `rights-asserted` | project proceeds on the current user's clearance plan; evidence/scope remain uninspected |
| rights | `rights-verified` | permission evidence and the production-relevant scope were inspected in the current run |
| reference level | `trait-reference` | only transferable craft traits are used; no exact protected expression is required |
| reference level | `exact-dependent` | a recognizable protected expression or asset is an explicit production dependency |
| protected asset source | `AUTHORIZED-ASSET` | full planned asset/clip/visual slot whose protected source is pending |
| protected asset source | `USER-SUPPLIED-ASSET` | exact reference asset supplied in the current user materials |
| lyric text source | `AUTHORIZED-LYRIC` | full planned lyric slot whose protected text is intentionally pending |
| dialogue text source | `AUTHORIZED-DIALOGUE` | full planned dialogue/subtitle/screenplay slot whose protected wording is pending |
| protected text source | `USER-SUPPLIED-TEXT` | exact protected text supplied in the current user materials |
| protected text source | `RIGHTS-VERIFIED-SOURCE` | exact protected text read from a source covered by inspected permission |

New output declares modes with exactly two machine fields:

- `timing_mode`: exactly one of `silent-default`, `contract-budget`, or
  `media-frame-lock`
- `active_modules`: `none` or a comma-separated subset of `revision`,
  `production-lock`, `GEN`, and `Asset/SCN`

The two declarations must equal the current contract and trigger table. Labels
such as `当前模式`, `时长模式`, `asset lock`, and `frame mode` are legacy input
aliases, not valid new-output fields.

## Literal Serialization Lock

Machine-facing labels are protocol strings, not natural-language headings:

- Copy every active section label, table column, CUT field label, and GEN field
  label from `storyboard-output.md` exactly. Do not add/delete spaces, remove
  punctuation, translate, shorten, or substitute synonyms.
- In particular, the last two CUT labels are exactly `AI画面事实` and
  `连续性/资产`.
- Write the mode lines as plain list items such as
  `- timing_mode：silent-default` and `- active_modules：Asset/SCN`. Do not wrap
  the field names in Markdown code marks.
- Inside `叙事视点/知识边界`, write plain values such as `模式=客观`; do not wrap
  machine keys or values in Markdown code marks.
- Preserve the arrow-chain grammar shown by the output owner inside
  `演员调度/动作节拍`, `情绪与表演`, `视觉焦点/动势`, and
  `剪辑/转场相位`. Do not replace required `->` separators with commas or
  semicolons; the transition field must always serialize all five phases.
- Emit `【资产注册表】`, `【场景母版注册表】`,
  `【受保护文本填入表】`, and `【版权出处与使用声明】` as literal standalone
  section labels when active.
  Styling may appear on a separate preceding line but may not replace the label.
- After drafting, compare the serialized labels against the output owner before
  evaluating story quality. A semantically similar label is a hard schema error.

Do not invent synonyms in machine-facing fields. For example, `近主观`,
`第一人称镜头`, and `贴肩主观` are camera descriptions, not viewpoint mode
tokens; map them to `角色对齐` or `字面POV` and place the physical framing under
`摄影`.

IDs are uppercase and zero-padded: `S01-B01`, `D-001`, `CUT-001`, `GEN-001`,
`EVT-001`, `ASSET-001`, and `SCN-001`. Canonical CUT headings use
`### CUT-001 | S01-B01`; canonical GEN headings use
`### GEN-001 | CUT-001—CUT-003`. Labels and EVT annotations belong in fields or
sync tables, not in these headings.

## Artifact Definitions

- `complete screenplay`: all requested narrative scenes with visible/audible
  action, exact dialogue, Scene/Beat IDs, causal ending state, and the two
  screenplay-derived global style prompts. It is not an outline or Beat list.
- `complete screenplay delivery`: the complete screenplay plus canonical CUTs
  unless the user explicitly requests screenplay-only output.
- `authoritative screenplay dialogue`: the D-ID line in the complete screenplay.
- `CUT dialogue projection`: ordered audible fragments derived from that D-ID.
- `complete dialogue lock`: the production-lock table derived from the same D-ID.
- `three-layer dialogue synchronization`: equality among the previous three
  artifact surfaces. It does not mean dialogue text, subtext, and performance.
- `Scene`: a narrative scene in the screenplay.
- `Beat`: a meaningful change inside a Scene.
- `SCN-ID` / `scene master`: the authority for spatial identity and geometry.
- `master shot`: a photographic coverage setup; it is not a scene master.
- `primary shot` / `主镜`: an indispensable target image; it is not necessarily
  a wide master shot and a scene may contain more than one.
- `Asset-ID`: the authority record for a character period, wardrobe, object,
  scene plate, screen state, audio source, or another controlled asset.
- `canon candidate`: a protected new version awaiting acceptance.
- `canon`: the version explicitly accepted or named as authoritative.
- `impact sidecar`: a separate report containing the change matrix, residue
  audit, validation evidence, and downstream re-baseline information.
- `responsibility shot`: an objective result image used when subjective coverage
  would otherwise conceal who chose, caused, or received a consequential act.
- `cold-start IN`: enough factual state to rebuild a GEN without copying the
  previous GEN's pixels, pose, framing, lighting, or hidden state.

## Conditional Trigger Lock

Replace unspecified conditional wording with these triggers:

| Module | Activate when |
|---|---|
| revision | a source draft/version/canon is named or existing production IDs must remain synchronized |
| production-lock | exact line count, canon revision, downstream prompt compilation, or production-grade dialogue lock is requested |
| GEN | AI-video generation, a model unit limit, production packing, or segment handoff is requested |
| Asset/SCN lock | the user supplies assets/paths/approved frames, continuity must persist across units, or downstream production needs stable IDs |
| callbacks | an event repeats and its later meaning affects interpretation |
| responsibility shot | a consequential choice/harm would be unclear or excused without an objective result image |
| research | a current, niche, factual, dialect, meme, named-work, music-rights, or open-source claim can change the result |
| BGM | the user requests music or music has a distinct narrative function not already carried better by performance/sound |

If a trigger is absent, leave the module inactive. Do not print empty mode
sections merely to show that they exist.

## Operational Meanings for Quality Words

- `natural dialogue`: an actor can say it at the intended relationship distance
  and pressure without rewriting its syntax; it performs an immediate language
  action and does not recite shared information.
- `playable emotion`: a start state, trigger, breath/voice behavior when audible,
  one primary visible action, and an end state; not an emotion label alone.
- `visible`: directly depictable in image, blocking, screen state, or a declared
  controlled post layer. Internal intention is not visible until behavior proves it.
- `audible`: recordable dialogue, VO, narration, sound, or music with a declared source.
- `executable`: identity, space, start state, action order, end state, and
  continuity are specific enough for a crew or model to perform without inventing
  a causal fact.
- `exact`: character-for-character equality after Unicode NFC normalization;
  punctuation, order, source mode, lip-sync subject, and fragment mapping count.
- `complete`: all fields owned by the active schema are present. It does not mean
  adding inactive modules.
- `preserve`: do not change text or facts designated as locked; downstream
  projections may be regenerated only to remain synchronized.
- `derive`: regenerate from the named authority source; do not independently
  improvise or patch the projection.
- `reasonable assumption`: a reversible, low-risk creative detail that does not
  change canon, mandatory premise, hard production limits, legal rights, asset
  identity/path, or delivery scope. State it in `创作假设`.
- `authorized text`: protected text supplied by the user or read from a source
  covered by inspected permission. It never means text reconstructed from model
  memory, search snippets, or an uninspected purchase plan.
- `hard error`: blocks release until corrected.
- `warning`: a non-structural condition requiring recorded human/semantic review;
  it is not an automatic pass.

## Timing Language Boundary

`silent` modifies timing output only. It does not mean skipping scale judgment,
story-density review, or feasibility reasoning. In `silent-default`, keep any
such judgment internal and output no runtime, seconds, timecode, frame number,
budget, or duration arithmetic.

`planned` means a production allocation or estimate. `measured` means read from
real media or recorded performance. Never label a planned budget as measured
runtime or final-film duration.

## Path and Computer Portability

- Treat user paths and external IDs as opaque runtime values. Never copy a path
  from an example, test, prior computer, or private regression into a new task.
- Do not hardcode drive letters, home directories, usernames, path separators,
  repository locations, tool locations, or network mounts in deployable rules.
- Resolve relative sidecar paths from their contract or manifest directory.
- Before reading, writing, hashing, or packaging a local path, verify that it
  exists and identify whether it is a file or directory.
- Before creating a version or archive, verify that the destination is unused.
- Preserve UTF-8 text and Unicode NFC. Treat case sensitivity and slash direction
  as environment-dependent; compare resolved paths rather than raw strings.
- Accept LF and CRLF as equivalent structural line boundaries. Hash a protected
  source from its original bytes, and do not rewrite line endings to make a
  source hash pass. Dialogue equality still follows its NFC/exact-punctuation
  rule.
- A script, browser, network, media probe, image generator, or video model may be
  unavailable on another computer. Check capability before use. If unavailable,
  keep the textual production contract and state the unverified boundary instead
  of fabricating a result.
- The bundled report-only validators require Python 3.10 or newer and no
  third-party Python packages. Independent media-duration checks use `ffprobe`
  only when available.
- `GEN` is a production-planning unit, not a promise that every model accepts one
  prompt containing several edits. Before downstream generation, compile or
  split the approved GEN only when the selected tool's documented input contract
  requires it; do not change screenplay causality or CUT identity silently.
- Never claim a local file, URL, asset, duration, frame rate, hash, or license was
  checked when it was not checked in the current run.

## Model Portability

- Do not rely on hidden chain-of-thought, persistent memory, prior agent state,
  or an example answer. Put required observable facts in the current brief,
  authority source, contract, or active owner.
- Keep identity, spatial geometry, action order, and causal UI state explicit at
  every independent GEN boundary.
- Use deterministic validators for structure and arithmetic, then separate blind
  semantic review for naturalness, event credibility, brief fidelity, and visual
  causality. A static pass cannot certify performance quality.
- Never repair a failed semantic review by weakening the contract or renaming the
  same failed event. Revise the underlying event, dialogue load, or production unit.

## Retrieval and Length Health

- Keep `SKILL.md` as a routing and execution file. Keep full rules in their single
  owner references.
- Load this glossary plus only the domain owners triggered by the current task.
- Do not duplicate full schemas, mode rules, or long examples across owners.
- Do not compress away triggers, exceptions, field definitions, or acceptance
  checks merely to reduce length.
- Prefer one complete authoritative definition plus short cross-file routes.
- Keep private regression stories, test answers, personal paths, and accepted
  sample dialogue outside deployable references and GPT knowledge files.
