# 剧本生成器（Script Generator Skill）

Codex skill for turning rough story ideas, genre briefs, short-video prompts, episodic concepts, or storyboard requests into complete executable screenplays and synchronized per-CUT director storyboards.

Display name: 剧本生成器  
Skill folder: `script-generator`

## What It Does

- Expands loose story ideas or canon-safe revision requests into complete shootable screenplays followed by synchronized director-grade storyboards.
- Runs an event-authenticity gate before dialogue polish so decisive beats arise from character choice and visible response; decisive clues also require provenance, custody, legal character knowledge, and credible hidden/sealed-object physics.
- Doctors natural speech, subtext, breath, micro-action, and playable emotional transitions; production-lock mode synchronizes authoritative screenplay dialogue, CUT fragments, and the complete dialogue lock.
- Adds one screenplay-specific overall image-style prompt and one unified camera-movement prompt to every screenplay delivery.
- Produces one strict 13-field director map per screenplay scene and the canonical 14-field block for every CUT, including a separate viewpoint/knowledge-boundary field, focal length, camera position, composition, focus, visual-focus/motion handoff, actor blocking, visible emotion, exact dialogue, sound, transition phase, director intent, AI-readable visual facts, and continuity. Historical 12-field input is compatibility-only.
- Separates editorial CUTs from model-generation GEN units and packs GENs by causal/production coherence rather than one prompt per CUT.
- Supports three timing modes: silent by default, explicit hard production contracts, and measured media/frame locks. Even hard contracts keep numeric budgets out of individual CUT fields.
- Protects source canon and occupied version lanes, builds revision impact matrices, scans stale story/asset residue, and keeps affected downstream work paused until re-baselined.
- Registers authoritative Asset/SCN IDs, enforces one scene-space master per continuous event, and keeps songs, lyrics, audio paths, and theme cards in the post-production layer.
- Supports short videos, episodic unit drama, web-series bibles, and production-ready分镜剧本.
- Selectively strengthens character agency, power/advantage costs, opposing-force logic, fair strategic conflict, and payoff design when the brief needs them.
- Uses web and open-source research when current facts, trend references, dialect, BGM, named works, or project logic matter.
- Keeps explicit third-party film, character/likeness, costume, prop, dialogue,
  music, lyric, and recording dependencies in the complete production plan under
  `rights-asserted` by default; missing exact material receives full
  `AUTHORIZED-ASSET`/`AUTHORIZED-LYRIC`/`AUTHORIZED-DIALOGUE` slots with
  structure and downstream maps, while source and use choices are disclosed
  only in the final rights notice.
- Guards against style contamination: examples and test prompts do not become defaults.
- Includes independent pre-write and post-delivery validators for version protection, scene-director-map/CUT schema, dialogue/timing/GEN/viewpoint/asset closure, and deterministic sidecar reports.
- Locks ambiguous Chinese/English production terms, module triggers, and path/model capability boundaries so the same package behaves consistently across supported models and computers.

## Installation

Copy the `script-generator` folder into your Codex skills directory:

```powershell
Copy-Item -Recurse .\script-generator $env:USERPROFILE\.codex\skills\
```

Then start a new Codex session and ask to use `$script-generator`.

The optional report-only validators require Python 3.10 or newer and otherwise
use only the standard library. `media-frame-lock` duration cross-checks also use
`ffprobe` when it is installed; absence is reported rather than fabricated.

## Usage Example

```text
Use $script-generator to turn this premise into a vertical short-video storyboard:
A night-shift convenience-store clerk discovers every customer is buying the same item for different secret reasons.
```

## Source and Attribution

This skill was built from original workflow design plus research into the open-source MIT-licensed project:

- `Shanyin-ai/shanyin-screenwriting-master`

The source project contributed high-level screenwriting workflow ideas such as format routing, visual writing discipline, self-checks, pacing, and continuity management. This repository does not copy the source project's long-form prompt text.

The character-and-conflict engine was also refined through an authorized local study of 26 public craft videos by [田老师写作力](https://www.douyin.com/user/MS4wLjABAAAAAZwNpcWrxcCm1JcNKqjlHywZj7RtbkuKGN1hicElUxGilV9xZ__oKK_vhBFRTt2l), covering the public collections [金手指哲学](https://www.douyin.com/collection/7658852716386453567/1), [主角哲学](https://www.douyin.com/collection/7655611524052060186/1), [反派哲学](https://www.douyin.com/collection/7655609940928825371/1), and [智斗三部曲](https://www.douyin.com/collection/7613582181931157513/1). Only original, generalized craft rules are included here. Downloaded media, audio, transcripts, OCR evidence, source examples, and source slogans are not redistributed in this repository.

The director and per-CUT storyboard workflow was further refined through a local study, requested by the user, of three publicly shared videos by `老白的分镜`: [AI 视频为什么要学分镜](https://v.douyin.com/_ky9SDY7Z7k/), [分镜课合集（上）](https://v.douyin.com/GIO1uzY2WL8/), and [分镜课合集（下）](https://v.douyin.com/J062jOxJXRg/). The study covered reverse coverage, action axes, perspective, primary shots (`主镜`), deriving camera positions from target images, shot size, camera height, composition, visual focus, spatial clarity, movement, intentional axis crossing, viewpoint, and information control. Only generalized original rules are published; source media are not included or redistributed, and derived research artifacts remain outside this repository.

Lens-format and angle-of-view conventions were cross-checked against official [ARRI](https://www.arri.com/en/learn-help/learn-help-camera-system/frequently-asked-questions/alexa-lf-faq), [Sony](https://www.sony.com/electronics/support/articles/00268239), and [Canon](https://files.canon-europe.com/files/webcontent/rf-lens-world/knowledge/perspective/index.html) documentation.

## Copyright and Usage Restrictions

Copyright (c) 2026 MARIOZHAOFAN. All rights reserved unless explicitly granted in writing.

This repository is published for visibility, review, learning, and authorized personal/internal use. It is not a grant to repackage, redistribute, resell, sublicense, or use this project as the core component of a commercial product or paid service.

You may:

- Read and study the source files.
- Use the skill for personal learning, private testing, or internal non-commercial workflows.
- Link to this original GitHub repository with attribution.

You may not, without prior written permission:

- Republish, mirror, redistribute, or repackage this project or substantial parts of it.
- Sell this project, bundle it into a paid product, or use it as the core component of a commercial service.
- Remove copyright notices, attribution, or usage restrictions.
- Claim authorship of this project or a lightly modified copy.

For redistribution, commercial use, paid deployment, licensing, or partnership requests, contact:

- WeChat: `MARIOZHAOFAN`

See `LICENSE` for the full usage terms.
