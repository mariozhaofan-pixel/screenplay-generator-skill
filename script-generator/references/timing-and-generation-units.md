# Timing Modes and Generation Units

Use this reference for every complete screenplay/storyboard task to select a timing mode. It is the sole owner for runtime rules, hard production budgets, measured media/frame locks, CUT versus GEN semantics, and generation-unit packing.

## Contents

- Mode selection and precedence
- Default-silent mode
- Contract-budget mode
- Media/frame-lock mode
- Planned versus measured truth
- CUT and GEN definitions
- GEN types, fields, and packing
- Dialogue/action feasibility and trimming

## Mode Selection and Precedence

Select exactly one mode:

| Mode | Trigger | Output behavior |
|---|---|---|
| `silent-default` | No explicit numeric production contract and no measured media lock | Keep scale judgment internal; output no runtime, seconds, timecodes, or duration arithmetic |
| `contract-budget` | User explicitly gives a total target/maximum, scene/sequence budget, model generation limit, or asks for a numeric feasibility plan | Output only the contract and budget detail needed to prove compliance |
| `media-frame-lock` | User supplies real audio/video/frames or explicitly requests exact edit synchronization | Read real media and output only measured fields requested by the contract or required to perform the synchronization |

An explicit current-user contract overrides default silence. Never reinterpret a hard maximum as a soft suggestion.

## Default-Silent Mode

- Infer only broad scale and density internally.
- Do not print total runtime, scene/CUT/GEN seconds, timecodes, frame numbers, timing budgets, or arithmetic checks.
- Describe pace with event order, escalation, interruption, breath, acceleration, reversal, and release.
- Derive CUT and GEN structure from story, viewpoint, action continuity, and production needs rather than a duration formula.

## Contract-Budget Mode

Output a compact contract block:

```text
【时长与生成合同】
- 模式：contract-budget
- 合同来源：用户明确要求
- 总目标/上限：
- GEN 单元上限（如有）：
- 预算性质：生产计划值，不是实测成片时长
```

Then output only the necessary budget table:

```text
| GEN/场景 | CUT范围 | 计划预算 | 显式上限 | 对白/动作可行性 |
```

Rules:

- Prefer GEN budgets when a generation-unit limit exists; otherwise use the smallest set of scene/sequence budget rows whose arithmetic proves the declared total or bound.
- Do not mechanically assign seconds to every CUT.
- Use decimal arithmetic and show one sum check against the explicit target or maximum.
- Pass two independent checks: arithmetic closure and performability. A correct sum does not prove the scene can be spoken, acted, read, and handed off inside the ceiling.
- For every budget row, format `对白/动作可行性` as:
  `D-ID=...；自然读演=实测桌读或保守估读；不可并行=...；允许重叠=...；冷启动/反应余量=...；结论=PASS/FAIL`.
- `自然读演` may use a planned range at GEN/scene level when no recorded table read exists, but must be labeled as an estimate. Do not invent measured precision.
- Check spoken-text load, required breath, sequential non-overlappable actions, readable reaction, transition, and cold-start/hand-off needs.
- A budget is a production allocation, not a claim that prose predicts the final measured edit.
- If the contract is infeasible, revise content or report the conflict; do not hide the overage.
- Never fix an overloaded GEN by assigning numeric durations to every CUT. Remove, merge, overlap, or move story work until the GEN-level rehearsal ledger passes.

## Media/Frame-Lock Mode

- Inspect the supplied media instead of estimating its duration.
- Record source path or media ID, measured duration, frame rate/timebase, and measurement method.
- Use timecodes, frame numbers, waveform anchors, or action phase only for the affected CUT/GEN/edit surface.
- Keep measured values separate from planned budgets.
- Do not invent frame precision for media that was not supplied or inspected.
- A script may still contain untimed sections; exactness is local to the locked media contract.

## Planned Versus Measured Truth

Label numeric timing facts:

- `planned_budget`: a production allocation or maximum
- `measured_media`: read from real media
- `derived_check`: arithmetic using contract or measured inputs

Never label a planned budget as measured final runtime.

## CUT and GEN Definitions

- `CUT`: one uninterrupted camera segment between edits.
- `GEN`: one model-generation production unit. It may contain one CUT or several ordered CUTs.
- `SEG`: accepted only as an input alias; normalize final output to `GEN`.

A new generation prompt or changed model state does not by itself create a new CUT. Remove any rule that splits a CUT merely because a separate prompt is needed.

Start a new CUT when camera setup/viewpoint, story time/location, dominant subject/action, information task, independent insert/reaction, or the edit itself changes.

Start a new GEN when the production unit needs a new cold start, exceeds an explicit model limit, changes incompatible assets or space, cannot preserve causal continuity, or needs an independently reviewable output.

## GEN Types and Fields

Use:

- `narrative GEN`: contains a causal micro-unit.
- `supporting GEN`: a necessary environment, insert, transition plate, or technical unit that cannot carry a character choice.
- `transition GEN`: crosses time/space only because the transition itself is the unit's primary story task.

For every GEN, record:

```text
GEN-ID | type | CUT range | causal/story task | trigger | choice/action |
visible response | new end state | scene/time change | viewpoint sequence |
dialogue load/D-IDs | ASSET/SCN IDs | IN state | OUT state
```

In contract modes, add planned budget and explicit maximum in the separate contract table rather than changing CUT fields.

`触发` must become visible inside the GEN's opening CUT; a prior GEN's final line is context, not a self-sufficient local trigger. `IN状态` must be a complete cold-start package: character positions and facing, hands/props, exact story/UI states, active Asset/SCN IDs, and the causal fact the audience needs. It must allow the unit to be rebuilt without copying the previous GEN's pixels.

When exact screen text, UI animation, state ordering, signatures, or indicators carry causality, list their locked Asset/state IDs and mark them for controlled post/screen replacement. Do not make a video model invent decisive evidence.

## Packing Rules

- Pack by causal and production coherence, not one CUT per prompt.
- A narrative GEN should contain `trigger -> choice/action -> visible response -> new end state`.
- Merge inserts, reactions, and brief establishing information into the surrounding causal GEN when they rely on the same assets and state.
- A supporting GEN must state its indispensable function plus a valid IN/OUT handoff; do not create it merely for atmosphere.
- A cross-time or cross-space transition GEN must cold-start clearly and leave a complete, reusable end state.
- Record the ordered viewpoint sequence when one GEN contains several CUTs.
- Keep dialogue load within the model and performance contract; do not compress speech until it becomes unplayable.
- Every GEN must be independently reviewable without inventing identity, space, asset, or end-state facts.
- A hard-contract GEN fails when natural speech plus non-overlappable actions and readable reactions exceed its ceiling, even if its budget table adds up.

## Feasibility and Trimming

Before squeezing actions into a contract:

1. delete repeated confirmation
2. delete replay that adds no changed meaning
3. delete explanation already visible in action
4. delete empty establishing coverage
5. delete duplicated reaction
6. simplify competing actions inside the same GEN

Preserve causal choice, visible response, dialogue intelligibility, and handoff state. Never fill unused budget with empty shots, slow motion, or repeated action.
