---
name: screenplay-generator
description: Turn a rough story idea, genre brief, reference work, meme premise, episode concept, or user demand into an executable screenplay and storyboard script. Use when the user asks to expand simple story requirements into short-video scripts, episodic unit dramas, scene-by-scene screenplays, shot tables, dialogue with catchphrases, web-series bibles, or production-ready分镜剧本, especially when the task benefits from web research, open-source project research, trend/meme lookup, dialect/tone research, or adaptation of screenwriting workflows.
---

# 剧本生成器

## Core Behavior

Transform loose input into a shootable script, not just an outline. Default to a complete working draft when the user asks for a test, sample, full script, or "直接生成"; use interactive checkpoints only when the user explicitly wants step-by-step development.

Use named reference works as high-level tonal or structural anchors only. Extract abstract traits such as pace, family chaos, social satire, handheld realism, or black-comedy density; do not copy specific plots, scenes, characters, or signature expression.

Never output a draft before an internal doctor pass. Remove psychological narration, over-explained dialogue, dead scenes, continuity breaks, unsupported trend claims, and shots that cannot be filmed.

## Load References

Read only the references needed for the current task:

- `references/shanyin-methodology-notes.md`: load for every substantive screenplay/storyboard task.
- `references/storyboard-output.md`: load whenever the user needs an executable script, shot list, storyboard, video prompt, or production table.
- `references/short-video-series.md`: load for short video, web-series, episodic unit drama, meme comedy, recurring character relationships, catchphrases, dialect, or BGM-heavy requests.
- `references/open-source-research.md`: load when current facts, internet memes, platform conventions, dialect examples, BGM references, named works, or open-source project logic need research.
- `references/style-contamination.md`: load whenever a task references a prior example, named style, dialect, nickname rule, catchphrase density, or when output risks inheriting irrelevant test/example details.
- `references/quality-checks.md`: load before final output or when the user asks for self-check, revision, or "剧本医生".

## Workflow

1. Parse the brief.
   Identify target format, duration, platform, audience, genre, style anchors, must-use elements, taboo elements, character relationship constraints, and output depth. If unspecified, default to a 60-120 second short-video episode with a cold open, 5-9 shots, and at least one episode hook.

2. Research when useful.
   Search the web or inspect open-source projects when references may be current or specialized. Convert findings into decisions: tone, structure, language texture, BGM direction, meme bank, platform pacing, or production constraints. Cite sources in the final response when web sources are used.

3. Build the story engine.
   Reduce the episode to `protagonist want -> obstacle -> escalation -> irreversible choice/payoff`. For unit drama, lock the recurring relationship matrix before writing the episode.

4. Create a compact show bible when the premise is episodic.
   Include series premise, fixed character roles, nicknames only when requested, running conflict, catchphrase rules only when requested, continuity ledger, and next-episode hook logic.

5. Plan the episode.
   Use a cold open in the first 3-5 seconds. Place at least three strong lines when the user asks for "金句" density: one in the hook, one at the midpoint reversal, one in the climax/tag. Keep every scene tied to a visible action.

6. Produce the executable draft.
   Output a beat sheet, then a shot table with time, camera/framing, action, dialogue/subtitles, sound/BGM/SFX, transition, props, and continuity notes. Add a formatted script if the user needs dialogue in screenplay form.

7. Run the doctor pass internally.
   Check visuality, rhythm, duration, joke/catchphrase density when requested, dialect consistency when requested, production feasibility, research grounding, continuity, and contamination from irrelevant examples. Repair before finalizing.

## Default Output Order

For a complete short-video/storyboard request, output:

1. `创作假设`
2. `系列设定/人物关系`
3. `本集Logline`
4. `关键台词/金句银行（按用户需求输出；未要求金句时可省略或改为关键对白）`
5. `分镜表`
6. `对白剧本`
7. `BGM/声音方案`
8. `连续性与下一集钩子`
9. `自检修复摘要`

If the user requests only an outline, bible, scene list, dialogue polish, research summary, or doctor pass, output only that artifact.
