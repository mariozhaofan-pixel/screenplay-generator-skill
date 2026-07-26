#!/usr/bin/env python3
"""Validate a screenplay/storyboard delivery without modifying it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


CUT_FIELDS = [
    "场景",
    "剧情/故事变化",
    "人物与连续性",
    "演员调度/动作节拍",
    "情绪与表演",
    "台词/字幕",
    "叙事视点/知识边界",
    "摄影",
    "视觉焦点/动势",
    "声音",
    "剪辑/转场相位",
    "导演意图",
    "AI画面事实",
    "连续性/资产",
]

GEN_FIELDS = [
    "类型",
    "因果/叙事任务",
    "触发",
    "选择/行动",
    "对方可见反应",
    "新结束状态",
    "场景/时空变化",
    "视点序列",
    "对白负载/D-IDs",
    "Asset/SCN IDs",
    "IN状态",
    "OUT状态",
]

SCENE_DIRECTOR_FIELDS = [
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

CUT_HEADING_RE = re.compile(
    r"(?m)^###\s+CUT-(?P<number>\d{3})\s*[|｜]\s*(?P<beat>S\d+-B\d+)\s*$"
)
GEN_HEADING_RE = re.compile(
    r"(?m)^###\s+GEN-(?P<number>\d{3})\s*[|｜]\s*"
    r"CUT-(?P<start>\d{3})\s*[—–-]+\s*CUT-(?P<end>\d{3})\s*$"
)
SCENE_DIRECTOR_HEADING_RE = re.compile(
    r"(?m)^(?P<prefix>#{1,6}\s*)?【(?P<scene>S\d+)\s+场景导演图】\s*$"
)
BLOCK_BOUNDARY_RE = re.compile(r"(?m)^(?:#{1,3}\s+|【[^\n]+】\s*$)")
FIELD_RE = re.compile(r"(?m)^-\s+([^：:\n]+)[：:]\s*(.*)$")
BEAT_DECL_RE = re.compile(
    r"(?m)^(?:#{1,6}\s*)?(S\d+-B\d+)"
    r"(?:(?:\s*[|｜]\s*.*)|(?:\s+.+))?\s*$"
)
AUTH_RE = re.compile(
    r"(?m)^\*\*(?P<id>D-\d{3})\s*\|\s*(?P<role>[^|]+?)\s*\|\s*"
    r"(?P<mode>[^|]+?)\s*\|\s*口型=(?P<lip>[^：:]+?)[：:]\*\*\s*(?P<text>.*)$"
)
FRAGMENT_RE = re.compile(
    r"(?m)^\s+-\s+(?P<id>D-\d{3})\[(?P<part>\d+)/(?P<total>\d+)\]\s*"
    r"\|\s*剧情对白\s*\|\s*(?P<role>[^|]+?)\s*\|\s*(?P<mode>[^|]+?)\s*"
    r"\|\s*口型=(?P<lip>[^|]+?)\s*\|\s*文本=(?P<text>.*)$"
)
TIME_VALUE_RE = re.compile(
    r"(?i)(?<![\w.-])\d+(?:\.\d+)?\s*(?:秒|分钟|小时|s|sec(?:onds?)?|min(?:utes?)?|hours?)\b"
)
TIMECODE_RE = re.compile(r"(?<!\d)\d{1,2}:\d{2}(?::\d{2})?(?:[.:]\d+)?(?!\d)")
FRAME_VALUE_RE = re.compile(r"(?<![\w.-])\d+(?:\.\d+)?\s*帧")
ID_RE = re.compile(r"\b(?:D|EVT|ASSET|SCN)-\d{3}\b")


class ConstraintError(Exception):
    """The document is parseable but violates its delivery contract."""


class ParseError(Exception):
    """The document or contract cannot be parsed reliably."""


@dataclass(frozen=True)
class Issue:
    code: str
    location: str
    message: str


@dataclass
class Cut:
    number: int
    cut_id: str
    beat_id: str
    fields: list[tuple[str, str]]
    block: str

    @property
    def field_map(self) -> dict[str, str]:
        return {name: value for name, value in self.fields}


@dataclass
class Gen:
    number: int
    gen_id: str
    start_cut: int
    end_cut: int
    fields: list[tuple[str, str]]
    block: str

    @property
    def field_map(self) -> dict[str, str]:
        return {name: value for name, value in self.fields}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm_path(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def read_utf8_nfc(path: Path, label: str) -> tuple[bytes, str]:
    try:
        data = path.read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ParseError(f"cannot read {label} as UTF-8: {exc}") from exc
    if unicodedata.normalize("NFC", text) != text:
        raise ConstraintError(f"{label} is not Unicode NFC")
    return data, text


def load_contract(path: Path) -> tuple[bytes, dict[str, Any]]:
    data, text = read_utf8_nfc(path, "contract")
    try:
        value = json.loads(text, parse_float=Decimal)
    except (json.JSONDecodeError, InvalidOperation) as exc:
        raise ParseError(f"invalid contract JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ParseError("contract root must be a JSON object")
    validate_contract_shape(value)
    return data, value


def validate_contract_shape(contract: dict[str, Any]) -> None:
    allowed: dict[str, set[str] | None] = {
        "schema_version": None,
        "assets": {
            "allow_multi_master_scenes",
            "required",
            "scene_master_required",
            "verify_local_paths",
        },
        "brief": {
            "forbidden_exact",
            "required_exact",
            "required_regex",
            "semantic_review_required",
            "semantic_reviewed",
        },
        "dialogue": {
            "mode",
            "semantic_review_required",
            "semantic_reviewed",
        },
        "directing": {"require_literal_labels", "scene_maps_required"},
        "events": {"callbacks_required"},
        "gen": {"require_full_cut_coverage", "required"},
        "revision": {
            "deprecated_paths",
            "enabled",
            "forbidden_exact",
            "forbidden_regex",
            "impact_report_path",
            "semantic_residue_reviewed",
            "source_canon_path",
            "source_sha256",
        },
        "rights": {
            "notice_must_be_last",
            "require_literal_label",
            "required",
            "required_status",
            "required_tokens",
            "semantic_review_required",
            "semantic_reviewed",
        },
        "schema": {"allow_legacy_12", "legacy_input"},
        "style": {"forbidden_exact"},
        "timing": {
            "duration_tolerance",
            "gen_limit",
            "maximum",
            "media_sources",
            "minimum",
            "mode",
            "total",
            "total_kind",
        },
        "viewpoint": {"responsibility_requirements"},
    }
    unknown_root = sorted(set(contract) - set(allowed))
    if unknown_root:
        raise ParseError(f"unknown contract properties: {unknown_root}")
    if contract.get("schema_version") != 1:
        raise ParseError("contract schema_version must be 1")
    for required in ("timing", "dialogue"):
        if not isinstance(contract.get(required), dict):
            raise ParseError(f"contract.{required} must be an object")
    for key, nested_allowed in allowed.items():
        if nested_allowed is None or key not in contract:
            continue
        value = contract[key]
        if not isinstance(value, dict):
            raise ParseError(f"contract.{key} must be an object")
        unknown_nested = sorted(set(value) - nested_allowed)
        if unknown_nested:
            raise ParseError(f"unknown contract.{key} properties: {unknown_nested}")


def as_decimal(value: Any, label: str) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ParseError(f"{label} is not a decimal: {value}") from exc


def add_issue(
    target: list[Issue], code: str, location: str, message: str
) -> None:
    target.append(Issue(code=code, location=location, message=message))


def parse_blocks(
    text: str, pattern: re.Pattern[str], block_type: str
) -> list[tuple[re.Match[str], str]]:
    matches = list(pattern.finditer(text))
    blocks: list[tuple[re.Match[str], str]] = []
    for match in matches:
        next_heading = BLOCK_BOUNDARY_RE.search(text, match.end())
        end = next_heading.start() if next_heading else len(text)
        blocks.append((match, text[match.end() : end]))
    return blocks


def parse_cuts(text: str) -> list[Cut]:
    cuts: list[Cut] = []
    for match, block in parse_blocks(text, CUT_HEADING_RE, "CUT"):
        fields = [(m.group(1).strip(), m.group(2).strip()) for m in FIELD_RE.finditer(block)]
        number = int(match.group("number"))
        cuts.append(
            Cut(
                number=number,
                cut_id=f"CUT-{number:03d}",
                beat_id=match.group("beat"),
                fields=fields,
                block=block,
            )
        )
    return cuts


def parse_gens(text: str) -> list[Gen]:
    gens: list[Gen] = []
    for match, block in parse_blocks(text, GEN_HEADING_RE, "GEN"):
        fields = [(m.group(1).strip(), m.group(2).strip()) for m in FIELD_RE.finditer(block)]
        number = int(match.group("number"))
        gens.append(
            Gen(
                number=number,
                gen_id=f"GEN-{number:03d}",
                start_cut=int(match.group("start")),
                end_cut=int(match.group("end")),
                fields=fields,
                block=block,
            )
        )
    return gens


def strip_level3_blocks(text: str) -> str:
    spans: list[tuple[int, int]] = []
    for pattern in (CUT_HEADING_RE, GEN_HEADING_RE):
        for match, block in parse_blocks(text, pattern, "block"):
            spans.append((match.start(), match.end() + len(block)))
    chars = list(text)
    for start, end in spans:
        chars[start:end] = "\n" * (end - start)
    return "".join(chars)


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def extract_section(text: str, marker: str) -> str:
    lines = text.splitlines()
    start = None
    plain_marker = marker.strip("【】")
    for index, line in enumerate(lines):
        if marker in line or re.fullmatch(
            rf"\s*#{{1,6}}\s*{re.escape(plain_marker)}\s*", line
        ):
            start = index + 1
            break
    if start is None:
        return ""
    collected: list[str] = []
    for line in lines[start:]:
        if line.strip().startswith("【") and line.strip().endswith("】"):
            break
        if re.match(r"^#{1,2}\s+", line):
            break
        collected.append(line)
    return "\n".join(collected)


def nonempty(value: str) -> bool:
    return value.strip() not in {"", "无", "不适用", "未指定", "N/A", "n/a"}


def has_disallowed_timecode(text: str) -> bool:
    for match in TIMECODE_RE.finditer(text):
        if match.group(0) == "9:16":
            continue
        return True
    return False


def validate_cut_schema(
    cuts: list[Cut], contract: dict[str, Any], errors: list[Issue], warnings: list[Issue]
) -> None:
    schema = contract.get("schema", {})
    allow_legacy_12 = bool(schema.get("allow_legacy_12", False))
    legacy_input = bool(schema.get("legacy_input", False))

    if not cuts:
        add_issue(errors, "CUT_MISSING", "document", "no CUT blocks were found")
        return

    numbers = [cut.number for cut in cuts]
    if len(numbers) != len(set(numbers)):
        add_issue(errors, "CUT_DUPLICATE", "CUT", "CUT IDs are not unique")
    expected = list(range(1, len(cuts) + 1))
    if numbers != expected:
        add_issue(
            errors,
            "CUT_SEQUENCE",
            "CUT",
            f"CUT IDs must be consecutive from 001; found {numbers}",
        )

    legacy_count = 0
    for cut in cuts:
        names = [name for name, _ in cut.fields]
        if len(names) == 12 and allow_legacy_12 and legacy_input:
            legacy_count += 1
            continue
        if names != CUT_FIELDS:
            missing = [name for name in CUT_FIELDS if name not in names]
            extra = [name for name in names if name not in CUT_FIELDS]
            add_issue(
                errors,
                "CUT_SCHEMA",
                cut.cut_id,
                f"expected canonical 14 fields in order; missing={missing}, extra={extra}, found={names}",
            )
            continue
        transition = cut.field_map.get("剪辑/转场相位", "")
        if len([part for part in re.split(r"(?:->|→)", transition) if part.strip()]) < 5:
            add_issue(
                errors,
                "TRANSITION_PHASE",
                cut.cut_id,
                "transition must state story function -> source phase -> cut point -> destination phase -> continuity variable",
            )
    if legacy_count:
        add_issue(
            warnings,
            "CUT_LEGACY_12",
            "CUT",
            f"{legacy_count} historical 12-field CUTs accepted in compatibility mode",
        )


def validate_beat_closure(
    text: str, cuts: list[Cut], errors: list[Issue], warnings: list[Issue]
) -> None:
    non_blocks = strip_level3_blocks(text)
    declared = set(BEAT_DECL_RE.findall(non_blocks))
    if not declared:
        add_issue(
            errors,
            "BEAT_DECLARATION_MISSING",
            "screenplay",
            "no standalone screenplay Beat IDs were found",
        )
        return
    for cut in cuts:
        if cut.beat_id not in declared:
            add_issue(
                errors,
                "BEAT_REFERENCE",
                cut.cut_id,
                f"referenced Beat ID is not declared in the screenplay: {cut.beat_id}",
            )


def validate_scene_director_maps(
    text: str,
    cuts: list[Cut],
    contract: dict[str, Any],
    errors: list[Issue],
    warnings: list[Issue],
) -> None:
    directing = contract.get("directing", {})
    if not directing.get("scene_maps_required", False):
        return

    matches = list(SCENE_DIRECTOR_HEADING_RE.finditer(text))
    maps: dict[str, tuple[re.Match[str], str]] = {}
    cut_section = re.search(
        r"(?m)^(?:#{1,6}\s*)?【逐CUT完整分镜】\s*$",
        text,
    )
    first_cut = CUT_HEADING_RE.search(text)
    fallback_end = (
        cut_section.start()
        if cut_section
        else first_cut.start()
        if first_cut
        else len(text)
    )

    for index, match in enumerate(matches):
        scene_id = match.group("scene")
        if scene_id in maps:
            add_issue(
                errors,
                "SCENE_DIRECTOR_MAP_DUPLICATE",
                scene_id,
                "scene director map appears more than once",
            )
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else fallback_end
        maps[scene_id] = (match, text[match.end() : end])

    required_scenes = sorted({cut.beat_id.split("-B", 1)[0] for cut in cuts})
    for scene_id in required_scenes:
        entry = maps.get(scene_id)
        if entry is None:
            add_issue(
                errors,
                "SCENE_DIRECTOR_MAP_MISSING",
                scene_id,
                "every scene represented by CUTs requires a director map",
            )
            continue

        match, block = entry
        if directing.get("require_literal_labels", True) and match.group("prefix"):
            add_issue(
                errors,
                "SCENE_DIRECTOR_MAP_LABEL",
                scene_id,
                f"new output must use the literal 【{scene_id} 场景导演图】 label",
            )

        fields = [
            (field.group(1).strip(), field.group(2).strip())
            for field in FIELD_RE.finditer(block)
        ]
        names = [name for name, _ in fields]
        if names != SCENE_DIRECTOR_FIELDS:
            missing = [name for name in SCENE_DIRECTOR_FIELDS if name not in names]
            extra = [name for name in names if name not in SCENE_DIRECTOR_FIELDS]
            add_issue(
                errors,
                "SCENE_DIRECTOR_MAP_SCHEMA",
                scene_id,
                "director map fields/order mismatch; "
                f"missing={missing}, extra={extra}, actual={names}",
            )
            continue
        for name, value in fields:
            if not nonempty(value):
                add_issue(
                    errors,
                    "SCENE_DIRECTOR_MAP_EMPTY",
                    f"{scene_id}.{name}",
                    "director map field must be explicit or state 无；原因=...",
                )


def parse_ordered_map(raw: str, total: int) -> list[str] | None:
    tokens = [token.strip() for token in re.split(r"[；;]", raw) if token.strip()]
    if not tokens:
        return None
    mapped: dict[int, str] = {}
    plain: list[str] = []
    for token in tokens:
        match = re.match(r"^(.*?)@(\d+)/(\d+)$", token)
        if match:
            index = int(match.group(2))
            declared_total = int(match.group(3))
            if declared_total != total or index < 1 or index > total:
                return None
            mapped[index] = match.group(1).strip()
        else:
            plain.append(token)
    if mapped and plain:
        return None
    if mapped:
        if set(mapped) != set(range(1, total + 1)):
            return None
        return [mapped[index] for index in range(1, total + 1)]
    if len(plain) == 1:
        return plain * total
    if len(plain) == total:
        return plain
    return None


def parse_lock_rows(text: str) -> dict[str, dict[str, str]]:
    section = extract_section(text, "【完整对白锁定表】")
    rows: dict[str, dict[str, str]] = {}
    for line in section.splitlines():
        cells = split_table_row(line)
        if len(cells) != 7 or not re.fullmatch(r"D-\d{3}", cells[0]):
            continue
        rows[cells[0]] = {
            "category": cells[1],
            "role": cells[2],
            "text": cells[3],
            "mode": cells[4],
            "lip": cells[5],
            "mapping": cells[6],
        }
    return rows


def validate_dialogue(
    text: str,
    cuts: list[Cut],
    contract: dict[str, Any],
    errors: list[Issue],
    warnings: list[Issue],
) -> None:
    dialogue_mode = contract.get("dialogue", {}).get("mode", "draft-sync")
    authorities: list[dict[str, str]] = []
    seen_auth: set[str] = set()
    for match in AUTH_RE.finditer(text):
        item = {key: match.group(key).strip() for key in ("id", "role", "mode", "lip", "text")}
        if item["id"] in seen_auth:
            add_issue(errors, "DIALOGUE_ID_DUPLICATE", item["id"], "duplicate authoritative D-ID")
        seen_auth.add(item["id"])
        authorities.append(item)

    if dialogue_mode == "production-lock" and not authorities:
        add_issue(
            errors,
            "DIALOGUE_AUTHORITY_MISSING",
            "screenplay",
            "production-lock requires authoritative D-ID lines",
        )
        return

    authority_by_id = {item["id"]: item for item in authorities}
    authority_numbers = [int(item["id"].split("-")[1]) for item in authorities]
    if authority_numbers and authority_numbers != list(range(1, len(authority_numbers) + 1)):
        add_issue(
            errors,
            "DIALOGUE_ID_SEQUENCE",
            "screenplay",
            f"D-IDs must be sequential from 001; found {authority_numbers}",
        )

    fragments: dict[str, list[dict[str, Any]]] = {}
    first_fragment_order: list[str] = []
    for cut in cuts:
        for match in FRAGMENT_RE.finditer(cut.block):
            item: dict[str, Any] = {
                "cut": cut.cut_id,
                "id": match.group("id").strip(),
                "part": int(match.group("part")),
                "total": int(match.group("total")),
                "role": match.group("role").strip(),
                "mode": match.group("mode").strip(),
                "lip": match.group("lip").strip(),
                "text": match.group("text").rstrip("\r"),
            }
            if item["id"] not in fragments:
                first_fragment_order.append(item["id"])
            fragments.setdefault(item["id"], []).append(item)

    lock_rows = parse_lock_rows(text)
    if dialogue_mode == "production-lock" and not lock_rows:
        add_issue(
            errors,
            "DIALOGUE_LOCK_MISSING",
            "dialogue-lock",
            "production-lock requires the complete dialogue-lock table",
        )

    auth_order = [item["id"] for item in authorities]
    if first_fragment_order and first_fragment_order != auth_order:
        add_issue(
            errors,
            "DIALOGUE_ORDER",
            "CUT dialogue",
            f"first audible fragment order {first_fragment_order} differs from screenplay order {auth_order}",
        )

    for dialogue_id, authority in authority_by_id.items():
        items = fragments.get(dialogue_id, [])
        if not items:
            add_issue(
                errors,
                "DIALOGUE_FRAGMENT_MISSING",
                dialogue_id,
                "authoritative line has no CUT fragment",
            )
            continue
        totals = {item["total"] for item in items}
        if len(totals) != 1:
            add_issue(errors, "DIALOGUE_FRAGMENT_TOTAL", dialogue_id, "fragment totals disagree")
            continue
        total = totals.pop()
        parts = [item["part"] for item in items]
        if parts != list(range(1, total + 1)):
            add_issue(
                errors,
                "DIALOGUE_FRAGMENT_SEQUENCE",
                dialogue_id,
                f"expected fragments 1..{total}; found {parts}",
            )
        joined = "".join(str(item["text"]) for item in items)
        if joined != authority["text"]:
            add_issue(
                errors,
                "DIALOGUE_TEXT_MISMATCH",
                dialogue_id,
                "ordered CUT fragments do not exactly equal authoritative text and punctuation",
            )
        if any(item["role"] != authority["role"] for item in items):
            add_issue(errors, "DIALOGUE_ROLE_MISMATCH", dialogue_id, "CUT fragment role differs")

        authority_modes = parse_ordered_map(authority["mode"], total)
        authority_lips = parse_ordered_map(authority["lip"], total)
        fragment_modes = [str(item["mode"]) for item in items]
        fragment_lips = [str(item["lip"]) for item in items]
        if authority_modes is None or authority_modes != fragment_modes:
            add_issue(
                errors,
                "DIALOGUE_SOURCE_MISMATCH",
                dialogue_id,
                "screenplay source-mode map differs from CUT fragments",
            )
        if authority_lips is None or authority_lips != fragment_lips:
            add_issue(
                errors,
                "DIALOGUE_LIP_MISMATCH",
                dialogue_id,
                "screenplay lip-sync map differs from CUT fragments",
            )

        if dialogue_mode == "production-lock":
            lock = lock_rows.get(dialogue_id)
            if not lock:
                add_issue(errors, "DIALOGUE_LOCK_ROW_MISSING", dialogue_id, "lock row is missing")
                continue
            if lock["category"] != "剧情对白":
                add_issue(errors, "DIALOGUE_CATEGORY", dialogue_id, "lock category must be 剧情对白")
            if lock["role"] != authority["role"]:
                add_issue(errors, "DIALOGUE_LOCK_ROLE", dialogue_id, "lock role differs")
            if lock["text"] != authority["text"]:
                add_issue(errors, "DIALOGUE_LOCK_TEXT", dialogue_id, "lock text differs")
            lock_modes = parse_ordered_map(lock["mode"], total)
            lock_lips = parse_ordered_map(lock["lip"], total)
            if lock_modes != fragment_modes:
                add_issue(errors, "DIALOGUE_LOCK_SOURCE", dialogue_id, "lock source map differs")
            if lock_lips != fragment_lips:
                add_issue(errors, "DIALOGUE_LOCK_LIP", dialogue_id, "lock lip map differs")
            actual_mapping = "；".join(
                f"{item['cut']}[{item['part']}/{item['total']}]" for item in items
            )
            normalized_mapping = lock["mapping"].replace(";", "；").replace(" ", "")
            if normalized_mapping != actual_mapping.replace(" ", ""):
                add_issue(
                    errors,
                    "DIALOGUE_LOCK_MAPPING",
                    dialogue_id,
                    "lock CUT/fragment mapping differs",
                )

    for dialogue_id in fragments:
        if dialogue_id not in authority_by_id:
            add_issue(
                errors,
                "DIALOGUE_ORPHAN_FRAGMENT",
                dialogue_id,
                "CUT fragment has no authoritative screenplay line",
            )
    if dialogue_mode == "production-lock":
        for dialogue_id in lock_rows:
            if dialogue_id not in authority_by_id:
                add_issue(
                    errors,
                    "DIALOGUE_ORPHAN_LOCK",
                    dialogue_id,
                    "lock row has no authoritative screenplay line",
                )

    for prefix in ("LYR", "CARD", "TXT"):
        if re.search(rf"\b{prefix}-\d{{3}}\b", text) and prefix == "LYR":
            pass
    if dialogue_mode not in {"draft-sync", "production-lock"}:
        add_issue(
            errors,
            "DIALOGUE_MODE",
            "contract",
            f"unsupported dialogue mode: {dialogue_mode}",
        )
    dialogue_contract = contract.get("dialogue", {})
    if dialogue_contract.get("semantic_review_required") and not dialogue_contract.get(
        "semantic_reviewed", False
    ):
        add_issue(
            warnings,
            "DIALOGUE_SEMANTIC_REVIEW",
            "contract",
            "spoken-naturalness and performance review is still required",
        )


def parse_duration_cell(value: str) -> Decimal | None:
    cleaned = value.strip()
    if cleaned in {"", "-", "未指定", "N/A", "n/a"}:
        return None
    cleaned = re.sub(r"(?i)\s*(?:秒|s|sec(?:onds?)?)\s*$", "", cleaned)
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_budget_rows(text: str, legacy_input: bool = False) -> list[dict[str, Any]]:
    section = extract_section(text, "【时长与生成合同】")
    rows: list[dict[str, Any]] = []
    for line in section.splitlines():
        cells = split_table_row(line)
        row_id = re.match(
            r"^(?P<id>GEN-\d{3}|S\d+(?:-S\d+)?)(?:\s*/.*)?$", cells[0]
        )
        if len(cells) < 5 or not row_id:
            continue
        rows.append(
            {
                "id": row_id.group("id"),
                "cut_range": cells[1],
                "planned": parse_duration_cell(cells[2]),
                "limit": parse_duration_cell(cells[3]),
                "feasibility": cells[4],
            }
        )
    if rows or not legacy_input:
        return rows
    for line in text.splitlines():
        cells = split_table_row(line)
        if len(cells) < 4 or cells[0] in {"总计", "**总计**"}:
            continue
        planned = parse_duration_cell(cells[2].replace("**", ""))
        if planned is None or not re.search(r"CUT-\d{3}", cells[1]):
            continue
        rows.append(
            {
                "id": f"LEGACY-{len(rows) + 1:03d}",
                "cut_range": cells[1],
                "planned": planned,
                "limit": None,
                "feasibility": cells[3],
            }
        )
    return rows


def validate_mode_declaration(
    text: str,
    contract: dict[str, Any],
    errors: list[Issue],
    warnings: list[Issue],
) -> None:
    schema = contract.get("schema", {})
    legacy_input = bool(schema.get("legacy_input", False))
    timing_mode = str(contract.get("timing", {}).get("mode", "silent-default"))
    mode_lines = re.findall(
        r"(?m)^[ \t]*-[ \t]*`?timing_mode`?[ \t]*[：:][ \t]*"
        r"`?(silent-default|contract-budget|media-frame-lock)`?"
        r"[ \t]*[。.]?[ \t]*\r?$",
        text,
    )
    legacy_lines = re.findall(
        r"(?m)^[ \t]*-[ \t]*(?:当前模式|时长模式)[：:].*$",
        text,
    )

    if legacy_input and not mode_lines:
        add_issue(
            warnings,
            "MODE_DECLARATION_LEGACY",
            "document",
            "legacy input has no canonical timing_mode declaration",
        )
    else:
        if len(mode_lines) != 1:
            add_issue(
                errors,
                "MODE_DECLARATION",
                "document",
                f"expected exactly one canonical timing_mode declaration; found {len(mode_lines)}",
            )
        elif mode_lines[0] != timing_mode:
            add_issue(
                errors,
                "MODE_TIMING_MISMATCH",
                "document",
                f"document declares {mode_lines[0]} but contract requires {timing_mode}",
            )
        elif not re.search(
            rf"(?m)^- timing_mode：{re.escape(timing_mode)}\r?$", text
        ):
            add_issue(
                errors,
                "MODE_DECLARATION_FORMAT",
                "document",
                "new output must serialize timing_mode as a plain canonical list item",
            )

    if legacy_lines:
        add_issue(
            warnings if legacy_input else errors,
            "MODE_LEGACY_ALIAS",
            "document",
            "replace 当前模式/时长模式 with timing_mode and active_modules",
        )

    module_lines = re.findall(
        r"(?m)^[ \t]*-[ \t]*`?active_modules`?[ \t]*[：:][ \t]*(.+?)[ \t]*\r?$",
        text,
    )
    expected_modules: set[str] = set()
    if contract.get("revision", {}).get("enabled"):
        expected_modules.add("revision")
    if contract.get("dialogue", {}).get("mode") == "production-lock":
        expected_modules.add("production-lock")
    if contract.get("gen", {}).get("required"):
        expected_modules.add("GEN")
    assets = contract.get("assets", {})
    if assets.get("required") or assets.get("scene_master_required"):
        expected_modules.add("Asset/SCN")

    if legacy_input and not module_lines:
        add_issue(
            warnings,
            "MODULE_DECLARATION_LEGACY",
            "document",
            "legacy input has no canonical active_modules declaration",
        )
        return
    if len(module_lines) != 1:
        add_issue(
            errors,
            "MODULE_DECLARATION",
            "document",
            f"expected exactly one active_modules declaration; found {len(module_lines)}",
        )
        return

    raw_modules = module_lines[0].strip().rstrip("。.").strip()
    if not re.search(r"(?m)^- active_modules：[^`\r\n]+\r?$", text):
        add_issue(
            errors,
            "MODULE_DECLARATION_FORMAT",
            "document",
            "new output must serialize active_modules as a plain canonical list item",
        )
    if raw_modules.lower() == "none":
        declared_modules: set[str] = set()
    else:
        declared_modules = {
            item.strip().strip("`")
            for item in re.split(r"[,，、]", raw_modules)
            if item.strip()
        }
    if declared_modules != expected_modules:
        add_issue(
            errors,
            "MODULE_DECLARATION_MISMATCH",
            "document",
            f"declared={sorted(declared_modules)} expected={sorted(expected_modules)}",
        )


def validate_timing(
    text: str,
    cuts: list[Cut],
    contract: dict[str, Any],
    errors: list[Issue],
    warnings: list[Issue],
) -> None:
    timing = contract.get("timing", {})
    mode = timing.get("mode", "silent-default")
    if mode not in {"silent-default", "contract-budget", "media-frame-lock"}:
        add_issue(errors, "TIMING_MODE", "contract", f"unsupported timing mode: {mode}")
        return

    if mode == "silent-default":
        forbidden = []
        if "【时长与生成合同】" in text:
            forbidden.append("contract block")
        if "【媒体/帧锁】" in text:
            forbidden.append("media-lock block")
        if TIME_VALUE_RE.search(text):
            forbidden.append("duration value")
        if has_disallowed_timecode(text):
            forbidden.append("timecode")
        if FRAME_VALUE_RE.search(text):
            forbidden.append("frame value")
        if re.search(r"\b(?:planned_budget|measured_media|derived_check)\b", text):
            forbidden.append("timing truth label")
        if forbidden:
            add_issue(
                errors,
                "TIMING_SILENT_LEAK",
                "document",
                f"silent-default contains: {sorted(set(forbidden))}",
            )
        return

    if mode == "contract-budget":
        legacy_input = bool(contract.get("schema", {}).get("legacy_input", False))
        has_contract = "【时长与生成合同】" in text or (
            legacy_input and "成片时长硬预算" in text
        )
        if not has_contract:
            add_issue(errors, "TIMING_CONTRACT_MISSING", "document", "contract block is missing")
            return
        if "数值性质：planned_budget" not in text and "预算性质：生产计划值" not in text:
            add_issue(
                warnings if legacy_input else errors,
                "TIMING_PLANNED_LABEL",
                "timing contract",
                "planned timing is not labeled as a production budget",
            )
        rows = parse_budget_rows(text, legacy_input=legacy_input)
        if not rows:
            add_issue(errors, "TIMING_BUDGET_ROWS", "timing contract", "no budget rows found")
            return
        if any(row["planned"] is None for row in rows):
            add_issue(
                errors,
                "TIMING_BUDGET_PARSE",
                "timing contract",
                "every budget row needs a parseable planned value",
            )
            return
        total = sum((row["planned"] for row in rows), Decimal("0"))
        kind = timing.get("total_kind", "exact")
        exact = as_decimal(timing.get("total"), "timing.total")
        minimum = as_decimal(timing.get("minimum"), "timing.minimum")
        maximum = as_decimal(timing.get("maximum"), "timing.maximum")
        if kind == "exact":
            if exact is None or total != exact:
                add_issue(
                    errors,
                    "TIMING_TOTAL",
                    "timing contract",
                    f"budget sum {total} does not equal exact contract {exact}",
                )
        elif kind == "maximum":
            bound = maximum if maximum is not None else exact
            if bound is None or total > bound:
                add_issue(
                    errors,
                    "TIMING_MAXIMUM",
                    "timing contract",
                    f"budget sum {total} exceeds maximum {bound}",
                )
        elif kind == "range":
            if minimum is None or maximum is None or not (minimum <= total <= maximum):
                add_issue(
                    errors,
                    "TIMING_RANGE",
                    "timing contract",
                    f"budget sum {total} is outside {minimum}..{maximum}",
                )
        else:
            add_issue(errors, "TIMING_TOTAL_KIND", "contract", f"unsupported kind: {kind}")

        gen_limit = as_decimal(timing.get("gen_limit"), "timing.gen_limit")
        for row in rows:
            planned = row["planned"]
            row_limit = row["limit"]
            if row_limit is not None and planned > row_limit:
                add_issue(
                    errors,
                    "TIMING_ROW_LIMIT",
                    row["id"],
                    f"planned {planned} exceeds displayed limit {row_limit}",
                )
            if row["id"].startswith("GEN-") and gen_limit is not None and planned > gen_limit:
                add_issue(
                    errors,
                    "TIMING_GEN_LIMIT",
                    row["id"],
                    f"planned {planned} exceeds GEN limit {gen_limit}",
                )
            if not nonempty(row["feasibility"]):
                add_issue(
                    errors,
                    "TIMING_FEASIBILITY",
                    row["id"],
                    "dialogue/action feasibility is empty",
                )
            elif not legacy_input:
                ledger_tokens = [
                    "D-ID=",
                    "自然读演=",
                    "不可并行=",
                    "允许重叠=",
                    "冷启动/反应余量=",
                    "结论=PASS",
                ]
                missing_tokens = [
                    token for token in ledger_tokens if token not in row["feasibility"]
                ]
                if missing_tokens:
                    add_issue(
                        errors,
                        "TIMING_FEASIBILITY_LEDGER",
                        row["id"],
                        f"feasibility ledger is missing {missing_tokens}",
                    )
        sum_line = re.search(r"(?m)^求和复核[：:].*$", text)
        sum_values = (
            re.findall(r"\d+(?:\.\d+)?", sum_line.group(0)) if sum_line else []
        )
        if not sum_values and legacy_input:
            total_line = next(
                (
                    line
                    for line in text.splitlines()
                    if "总计" in line and re.search(r"\d+(?:\.\d+)?\s*秒", line)
                ),
                "",
            )
            total_cells = split_table_row(total_line)
            legacy_total = (
                parse_duration_cell(total_cells[2].replace("**", ""))
                if len(total_cells) >= 3
                else None
            )
            sum_values = [str(legacy_total)] if legacy_total is not None else []
        if not sum_values:
            add_issue(errors, "TIMING_SUM_DISPLAY", "timing contract", "sum check is missing")
        elif not any(Decimal(value) == total for value in sum_values):
            add_issue(
                errors,
                "TIMING_SUM_DISPLAY",
                "timing contract",
                "displayed sum check differs from budget rows",
            )
        for cut in cuts:
            if (
                TIME_VALUE_RE.search(cut.block)
                or has_disallowed_timecode(cut.block)
                or FRAME_VALUE_RE.search(cut.block)
            ):
                add_issue(
                    errors,
                    "TIMING_IN_CUT",
                    cut.cut_id,
                    "contract-budget must not assign numeric timing to CUT fields",
                )
        return

    if "【媒体/帧锁】" not in text:
        add_issue(errors, "MEDIA_LOCK_MISSING", "document", "media-frame-lock table is missing")
    media_sources = timing.get("media_sources", [])
    if not isinstance(media_sources, list) or not media_sources:
        add_issue(
            errors,
            "MEDIA_SOURCE_CONTRACT",
            "contract",
            "media-frame-lock requires timing.media_sources",
        )
        return
    for index, source in enumerate(media_sources, start=1):
        location = f"media_sources[{index}]"
        if not isinstance(source, dict) or not source.get("path"):
            add_issue(errors, "MEDIA_SOURCE_PARSE", location, "source path is missing")
            continue
        path = Path(str(source["path"])).resolve(strict=False)
        if not path.exists() or not path.is_file():
            add_issue(errors, "MEDIA_SOURCE_MISSING", location, f"media file missing: {path}")
            continue
        expected_hash = source.get("sha256")
        if expected_hash:
            actual_hash = sha256_bytes(path.read_bytes())
            if actual_hash.lower() != str(expected_hash).lower():
                add_issue(errors, "MEDIA_SOURCE_HASH", location, "media SHA-256 differs")
        expected_duration = as_decimal(source.get("duration"), f"{location}.duration")
        if expected_duration is not None:
            ffprobe = shutil.which("ffprobe")
            if not ffprobe:
                add_issue(
                    warnings,
                    "MEDIA_PROBE_UNAVAILABLE",
                    location,
                    "ffprobe unavailable; duration could not be independently checked",
                )
                continue
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            try:
                actual_duration = Decimal(result.stdout.strip())
            except InvalidOperation:
                add_issue(errors, "MEDIA_PROBE_FAILED", location, "ffprobe returned no duration")
                continue
            tolerance = as_decimal(timing.get("duration_tolerance", "0.02"), "duration_tolerance")
            if tolerance is None or abs(actual_duration - expected_duration) > tolerance:
                add_issue(
                    errors,
                    "MEDIA_DURATION",
                    location,
                    f"measured {actual_duration} differs from contract {expected_duration}",
                )


def validate_gens(
    gens: list[Gen],
    cuts: list[Cut],
    contract: dict[str, Any],
    errors: list[Issue],
    warnings: list[Issue],
) -> None:
    gen_contract = contract.get("gen", {})
    required = bool(gen_contract.get("required", False))
    if required and not gens:
        add_issue(errors, "GEN_MISSING", "document", "GEN map is required")
        return
    if not gens:
        return

    numbers = [gen.number for gen in gens]
    if len(numbers) != len(set(numbers)):
        add_issue(errors, "GEN_DUPLICATE", "GEN", "GEN IDs are not unique")
    if numbers != list(range(1, len(gens) + 1)):
        add_issue(errors, "GEN_SEQUENCE", "GEN", f"GEN IDs are not consecutive: {numbers}")

    cut_numbers = {cut.number for cut in cuts}
    covered: list[int] = []
    for gen in gens:
        names = [name for name, _ in gen.fields]
        if names != GEN_FIELDS:
            add_issue(
                errors,
                "GEN_SCHEMA",
                gen.gen_id,
                f"expected GEN fields in canonical order; found={names}",
            )
        if gen.start_cut > gen.end_cut:
            add_issue(errors, "GEN_RANGE", gen.gen_id, "CUT range is reversed")
            continue
        unit_cuts = list(range(gen.start_cut, gen.end_cut + 1))
        covered.extend(unit_cuts)
        missing = [number for number in unit_cuts if number not in cut_numbers]
        if missing:
            add_issue(
                errors,
                "GEN_CUT_REFERENCE",
                gen.gen_id,
                f"GEN references missing CUTs: {missing}",
            )
        fields = gen.field_map
        gen_type = fields.get("类型", "").split("/")[0].strip()
        if gen_type not in {"narrative", "supporting", "transition"}:
            add_issue(errors, "GEN_TYPE", gen.gen_id, f"unsupported type: {gen_type}")
        for name in ("因果/叙事任务", "IN状态", "OUT状态"):
            if not nonempty(fields.get(name, "")):
                add_issue(errors, "GEN_CLOSURE", gen.gen_id, f"{name} is empty")
        if gen_type == "narrative":
            for name in ("触发", "选择/行动", "对方可见反应", "新结束状态"):
                if not nonempty(fields.get(name, "")):
                    add_issue(errors, "GEN_CAUSAL_CHAIN", gen.gen_id, f"{name} is empty")

    if len(covered) != len(set(covered)):
        add_issue(errors, "GEN_CUT_DUPLICATE", "GEN map", "a CUT is assigned to multiple GENs")
    if bool(gen_contract.get("require_full_cut_coverage", True)):
        missing = sorted(cut_numbers - set(covered))
        if missing:
            add_issue(
                errors,
                "GEN_CUT_COVERAGE",
                "GEN map",
                f"CUTs missing from GEN map: {missing}",
            )


def parse_registry(text: str, marker: str, id_prefix: str, columns: int) -> dict[str, list[str]]:
    section = extract_section(text, marker)
    rows: dict[str, list[str]] = {}
    for line in section.splitlines():
        cells = split_table_row(line)
        if len(cells) != columns or not re.fullmatch(rf"{id_prefix}-\d{{3}}", cells[0]):
            continue
        rows[cells[0]] = cells
    return rows


def parse_applicability(value: str) -> dict[str, set[str] | bool]:
    normalized = value.strip()
    universal = normalized.lower() in {"all", "global"} or any(
        token in normalized for token in ("全片", "全部", "全局")
    )
    range_separator = r"(?:\s*[—–-]\s*|\s*至\s*)"
    scenes = set(re.findall(r"(?<![A-Z0-9_])S\d{2,}(?![A-Z0-9_])", normalized))
    for match in re.finditer(
        rf"(?<![A-Z0-9_])S(\d{{2,}}){range_separator}S(\d{{2,}})(?![A-Z0-9_])",
        normalized,
    ):
        start = int(match.group(1))
        end = int(match.group(2))
        if start <= end:
            width = max(len(match.group(1)), len(match.group(2)))
            scenes.update(f"S{number:0{width}d}" for number in range(start, end + 1))
    result: dict[str, set[str] | bool] = {
        "universal": universal,
        "scenes": scenes,
        "CUT": set(),
        "GEN": set(),
    }
    for prefix in ("CUT", "GEN"):
        values = set(
            re.findall(
                rf"(?<![A-Z0-9_]){prefix}-\d{{3}}(?![A-Z0-9_])",
                normalized,
            )
        )
        for match in re.finditer(
            rf"(?<![A-Z0-9_]){prefix}-(\d{{3}}){range_separator}"
            rf"{prefix}-(\d{{3}})(?![A-Z0-9_])",
            normalized,
        ):
            start = int(match.group(1))
            end = int(match.group(2))
            if start <= end:
                values.update(f"{prefix}-{number:03d}" for number in range(start, end + 1))
        result[prefix] = values
    return result


def scope_has_constraints(scope: dict[str, set[str] | bool]) -> bool:
    return bool(
        scope["universal"]
        or scope["scenes"]
        or scope["CUT"]
        or scope["GEN"]
    )


def scope_allows_cut(
    scope: dict[str, set[str] | bool], cut: Cut
) -> bool:
    if scope["universal"]:
        return True
    scene_id = cut.beat_id.split("-B", 1)[0]
    return cut.cut_id in scope["CUT"] or scene_id in scope["scenes"]


def scope_allows_gen(
    scope: dict[str, set[str] | bool], gen: Gen, cut_map: dict[int, Cut]
) -> bool:
    if scope["universal"] or gen.gen_id in scope["GEN"]:
        return True
    covered = [
        cut_map[number]
        for number in range(gen.start_cut, gen.end_cut + 1)
        if number in cut_map
    ]
    return any(
        cut.cut_id in scope["CUT"]
        or cut.beat_id.split("-B", 1)[0] in scope["scenes"]
        for cut in covered
    )


def looks_absolute_path(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:[\\/]", value) or value.startswith("\\\\") or value.startswith("/"))


def validate_assets_and_scenes(
    text: str,
    cuts: list[Cut],
    gens: list[Gen],
    contract: dict[str, Any],
    errors: list[Issue],
    warnings: list[Issue],
) -> None:
    asset_contract = contract.get("assets", {})
    asset_rows = parse_registry(text, "【资产注册表】", "ASSET", 7)
    scn_rows = parse_registry(text, "【场景母版注册表】", "SCN", 7)

    if asset_contract.get("required") and not asset_rows:
        add_issue(errors, "ASSET_REGISTRY_MISSING", "document", "asset registry is required")
    if asset_contract.get("scene_master_required") and not scn_rows:
        add_issue(errors, "SCN_REGISTRY_MISSING", "document", "scene-master registry is required")
    if asset_contract.get("required") and not re.search(
        r"(?m)^【资产注册表】\s*$", text
    ):
        add_issue(
            errors,
            "ASSET_REGISTRY_LABEL",
            "document",
            "new output must include the literal 【资产注册表】 section label",
        )
    if asset_contract.get("scene_master_required") and not re.search(
        r"(?m)^【场景母版注册表】\s*$", text
    ):
        add_issue(
            errors,
            "SCN_REGISTRY_LABEL",
            "document",
            "new output must include the literal 【场景母版注册表】 section label",
        )

    identities: dict[str, str] = {}
    for scn_id, cells in scn_rows.items():
        identity = cells[1]
        if identity in identities:
            add_issue(
                errors,
                "SCN_DUPLICATE_MASTER",
                scn_id,
                f"event/location identity already has master {identities[identity]}",
            )
        identities[identity] = scn_id

    verify_paths = bool(asset_contract.get("verify_local_paths", False))
    for asset_id, cells in asset_rows.items():
        path_value = cells[3]
        status = cells[6].lower()
        if looks_absolute_path(path_value) and (
            verify_paths or "本地已验证" in status or "local-verified" in status
        ):
            if not Path(path_value).exists():
                add_issue(
                    errors,
                    "ASSET_PATH_MISSING",
                    asset_id,
                    f"locally verifiable asset path does not exist: {path_value}",
                )

    active_asset_ids = set(asset_rows)
    active_scn_ids = set(scn_rows)
    asset_scopes = {
        asset_id: parse_applicability(cells[4])
        for asset_id, cells in asset_rows.items()
    }
    scn_scopes = {
        scn_id: parse_applicability(cells[6])
        for scn_id, cells in scn_rows.items()
    }
    cut_number_map = {cut.number: cut for cut in cuts}
    state_owners: dict[str, str] = {}
    excluded_state_prefixes = {"ASSET", "CUT", "D", "EVT", "GEN", "SCN"}
    for asset_id, cells in asset_rows.items():
        for state in re.findall(r"\b([A-Z][A-Z0-9_]{1,15})-(\d{2,3})\b", cells[5]):
            prefix, number = state
            if prefix in excluded_state_prefixes:
                continue
            state_id = f"{prefix}-{number}"
            existing = state_owners.get(state_id)
            if existing and existing != asset_id:
                add_issue(
                    errors,
                    "ASSET_STATE_DUPLICATE",
                    state_id,
                    f"state authority is declared by both {existing} and {asset_id}",
                )
            state_owners[state_id] = asset_id

    scene_scn_map: dict[str, set[str]] = {}
    for cut in cuts:
        asset_refs = set(re.findall(r"\bASSET-\d{3}\b", cut.block))
        scn_refs = set(re.findall(r"\bSCN-\d{3}\b", cut.block))
        active_scene_match = re.search(
            r"\bSCN-\d{3}\b", cut.field_map.get("场景", "")
        )
        active_scene_refs = {active_scene_match.group(0)} if active_scene_match else set()
        for asset_id in sorted(asset_refs - active_asset_ids):
            add_issue(errors, "ASSET_REFERENCE", cut.cut_id, f"unknown Asset-ID: {asset_id}")
        for asset_id in sorted(asset_refs & active_asset_ids):
            scope = asset_scopes[asset_id]
            if scope_has_constraints(scope) and not scope_allows_cut(scope, cut):
                add_issue(
                    errors,
                    "ASSET_CUT_SCOPE",
                    cut.cut_id,
                    f"{asset_id} is outside its registered CUT/Scene applicability",
                )
        for scn_id in sorted(scn_refs - active_scn_ids):
            add_issue(errors, "SCN_REFERENCE", cut.cut_id, f"unknown SCN-ID: {scn_id}")
        for scn_id in sorted(active_scene_refs & active_scn_ids):
            scope = scn_scopes[scn_id]
            if scope_has_constraints(scope) and not scope_allows_cut(scope, cut):
                add_issue(
                    errors,
                    "SCN_CUT_SCOPE",
                    cut.cut_id,
                    f"{scn_id} is outside its registered CUT/Scene applicability",
                )
        if scn_rows and not active_scene_refs:
            add_issue(errors, "SCN_CUT_MISSING", cut.cut_id, "CUT has no SCN-ID")
        scene_id = cut.beat_id.split("-B", 1)[0]
        scene_scn_map.setdefault(scene_id, set()).update(active_scene_refs)

    allowed_multi = set(asset_contract.get("allow_multi_master_scenes", []))
    for scene_id, refs in scene_scn_map.items():
        if len(refs) > 1 and scene_id not in allowed_multi:
            add_issue(
                errors,
                "SCN_SCENE_MULTIPLE",
                scene_id,
                f"one screenplay scene resolves to multiple scene masters: {sorted(refs)}",
            )

    for gen in gens:
        refs = set(re.findall(r"\b(?:ASSET|SCN)-\d{3}\b", gen.block))
        declared_asset_ids = set(
            re.findall(
                r"\bASSET-\d{3}\b",
                gen.field_map.get("Asset/SCN IDs", ""),
            )
        )
        for ref in sorted(refs):
            if ref.startswith("ASSET-") and ref not in active_asset_ids:
                add_issue(errors, "ASSET_GEN_REFERENCE", gen.gen_id, f"unknown Asset-ID: {ref}")
            if ref.startswith("ASSET-") and ref in active_asset_ids:
                scope = asset_scopes[ref]
                if scope_has_constraints(scope) and not scope_allows_gen(
                    scope, gen, cut_number_map
                ):
                    add_issue(
                        errors,
                        "ASSET_GEN_SCOPE",
                        gen.gen_id,
                        f"{ref} is outside its registered GEN/CUT/Scene applicability",
                    )
            if ref.startswith("SCN-") and ref not in active_scn_ids:
                add_issue(errors, "SCN_GEN_REFERENCE", gen.gen_id, f"unknown SCN-ID: {ref}")
            if ref.startswith("SCN-") and ref in active_scn_ids:
                scope = scn_scopes[ref]
                if scope_has_constraints(scope) and not scope_allows_gen(
                    scope, gen, cut_number_map
                ):
                    add_issue(
                        errors,
                        "SCN_GEN_SCOPE",
                        gen.gen_id,
                        f"{ref} is outside its registered GEN/CUT/Scene applicability",
                    )
        for state_id in sorted(
            set(
                f"{prefix}-{number}"
                for prefix, number in re.findall(
                    r"\b([A-Z][A-Z0-9_]{1,15})-(\d{2,3})\b", gen.block
                )
                if prefix not in excluded_state_prefixes
            )
        ):
            owner = state_owners.get(state_id)
            if owner and owner not in declared_asset_ids:
                add_issue(
                    errors,
                    "ASSET_STATE_AUTHORITY",
                    gen.gen_id,
                    f"{state_id} requires {owner} in the Asset/SCN IDs field",
                )


def parse_viewpoint(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for token in re.split(r"[|；;]", value):
        token = token.strip()
        if "=" in token:
            key, val = token.split("=", 1)
            result[key.strip().strip("`")] = val.strip().strip("`")
    return result


def validate_viewpoint(
    text: str,
    cuts: list[Cut],
    contract: dict[str, Any],
    errors: list[Issue],
    warnings: list[Issue],
) -> None:
    viewpoint_contract = contract.get("viewpoint", {})
    required_keys = ["模式", "主人", "人物在场", "观众当前可知", "进入触发", "退出触发"]
    declared_ids = set(ID_RE.findall(text))
    cut_map = {cut.cut_id: cut for cut in cuts}
    for cut in cuts:
        if (
            len(cut.fields) == 12
            and contract.get("schema", {}).get("allow_legacy_12")
            and contract.get("schema", {}).get("legacy_input")
        ):
            continue
        value = cut.field_map.get("叙事视点/知识边界", "")
        if "`" in value:
            add_issue(
                errors,
                "POV_SERIALIZATION",
                cut.cut_id,
                "viewpoint machine keys and values must not use Markdown code marks",
            )
        parsed = parse_viewpoint(value)
        missing = [key for key in required_keys if key not in parsed]
        if missing:
            add_issue(
                errors,
                "POV_SCHEMA",
                cut.cut_id,
                f"viewpoint field must use key=value entries; missing={missing}",
            )
            continue
        mode = parsed["模式"]
        mode_aliases = {
            "角色对齐观察": "角色对齐",
            "近主观": "角色对齐",
            "贴肩近主观": "角色对齐",
            "字面第一人称": "字面POV",
            "第一人称": "字面POV",
            "记忆中的通讯视线": "字面POV",
        }
        if mode in mode_aliases:
            add_issue(
                warnings,
                "POV_MODE_ALIAS",
                cut.cut_id,
                f"normalize viewpoint mode {mode} to {mode_aliases[mode]}",
            )
            mode = mode_aliases[mode]
        if mode not in {"客观", "角色对齐", "字面POV", "临时全知"}:
            add_issue(errors, "POV_MODE", cut.cut_id, f"unsupported viewpoint mode: {mode}")
        if mode == "字面POV":
            if parsed["主人"] in {"", "无", "不适用"}:
                add_issue(errors, "POV_OWNER", cut.cut_id, "literal POV has no owner")
            if parsed["人物在场"].lower() not in {"是", "true", "yes", "媒体记忆"}:
                add_issue(
                    errors,
                    "POV_PRESENCE",
                    cut.cut_id,
                    "literal POV owner is not present or in a declared media-memory state",
                )
            if parsed["进入触发"] in {"", "无", "开场", "未说明"}:
                add_issue(errors, "POV_TRIGGER", cut.cut_id, "literal POV lacks a visible entry trigger")
        for key in ("进入触发", "退出触发"):
            value_id = parsed[key]
            if re.fullmatch(r"(?:D|EVT)-\d{3}", value_id) and value_id not in declared_ids:
                add_issue(
                    errors,
                    "POV_TRIGGER_REFERENCE",
                    cut.cut_id,
                    f"{key} references unknown ID: {value_id}",
                )

    requirements = viewpoint_contract.get("responsibility_requirements", [])
    if not isinstance(requirements, list):
        raise ParseError("viewpoint.responsibility_requirements must be a list")
    for item in requirements:
        if not isinstance(item, dict) or not item.get("cut"):
            raise ParseError("each responsibility requirement needs a cut")
        cut_id = str(item["cut"])
        cut = cut_map.get(cut_id)
        if not cut:
            add_issue(errors, "RESPONSIBILITY_CUT", cut_id, "required responsibility CUT is missing")
            continue
        parsed = parse_viewpoint(cut.field_map.get("叙事视点/知识边界", ""))
        if parsed.get("模式") != item.get("mode", "客观"):
            add_issue(
                errors,
                "RESPONSIBILITY_MODE",
                cut_id,
                "responsibility image is not in the required objective mode",
            )
        expected_after = item.get("after")
        if expected_after and expected_after not in text:
            add_issue(
                errors,
                "RESPONSIBILITY_TRIGGER",
                cut_id,
                f"declared causal trigger is absent: {expected_after}",
            )


def validate_revision_and_residue(
    text: str,
    document_path: Path,
    contract_path: Path,
    contract: dict[str, Any],
    errors: list[Issue],
    warnings: list[Issue],
) -> None:
    revision = contract.get("revision", {})
    enabled = bool(revision.get("enabled", False))
    patterns: list[tuple[str, str]] = []
    for value in revision.get("forbidden_exact", []):
        patterns.append(("exact", str(value)))
    for value in revision.get("deprecated_paths", []):
        raw = str(value)
        patterns.append(("deprecated", raw))
        patterns.append(("deprecated", raw.replace("\\", "/")))
        patterns.append(("deprecated", raw.replace("/", "\\")))
    for kind, pattern in patterns:
        if pattern and pattern in text:
            add_issue(
                errors,
                "REVISION_RESIDUE",
                "document",
                f"{kind} residue matched SHA-256 prefix {sha256_bytes(pattern.encode('utf-8'))[:12]}",
            )
    for index, pattern in enumerate(revision.get("forbidden_regex", []), start=1):
        try:
            compiled = re.compile(str(pattern), re.MULTILINE)
        except re.error as exc:
            raise ParseError(f"invalid forbidden_regex[{index}]: {exc}") from exc
        if compiled.search(text):
            add_issue(
                errors,
                "REVISION_REGEX_RESIDUE",
                "document",
                f"forbidden_regex[{index}] matched",
            )

    if not enabled:
        return
    source_value = revision.get("source_canon_path")
    expected_hash = revision.get("source_sha256")
    if not source_value or not expected_hash:
        add_issue(
            errors,
            "REVISION_SOURCE_CONTRACT",
            "contract",
            "revision mode requires source_canon_path and source_sha256",
        )
        return
    source = Path(str(source_value)).resolve(strict=False)
    if not source.exists() or not source.is_file():
        add_issue(errors, "REVISION_SOURCE_MISSING", "contract", f"source missing: {source}")
        return
    if norm_path(source) == norm_path(document_path):
        add_issue(errors, "REVISION_OVERWRITE", "document", "delivery path equals source canon path")
    actual_hash = sha256_bytes(source.read_bytes())
    if actual_hash.lower() != str(expected_hash).lower():
        add_issue(errors, "REVISION_SOURCE_HASH", "contract", "source canon hash changed")
    for required_marker in ("【版本与正典来源】", "source_canon_path", "source_sha256"):
        if required_marker not in text:
            add_issue(
                errors,
                "REVISION_HEADER",
                "document",
                f"revision header is missing {required_marker}",
            )

    impact_value = revision.get("impact_report_path")
    if not impact_value:
        add_issue(
            errors,
            "REVISION_IMPACT_CONTRACT",
            "contract",
            "revision mode requires impact_report_path",
        )
    else:
        impact_path = Path(str(impact_value))
        if not impact_path.is_absolute():
            impact_path = contract_path.parent / impact_path
        impact_path = impact_path.resolve(strict=False)
        if not impact_path.exists() or not impact_path.is_file():
            add_issue(
                errors,
                "REVISION_IMPACT_MISSING",
                "contract",
                f"impact report missing: {impact_path}",
            )
        elif norm_path(impact_path) == norm_path(document_path):
            add_issue(
                errors,
                "REVISION_IMPACT_PATH",
                "contract",
                "impact report must be a sidecar, not the delivery document",
            )
        else:
            _, impact_text = read_utf8_nfc(impact_path, "impact report")
            has_heading = "Impact Matrix" in impact_text or "影响矩阵" in impact_text
            rows = []
            for line in impact_text.splitlines():
                cells = split_table_row(line)
                if cells and re.fullmatch(r"(?:CHG|CHANGE)-\d{3}", cells[0], re.IGNORECASE):
                    rows.append(cells)
            if not has_heading:
                add_issue(
                    errors,
                    "REVISION_IMPACT_HEADING",
                    str(impact_path),
                    "impact report is missing an Impact Matrix heading",
                )
            if not rows:
                add_issue(
                    errors,
                    "REVISION_IMPACT_ROWS",
                    str(impact_path),
                    "impact report contains no CHG/CHANGE rows",
                )
            for index, cells in enumerate(rows, start=1):
                if len(cells) < 6 or any(not nonempty(cell) for cell in cells[:6]):
                    add_issue(
                        errors,
                        "REVISION_IMPACT_ROW",
                        f"{impact_path}#row-{index}",
                        "impact row must fill change, fact, direct impact, propagated surfaces, preserved constraints, and acceptance check",
                    )
            required_report_markers = {
                "source_canon_path": ("source_canon_path",),
                "source_sha256": ("source_sha256",),
                "explicit_delete": ("Explicit replacement", "explicit_delete", "明确删除"),
                "explicit_add": ("Explicit addition", "explicit_add", "明确新增"),
                "residue_audit": ("Residue", "残留"),
            }
            for label, alternatives in required_report_markers.items():
                if not any(marker in impact_text for marker in alternatives):
                    add_issue(
                        errors,
                        "REVISION_IMPACT_SURFACE",
                        str(impact_path),
                        f"impact report is missing {label}",
                    )
    if not revision.get("semantic_residue_reviewed", False):
        add_issue(
            warnings,
            "REVISION_SEMANTIC_REVIEW",
            "contract",
            "independent semantic residue review is not recorded",
        )


def validate_callbacks(
    text: str, contract: dict[str, Any], errors: list[Issue], warnings: list[Issue]
) -> None:
    event_contract = contract.get("events", {})
    section = extract_section(text, "【事件身份与回环】")
    rows: dict[str, list[str]] = {}
    for line in section.splitlines():
        cells = split_table_row(line)
        if len(cells) == 8 and re.fullmatch(r"EVT-\d{3}", cells[0]):
            rows[cells[0]] = cells
    if event_contract.get("callbacks_required") and not rows:
        add_issue(errors, "EVENT_LEDGER_MISSING", "document", "event callback ledger is required")
    for event_id, cells in rows.items():
        callback = cells[7]
        if re.fullmatch(r"EVT-\d{3}", callback) and callback not in rows:
            add_issue(
                errors,
                "EVENT_CALLBACK_REFERENCE",
                event_id,
                f"callback references unknown event: {callback}",
            )


def validate_style_contamination(
    text: str, contract: dict[str, Any], errors: list[Issue], warnings: list[Issue]
) -> None:
    style = contract.get("style", {})
    for index, value in enumerate(style.get("forbidden_exact", []), start=1):
        term = str(value)
        if term and term in text:
            add_issue(
                errors,
                "STYLE_CONTAMINATION",
                "document",
                f"style.forbidden_exact[{index}] matched",
            )


def validate_brief_fidelity(
    text: str, contract: dict[str, Any], errors: list[Issue], warnings: list[Issue]
) -> None:
    brief = contract.get("brief", {})
    for index, value in enumerate(brief.get("required_exact", []), start=1):
        pattern = str(value)
        if pattern and pattern not in text:
            add_issue(
                errors,
                "BRIEF_REQUIRED_MISSING",
                "document",
                f"brief.required_exact[{index}] missing; SHA-256 prefix {sha256_bytes(pattern.encode('utf-8'))[:12]}",
            )
    for index, pattern in enumerate(brief.get("required_regex", []), start=1):
        try:
            compiled = re.compile(str(pattern), re.MULTILINE)
        except re.error as exc:
            raise ParseError(f"invalid brief.required_regex[{index}]: {exc}") from exc
        if not compiled.search(text):
            add_issue(
                errors,
                "BRIEF_REQUIRED_REGEX_MISSING",
                "document",
                f"brief.required_regex[{index}] did not match",
            )
    for index, value in enumerate(brief.get("forbidden_exact", []), start=1):
        pattern = str(value)
        if pattern and pattern in text:
            add_issue(
                errors,
                "BRIEF_FORBIDDEN",
                "document",
                f"brief.forbidden_exact[{index}] matched; SHA-256 prefix {sha256_bytes(pattern.encode('utf-8'))[:12]}",
            )
    if brief.get("semantic_review_required") and not brief.get("semantic_reviewed"):
        add_issue(
            warnings,
            "BRIEF_SEMANTIC_REVIEW",
            "contract",
            "semantic review of current-brief fidelity is still required",
        )


def validate_rights_notice(
    text: str,
    contract: dict[str, Any],
    errors: list[Issue],
    warnings: list[Issue],
) -> None:
    rights = contract.get("rights", {})
    if not rights:
        return

    label = "【版权出处与使用声明】"
    notice_matches = list(
        re.finditer(
            r"(?m)^(?:#{1,6}\s*)?(?:【版权出处与使用声明】|版权出处与使用声明)\s*$",
            text,
        )
    )
    notice_start = notice_matches[-1].start() if notice_matches else -1
    required = bool(rights.get("required", False))
    if notice_start < 0:
        if required:
            add_issue(
                errors,
                "RIGHTS_NOTICE_MISSING",
                "document",
                "required final rights source and use notice is missing",
            )
        return

    notice = text[notice_start:]
    if bool(rights.get("require_literal_label", True)) and not re.search(
        r"(?m)^【版权出处与使用声明】\s*$", text
    ):
        add_issue(
            errors,
            "RIGHTS_NOTICE_LABEL",
            "document",
            "new output must include the literal 【版权出处与使用声明】 section label",
        )
    if bool(rights.get("notice_must_be_last", True)):
        section_headings = list(
            re.finditer(
                r"(?m)^(?:#{1,6}\s+[^#\n].*|【[^】\n]+】[^\n]*)$",
                text,
            )
        )
        last_heading = (
            re.sub(r"^#{1,6}\s*", "", section_headings[-1].group(0))
            if section_headings
            else ""
        )
        if "版权出处与使用声明" not in last_heading:
            add_issue(
                errors,
                "RIGHTS_NOTICE_NOT_LAST",
                "document",
                "rights source and use notice must be the final bracketed section",
            )

    required_status = rights.get("required_status")
    if required_status and str(required_status) not in notice:
        add_issue(
            errors,
            "RIGHTS_STATUS",
            "rights notice",
            f"required rights status is missing: {required_status}",
        )

    for token in rights.get("required_tokens", []):
        value = str(token)
        if value not in notice:
            add_issue(
                errors,
                "RIGHTS_TOKEN",
                "rights notice",
                f"required rights token is missing: {value}",
            )

    if rights.get("semantic_review_required") and not rights.get(
        "semantic_reviewed", False
    ):
        add_issue(
            warnings,
            "RIGHTS_SEMANTIC_REVIEW",
            "contract",
            "semantic review of source attribution and protected dependency coverage is still required",
        )


def sorted_issues(items: Iterable[Issue]) -> list[dict[str, str]]:
    return [
        asdict(item)
        for item in sorted(items, key=lambda issue: (issue.code, issue.location, issue.message))
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a screenplay/CUT/GEN delivery against a JSON contract."
    )
    parser.add_argument("--document", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    return parser


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(unicodedata.normalize("NFC", serialized) + "\n", encoding="utf-8")


def run(document_path: Path, contract_path: Path) -> dict[str, Any]:
    document_path = document_path.resolve(strict=False)
    contract_path = contract_path.resolve(strict=False)
    if not document_path.exists() or not document_path.is_file():
        raise ParseError(f"document does not exist: {document_path}")
    if not contract_path.exists() or not contract_path.is_file():
        raise ParseError(f"contract does not exist: {contract_path}")

    document_bytes, text = read_utf8_nfc(document_path, "document")
    contract_bytes, contract = load_contract(contract_path)
    errors: list[Issue] = []
    warnings: list[Issue] = []

    cuts = parse_cuts(text)
    gens = parse_gens(text)
    validate_cut_schema(cuts, contract, errors, warnings)
    validate_beat_closure(text, cuts, errors, warnings)
    validate_scene_director_maps(text, cuts, contract, errors, warnings)
    validate_dialogue(text, cuts, contract, errors, warnings)
    validate_mode_declaration(text, contract, errors, warnings)
    validate_timing(text, cuts, contract, errors, warnings)
    validate_gens(gens, cuts, contract, errors, warnings)
    validate_assets_and_scenes(text, cuts, gens, contract, errors, warnings)
    validate_viewpoint(text, cuts, contract, errors, warnings)
    validate_revision_and_residue(
        text, document_path, contract_path, contract, errors, warnings
    )
    validate_callbacks(text, contract, errors, warnings)
    validate_brief_fidelity(text, contract, errors, warnings)
    validate_style_contamination(text, contract, errors, warnings)
    validate_rights_notice(text, contract, errors, warnings)

    payload = {
        "contract_sha256": sha256_bytes(contract_bytes),
        "counts": {
            "cuts": len(cuts),
            "dialogue_authorities": len(AUTH_RE.findall(text)),
            "gens": len(gens),
        },
        "document_sha256": sha256_bytes(document_bytes),
        "errors": sorted_issues(errors),
        "schema_version": 1,
        "status": "pass" if not errors else "constraint_failed",
        "warnings": sorted_issues(warnings),
    }
    return payload


def main() -> int:
    parser = build_parser()
    try:
        args = parser.parse_args()
        payload = run(args.document, args.contract)
        if args.json_out:
            write_json(args.json_out.resolve(strict=False), payload)
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0 if payload["status"] == "pass" else 1
    except ConstraintError as exc:
        payload = {"error": str(exc), "schema_version": 1, "status": "constraint_failed"}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    except (ParseError, OSError, ValueError, TypeError) as exc:
        payload = {"error": str(exc), "schema_version": 1, "status": "parse_failed"}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
