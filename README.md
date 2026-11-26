# 爆款编剧 Skill v20

当前版本：2026-11-27 v20，提供**本地版**和**飞书版**。两版共用一套自写编剧方法卡和视频反推模块，不含任何书的全文。剧本始终交付 Markdown，每批最多2集；开场带剧情介绍、钩子与记忆锚点，视频模型提示词按需交给使用者已安装的导演skill。

| 安装版本 | 工作方式 | ZIP文件名 |
|---|---|---|
| 本地版 | 直接在用户项目工作，不询问飞书模式、不登录或部署飞书；通过本地采用稿与导演协作 | `viral-screenwriter_v20_local_2026-11-27.zip` |
| 飞书版 | 保留本地、加入已有多维表或创建新库的选择；飞书模式按需接入，定稿与采用修订同步同一项目 | `viral-screenwriter_v20_feishu_2026-11-27.zip` |

两包都以 `viral-screenwriter/` 为唯一技能根目录，技能名均为 `viral-screenwriter`；每台宿主只安装一版。相同名称保持导演的技能发现兼容，切换版本只替换技能目录，不删除或重建用户项目。普通写作不要求安装导演技能，只有实际交接视频提示词时读取对方当前入口。

更新记录见 [docs/CHANGELOG.md](docs/CHANGELOG.md)。

## 安装

从 [Releases](https://github.com/mariozhaofan-pixel/screenplay-generator-skill/releases) 选择对应版的技能ZIP，解压后把 `viral-screenwriter/` 放到所用宿主的技能目录，支持上传的宿主可直接上传ZIP。旧版先完整备份到技能目录之外，避免旧文件残留或双入口重复触发，再刷新技能或重新打开会话。

直接复制本仓库的 [`viral-screenwriter/`](viral-screenwriter/SKILL.md) 得到的是**飞书版完整维护源**。本地版须使用对应发行ZIP，或按下方命令从同一源构建，不能只复制入口而遗漏其本地交接规则。

两版包含全部方法卡、模板和内置视频反推模块；媒体依赖仅在实际视频任务缺少能力时准备。完整使用说明随各包的 `INSTALL.md` 一起生成。[仓库内安装说明](viral-screenwriter/INSTALL.md)对应飞书版。

安装后在 `viral-screenwriter/` 中可检查：

```text
python -X utf8 scripts/verify_portable.py
python -X utf8 scripts/check_environment.py --mode writing
```

本仓库保持公开可见，沿用 [LICENSE](LICENSE) 的使用及再发布限制。方法卡引用的书籍著作权归原作者和出版方，包内不含书的全文。联系方式：MARIOZHAOFAN（微信）。

## 两版与导演协作

本地版把 `workspace_mode=local`、用户项目目录、当前采用稿路径/版本、集场范围、授权边界与已有资产交给导演；已有本地选择直接沿用。格式整理、修改意见、采用稿和视频提示词分别保存，改稿只影响实际依赖的导演产物，不自动重编全项目。

飞书版：编剧与导演复用同一 Base 和项目ID，按项目总览、剧本交付、资产库、段落交付四表组织材料。先复用已授权连接，缺环境时读取[配置指引](viral-screenwriter/references/FEISHU_WORKSPACE_SETUP.md)。本地保存检查和云端读回分别核验；新库的分享默认与用户权限限制沿现有合同。包内不含飞书CLI、凭据或登录会话，首次接入仍由实际平台权限决定。见[同步合同](viral-screenwriter/references/FEISHU_SCREENPLAY_SYNC.md)。

## 单一维护源与双版本构建

后续只在 `viral-screenwriter/` 维护共同编剧能力，不复制出第二份可编辑源。`tools/edition_rules.json` 仅保存本地版必须替换的工作区/UI/交接文字和6个飞书专用文件的排除清单；打包器从同一维护源生成两个独立完整安装包，产物不作为第二维护源。

自 v20 起包内只有自写方法卡，书的全文不进仓库当前版本和安装包；源目录出现 `assets/books` 时打包器直接停止。默认成稿路径（入口加五页必读）不超过2万字，由 `tools/measure_default_path.py` 检查。早期验收记录：[精简布局验收](docs/compact-v11-validation.md) · [B11编码修复](docs/b11-encoding-fix.md) · [双版本验收](docs/dual-editions-v12.md)，其中关于书库全文的内容只适用于 v19 及以前。

使用 Python 3.11+ 标准库构建：

```text
python -X utf8 tools/package_viral_screenwriter.py --refresh --edition local --output ../viral-screenwriter_v20_local_2026-11-27.zip
python -X utf8 tools/package_viral_screenwriter.py --edition feishu --output ../viral-screenwriter_v20_feishu_2026-11-27.zip
```

`--refresh` 只更新维护源的完整性清单，以及按规则文件写入的源manifest版本字段与 `packaging_revision`；不加时源目录只读，版本字段与规则不一致即停止。源目录里有缓存、系统或编辑器临时文件（`__pycache__`、`.DS_Store`、`*.pyc`、`*.swp` 等，及git忽略的文件）时构建直接报错并列出路径，删除后重跑。构建在临时目录应用版本差异、重建派生包清单，验证CRC与逐文件SHA256后才替换目标ZIP。两版各自严格小于5,000,000字节、最多200文件、仅一个 `SKILL.md`。发布时同时上传两包，GitHub自动生成的整个仓库源码ZIP含历史技能，不是单技能安装包。

修改共同工作区文字后必须同步检查 `edition_rules.json`：原文锚点不匹配会停止构建，本地包出现未分类的飞书文件或流程文字也会失败。升版只改规则文件的版本/日期、`INSTALL.md` 的版本行（`版本：日期 版本 飞书版`，只写这三项）和更新记录，再用 `--refresh` 刷新；构建会核对两包的版本行和清单版本字段。运行双版回归检查会重新生成两包和验证报告：

```text
python -X utf8 tools/test_editions.py --output-dir ../screenwriter-release-check
python -X utf8 tools/measure_default_path.py
python -X utf8 tools/test_skill_scripts.py
```

## 自动发版

推送形如 `viral-screenwriter-v20-2026-11-27` 的标签（版本与日期须与 `tools/edition_rules.json` 一致），GitHub Actions 自动运行默认路径字数检查和双版回归，构建本地版、飞书版两个ZIP及SHA256，并以固定的简短说明创建 Release（详细记录留在 `docs/CHANGELOG.md`）。升版步骤见上节。

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
