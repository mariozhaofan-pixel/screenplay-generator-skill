---
name: script-generator
description: Turn a rough story idea, genre brief, existing canon, revision request, or production contract into a complete executable screenplay with script-derived visual-style prompts and a synchronized director-grade 14-field per-CUT storyboard. Use for short-video scripts, episodic drama, dialogue/performance rewrites, screenplay doctoring, canon-safe version revisions, exact dialogue locks, hard runtime or media/frame contracts, CUT-to-GEN production maps, AI-video storyboards, asset/scene-master continuity, strategic conflict, and research-backed screenwriting workflows.
---

# 剧本生成器

## Core Behavior

Transform loose input into a shootable script, not just an outline. Test the event before polishing dialogue: major changes must arise from character choice, visible response, and a credible new state rather than a convenient accident or a third party doing the relationship work.

Every delivered screenplay must be followed by one copy-ready `整体影像风格` prompt and one copy-ready `统一运镜风格` prompt derived from that screenplay. A complete script request continues into a synchronized storyboard in which every edit is an explicit `CUT`; only an explicit screenplay-only request omits CUTs while keeping both prompts. The default CUT schema has 14 fields, including a separate viewpoint/knowledge-boundary field.

Respect explicit production contracts. Default timing remains silent, but a user-provided hard budget or generation limit must be shown and validated; `media-frame-lock` must use measured source values. Keep editorial CUTs separate from model-generation `GEN` units.

Never overwrite a named canon or occupied version. Derive CUT text, dialogue locks, GEN maps, asset registries, and downstream handoffs from their authoritative screenplay/version sources.

When a named work is only a style/reference anchor, use `trait-reference` and
transfer abstract tonal, structural, or visual mechanisms. When the current
brief explicitly requests a recreation or exact third-party dependency, use
`exact-dependent`, preserve the full production slot, and route source/status
facts to the final rights notice. Do not invent missing exact expression from
memory. Default to a complete working draft for "直接生成", tests, and samples;
use checkpoints only when requested or when canon/production stage boundaries
require approval.

## Load References

Read only the references needed for the current task:

- `references/terminology-and-portability.md`: load for every substantive task; it locks canonical machine terms, condition triggers, ambiguity boundaries, and cross-model/cross-computer behavior.
- `references/shanyin-methodology-notes.md`: load for every substantive screenplay/storyboard task.
- `references/event-authenticity-and-callbacks.md`: load before writing or revising any major event; also use for behavior callbacks and repeated-event identity.
- `references/dialogue-performance-and-sync.md`: load for complete screenplays, dialogue or performance work, production locks, exact line counts, and downstream dialogue compilation.
- `references/timing-and-generation-units.md`: load for every complete screenplay/storyboard task; it alone selects timing mode and defines CUT/GEN separation.
- `references/revision-canon-and-impact.md`: load when an existing source, canon, version, locked draft, or downstream production range is being revised.
- `references/asset-and-scene-master-locks.md`: load when assets, reference images, scene plates, approved frames, paths, wardrobe periods, or downstream production handoffs are involved.
- `references/storyboard-output.md`: load for every executable script, shot list, storyboard, GEN map, dialogue lock, or production table; it is the only output-schema owner.
- `references/directing-and-shot-design.md`: load for every screenplay delivery and all CUT, viewpoint, transition, camera, focal-length, blocking, continuity, or director-intent work.
- `references/short-video-series.md`: load for short video, web-series, episodic unit drama, meme comedy, recurring character relationships, catchphrases, dialect, or BGM-heavy requests.
- `references/character-and-conflict-engine.md`: load when character identity, protagonist agency, a power/system/advantage, an opposing force, strategic conflict, suspense, reversal, or payoff is central. Activate only the relevant modules; do not invent a power or antagonist for briefs that do not need one.
- `references/open-source-research.md`: load when current facts, internet memes, platform conventions, dialect examples, BGM references, named works, or open-source project logic need research.
- `references/style-contamination.md`: load for unrelated example/style leakage. Route stale canon residue to the revision owner instead.
- `references/quality-checks.md`: load before every final output; it validates but does not redefine owner rules.

## Workflow

1. Parse the brief.
   Identify format, platform, audience, genre, style anchors, must-use material, inspiration-only material, excluded/post-only material, character constraints, production limits, and output depth. Freeze a current-brief contract before drafting: every mandatory premise, character objective, relationship, event, and deliverable must map to the screenplay or its production surfaces; do not substitute a different but well-executed premise.

2. Select operating modes and protect sources.
   Select one timing mode from `timing-and-generation-units.md`; activate revision, production dialogue lock, GEN mapping, and asset/SCN locking only when their triggers apply. Before drafting, copy the literal mode lines, section labels, CUT field labels, and registry columns from `storyboard-output.md`; treat them as protocol symbols, not prose to paraphrase. In revision mode, run preflight before writing, read the complete source, preserve its hash, and allocate an unused output version.

3. Test event authenticity.
   Run the event-first gate before dialogue polish. Replace contrived coincidence, humiliation, proxy action, or plot-bearing props when ordinary character choice and visible response can preserve the intended change with equal causal clarity and fewer arbitrary assumptions. For every decisive clue, lock origin, insertion/availability, custody/access, visible setup, reveal trigger, permitted inference, changed choice, and payoff; sealed or hidden objects also need a credible physical mechanism. Register EVT callbacks when repeated events change meaning.

4. Research only when `terminology-and-portability.md` activates the `research`
   trigger.
   Search the web or inspect open-source projects when references may be current or specialized. Convert findings into decisions: tone, structure, language texture, BGM direction, meme bank, platform pacing, or production constraints. Named third-party dependencies proceed under `rights-asserted` by default; rights status does not reject or shorten the requested screenplay. Cite sources in the final response when web sources are used.

5. Build the story engine.
   Reduce the episode to `protagonist want -> obstacle -> escalating choices -> cost -> irreversible choice/payoff`. When character identity, an advantage, an opposing force, or strategic conflict is central, select only the needed modules from `references/character-and-conflict-engine.md`. Make every major actor choose from the information and resources available at that moment. For unit drama, lock the recurring relationship matrix before writing the episode.

6. Plan scenes and production constraints.
   Define each scene's task, meaningful change, audience alignment, key images, information hierarchy, event identity, emotional turn, and required Asset/SCN state. For episodic work, maintain the series ledger. For a hard timing contract, require both arithmetic closure and a GEN/scene-level natural read/act feasibility ledger; never repair overload by timing every CUT.

7. Write and doctor the authoritative screenplay.
   Write visible/audible action and exact dialogue with stable scene/beat IDs. Apply language-action, cold-read, subtext, playable emotion, and micro-action checks. In production-lock mode, assign stable D-IDs; treat the screenplay as the sole dialogue authority.

8. Derive global visual grammar, director maps, and 14-field CUTs.
   Compile the two screenplay-specific global prompts first. Then lock geography, viewpoint legality, responsibility shots, transition phase, axis/screen direction, lighting, lens palette, information reveal, blocking, and continuity. Emit the canonical 13-field director map for every scene represented by CUTs. Every CUT uses the canonical 14-field schema in `storyboard-output.md`; CUTs remain editorial units, not generation prompts.

9. Build derived production maps and propagate changes.
   Map beats to CUTs; when the GEN trigger in `terminology-and-portability.md` is active, package CUTs into GEN units with a local visible trigger and complete cold-start IN state. Regenerate CUT dialogue fragments and the conditional dialogue-lock table, resolve active Asset/SCN and causal screen-state layers, and update active timing contracts. In revision mode, use the impact matrix and scan every affected surface for stale facts and paths.

10. Validate and deliver.
   Run owner-aware quality checks and the deterministic validators when their modes apply. Require dialogue/CUT/lock equality, ID closure, timing-mode compliance, GEN limits, canon non-overwrite, residue clearance, viewpoint legality, and Asset/SCN closure. Deliver the complete screenplay and production surfaces first; place any third-party source, rights status, and user choice notice in the final `版权出处与使用声明`. Keep detailed audit findings in a sidecar report rather than contaminating the canon.

## Output Routing

For any screenplay delivery, follow the single canonical schema in `references/storyboard-output.md`. Include only the mode-conditional sections that apply. A screenplay-only request still includes both global style prompts. Outline, bible, research, dialogue-polish, and doctor-only requests remain scoped to the requested artifact. Do not expose internal reasoning; output contract, revision, or validation evidence only when the active mode or user request requires it.
