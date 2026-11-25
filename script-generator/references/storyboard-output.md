# Executable Screenplay and Storyboard Output

Use this for a shootable screenplay, director storyboard, GEN map, production revision, dialogue lock, timing contract, or asset handoff. This file is the single canonical output-schema owner. Workflow order lives in `../SKILL.md`; all methods and validation rules live in their domain owners.

## Contents

- Standard deliverable and conditional sections
- IDs and authority
- Revision and timing headers
- Screenplay and global style prompts
- Asset/SCN and scene director maps
- Final third-party source and rights-use notice
- Canonical 14-field CUT
- GEN map and timing/media tables
- Synchronization and dialogue lock
- Sound/post layers and output routing
- Legacy compatibility

## Standard Deliverable

Use this order and omit conditional sections that are inactive:

```text
【版本与正典来源】（仅 revision mode）
【创作假设】
【时长与生成合同】（仅 contract-budget）
【媒体/帧锁】（仅 media-frame-lock）
【人物/关系与生产约束】
【Logline】
【事件身份与回环】（仅有重复/回环事件时）
【关键台词/金句银行】（用户要求金句/口号/重复台词，或系列回环需要锁句时）
【完整对白剧本】
【影像风格与运镜风格提示词】
【资产注册表】（有生产资产时）
【场景母版注册表】（Asset/SCN锁触发时）
【场景导演图/场面调度锁】
【逐CUT完整分镜】
【GEN-CUT映射】（需要AI视频生成或GEN合同时）
【剧本-分镜同步表】
【完整对白锁定表】（仅 production-lock）
【声音方案】
【BGM与后期层】（用户要求音乐，或音乐具有独立叙事功能时）
【受保护文本填入表】（存在待授权逐字歌词/台词/字幕/剧本文本时）
【连续性与结束状态】
【版权出处与使用声明】（当前brief命名第三方作品/形象/素材时；必须最后输出）
```

Revision impact, residue findings, validator JSON, and downstream re-baseline notices are sidecar artifacts. Do not paste banned legacy terms or a full diagnostic report into the canon document.

All labels inside the delivery-order block, registry schemas, canonical CUT
schema, and GEN schema are literal protocol strings. Copy them exactly; do not
paraphrase, translate, respell, add spaces, or remove punctuation. Apply the
serialization lock in `terminology-and-portability.md` before content review.

## IDs and Authority

- `S01`: screenplay scene
- `S01-B01`: dramatic beat
- `EVT-001`: repeated or interpretively important event
- `D-001`: audible story dialogue in production-lock mode
- `LYR-001`: lyric/sung-text layer
- `CARD-001`: title or theme card
- `TXT-001`: ordinary screen text
- `CUT-001`: uninterrupted editorial camera segment
- `GEN-001`: model-generation production unit
- `ASSET-001`: authoritative production asset
- `SCN-001`: authoritative scene-space master
- `RIGHTS-001`: named third-party rights dependency
- `CHG-001`: revision impact item

The complete screenplay is the dialogue and story authority. CUTs, GENs, locks, registries, and synchronization tables are derived projections.

## Final Rights Source and Use Notice

Output last when the current brief names a third-party film/clip, character or
likeness, costume, prop, artwork, logo, dialogue, lyric, song, recording, or
other protected dependency. Do not insert this section before or inside the
screenplay, CUTs, GEN map, or asset plan:

```text
【版权出处与使用声明】
Rights-ID | 类型 | 命名来源/版本 | replication_level |
rights_status | 素材来源状态 | 拟使用方式 | 需取得的权利 |
证据与适用范围 | 影响Scene/CUT/GEN/Asset | 授权后填入/替换动作

素材来源状态只用：AUTHORIZED-ASSET / USER-SUPPLIED-ASSET /
AUTHORIZED-LYRIC / AUTHORIZED-DIALOGUE / USER-SUPPLIED-TEXT /
RIGHTS-VERIFIED-SOURCE
使用选择：保留并取得授权 / 使用用户提供或已核验素材 / 替换为原创或适当授权方案
事实边界：只陈述本轮已读取的出处、证据和范围；未知项写“未核验”，不猜测。
```

Use only the machine terms defined in `terminology-and-portability.md`; apply
the decision rules from `open-source-research.md`. This final notice preserves a
planned exact recreation without rejecting it or claiming that
`rights-asserted` is verified. The user chooses whether to retain, authorize, or
replace each dependency.

## Revision Header

Output only in revision mode:

```text
【版本与正典来源】
- 当前候选版本：
- 父版本：
- source_canon_path：
- source_sha256：
- 本次修改请求：
- locked_invariants：
```

Never put the complete deletion-pattern list inside the canon.

## Timing Contract

Use the mode chosen by `timing-and-generation-units.md`.

### Contract-budget

```text
【时长与生成合同】
- 模式：contract-budget
- 合同来源：
- 总目标/上限：
- GEN单元上限：（没有则写“未指定”）
- 数值性质：planned_budget

| GEN/场景 | CUT范围 | 计划预算 | 显式上限 | 对白/动作可行性 |
|---|---|---:|---:|---|

求和复核：
```

Do not add a duration field to every CUT.

In each feasibility cell use:

```text
D-ID=...；自然读演=实测桌读或保守估读；
不可并行=...；允许重叠=...；冷启动/反应余量=...；结论=PASS/FAIL
```

### Media/frame-lock

```text
【媒体/帧锁】
| 锁定对象 | 来源媒体/ID | 实测时长 | 帧率/时基 | 入点 | 出点 | 帧/相位锚点 | 测量方法 |
|---|---|---:|---|---|---|---|---|
```

Only inspected media may be labeled `measured_media`.

## Creative Assumptions

```text
【创作假设】
- 平台/画幅：
- 类型：
- 风格锚点：
- 生产限制：
- timing_mode：silent-default | contract-budget | media-frame-lock（三选一，只写选中值）
- active_modules：none，或从 revision、production-lock、GEN、Asset/SCN 中列出已触发项
```

Do not print inactive internal modes.

## Characters and Logline

```text
【人物/关系与生产约束】
角色 | 称呼 | 关系 | 外在目标 | 台词质感 | 连续性状态

【Logline】
谁为了什么，被什么阻挡，作出什么决定，结果发生什么变化。
```

Series/episodic work may add a continuity ledger. Independent work does not need a series hook.

## Event Identity and Callback

Use only when an event repeats or changes meaning:

```text
【事件身份与回环】
EVT-ID | 时间/年份 | 项目/地点 | 参与者 | 主动选择 | 即时结果 | 后续变义 | callback ID
```

## Key Lines

Output only when the user asks for catchphrases, quote density, promotional dialogue, or a key-line bank:

```text
【关键台词/金句银行】
编号 | 台词 | 角色 | 语言动作 | 剧情功能 | 放置位置
```

## Screenplay Scene

Draft-sync mode:

```text
【S01 / 场景1：地点 / 内外 / 时段】
S01-B01
只写摄影机能看见或麦克风能听见的动作、空间、声音和结果。

角色：对白。

SFX：声音。
字幕：TXT/CARD/LYR 分类后的屏幕文字。
转场：叙事作用与可见触发。
```

Production-lock dialogue line:

```text
**D-001 | 角色 | 画内 | 口型=角色：** 逐字对白。
```

Use `画外`, `VO`, or `旁白` and `口型=无` when the sound source is not a visible speaking mouth. If a line crosses CUTs and visibility changes, use ordered maps such as `画内@1/2；画外@2/2` and `口型=角色@1/2；无@2/2`. Performance direction appears in surrounding action, not inside the authoritative audible text.

## Global Style Prompt Block

Place immediately after every delivered screenplay:

```text
【影像风格与运镜风格提示词】
**整体影像风格：** 一个从本剧本推导、已经决策完成、可直接复制的影像风格段落。
**统一运镜风格：** 一个从本剧本推导、已经决策完成、可直接复制的运镜风格段落。
```

The two prompts remain mutually compatible and contain no timing contract data. Per-CUT photography executes the grammar without repeating the paragraphs.

## Asset and Scene-Master Registries

Output when production assets or locked spaces exist:

```text
【资产注册表】
Asset-ID | 类型 | 人物时期/造型 | 绝对路径或外部ID | 适用Scene/CUT/GEN | 锁定事实 | 状态

【场景母版注册表】
SCN-ID | 地点/事件身份 | 母版Asset-ID | 几何锁 | 允许增加 | 禁止替代空间 | 适用Scene/CUT/GEN
```

Deprecated paths belong in the sidecar audit, not active canon prose.

## Scene Director Map

```text
【S01 场景导演图】
- EVT/场景任务与有意义变化：
- 观众视角、当前已知与延迟信息：
- 视点序列与合法进入/退出触发：
- 关键画面/戏点：
- 重要信息 / 次要信息 / 应排除干扰：
- SCN-ID、空间地标与前中后景：
- 人物/道具起始位置：
- 轴线、视线、屏幕方向、入画/出画：
- 视觉焦点路径与主运动方向：
- 35mm等效焦段组：基础 / 强调 / 插入
- 光线、天气、色彩、服装、Asset-ID连续性：
- 情绪与表演曲线：
- 转场主机制与声音辅助：
```

Every screenplay scene represented by CUTs must have one map. Repeat all 13
labels exactly and in the shown order; a summary paragraph or renamed field is
not a valid map. Use `无；原因=...` when a field is intentionally inapplicable.

## Canonical 14-Field CUT

Repeat all 14 fields for every CUT. Do not write `同上`, `按剧情`, or `自由发挥`.
The heading must match `### CUT-NNN | SNN-BNN` exactly. Put EVT IDs, labels,
and annotations inside fields or the sync table, never after the Beat ID.
The viewpoint `模式` must be exactly one of `客观`, `角色对齐`, `字面POV`, or
`临时全知`; describe framing variants such as over-shoulder or close alignment
under `摄影`, not by inventing another mode name.

```text
### CUT-001 | S01-B01
- 场景：SCN-ID；地点、内/外、时段、天气/光线、空间区域。
- 剧情/故事变化：本CUT开始与结束之间的可见变化，以及观众获得或失去的信息。
- 人物与连续性：出镜人物、Asset-ID、服装/妆发/手持物、起始站位、朝向、前中后景关系。
- 演员调度/动作节拍：触发 -> 路线/速度 -> 人物/道具交互 -> 结束站位；按因果拆分。
- 情绪与表演：起始状态 -> 触发 -> 呼吸/音量/语速 -> 一个主要视线或身体动作 -> 句后反应/结束状态。
- 台词/字幕：
  - D-001[1/1] | 剧情对白 | 角色 | 画内 | 口型=角色 | 文本=逐字对白。
  - TXT/LYR/CARD按类别单列；无则写“无”。
- 叙事视点/知识边界：模式=客观 | 主人=无 | 人物在场=是 | 观众当前可知=当前可见事实 | 进入触发=上一CUT落幅/可见动作/D-ID/EVT-ID | 退出触发=本CUT落幅/可见动作/D-ID/EVT-ID。
- 摄影：景别；35mm等效焦段；机位距离/高度/角度；构图；轴线/视线/屏幕方向；运镜；焦点/景深。
- 视觉焦点/动势：入镜焦点 -> 主体/动作 -> 出镜焦点；主体与相机主运动向量；与前后CUT的顺接或故意跳变。
- 声音：对白、环境、SFX及事件触发的音乐动作；仅media-frame-lock模式写精确时间参数。
- 剪辑/转场相位：叙事作用 -> 起幅/动作相位 -> 切点 -> 落幅/相位 -> 连续性变量；一个主机制，可有一个声音辅助。
- 导演意图：观众必须注意、理解、期待或感受什么，以及为何这样安排视点、镜头和剪辑。
- AI画面事实：无歧义写清主体、空间、动作顺序、镜头与连续性；运动时写起幅状态、过程和落幅状态。
- 连续性/资产：SCN/Asset、角色、服装、道具、屏幕方向、光线、上一CUT继承状态和下一CUT交接状态。
```

Use one final focal length per CUT. `起幅/落幅` describe visual states, not numeric frames unless `media-frame-lock` is active.

## GEN-CUT Map

Use when AI-video generation, a GEN limit, or downstream production mapping is requested:

```text
### GEN-001 | CUT-001—CUT-003
- 类型：narrative
- 因果/叙事任务：
- 触发：
- 选择/行动：
- 对方可见反应：
- 新结束状态：
- 场景/时空变化：
- 视点序列：
- 对白负载/D-IDs：
- Asset/SCN IDs：
- IN状态：
- OUT状态：
```

Timing values remain in the timing contract or `media-frame-lock` table. `SEG` input is normalized to `GEN`.
Select exactly one GEN type; the slash-separated names above are not output alternatives.
`触发` must be visible inside this GEN. `IN状态` must fully state cold-start character positions, hands/props, exact story/UI state, Asset/SCN facts, and causal context; do not rely on reproducing the previous GEN's pixels. Put exact causal UI/state changes in controlled post/screen-replacement assets.

## Screenplay-Storyboard Sync

```text
【剧本-分镜同步表】
Scene/Beat/EVT | 对应CUT | 剧情变化 | 动作/对白一致 | 视点触发 | 连续性结果
```

## Complete Dialogue Lock

Output only in production-lock mode:

```text
【完整对白锁定表】
| D-ID | 类别 | 角色 | 逐字文本 | 声源 | 口型对象 | CUT/片段 |
|---|---|---|---|---|---|---|
| D-001 | 剧情对白 | 角色 | 逐字对白。 | 画内 | 角色 | CUT-001[1/1] |
```

The screenplay, CUT fragments, and this table must match exactly in text, punctuation, order, source mode, lip-sync subject, and mapping.

For a multi-CUT line, keep one D-ID row and use the same ordered `@片段` maps in `声源` and `口型对象`; list ordered CUT fragments with `；`.

## Sound, BGM, and Post Layers

```text
【声音方案】
环境、对白空间、SFX、声音桥与事件触发。

【BGM与后期层】（用户要求音乐，或音乐具有独立叙事功能时）
歌曲/版本与叙事功能：
事件触发：
LYR-ID与文本来源：AUTHORIZED-LYRIC / USER-SUPPLIED-TEXT / RIGHTS-VERIFIED-SOURCE
原曲占位长度依据：段落名、乐句/小节范围、音节或字符容量、入点/出点；时间数值只在时长owner允许时写
口型对象与填词后同步面：
layer=post内容：歌曲、歌词字幕、主题卡、音频路径或后期文字
```

BGM is conditional. Apply the rights states and text-source boundary from
`open-source-research.md`; default planned protected use to `rights-asserted`,
but never infer `rights-verified` from a purchase plan. Preserve a full
`AUTHORIZED-LYRIC` slot instead of shortening the scene. Put source attribution,
clearance paths, scope, and user choices only in the final rights notice.
In `silent-default` and `contract-budget`, bind cues to events. Precise timing
belongs only to `media-frame-lock`.

When exact protected wording is pending, output this production map without
rights warnings inside the creative surfaces:
```text
【受保护文本填入表】
Slot-ID | 类型 | 文本来源 | 作品/版本 | 段落/场景位置 |
说话人/口型对象 | 轮次/行/乐句/小节 | 音节或字符容量 |
IN事件 | OUT事件 | 动作/声源/口型映射 | 填入CUT/GEN/Asset/后期层
```
Use `AUTHORIZED-LYRIC` for pending lyrics and `AUTHORIZED-DIALOGUE` for
pending dialogue, subtitles, or screenplay text. The slot must be complete
enough to replace the token with authorized wording without changing the
scene, edit boundaries, blocking, lip-sync ownership, or downstream map.
Use stable structural IDs such as `L01`, `PH01`, or `BAR01` and bind each
line/phrase/bar group to an action or lip-sync interval. Public-source research
may verify non-expressive counts. If the exact count or mapping cannot yet be
verified, mark it `structure-pending`; do not claim that the slot is ready for
zero-rearrangement insertion.
Source attribution and clearance state still appear only in the final rights
notice.

## Continuity and Ending State

```text
【连续性与结束状态】
本次改变、未回收信息、人物/关系/EVT/Asset/SCN结束状态，以及下一授权阶段。
```

Add a next-episode hook only for episodic work or an explicit request.

## Output Routing

- Complete screenplay/storyboard: use the standard order and active conditional modules.
- Screenplay-only: include screenplay plus both global style prompts; omit CUT/GEN unless requested.
- Outline/bible/research/doctor/dialogue-polish only: output the requested artifact.
- Revision mode: produce a new version and sidecar impact/validation artifacts; do not overwrite canon.

## Legacy Compatibility

The default output is the 14-field schema above. A historical 12-field CUT that combines `声音/剪辑` may be read in compatibility mode and must be reported as legacy input. Do not emit it as a new default. A historical 13-field CUT may be upgraded by adding the viewpoint/knowledge-boundary field without merging any existing field.
