# Dialogue, Performance, and Synchronization

Use this reference for complete screenplays, dialogue rewrites, actor-facing revisions, production locks, exact line counts, downstream prompt compilation, and canon revisions. This file owns natural speech, subtext, playable performance, stable dialogue IDs, and three-layer dialogue synchronization.

## Contents

- Authority and operating modes
- Dialogue as immediate action
- Natural speech and cold-read checks
- Playable performance and crying
- Stable D-IDs and text categories
- Screenplay, CUT, and lock-table projections
- Revision and validation rules

## Authority and Operating Modes

The complete screenplay is the sole dialogue authority. CUT text and the complete dialogue-lock table are derived projections and must never be edited independently.

Use two modes:

- `draft-sync`: keep IDs and projection checks internal; do not print a lock table unless requested.
- `production-lock`: print stable D-IDs and the complete lock table for production-grade scripts, exact line counts, canon revision, or downstream prompt compilation.

When a production-locked line changes, update the screenplay authority first, then regenerate every CUT fragment and lock-table row.

## Dialogue as Immediate Action

Before writing a key line, identify its present-tense language action:

`delay | deflect | deny | seek confirmation | interrupt | bargain | test | conceal | assign blame | transfer responsibility | invite | refuse | release`

The character speaks to change what the other person does, knows, permits, or feels now. Do not let the line become an author's summary of the theme, relationship, backstory, or the speaker's personality.

A directive, condition, question, or bargain must precede and trigger the visible result it seeks. If the result has already happened, the line must perform a new action such as confirm, challenge, refuse, or reinterpret it; do not restate an instruction after the system or person has already complied.

For strategic or high-pressure dialogue, record internally:

`surface text | language action | withheld fact | leverage | expected response | actual response | status change`

## Natural Speech and Subtext

- High-context relationships may omit names, causes, and objects both people already know.
- Allow pronouns, short clauses, unfinished lines, interruption, self-correction, repetition under pressure, and strategic silence.
- Do not make a character accurately summarize their own flaw, complete every causal chain, or verbalize all subtext.
- Shared facts should remain implicit unless one character is reframing, challenging, denying, or weaponizing them.
- Exposition must have a current tactic: prove, warn, recruit, defend, shame, negotiate, or correct.
- Distinguish character cadence without relying on catchphrases, dialect caricature, or constant sentence fragments.

## Cold-Read Checks

Read each important line aloud and ask:

1. Would an actor instinctively rewrite it to say it naturally?
2. Can it be spoken in one believable breath pattern?
3. Can shared information be removed without losing clarity?
4. Does the line alter the other person's action, response, or relationship state?
5. Is the intended subtext visible from context and performance without explanation?
6. In a hard timing contract, can the line, its indispensable trigger, the other person's readable reaction, and the next handoff fit naturally without rushed delivery?

If the answer fails, rewrite the line before adding more performance direction.

## Playable Performance

For each key line and meaningful silent reaction, use:

`start state -> trigger -> breath/volume/rate -> one primary eyeline or body action -> after-reaction/end state`

- Choose one dominant playable action. Do not stack looking down, hair touching, lip biting, hand clenching, trembling, and long eye contact as an emotion menu.
- Use breath, volume, rate, articulation, interruption, posture, distance, task behavior, and one eyeline target to make change playable.
- Avoid abstract directions such as "painful", "restrained", "regretful", or "devastated" without visible or audible execution.
- Do not prescribe centimeters, degrees, frames, or micro-timing unless the task is in `media-frame-lock`.
- Under a hard GEN ceiling, identify which actions cannot overlap the line or reaction. Keep one primary action and one readable after-reaction; trim optional breath, gaze, and hand-detail menus before compressing speech.

Crying is a process:

`attempt to hold -> breath breaks or voice fails -> tear/sound appears -> attempt to recover or continue`

Do not replace this progression with a single instruction such as "cries hard".

## Stable D-IDs and Text Categories

In `production-lock`, assign every audible story-dialogue line a stable sequential ID: `D-001`, `D-002`, and so on. Preserve an ID when the same canonical line remains; create or retire IDs explicitly during revision rather than silently reusing them for different text.

Use separate IDs or categories for non-dialogue text:

- `D-ID`: audible story dialogue only
- `LYR-ID`: lyric subtitle or sung lyric
- `CARD-ID`: theme/title card
- `TXT-ID`: ordinary screen text, signage, chat, or interface text

Only `D-ID` rows count toward the story-dialogue total.

Canonical screenplay line format in production-lock mode:

```text
**D-001 | 角色 | 画内 | 口型=角色：** 逐字对白。
```

Use `画外`, `VO`, or `旁白` when the sound source is not a visible speaking mouth. Use `口型=无` when no visible mouth must synchronize.

If one line crosses CUTs and its visibility changes, preserve one D-ID and record ordered technical maps:

```text
**D-001 | 角色 | 画内@1/2；画外@2/2 | 口型=角色@1/2；无@2/2：** 完整逐字对白。
```

The suffixes describe derived fragment order, not new dialogue text. A single-fragment line keeps the compact form.

## Three-Layer Projection

### Layer 1: complete screenplay

Stores the authoritative speaker, exact text, punctuation, order, sound mode, and lip-sync subject.

### Layer 2: CUT audible fragments

Under the CUT's `台词/字幕` field, write one derived entry per fragment:

```text
  - D-001[1/2] | 剧情对白 | 角色 | 画内 | 口型=角色 | 文本=前半句
  - D-001[2/2] | 剧情对白 | 角色 | 画外 | 口型=无 | 文本=后半句。
```

Ordered fragments must concatenate exactly to the screenplay text, including punctuation. Do not repeat the complete line in every CUT and do not write `接上`.

### Layer 3: complete dialogue-lock table

Output only in production-lock mode:

```text
| D-ID | 类别 | 角色 | 逐字文本 | 声源 | 口型对象 | CUT/片段 |
|---|---|---|---|---|---|---|
| D-001 | 剧情对白 | 角色 | 逐字对白。 | 画内 | 角色 | CUT-001[1/1] |
```

The table is a verification manifest, not a second writing surface.

For a multi-CUT line, keep one row and write ordered maps in `声源`, `口型对象`, and `CUT/片段`, for example `画内@1/2；画外@2/2`, `角色@1/2；无@2/2`, and `CUT-001[1/2]；CUT-002[2/2]`.

## Revision and Validation

Compare all three layers for:

- ID continuity and uniqueness
- speaker
- exact text and punctuation
- line order
- on-screen/off-screen/VO status
- lip-sync subject
- CUT and fragment mapping
- category counts

A mismatch is a hard production error. Fix the authoritative screenplay or regenerate its projections; never make independent compensating edits in CUTs or the lock table.
