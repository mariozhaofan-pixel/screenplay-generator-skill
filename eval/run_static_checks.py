#!/usr/bin/env python3
"""Run deterministic repository/GPT-package consistency checks."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "script-generator"
GPT = ROOT.parent / "剧本生成器_GPT知识库"
ARTIFACTS = ROOT / "eval" / ".artifacts"
PRIVATE_LEAKAGE_TERMS = ARTIFACTS / "private_leakage_terms.txt"


def load_leakage_tokens() -> list[str]:
    tokens = [".chatgpt-projects"]
    if PRIVATE_LEAKAGE_TERMS.is_file():
        tokens.extend(
            line.strip()
            for line in PRIVATE_LEAKAGE_TERMS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    return list(dict.fromkeys(tokens))


LEAKAGE_TOKENS = load_leakage_tokens()

STALE_CONFLICTS = [
    "output no durations or timecodes",
    "时长判断只能作为内部静默任务",
    "其余文件按编号从小到大优先，编号小的文件覆盖编号大的文件",
    "visual state that requires a separate generation prompt",
    "有运动时写起始帧与结束帧",
    "media/frame-lock mode",
    "模式=近主观",
    "模式=角色对齐观察",
    "模式=字面第一人称",
    "我已上传 00-12 共13个编号知识文件",
    "上传以下13个编号知识文件",
    "任何版权都可以忽略",
    "用户说能授权就视为已授权",
    "每首歌摘录最多10个汉字或英文词",
    "Use named reference works only as abstract",
    "参考作品只抽象高层特征，不复制人物",
    "【第三方权利依赖表】",
    "AUTHORIZED-TEXT",
    "lyric limits",
    "AI 画面事实：",
    "连续性资产：",
]

VAGUE_PHRASES = [
    "按需",
    "需要时",
    "必要时",
    "视情况",
    "酌情",
    "根据需要",
    "若有需要",
    "when needed",
    "if needed",
    "as needed",
    "where appropriate",
    "as appropriate",
    "if appropriate",
    "where useful",
    "if useful",
    "when useful",
    "more naturally",
    "更自然地",
    "更合理地",
]

ABSOLUTE_USER_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:[\\/](?:Users|Documents|Desktop|Downloads)[\\/]|"
    r"/(?:Users|home)/[^/\s]+/)"
)


def load_validator():
    path = SKILL / "scripts" / "validate_delivery.py"
    spec = importlib.util.spec_from_file_location("delivery_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load delivery validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    files = [
        path
        for base in (SKILL, GPT)
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".yaml", ".json", ".py"}
    ]

    decoded: dict[Path, str] = {}
    line_counts: dict[Path, int] = {}
    for path in files:
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"UTF8:{path}:{exc}")
            continue
        decoded[path] = text
        if unicodedata.normalize("NFC", text) != text:
            errors.append(f"NFC:{path}")
        if path.suffix.lower() == ".md" and text.count("```") % 2:
            errors.append(f"MARKDOWN_FENCE:{path}")
        if path.suffix.lower() in {".md", ".yaml", ".json"} and ABSOLUTE_USER_PATH_RE.search(text):
            errors.append(f"HARDCODED_USER_PATH:{path}")
        line_count = len(text.splitlines())
        line_counts[path] = line_count
        if path == SKILL / "SKILL.md" and line_count > 120:
            errors.append(f"SKILL_ROUTER_TOO_LONG:{line_count}")
        if path.parent == SKILL / "references":
            if line_count > 600:
                errors.append(f"SKILL_REFERENCE_TOO_LONG:{path.name}:{line_count}")
            elif line_count > (425 if path.name == "storyboard-output.md" else 350):
                warnings.append(f"SKILL_REFERENCE_REVIEW_LENGTH:{path.name}:{line_count}")
        if path.parent == GPT and re.match(r"^\d{2}_", path.name):
            if line_count > 500:
                errors.append(f"GPT_KNOWLEDGE_FILE_TOO_LONG:{path.name}:{line_count}")
            elif line_count > (
                400 if path.name == "05_分镜剧本输出模板.md" else 350
            ):
                warnings.append(f"GPT_KNOWLEDGE_REVIEW_LENGTH:{path.name}:{line_count}")

    combined_deployable = "\n".join(decoded.values())
    for token in LEAKAGE_TOKENS:
        if token in combined_deployable:
            errors.append(f"PRIVATE_REGRESSION_LEAK:{token}")
    for token in STALE_CONFLICTS:
        if token in combined_deployable:
            errors.append(f"STALE_CONFLICT:{token}")
    deployable_lower = combined_deployable.lower()
    for token in VAGUE_PHRASES:
        if token.lower() in deployable_lower:
            errors.append(f"VAGUE_PHRASE:{token}")

    skill_text = decoded.get(SKILL / "SKILL.md", "")
    references = re.findall(r"`(references/[^`]+\.md)`", skill_text)
    for relative in references:
        if not (SKILL / relative).is_file():
            errors.append(f"BROKEN_REFERENCE:{relative}")

    validator = load_validator()
    schema_text = decoded.get(SKILL / "references" / "storyboard-output.md", "")
    cut_block_match = re.search(
        r"## Canonical 14-Field CUT.*?```text\n(?P<body>.*?)\n```",
        schema_text,
        re.DOTALL,
    )
    if not cut_block_match:
        errors.append("CUT_SCHEMA_BLOCK_MISSING")
    else:
        names = re.findall(r"(?m)^-\s+([^：:\n]+)[：:]", cut_block_match.group("body"))
        if names != validator.CUT_FIELDS:
            errors.append(f"CUT_SCHEMA_MISMATCH:{names}")

    gpt_schema_text = decoded.get(GPT / "05_分镜剧本输出模板.md", "")
    gpt_cut_block_match = re.search(
        r"## 默认14字段CUT.*?```text\n(?P<body>.*?)\n```",
        gpt_schema_text,
        re.DOTALL,
    )
    if not gpt_cut_block_match:
        errors.append("GPT_CUT_SCHEMA_BLOCK_MISSING")
    else:
        names = re.findall(
            r"(?m)^-\s+([^：:\n]+)[：:]", gpt_cut_block_match.group("body")
        )
        if names != validator.CUT_FIELDS:
            errors.append(f"GPT_CUT_SCHEMA_MISMATCH:{names}")

    for label, text, heading in (
        ("SKILL", schema_text, "GEN-CUT Map"),
        ("GPT", gpt_schema_text, "GEN-CUT映射"),
    ):
        gen_block_match = re.search(
            rf"## {re.escape(heading)}.*?```text\n(?P<body>.*?)\n```",
            text,
            re.DOTALL,
        )
        if not gen_block_match:
            errors.append(f"{label}_GEN_SCHEMA_BLOCK_MISSING")
            continue
        names = re.findall(
            r"(?m)^-\s+([^：:\n]+)[：:]", gen_block_match.group("body")
        )
        if names != validator.GEN_FIELDS:
            errors.append(f"{label}_GEN_SCHEMA_MISMATCH:{names}")

    numbered = sorted(path.name for path in GPT.glob("[0-9][0-9]_*.md"))
    expected_prefixes = [f"{number:02d}_" for number in range(14)]
    if len(numbered) != 14:
        errors.append(f"GPT_NUMBERED_COUNT:{len(numbered)}")
    for prefix in expected_prefixes:
        if not any(name.startswith(prefix) for name in numbered):
            errors.append(f"GPT_NUMBERED_MISSING:{prefix}")
    if len([path for path in GPT.iterdir() if path.is_file()]) != 16:
        errors.append("GPT_TOTAL_FILE_COUNT")
    gpt_bytes = sum(path.stat().st_size for path in GPT.iterdir() if path.is_file())
    if gpt_bytes > 512 * 1024:
        errors.append(f"GPT_KNOWLEDGE_TOTAL_TOO_LARGE:{gpt_bytes}")

    owner_checks = {
        "00_GPT创建配置.md": "唯一 Owner",
        "01_主控执行协议.md": "唯一执行顺序 owner",
        "05_分镜剧本输出模板.md": "唯一结构 owner",
        "08_事件真实性与回环.md": "唯一 owner",
        "09_对白表演与同步.md": "唯一 owner",
        "10_时长合同与生成单元.md": "唯一 owner",
        "11_正典修订与影响面.md": "唯一 owner",
        "12_资产与场景母版锁.md": "唯一 owner",
        "13_术语与可迁移性锁.md": "唯一 owner",
    }
    for name, phrase in owner_checks.items():
        if phrase not in decoded.get(GPT / name, ""):
            errors.append(f"GPT_OWNER_DECLARATION:{name}")

    rights_token_locations = {
        "rights-unverified": (
            SKILL / "references" / "terminology-and-portability.md",
            SKILL / "references" / "open-source-research.md",
            GPT / "13_术语与可迁移性锁.md",
            GPT / "04_网络与开源调研规则.md",
        ),
        "rights-asserted": (
            SKILL / "references" / "terminology-and-portability.md",
            SKILL / "references" / "open-source-research.md",
            GPT / "13_术语与可迁移性锁.md",
            GPT / "04_网络与开源调研规则.md",
        ),
        "rights-verified": (
            SKILL / "references" / "terminology-and-portability.md",
            SKILL / "references" / "open-source-research.md",
            GPT / "13_术语与可迁移性锁.md",
            GPT / "04_网络与开源调研规则.md",
        ),
        "trait-reference": (
            SKILL / "references" / "terminology-and-portability.md",
            SKILL / "references" / "open-source-research.md",
            GPT / "13_术语与可迁移性锁.md",
            GPT / "04_网络与开源调研规则.md",
        ),
        "exact-dependent": (
            SKILL / "references" / "terminology-and-portability.md",
            SKILL / "references" / "open-source-research.md",
            GPT / "13_术语与可迁移性锁.md",
            GPT / "04_网络与开源调研规则.md",
        ),
        "AUTHORIZED-ASSET": (
            SKILL / "references" / "terminology-and-portability.md",
            SKILL / "references" / "storyboard-output.md",
            GPT / "13_术语与可迁移性锁.md",
            GPT / "05_分镜剧本输出模板.md",
        ),
        "AUTHORIZED-LYRIC": (
            SKILL / "references" / "terminology-and-portability.md",
            SKILL / "references" / "storyboard-output.md",
            GPT / "13_术语与可迁移性锁.md",
            GPT / "05_分镜剧本输出模板.md",
        ),
        "AUTHORIZED-DIALOGUE": (
            SKILL / "references" / "terminology-and-portability.md",
            SKILL / "references" / "storyboard-output.md",
            GPT / "13_术语与可迁移性锁.md",
            GPT / "05_分镜剧本输出模板.md",
        ),
        "【受保护文本填入表】": (
            SKILL / "references" / "terminology-and-portability.md",
            SKILL / "references" / "storyboard-output.md",
            SKILL / "references" / "quality-checks.md",
            GPT / "13_术语与可迁移性锁.md",
            GPT / "05_分镜剧本输出模板.md",
            GPT / "06_质量闸.md",
        ),
        "版权出处与使用声明": (
            SKILL / "SKILL.md",
            SKILL / "references" / "storyboard-output.md",
            SKILL / "references" / "quality-checks.md",
            GPT / "01_主控执行协议.md",
            GPT / "05_分镜剧本输出模板.md",
            GPT / "06_质量闸.md",
        ),
    }
    for token, paths in rights_token_locations.items():
        for path in paths:
            if token not in decoded.get(path, ""):
                errors.append(f"RIGHTS_TOKEN_PARITY:{token}:{path.name}")

    expected_scene_map_fields = [
        "EVT/场景任务与有意义变化",
        "观众视角、当前已知与延迟信息",
        "视点序列与合法进入/退出触发",
        "关键画面/戏点",
        "重要信息 / 次要信息 / 应排除干扰",
        "SCN-ID、空间地标与前中后景",
        "人物/道具起始位置",
        "轴线、视线、屏幕方向、入画/出画",
        "视觉焦点路径与主运动方向",
        "35mm等效焦段组",
        "光线、天气、色彩、服装、Asset-ID连续性",
        "情绪与表演曲线",
        "转场主机制与声音辅助",
    ]
    for label, text, heading in (
        ("SKILL", schema_text, "Scene Director Map"),
        ("GPT", gpt_schema_text, "场景导演图"),
    ):
        map_match = re.search(
            rf"## {re.escape(heading)}.*?```text\n(?P<body>.*?)\n```",
            text,
            re.DOTALL,
        )
        if not map_match:
            errors.append(f"{label}_SCENE_DIRECTOR_MAP_BLOCK_MISSING")
            continue
        map_fields = re.findall(
            r"(?m)^-\s+([^：\n]+)：",
            map_match.group("body"),
        )
        if map_fields != expected_scene_map_fields:
            errors.append(
                f"{label}_SCENE_DIRECTOR_MAP_FIELDS:{map_fields}"
            )

    for label, text, heading, final_label in (
        (
            "SKILL",
            schema_text,
            "Standard Deliverable",
            "【版权出处与使用声明】",
        ),
        (
            "GPT",
            gpt_schema_text,
            "标准交付顺序",
            "【版权出处与使用声明】",
        ),
    ):
        order_match = re.search(
            rf"## {re.escape(heading)}.*?```text\n(?P<body>.*?)\n```",
            text,
            re.DOTALL,
        )
        if not order_match:
            errors.append(f"{label}_DELIVERY_ORDER_BLOCK_MISSING")
            continue
        order_lines = [
            line.strip()
            for line in order_match.group("body").splitlines()
            if line.strip()
        ]
        if not order_lines or not order_lines[-1].startswith(final_label):
            errors.append(f"{label}_RIGHTS_NOTICE_NOT_LAST")

    for label, text, heading in (
        ("SKILL", schema_text, "Sound, BGM, and Post Layers"),
        ("GPT", gpt_schema_text, "声音、BGM与后期层"),
    ):
        bgm_match = re.search(
            rf"## {re.escape(heading)}.*?```text\n(?P<body>.*?)\n```",
            text,
            re.DOTALL,
        )
        if not bgm_match:
            errors.append(f"{label}_BGM_BLOCK_MISSING")
        elif "rights_status" in bgm_match.group("body"):
            errors.append(f"{label}_RIGHTS_NOTICE_LEAKED_BEFORE_END")

    try:
        json.loads(
            decoded.get(
                SKILL / "scripts" / "schemas" / "delivery-contract.schema.json", ""
            )
        )
    except json.JSONDecodeError as exc:
        errors.append(f"CONTRACT_SCHEMA_JSON:{exc}")

    yaml_text = decoded.get(SKILL / "agents" / "openai.yaml", "")
    if "14-field" not in yaml_text or "GEN" not in yaml_text:
        errors.append("OPENAI_YAML_ROUTING")

    payload = {
        "checked_files": len(files),
        "errors": sorted(errors),
        "gpt_numbered_files": len(numbered),
        "gpt_total_files": len([path for path in GPT.iterdir() if path.is_file()]),
        "health": {
            "gpt_total_bytes": gpt_bytes,
            "largest_gpt_numbered_lines": max(
                (line_counts.get(path, 0) for path in GPT.glob("[0-9][0-9]_*.md")),
                default=0,
            ),
            "largest_skill_reference_lines": max(
                (
                    line_counts.get(path, 0)
                    for path in (SKILL / "references").glob("*.md")
                ),
                default=0,
            ),
            "skill_router_lines": line_counts.get(SKILL / "SKILL.md", 0),
        },
        "skill_reference_routes": len(references),
        "status": "pass" if not errors else "fail",
        "warnings": sorted(warnings),
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "static_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
