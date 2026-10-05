# 爆款编剧skill：独立文字版（含视频模块）

版本：2026-10-06 v7（在v6基础上修正单技能入口与模块路由）。这个目录可以整体复制到自己的另一台电脑；包内文字资料、模板、执行卡与视频反推代码不依赖原电脑的盘符、用户名或微信目录。普通编剧功能独立可用，视频模型提示词按需联动另行安装的director-seedance-prompt。

## 安装

1. 解压ZIP，得到 `viral-screenwriter` 文件夹，保持其中目录结构。
2. 放入目标电脑的 Codex skills 目录，通常是当前用户的 `.codex/skills/`。最终层级应为 `.codex/skills/viral-screenwriter/SKILL.md`，不要多套一层同名目录。若目标电脑已自定义技能目录，使用该目录。
3. 若已有旧版，先将旧文件夹备份到技能目录之外，再用整个新文件夹替换，避免新旧文件混杂。重新打开会话或刷新技能后，用 `$viral-screenwriter` 调用。

例如：“使用爆款编剧skill，按标准格式写一集”；或“参考这个片名的对白和信息差，查公开资料后发展一个原创故事”。主入口及范围见 [SKILL.md](SKILL.md)。剧本、分镜与修订稿始终交付.md，Word附件只作结构参考。

## 与导演技能联动

按[交接接口](references/director-handoff.md)接收导演发来的格式整理、修改意见和已授权修稿；用户需要视频模型提示词时，定位并实际读取独立director-seedance-prompt技能。两者安装在同级skills目录即可按名称发现，导演技能不复制进本包；未安装导演时仍可完成普通编剧工作。

本版以v6安装包为发布基线，保留书籍文字、方法卡、模板、导演交接和视频反推能力。整个ZIP仅有主目录一个`SKILL.md`；内置视频说明改为`modules/video-reverse-storyboard/MODULE.md`，由主入口按需读取，不再注册第二个技能。视频脚本仍在原模块目录；不重新加入本机原PDF、EPUB、扫描页图、原Word或原始OCR文件。

## 随包内容

- Coffee Break 全部127张方法卡、人物/结构/对白方法、项目交付与对标研究流程。
- 主书与11份补充书的全部已有Markdown转写、分章/分节文字及来源索引，保留原文件名、版本与来源哈希。先从[书库总索引](references/book-library.md)按创作问题定位，再进入[主书方法与书源](references/coffee-break-method.md)、[补充书库](references/library/index.md)及[书库文字保真检查](assets/books/VALIDATION.md)。这些资料随包用于你的多设备查阅，不用回原电脑寻找。
- [格式附件的完整段落文字](assets/templates/delivery-reference-text.md)、[可填写Markdown模板](assets/templates/screenplay-template.md)及包含已测字体、字号、页边距的[格式规范](references/screenplay-format.md)。
- [完整视频反推模块](modules/video-reverse-storyboard/MODULE.md)，包括参考协议与4个配套脚本，不需要另装同名技能。
- [样本规则](references/viral-rules.md)、[动态规则快照](references/dynamic-viral-rules.md)及现有历史记录。部分旧样本证据在源电脑已缺失，见[证据状态与缺失清单](assets/evidence/README.md)；包不会把缺图/缺原表的历史记录冒充可复核证据，也不会要求连接原来的数据库。
- 本目录的 `package-manifest.json` 逐文件记录大小与SHA256，用于完整性检查。

本版不附原PDF/EPUB、扫描页图、原Word、逐页TXT或原始OCR坐标JSON；已有转写正文没有因瘦身删节。保留的JSON是来源、导航及核验索引。正文保真是相对现有转写的比较，不表示OCR从无识别错误；需要核对原图、插图或版式时，须取得对应原件，不能声称包内仍有原件可看。

书籍和参考资料默认只在相关任务中读取。全文随包不表示每次把全库放入上下文；仍按索引定位章节、页码和所需练习。

## 当前电脑需要什么

这个ZIP是模型使用的技能与资料包，不是离线运行的大模型或Codex应用本体。目标电脑需要可运行的Codex/兼容宿主和模型。普通编剧、人物小传、续写、格式整理、书库查阅直接使用包内Markdown，不要求媒体工具或连接旧电脑。

联网调查公开资料使用当前宿主的搜索/浏览能力与网络；本包不保存账号、Cookie、密钥或登录会话。新的参考视频/小说等项目素材由当前用户提供。

视频模块与4个配套脚本随包保留。实际处理视频时按[宿主工具与按需准备](references/media-tools.md)检查当前电脑，优先使用已有能力；仅为本次任务的实际缺口，在宿主权限允许的范围内配置必要公开依赖。下列是配套脚本各自需要的工具，不是安装Skill时必须预装的清单：

| 功能 | 通用依赖 | 随包入口 |
|---|---|---|
| 包完整性、逐镜稿结构检查 | Python 3.10+，标准库即可 | `scripts/verify_portable.py`、`scripts/validate_output.py` |
| 视频全帧与音轨准备 | Python、numpy、Pillow、FFmpeg/FFprobe | `modules/video-reverse-storyboard/scripts/prepare_video_evidence.py` |
| 画面字幕OCR | Python、OpenCV、RapidOCR及其模型资源、FFprobe | `modules/video-reverse-storyboard/scripts/extract_subtitles_ocr.py` |
| 语音转写 | Python、faster-whisper及所选模型资源 | `modules/video-reverse-storyboard/scripts/transcribe_audio.py` |

上述通用软件/模型不绑定任何开发机路径。依赖安装遵循当前官方文档，并先做小样验证；不替换已有全局运行环境。模型权重可能需要首次下载，只准备所选方案必要的模型。自动OCR/ASR不等于完成实际观看和听音；真实声画审阅仍需宿主具备相应能力。

本包没有附带Codex程序、Python/FFmpeg可执行程序或通用OCR/ASR模型权重，避免误称“安装技能就获得宿主没有的模型能力”。这些属于目标机器的通用运行环境，不是对原电脑文件的依赖；不会因此阻止普通文本编剧工作。

## 安装后可自行检查

在 `viral-screenwriter` 目录执行：

```text
python -X utf8 scripts/verify_portable.py
python -X utf8 scripts/check_environment.py --mode writing
```

视频任务开始前可用 `--mode video`、`--mode ocr`、`--mode asr` 或 `--mode all` 检查目标电脑。该命令只检查，不联网、不安装、不修改系统；缺少可选媒体工具时会具体列出。它不证明模型已完成声画审阅。

完整性检查以本目录为根，不回源电脑补文件。若你自行修改了技能/资料，原SHA256会变，核验会如实报差异。项目剧本、研究过程、视频展开帧和临时缓存应保存在当前项目目录，不写进只读参考书库。
