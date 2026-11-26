# 爆款编剧skill：飞书版（含视频模块）

版本：2026-11-27 v20 飞书版

与本地版共用同一套编剧方法卡，飞书协作为可选模式。这个目录可以整体复制到另一台电脑；包内文字资料、模板、执行卡与视频反推代码不依赖原电脑的盘符或用户名。普通编剧功能独立可用，视频模型提示词按需交给你已安装的导演skill。

## 安装

1. 解压ZIP，得到 `viral-screenwriter` 文件夹，保持其中目录结构。
2. 放入所用宿主的技能目录；支持上传的宿主可直接上传ZIP。最终层级应为 `<技能目录>/viral-screenwriter/SKILL.md`，不要多套一层同名目录。
3. 本地版与飞书版使用相同技能名 `viral-screenwriter`，每台宿主只安装其中一版，避免重复触发；切换版本不移动或删除用户项目。若已有旧版，先将旧文件夹备份到技能目录之外，再用整个新文件夹替换，避免新旧文件混杂。重新打开会话或刷新技能后，按宿主的方式调用 `viral-screenwriter`。

例如：“使用爆款编剧skill，按标准格式写一集”；或“参考这个片名的对白和信息差，查公开资料后发展一个原创故事”。主入口及范围见 [SKILL.md](SKILL.md)。剧本、分镜与修订稿始终交付.md，Word附件只作结构参考。

## 本地或飞书协作

新项目开始时选择本地工作、加入已有飞书多维表资产库或创建新库。已有项目沿用选择。飞书首次部署和账号授权会增加启动时间；后续在同一 Base 与项目ID下管理剧本、资产、段落提示词和用户视频，编剧与导演不各建一份库。

飞书是可选模式，本地写作不需要安装或登录飞书。选择飞书后先复用宿主已有连接器或独立CLI；缺环境时按[配置指引](references/FEISHU_WORKSPACE_SETUP.md)补齐所需能力并由用户完成授权。本包只提供配置说明、四表蓝图及本地同步规划器，不封装飞书Skill、CLI、Node依赖或账号凭据，也不要求先安装导演Skill。新库默认密码分享、链接可编辑；用户已有权限限制优先，网页密码不代替API授权。

实际写作仍在本地项目完成。已授权的定稿与后续采用改稿检查后自动上传同一个 Base 的 `剧本md文件` 附件字段，并维护各批当前采用版本；完整历史修订保留，不因每次最多2集而丢掉此前批次。草案、意见或孤立替换片段不自动覆盖当前采用稿。云端失败保留本地交付并明确待同步；详情见[飞书剧本工作区](references/feishu-workspace.md)和[剧本同步合同](references/FEISHU_SCREENPLAY_SYNC.md)。

## 与导演技能联动

按[交接接口](references/director-handoff.md)接收导演发来的格式整理、修改意见和已授权修稿；用户需要视频模型提示词时，定位并实际读取你已安装的导演skill（任何能把剧本编译成视频提示词的skill，`director-seedance-prompt` 是已对接过的一种）。导演skill不随本包提供；未安装时仍可完成普通编剧工作。

## 随包内容

- Coffee Break 全部127张方法卡和3本补书的已读章节卡（[方法卡总索引](references/method-cards.md)），人物/结构/对白方法、项目交付与对标研究流程。
- [格式附件的完整段落文字](assets/templates/delivery-reference-text.md)、[可填写Markdown模板](assets/templates/screenplay-template.md)及[格式规范](references/screenplay-format.md)。
- [完整视频反推模块](modules/video-reverse-storyboard/MODULE.md)，包括参考协议与4个配套脚本，由主入口按需读取；整个ZIP只有主目录一个`SKILL.md`，不需要另装同名技能。
- [样本规则](references/viral-rules.md)、[动态规则快照](references/dynamic-viral-rules.md)及现有历史记录。部分旧样本证据在源电脑已缺失，见[证据状态与缺失清单](assets/evidence/README.md)；包不会把缺图/缺原表的历史记录冒充可复核证据，也不会要求连接原来的数据库。
- 飞书协作的[四表蓝图](assets/feishu-base-blueprint.json)、[布局合同](references/FEISHU_BASE_LAYOUT.md)、[配置指引](references/FEISHU_WORKSPACE_SETUP.md)、[剧本同步合同](references/FEISHU_SCREENPLAY_SYNC.md)及 `scripts/plan_feishu_sync.py` 本地规划器；只在选择飞书时使用。
- 本目录的 `package-manifest.json` 逐文件记录大小与SHA256，用于完整性检查。

本包不含任何书的全文、原PDF/EPUB、扫描页图或原Word。方法卡是自写释义，卡上的书页和章节供你用自己的版本核对；方法卡只在相关任务中读取。

## 当前电脑需要什么

这个ZIP是模型使用的技能与资料包，不是离线运行的大模型或宿主应用本体。目标电脑需要支持技能的宿主和模型。普通编剧、人物小传、续写、格式整理直接使用包内Markdown，不要求媒体工具或连接旧电脑。

联网调查公开资料使用当前宿主的搜索/浏览能力与网络；本包不保存账号、Cookie、密钥或登录会话。新的参考视频/小说等项目素材由当前用户提供。

视频模块与4个配套脚本随包保留。实际处理视频时按[宿主工具与按需准备](references/media-tools.md)检查当前电脑，优先使用已有能力；仅为本次任务的实际缺口，在宿主权限允许的范围内配置必要公开依赖。下列是配套脚本各自需要的工具，不是安装Skill时必须预装的清单：

| 功能 | 通用依赖 | 随包入口 |
|---|---|---|
| 包完整性、逐镜稿结构检查 | Python 3.10+，标准库即可 | `scripts/verify_portable.py`、`scripts/validate_output.py` |
| 飞书增量同步计划与冲突检查 | Python 3.11+，标准库即可（`check_environment.py --mode sync` 可查）；脚本自身不联网 | `scripts/plan_feishu_sync.py`；实际上传使用独立飞书连接器或CLI |
| 视频全帧与音轨准备 | Python、numpy、Pillow、FFmpeg/FFprobe | `modules/video-reverse-storyboard/scripts/prepare_video_evidence.py` |
| 画面字幕OCR | Python、OpenCV、RapidOCR及其模型资源、FFprobe | `modules/video-reverse-storyboard/scripts/extract_subtitles_ocr.py` |
| 语音转写 | Python、faster-whisper及所选模型资源 | `modules/video-reverse-storyboard/scripts/transcribe_audio.py` |
| 逐镜还原稿结构检查 | Python 3.10+，标准库即可 | `modules/video-reverse-storyboard/scripts/validate_storyboard.py` |

上述通用软件/模型不绑定任何开发机路径。依赖安装遵循当前官方文档，并先做小样验证；不替换已有全局运行环境。模型权重可能需要首次下载，只准备所选方案必要的模型。自动OCR/ASR不等于完成实际观看和听音；真实声画审阅仍需宿主具备相应能力。

本包没有附带宿主程序、Python/FFmpeg可执行程序或通用OCR/ASR模型权重，避免误称“安装技能就获得宿主没有的模型能力”。这些属于目标机器的通用运行环境，不是对原电脑文件的依赖；不会因此阻止普通文本编剧工作。

## 安装后可自行检查

在 `viral-screenwriter` 目录执行：

```text
python -X utf8 scripts/verify_portable.py
python -X utf8 scripts/check_environment.py --mode writing
```

视频任务开始前可用 `--mode video`、`--mode ocr`、`--mode asr` 或 `--mode all` 检查目标电脑。该命令只检查，不联网、不安装、不修改系统；缺少可选媒体工具时会具体列出。它不证明模型已完成声画审阅。

完整性检查以本目录为根，不回源电脑补文件。若你自行修改了技能/资料，原SHA256会变，核验会如实报差异。项目剧本、研究过程、视频展开帧和临时缓存应保存在当前项目目录，不写进技能目录。
