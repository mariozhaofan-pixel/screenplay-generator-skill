# 内置视频模块运行环境

本模块的入口、3份参考协议、4个Python脚本均随包提供，不需要另装同名技能。Python解释器、FFmpeg可执行文件、第三方Python包和ASR/OCR模型属于目标电脑的通用运行环境，未复制巨大二进制，也不搜索开发机目录作为回退。实际处理视频时遵循[按需检查与准备](../../references/media-tools.md)：先复用宿主已有工具，在当前授权和权限内补齐必要依赖，完成小样验证；不因读取本模块就预装全部程序或模型。

建议Python 3.10或更新版本；本模块用了3.10的类型语法。所有命令在此模块目录执行，或由调用方将脚本路径解析为本包的实际位置。输入媒体和输出目录由本次项目提供。Python包须安装到执行脚本的同一个解释器环境。

| 脚本 | 直接第三方依赖 | 外部工具或资源 | 探测方式 |
|---|---|---|---|
| scripts/prepare_video_evidence.py | numpy、Pillow（导入名PIL） | PATH中的ffmpeg和ffprobe | 运行时导入numpy/PIL，并用shutil.which查找两个工具；缺失时报错，不降级抽样。 |
| scripts/extract_subtitles_ocr.py | opencv-python（导入名cv2），rapidocr或rapidocr-onnxruntime二选一及其后端依赖 | ffprobe；OCR模型资源取决于所选包/后端，可能需要首次下载 | 脚本延迟导入cv2，依次尝试RapidOCR；ffprobe默认从PATH调用，也可用--ffprobe传目标电脑上的实际程序。初始化模型成功才说明OCR可用。 |
| scripts/transcribe_audio.py | faster-whisper及其依赖（包括CTranslate2等） | 对应Whisper模型；默认small会使用本机缓存或尝试下载 | 延迟导入WhisperModel并在运行时加载模型；--model可传目标电脑已有模型目录。仅能import成功不足以证明模型可用。 |
| scripts/validate_storyboard.py | 无，仅Python标准库 | 用户的分镜Markdown文件 | --help可验证入口；实际输入文件后才检查结构。 |

典型安装命令（按需要的功能选择，不自动运行）：

```text
python -m pip install numpy Pillow
python -m pip install opencv-python rapidocr-onnxruntime
python -m pip install faster-whisper
```

若选择新版rapidocr，则由目标电脑安装该包与其所需推理后端；不同时强制安装两种OCR实现。FFmpeg/FFprobe需使用目标操作系统可运行的发行版，并把其bin目录加入PATH。ASR/OCR模型未随包提供，首次运行可能需要网络；离线前必须另行准备对应模型或包资源。网络下载、包版本和GPU驱动由目标环境决定，不能声称一个只通过--help的环境已完成识别。

可先检查：

```text
python --version
ffmpeg -version
ffprobe -version
python -c "import numpy, PIL; print('frame dependencies OK')"
python -c "import cv2; from rapidocr_onnxruntime import RapidOCR; print('OCR imports OK')"
python -c "from faster_whisper import WhisperModel; print('ASR import OK')"
python scripts/prepare_video_evidence.py --help
python scripts/extract_subtitles_ocr.py --help
python scripts/transcribe_audio.py --help
python scripts/validate_storyboard.py --help
```

软件准备只能辅助完整分析。模型输出、全帧导出和结构校验都不等于已经实际观看每帧或完整听音；仍须遵守[模块入口](MODULE.md)与[分析协议](references/analysis-protocol.md)。该模块不自动下载用户影片或调用任何私人数据库。
