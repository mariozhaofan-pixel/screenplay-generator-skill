# Executable Screenplay and Storyboard Output

Use this when producing a shootable script, storyboard table, scene list, video prompt pack, or production breakdown.

## Standard Deliverable

```
【创作假设】
- 时长：
- 平台/画幅：
- 类型：
- 风格锚点：
- 生产限制：

【人物/关系与生产约束】
角色 | 昵称 | 关系 | 外在目标 | 口头禅/台词质感 | 连续性状态
系列/单元剧任务再增加系列前提、固定关系、长线矛盾和回调项；独立作品不强行系列化。

【本集Logline】
一句话写清主角、目标、阻碍、结果或反转。

【关键台词/金句银行（按需）】
编号 | 台词 | 角色 | 功能 | 放置位置
仅在用户要求金句、梗密度、传播台词、口播爆点或短视频喜剧时输出；普通剧情片、严肃剧、纪录片风格可改为“关键台词/对白重点”或省略。

【完整对白剧本】
先按场景和节拍写完整可拍内容。固定场景 ID 与节拍 ID，后续 CUT 必须引用这些 ID，台词保持逐字一致。

【场景导演图/场面调度锁】
逐场写场景任务、关键画面、信息层级、观众视角、空间地标、人物/道具起点、轴线/视线/屏幕方向、焦段组、光线和连续性。

【逐CUT完整分镜】
每个剪辑段单独成块，使用下方字段，不以超宽表格压缩。

【剧本-分镜同步表】
场景/节拍 ID | 对应 CUT | 剧情变化 | 台词一致 | 时长

【BGM/声音方案】
音乐方向、入点、duck点、sting点、循环点。

【连续性与结束状态】
本次改变、未回收信息、角色/关系/道具结束状态。只有系列、单元剧或用户明确要求时，再写下一集压力和钩子。
```

## IDs

- Use `S01`, `S02` for screenplay scenes.
- Use `S01-B01`, `S01-B02` for dramatic beats.
- Use `CUT-001`, `CUT-002` for every uninterrupted camera segment, including empty environments and inserts.
- Use `PROP-001` for important props that need continuity.
- Use `COST-001` for wardrobe continuity.
- If generating image/video prompts later, carry the same IDs forward.

## Screenplay Scene Format

```
【S01 / 场景1：地点 / 内外 / 时间 / X秒】
S01-B01
画面只写摄影机能看见或麦克风能听见的内容，并写清可见动作与道具状态变化。

角色：对白。

SFX：声音。
字幕：屏幕字。
转场：切/甩镜/音桥/匹配剪辑。
```

## Scene Director Map

```text
【S01 场景导演图】
- 场景任务/有意义的变化：
- 观众视角与已知信息：
- 关键画面/戏点：
- 重要信息 / 有效但次要信息 / 应排除干扰：
- 空间地标与前中后景：
- 人物/道具起始位置：
- 轴线、视线、屏幕方向、入画/出画：
- 视觉焦点路径与主运动方向：
- 35mm 等效焦段组：基础 / 强调 / 插入
- 光线、天气、色彩、服装、道具连续性：
- 情绪曲线：
- 声音锚点：
```

## Detailed CUT Block

Repeat every field for every CUT. Do not write `同上`.

```text
### CUT-001 | 00:00.000-00:03.200 | 3.2s | S01-B01
- 场景：地点、内/外、时段、天气/光线、空间区域。
- 剧情/故事变化：本 CUT 开始与结束之间发生的可见变化，以及观众获得或失去的信息。
- 人物与连续性：出镜人物、服装/妆发/手持物、起始站位、朝向、前中后景关系。
- 演员调度/动作节拍：触发 -> 路线/速度 -> 与人或道具的交互 -> 结束站位；必要时按秒拆分。
- 情绪与表演：起始状态 -> 触发 -> 可表演动作 -> 结束状态，不写隐藏心理。
- 台词/字幕：写本 CUT 实际听到的逐字片段、说话者、画内/画外/旁白和口型对象；无台词写“无”。一句跨 CUT 时，各段按顺序拼合必须等于剧本原句，不重复整句，不用“接上”代替文字。
- 摄影：景别；35mm 等效焦段；机位距离/高度/角度；构图；轴线/视线/屏幕方向；运镜；焦点/景深。
- 视觉焦点/动势：入镜焦点位置 -> 主要主体/动作 -> 出镜焦点位置；主体与相机各自的主运动向量；与前后 CUT 是顺接还是故意跳变，以及原因。
- 声音：对白、环境、SFX、BGM 入点/duck/sting/停拍。
- 剪辑：入点、出点、与前后 CUT 的连接方式及剪辑依据。
- 导演意图：观众必须注意、理解、期待或感受到什么，以及为何此刻这样拍。
- AI画面事实：用无歧义的一段话写清主体、空间、动作顺序、镜头和连续性；需要运动时写起始帧与结束帧。
- 连续性/资产：场景、角色、服装、道具、屏幕方向、光线、上一 CUT 继承状态和下一 CUT 交接状态。
```

If the scene uses a known camera format, state actual focal length plus 35mm equivalent. Otherwise use 35mm equivalent only. Choose one final focal length per CUT, not a range.

## Duration Rules

- Dialogue-heavy Mandarin: about 200-250 Chinese characters per screen minute, adjusted for pauses and reactions.
- Insert gags: 2-5 seconds each.
- Silent reaction: 1-3 seconds for comedy, 5-10 seconds for emotion.
- Short-video hook: first visible beat should land by 3 seconds; first full joke, conflict, or suspense turn by 10-15 seconds.
- For 60-120 seconds, 10-24 CUTs is a common range. Dialogue scenes may use fewer and action/comedy may use more. Story and emphasis decide the count.
- CUT durations and scene durations must sum to the declared total; use exact values rather than approximate row totals.

## Shot Table Checks

Every CUT should answer:

- What changes on screen?
- Where are the camera, characters, props, and action axis?
- Why are this focal length, distance, framing, movement, and duration used?
- What does the viewer learn or feel?
- What do actors do from start position to end position?
- Why does the edit enter and leave at these moments?
- What audio cue supports the beat?
- What continuity asset must be preserved?
- Can an AI video model generate the dominant action without inventing missing spatial facts?

If a row only repeats known information, delete or merge it.
