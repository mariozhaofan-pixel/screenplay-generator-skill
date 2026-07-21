---
name: script-generator
description: Turn a rough story idea, genre brief, reference work, meme premise, episode concept, or user demand into a complete executable screenplay with script-derived image-style and camera-movement prompts, followed by a synchronized director-grade per-CUT storyboard. Use when the user asks for short-video scripts, episodic unit dramas, scene-by-scene screenplays, shot lists, AI-video storyboards, dialogue with catchphrases, character or antagonist design, power-system conflict, strategic confrontation, web-series bibles, or production-ready分镜剧本 with focal length, staging, emotion, dialogue, camera, sound, editing logic, and director intent, especially when the task benefits from web research, open-source project research, trend/meme lookup, dialect/tone research, or adaptation of screenwriting workflows.
---

# 剧本生成器

## Core Behavior

Transform loose input into a shootable script, not just an outline. Every delivered screenplay must be followed by one copy-ready `整体影像风格` prompt and one copy-ready `统一运镜风格` prompt derived from that screenplay. A complete script request continues into a synchronized storyboard in which every edit is an explicit `CUT`; only an explicit screenplay-only request omits the CUTs while keeping both global prompts. Default to a complete working draft when the user asks for a test, sample, full script, or "直接生成"; use interactive checkpoints only when the user explicitly wants step-by-step development.

Use named reference works as high-level tonal or structural anchors only. Extract abstract traits such as pace, family chaos, social satire, handheld realism, or black-comedy density; do not copy specific plots, scenes, characters, or signature expression.

Never output a draft before an internal doctor pass. Remove psychological narration, over-explained dialogue, dead scenes, continuity breaks, unsupported trend claims, and shots that cannot be filmed.

## Load References

Read only the references needed for the current task:

- `references/shanyin-methodology-notes.md`: load for every substantive screenplay/storyboard task.
- `references/storyboard-output.md`: load whenever the user needs an executable script, shot list, storyboard, video prompt, or production table.
- `references/directing-and-shot-design.md`: load for every screenplay delivery because it defines the required global image/camera style prompts; also use it for shots, CUTs, camera direction, AI-video prompts, actor blocking, focal lengths, visual continuity, or director intent.
- `references/short-video-series.md`: load for short video, web-series, episodic unit drama, meme comedy, recurring character relationships, catchphrases, dialect, or BGM-heavy requests.
- `references/character-and-conflict-engine.md`: load when character identity, protagonist agency, a power/system/advantage, an opposing force, strategic conflict, suspense, reversal, or payoff is central. Activate only the relevant modules; do not invent a power or antagonist for briefs that do not need one.
- `references/open-source-research.md`: load when current facts, internet memes, platform conventions, dialect examples, BGM references, named works, or open-source project logic need research.
- `references/style-contamination.md`: load whenever a task references a prior example, named style, dialect, nickname rule, catchphrase density, or when output risks inheriting irrelevant test/example details.
- `references/quality-checks.md`: load before final output or when the user asks for self-check, revision, or "剧本医生".

## Workflow

1. Parse the brief.
   Identify target format, platform, audience, genre, style anchors, must-use elements, taboo elements, character relationship constraints, production limits, and output depth. Treat any user-provided runtime as a silent, approximate density signal only. Internally form a broad runtime suggestion when useful, but never output runtime, scene/CUT durations, timecodes, or per-beat time budgets in a screenplay or storyboard. If scope is unspecified, infer it from the story and platform rather than defaulting to a fixed number of seconds. Add a next-episode hook only for a series/episodic brief or when the user requests one. Derive CUT count from story beats, visual emphasis, and production needs rather than a duration formula or fixed range.

2. Research when useful.
   Search the web or inspect open-source projects when references may be current or specialized. Convert findings into decisions: tone, structure, language texture, BGM direction, meme bank, platform pacing, or production constraints. Cite sources in the final response when web sources are used.

3. Build the story engine.
   Reduce the episode to `protagonist want -> obstacle -> escalating choices -> cost -> irreversible choice/payoff`. When character identity, an advantage, an opposing force, or strategic conflict is central, select only the needed modules from `references/character-and-conflict-engine.md`. Make every major actor choose from the information and resources available at that moment. For unit drama, lock the recurring relationship matrix before writing the episode.

4. Create a compact show bible when the premise is episodic.
   Include series premise, fixed character roles, nicknames only when requested, running conflict, catchphrase rules only when requested, continuity ledger, and next-episode hook logic.

5. Plan the piece.
   For short video, open on a visible disturbance, conflict, strong question, or active decision before exposition unless the chosen form deliberately calls for a slower reveal. Place at least three strong lines when the user asks for "金句" density: one near the hook, one around a midpoint turn, and one near the climax/tag. Keep every scene tied to a visible action. Define each scene's dramatic task, meaningful change, audience alignment, key images, information hierarchy, and emotional turn before choosing camera coverage.

6. Write the screenplay.
   Write the complete scene action and exact dialogue before designing shots. Use stable scene and beat IDs. Specify only visible or audible events, including prop state changes and performance actions that drive the scene.

7. Derive the global visual grammar, director map, and detailed CUTs.
   First compile one global image-style prompt and one global camera-movement prompt from the finished screenplay's era, genre, locations, characters, emotional design, key images, platform, and production limits. Include this pair even when the user asks for a screenplay without a storyboard. When detailed shots are requested, lock each scene's geography, axis/screen direction, lighting and continuity, lens palette, key images, information reveal, visual-focus path, and dominant motion flow, then output every uninterrupted camera segment as one `CUT`. Each CUT must state scene and time of day when relevant, story change, characters and starting positions, blocking, visible emotion/performance, exact dialogue, 35mm-equivalent focal length, shot size, camera position/height/angle/distance, composition, movement, focus/depth plan, visual-focus and motion-vector handoff, sound, edit motivation, director intent, AI-readable visual facts, and continuity state. Do not add a duration or timecode. Split a CUT when the camera setup, story time/space, dominant action, or information task changes.

8. Reconcile screenplay and storyboard.
   Map every screenplay beat to one or more CUTs and every CUT back to one beat. Keep dialogue, visible actions, story results, and continuity states consistent across both surfaces. Bind sound and edit cues to observable events rather than timestamps, and remove camera blocks that add no story, emotion, information, rhythm, or continuity value.

9. Run the doctor pass internally.
   Check visuality, qualitative rhythm, lens and spatial logic, blocking, edit motivation, dialogue/CUT synchronization, AI-video executability, joke/catchphrase density when requested, dialect consistency when requested, production feasibility, research grounding, continuity, and contamination from irrelevant examples. Silently correct obvious scope-density mismatches, then confirm the deliverable contains no runtime, duration, timecode, or per-beat timing output.

## Output Routing

For a complete screenplay-and-storyboard request, follow the single canonical deliverable schema in `references/storyboard-output.md`. A screenplay-only request still includes the two global style prompts immediately after the screenplay. If the user requests only an outline, bible, scene list, dialogue polish, research summary, or doctor pass, output only that artifact. Do not expose internal workflow notes, runtime judgment, or quality-check reasoning unless the user explicitly requests a diagnostic report.
