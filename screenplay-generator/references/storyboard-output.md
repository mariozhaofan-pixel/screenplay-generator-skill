# Executable Storyboard Output

Use this when producing a shootable script, storyboard table, scene list, video prompt pack, or production breakdown.

## Standard Deliverable

```
【创作假设】
- 时长：
- 平台/画幅：
- 类型：
- 风格锚点：
- 生产限制：

【系列设定/人物关系】
角色 | 昵称 | 关系 | 外在目标 | 口头禅/台词质感 | 连续性状态

【本集Logline】
一句话写清主角、目标、阻碍、结果或反转。

【关键台词/金句银行（按需）】
编号 | 台词 | 角色 | 功能 | 放置位置
仅在用户要求金句、梗密度、传播台词、口播爆点或短视频喜剧时输出；普通剧情片、严肃剧、纪录片风格可改为“关键台词/对白重点”或省略。

【分镜表】
镜号 | 时长 | 景别/机位/运动 | 画面动作 | 台词/字幕 | 声音/BGM/SFX | 转场/执行备注 | 连续性资产

【对白剧本】
按场景和镜头写可拍内容。

【BGM/声音方案】
音乐方向、入点、duck点、sting点、循环点。

【连续性与下一集钩子】
本集改变、保留伏笔、下一集压力。
```

## Shot IDs

- Use `SHOT-001`, `SHOT-002` for shots containing characters.
- Use `SCN-001` for empty environment or establishing shots.
- Use `PROP-001` for important props that need continuity.
- If generating image/video prompts later, carry the same IDs forward.

## Screenplay Scene Format

```
【S01E01 / 场景1：地点 / 时间 / 约X秒】
SHOT-001（景别/机位/运动）
画面只写摄影机能看见或麦克风能听见的内容。

角色：对白。

SFX：声音。
字幕：屏幕字。
转场：切/甩镜/音桥/匹配剪辑。
```

## Duration Rules

- Dialogue-heavy Mandarin: about 200-250 Chinese characters per screen minute, adjusted for pauses and reactions.
- Insert gags: 2-5 seconds each.
- Silent reaction: 1-3 seconds for comedy, 5-10 seconds for emotion.
- Short-video hook: first visible beat should land by 3 seconds; first full joke by 10-15 seconds.

## Shot Table Checks

Every shot should answer:

- What changes on screen?
- Why is the camera here?
- What does the viewer learn or feel?
- What audio cue supports the beat?
- What continuity asset must be preserved?

If a row only repeats known information, delete or merge it.
