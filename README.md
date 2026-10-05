# 爆款编剧 Skill v7

当前版本：2026-10-06。安装入口为 [`viral-screenwriter/SKILL.md`](viral-screenwriter/SKILL.md)，支持标准中文 Markdown 剧本、人物与对白开发、分批续写、定点修订、参考片研究及按需分镜。每批最多交付2集正文；视频模型提示词通过独立的 `director-seedance-prompt` 协作。

## 安装当前版本

将本仓库的 `viral-screenwriter/` 整个目录复制到宿主技能目录，例如 `~/.codex/skills/viral-screenwriter/`。旧版先备份到技能目录之外，避免多个入口重复触发；刷新技能或重新打开会话后调用 `$viral-screenwriter`。

完整安装、媒体依赖及使用方式见 [INSTALL.md](viral-screenwriter/INSTALL.md)。当前包包含书库转写、方法卡、模板、来源索引和内置视频反推模块；书库按当前创作问题读取，不默认全量加载。第三方书籍及参考资料保留各自著作权与来源标识，不因仓库公开而赋予下游再发布或商业授权。

在 `viral-screenwriter/` 目录验证：

```text
python -X utf8 scripts/verify_portable.py
python -X utf8 scripts/check_environment.py --mode writing
```

本仓库保持公开可见，沿用 [LICENSE](LICENSE) 的使用及再发布限制。联系方式：MARIOZHAOFAN（微信）。

## 历史 Script Generator

`script-generator/` 保留为独立历史版本；其格式、校验及下列说明不作为新版 `viral-screenwriter` 的运行规则。安装新版无需同时安装旧入口。

Codex skill for turning rough story ideas, genre briefs, short-video prompts, episodic concepts, or storyboard requests into complete executable screenplays and synchronized per-CUT director storyboards.

Display name: 剧本生成器  
Skill folder: `script-generator`

## What It Does

- Expands loose story ideas into complete shootable screenplays followed by synchronized director-grade storyboards.
- Adds one screenplay-specific overall image-style prompt and one unified camera-movement prompt to every screenplay delivery.
- Produces scene/beat IDs and a detailed block for every CUT, including focal length, camera position, composition, focus, visual-focus/motion handoff, actor blocking, visible emotion, exact dialogue, sound, edit motivation, director intent, AI-readable visual facts, and continuity, without per-CUT durations or timecodes.
- Supports short videos, episodic unit drama, web-series bibles, and production-ready分镜剧本.
- Selectively strengthens character agency, power/advantage costs, opposing-force logic, fair strategic conflict, and payoff design when the brief needs them.
- Uses web and open-source research when current facts, trend references, dialect, BGM, named works, or project logic matter.
- Guards against style contamination: examples and test prompts do not become defaults.

## Installation

Copy the `script-generator` folder into your Codex skills directory:

```powershell
Copy-Item -Recurse .\script-generator $env:USERPROFILE\.codex\skills\
```

Then start a new Codex session and ask to use `$script-generator`.

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
