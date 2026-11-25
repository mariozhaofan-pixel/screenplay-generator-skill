# Quality Checks

Run this internally before delivery. This file owns acceptance only. It does not redefine the methods or schemas owned by the other references. Show diagnostic reasoning only when the user requests a doctor report; otherwise keep the detailed report in a sidecar.

## 1. Active Modes and Authorities

- The current brief's mandatory premise, character objectives, relationships, events, exclusions, and deliverables are preserved; a polished substitute premise is a hard failure.
- Deterministic brief anchors in the delivery contract are present, and semantic review confirms that synonyms or surface mentions did not conceal a premise-level substitution.
- New output contains exactly one canonical `timing_mode` declaration and one
  `active_modules` declaration; both exactly match the current delivery contract
  and trigger table. `当前模式` and `时长模式` are legacy input labels, not new
  output fields.
- Revision, production dialogue lock, GEN mapping, Asset/SCN locking, short-series behavior, and research modules are active only when triggered.
- The complete screenplay is the story and dialogue authority.
- `storyboard-output.md` is the only output-schema authority.
- The source canon path, parent version, source hash, locked invariants, explicit deletions, and explicit additions are recorded when revision mode is active.

## 2. Event Authenticity

- Every key event passed the gate in `event-authenticity-and-callbacks.md` before dialogue polishing.
- The relationship or plot change follows from a visible choice and response rather than an arbitrary accident, forced misunderstanding, humiliating malfunction, proxy rescue, or third-party explanation.
- Removing the coincidence does not collapse the relationship logic.
- Props carrying plot weight are necessary, action-changing, and cannot be
  replaced by a character choice with equal causal clarity and fewer arbitrary
  assumptions.
- Every decisive clue has an origin, insertion/availability, custody/access,
  first visible setup, reveal trigger, permitted inference, changed choice, and
  payoff. No character speaks author-only knowledge.
- Hidden or sealed objects have a credible physical insertion, identification,
  and access chain; the target is selected by a visible rule before opening.
- Repeated events have distinct identities, later meaning changes through action, and callbacks are not mere repeated wording or object display.
- The ending remains understandable in a silent/no-title pass before any theme card appears.

## 3. Story, Character, and Strategy

- The protagonist has a visible objective, an active obstacle, escalation, a costly choice, and an altered ending state.
- The decisive result depends on this character's values, history, expertise, relationship, or flaw rather than a generic replacement.
- Important allies retain objectives, competence, boundaries, and the ability to disagree.
- Any power, access, system, or strategic advantage has applicable limits, counterplay, and consequences.
- Capable opposing sides act from available knowledge and update after new information.
- Payoff answers the story's central pressure and shows an aftermath.

## 4. Dialogue and Performance

- Every key line has a playable language action and changes the other person's action, knowledge, leverage, or relationship state.
- Shared information is not unnaturally recited; high-context speech may use omission, interruption, self-correction, short clauses, and unfinished syntax without becoming unclear.
- A cold read does not force an actor to rewrite the line to say it naturally.
- Directives, conditions, questions, and bargains occur before and visibly trigger their results; no line arrives after compliance merely to explain what just happened.
- Key speech and silent reactions contain a readable start state, trigger, vocal/breath behavior for audible speech or breathing, one primary physical or eyeline action, and an end state.
- Emotion labels are not used as a substitute for playable behavior; crying and recovery are written as a process.
- In production-lock mode, screenplay authority, ordered CUT fragments, and the complete dialogue-lock table match exactly in category, role, text, punctuation, order, source mode, lip-sync subject, and CUT/fragment mapping.
- `D-*`, `LYR-*`, `CARD-*`, and `TXT-*` are classified separately; lyrics or screen cards are never counted as plot dialogue.

## 5. Global Visual Grammar

- Every screenplay delivery contains one screenplay-specific `整体影像风格` prompt and one `统一运镜风格` prompt.
- The two prompts are compatible, visibly actionable, and derived from the current screenplay rather than an old example.
- Per-CUT photography instantiates the global grammar without pasting it repeatedly.
- Timing contracts, media timecodes, and frame data do not leak into the global style prompts.

## 6. Screenplay, CUT, and Schema Closure

- The complete screenplay precedes the storyboard unless the user requested another artifact order.
- Every Scene/Beat maps to at least one CUT; every CUT cites existing Scene/Beat IDs.
- New output uses the exact canonical 14-field sequence in `storyboard-output.md`.
- A historical 12-field input is accepted only in declared compatibility mode and is reported as legacy; it is never emitted as the default.
- A historical 13-field input is upgraded by adding the viewpoint field without merging another field.
- CUT IDs are unique, consecutive, and reference-closed.
- No required action, line, reveal, setup/payoff, or emotional turn disappears during shot conversion.
- No CUT invents a story fact absent from the screenplay, approved event ledger, or registered continuity state.
- Every scene represented by CUTs has one literal `【SNN 场景导演图】` whose 13
  fields match the output owner exactly and are nonempty.
- Each CUT transition occurs after its final listed action and audible text, or
  explicitly maps continuing audio/action into the destination CUT.

## 7. Timing and GEN

### `silent-default`

- The delivery contains no runtime, seconds, timecodes, frame numbers, timing budgets, or duration arithmetic.
- CUT/GEN structure follows story and production logic, not a duration formula.

### `contract-budget`

- The user's explicit total, upper/lower bounds, and GEN limit are restated as production-plan constraints.
- Only the requested total and scene/sequence/GEN budget surfaces contain numeric timing; CUT fields do not gain mechanical seconds.
- Decimal arithmetic closes to the declared total or permitted range, and every explicit GEN ceiling is satisfied.
- Every budget row includes the D-ID load, natural table-read or conservative read/act estimate, non-overlappable actions, permitted overlaps, cold-start/reaction reserve, and PASS/FAIL result.
- Dialogue and action load is feasible within each planned unit; arithmetic-only compliance fails.
- Planned values are not described as measured final runtime.

### `media-frame-lock`

- Source media exists or is otherwise verifiable, and duration/frame/timebase values are measured rather than guessed.
- Timecode, frame, waveform, and phase data appear only on affected edit surfaces.
- Planned and measured values are clearly distinguished.

### GEN closure

- CUT and GEN IDs are distinct; `SEG` appears only as a normalized input alias.
- Every required CUT belongs to the intended GEN map without accidental gaps or duplicate assignment.
- Each narrative GEN has trigger, choice/action, visible response, and a new end state.
- Each GEN's opening CUT contains its own visible trigger, and its IN state fully declares positions, hands/props, story/UI state, Asset/SCN facts, and causal context without pixel inheritance.
- Supporting and transition GENs state an indispensable purpose and valid IN/OUT handoff.
- GEN boundaries reflect cold starts, explicit limits, incompatible state/assets, causality, or review needs, not one prompt per CUT.
- Exact screen text, UI animation, signature order, warning/permission sequence, and other causal display states resolve to controlled Asset/post layers rather than untrusted organic generation.

## 8. Viewpoint, Responsibility, and Transitions

- Every CUT declares `模式 / 主人 / 人物在场 / 观众当前可知 / 进入触发 / 退出触发` as explicit key-value entries.
- Literal POV owners are present or demonstrably viewing/remembering the represented media.
- Subjective views reveal no unavailable facts and begin only after a visible trigger.
- Objective geography or responsibility is established before subjective immersion when clarity or accountability requires it.
- A consequential harmful line or choice receives an objective result image when otherwise the edit would hide responsibility.
- Every designed transition names one primary mechanism and valid source phase, cut point, destination phase, and continuity variable.
- Action matches have independently valid states on both sides; no decorative prop, wipe, or incomplete long-gap action was invented to force the transition.

## 9. Camera, Blocking, and AI Executability

- Every CUT specifies one focal length, shot size, camera position/distance/height/angle, composition, movement, and focus plan.
- Axis, eyelines, screen direction, geography, foreground/background relations, and character scale remain coherent or have a visible motivated reset.
- Each CUT has one dominant visual action, one primary focus, a readable start state, chronological action, and end state.
- Actor blocking states positions, trigger, route, interaction, eyeline, and end orientation without an action menu.
- Director intent explains the viewer effect and information handoff rather than repeating the action.
- No final CUT contains alternatives, `同上`, `按剧情`, `自由发挥`, ambiguous pronouns, or hidden psychology.

## 10. Canon Revision and Residue

- Preflight passed before writing; source and output are different, the source hash is unchanged, and the output version was unused.
- The impact matrix covers every direct and transitive surface named in `revision-canon-and-impact.md`.
- ID remaps, if any, are declared and propagated globally.
- Exact/regex residue scans report zero forbidden old dialogue, actions, props, scenes, transitions, terminology, continuity facts, and deprecated paths.
- An independent semantic review finds no renamed or paraphrased version of a deleted event.
- Deleted terms are not reintroduced into the final canon by a self-check note.
- Affected downstream production is paused until the new canon passes and is explicitly re-baselined.

## 11. Asset and Scene-Master Closure

- Every active Asset-ID resolves to one authority for its character period or object state.
- Pending `AUTHORIZED-ASSET` entries lock no unsupported geometry or function;
  a visual recognition asset is separated from a controlled functional prop
  when the story requires precise physical behavior.
- No asset is simultaneously declared fixed/unchanged and moved, removed,
  opened, or relocated without an explicit state transition.
- Local paths marked as locally verifiable exist; deprecated paths have zero active-document hits.
- Every CUT and GEN resolves to approved Asset/SCN IDs.
- Each continuous event resolves to one SCN-ID unless the screenplay visibly moves to another registered space.
- A scene master locks geography without being confused with a photographic master shot.
- No undeclared second studio, backstage area, monitoring area, or substitute location was invented.

## 12. Format, Style, Research, and Music

- Short-form hooks, catchphrase density, dialect, subtitles, and series tags appear only when the current brief triggers them.
- No old test's plot, names, family pattern, nickname rule, dialect, catchphrases, song, image style, or camera ban leaked into this delivery.
- Every active section label, table column, CUT/GEN field label, mode line, and
  registry header matches the literal output schema; no spacing, slash, Markdown
  decoration, translation, or synonym changed a machine token.
- Current, niche, factual, dialect, meme, named-work, music-rights, and open-source claims were researched when they could change the creative or production result.
- A style-only named-work request uses `trait-reference`; an explicit recreation uses `exact-dependent`. Neither path silently replaces the user's requested reference level.
- Every named third-party clip, character/likeness, costume, prop, artwork, logo, dialogue, lyric, song, recording, or protected asset declares exactly one `rights_status`.
- `trait-reference` and `exact-dependent` are not conflated. Every `exact-dependent` item has a `RIGHTS-ID`, source-state token, affected Scene/CUT/GEN/Asset range, and authorization fill/replace action.
- Missing exact media uses `AUTHORIZED-ASSET`; current user materials use `USER-SUPPLIED-ASSET`; neither is mislabeled as a rights-verified source.
- Rights status did not reject, truncate, or replace a requested screenplay/CUT/GEN/asset dependency. The complete creative and production delivery appears first.
- `版权出处与使用声明` is the final section, identifies known sources without guessing, and gives the user retain/authorize/replace choices.
- Planned named third-party use defaults to `rights-asserted`; it is never reported as independently verified. `rights-unverified` is used when the current brief does not assert a clearance plan; `rights-verified` names the inspected evidence and production-relevant scope.
- Public-source research records version, section/scene, speaker or lip-sync
  owner, line/turn/phrase/bar counts, capacity, entry/exit events, and dramatic
  function without treating public accessibility as permission.
- Missing lyrics, dialogue, subtitles, or screenplay text were not retrieved,
  reconstructed, or completed from model memory, snippets, search results, or
  an unverified public page.
- Missing lyrics use a full `AUTHORIZED-LYRIC` slot with section/phrase length
  basis, entry/exit event, lip-sync owner, and downstream fill map. Missing
  protected dialogue uses a full `AUTHORIZED-DIALOGUE` slot with speaker turns,
  line/character capacity, action or lip-sync mapping, entry/exit event, and
  downstream fill location. Both serialize through the active
  `【受保护文本填入表】`; the screenplay is not shortened around either slot.
- Direct-fill text slots use stable line/phrase/bar IDs and bind each structural
  unit to action, sound, lip-sync, and downstream placement. A
  `structure-pending` slot is honest but does not pass zero-rearrangement
  readiness.
- `AUTHORIZED-DIALOGUE` is not introduced for an original story fact unless the
  brief or inspected source establishes an external protected dependency.
- Exact protected text appears only as `USER-SUPPLIED-TEXT` or
  `RIGHTS-VERIFIED-SOURCE`; no fixed character cap is imposed on those sources,
  but use remains within the current task and recorded scope.
- Non-commercial use is not treated as automatic clearance; commercial released-recording plans address composition/sync and master rights or record the unresolved gap.
- Every named song includes a licensing path and an original or appropriately licensed alternative.
- Music, lyrics, source paths, and theme cards marked as post-production layers do not leak into downstream video-generation prompts.

## Release Gate

For production-lock or revision deliveries, run:

1. `scripts/preflight_revision.py` before writing when revision mode applies.
2. `scripts/validate_delivery.py` after writing with the delivery contract; revision contracts point `revision.impact_report_path` to the sidecar impact/residue report.
3. A semantic blind review for event naturalness, spoken dialogue, performance, viewpoint, and independent GEN usability.

Hard errors block release. Warnings require review but may pass when documented. Validators report only; they never rewrite canon.
When a named third-party dependency is present, the optional `rights` contract
checks that the final notice exists, is last, uses the declared state, and
contains required dependency/source tokens. Semantic review still decides
whether every actual clip, image, costume, prop, text, song, and recording was
covered.

The post-delivery command is:

```text
python scripts/validate_delivery.py --document DELIVERY.md \
  --contract CONTRACT.json --json-out VALIDATION.json
```

The portable contract shape is documented by `scripts/schemas/delivery-contract.schema.json`. Exit `0` passes, `1` reports constraint failures, and `2` reports parse failures.
