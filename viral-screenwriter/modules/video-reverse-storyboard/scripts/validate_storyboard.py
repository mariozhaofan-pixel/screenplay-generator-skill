#!/usr/bin/env python3
"""Validate the mechanical structure of a reverse-storyboard Markdown file."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any


PASS_SCOPE = (
    "结构 PASS 只表示文档通过本脚本的机械结构检查，不代表分镜事实正确、"
    "与源视频一致或符合摄影机视锥，也不代表已完成全帧分析、完整听音或人工核验。"
)

SHOT_HEADING_RE = re.compile(
    r"^\s{0,3}###(?!#)\s+(?:镜头\s*)?(?P<shot_id>S(?P<number>\d{3,}))\b",
    re.IGNORECASE,
)
FENCE_RE = re.compile(r"^\s{0,3}(?P<marker>`{3,}|~{3,})")
FIELD_HEADING_RE = re.compile(r"^\s{0,3}#{4,6}\s+(?P<label>.+?)\s*$")
LABELED_LINE_RE = re.compile(r"^(?P<label>[^:：\n]{1,60})[:：]\s*(?P<value>.*)$")

TIME_TOKEN = (
    r"(?:\d{1,3}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?"
    r"|\d+(?:[.,]\d+)?\s*(?:s|秒))"
)
RANGE_SEPARATOR = r"(?:-->|->|→|—|–|~|～|至|到|-)"
TIME_RANGE_RE = re.compile(
    rf"(?P<start>{TIME_TOKEN})\s*{RANGE_SEPARATOR}\s*(?P<end>{TIME_TOKEN})",
    re.IGNORECASE,
)
BARE_RANGE_RE = re.compile(
    rf"(?<![\w.])(?P<start>\d+(?:[.,]\d+)?)\s*{RANGE_SEPARATOR}\s*"
    rf"(?P<end>\d+(?:[.,]\d+)?)(?![\w.])"
)

REQUIRED_FIELDS = {
    "scene_people": "场景与人物",
    "visual_composition": "画面与构图",
    "camera": "摄影机",
    "layers_masks": "前后景、遮挡与遮罩",
    "blocking": "演员、道具运动与调度",
    "performance": "表演与微表情",
    "vfx": "特效与画面处理",
    "sound": "声音",
    "editing": "剪辑与节奏",
}

DIALOGUE_CATEGORY_RE = re.compile(
    r"(?:回忆现场对白|画内对白|画外对白|同期对白|现场对白|人物对白|"
    r"旁白|画外音|内心独白|电话声|广播声|设备声|媒介声|声桥|无对白|无台词|无语音|无人声|静默|"
    r"V\.?\s*O\.?|O\.?\s*S\.?)",
    re.IGNORECASE,
)
FULL_SILENCE_RE = re.compile(
    r"(?:无音(?:轨|频轨道)|(?:全镜|整镜|全程|整段)(?:均|保持|为)?(?:静默|静音|无声))"
)
ENVIRONMENT_SOUND_RE = re.compile(r"环境(?:声|音)|拟音|音效|声效|SFX", re.IGNORECASE)
MUSIC_RE = re.compile(r"音乐|配乐|BGM", re.IGNORECASE)
SPEECH_RE = re.compile(
    r"回忆现场对白|画内对白|画外对白|同期对白|现场对白|人物对白|"
    r"旁白|画外音|内心独白|电话声|广播声|设备声|媒介声|V\.?\s*O\.?|O\.?\s*S\.?",
    re.IGNORECASE,
)
PROHIBITED_SECTION_RE = re.compile(
    r"分析|证据|不确定项|导演意图|叙事意图|导演拆解|出处|取证|"
    r"(?:参考|素材|信息|数据)来源|^来源|(?:工作|制作|执行|核验)(?:流程|过程)|"
    r"^过程(?:说明|记录)?$|总结|梗索引|梗清单|文化语境|质量自检|校验报告"
)


def configure_console_utf8() -> None:
    """Keep Chinese diagnostics readable in redirected Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (LookupError, OSError):
                pass


@dataclass(frozen=True)
class ShotBlock:
    shot_id: str
    number: int
    heading: str
    heading_line: int
    body_lines: list[tuple[int, str]]


@dataclass(frozen=True)
class ParsedLabel:
    label: str
    value: str
    kind: str


@dataclass(frozen=True)
class Timecode:
    start: float
    end: float
    raw: str
    line: int


def _nonnegative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是非负数") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("必须大于或等于 0")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "校验纯分镜 Markdown 的镜号、九项字段、声音层和可选时码，并输出 JSON。"
        )
    )
    parser.add_argument("storyboard", type=Path, help="输入 Markdown 文件")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="JSON 报告路径；省略或设为 - 时写到标准输出",
    )
    parser.add_argument(
        "--require-timecodes",
        action="store_true",
        help="把缺失时码视为错误；默认只在存在时码时检查",
    )
    parser.add_argument(
        "--strict-coverage",
        action="store_true",
        help="把相邻时码空档视为错误；默认记为 warning",
    )
    parser.add_argument(
        "--expected-start",
        type=_nonnegative_float,
        default=None,
        help="可选预期覆盖起点（秒）",
    )
    parser.add_argument(
        "--expected-end",
        type=_nonnegative_float,
        default=None,
        help="可选预期覆盖终点（秒）",
    )
    parser.add_argument(
        "--time-tolerance",
        type=_nonnegative_float,
        default=0.05,
        help="时码衔接容差，单位秒（默认：0.05）",
    )
    return parser


def _issue(
    code: str,
    message: str,
    *,
    shot: str | None = None,
    line: int | None = None,
) -> dict[str, Any]:
    issue: dict[str, Any] = {"code": code, "message": message}
    if shot is not None:
        issue["shot"] = shot
    if line is not None:
        issue["line"] = line
    return issue


def _fence_transition(line: str, active: str | None) -> str | None:
    match = FENCE_RE.match(line)
    if not match:
        return active
    marker = match.group("marker")
    marker_char = marker[0]
    if active is None:
        return marker_char
    if active == marker_char:
        return None
    return active


def _parse_shots(markdown: str) -> list[ShotBlock]:
    lines = markdown.splitlines()
    headings: list[tuple[int, re.Match[str]]] = []
    active_fence: str | None = None
    for index, line in enumerate(lines):
        next_fence = _fence_transition(line, active_fence)
        if active_fence is None and next_fence is None:
            match = SHOT_HEADING_RE.match(line)
            if match:
                headings.append((index, match))
        active_fence = next_fence

    shots: list[ShotBlock] = []
    for position, (line_index, match) in enumerate(headings):
        next_line_index = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        body = [
            (index + 1, lines[index])
            for index in range(line_index + 1, next_line_index)
        ]
        shots.append(
            ShotBlock(
                shot_id=match.group("shot_id").upper(),
                number=int(match.group("number")),
                heading=lines[line_index],
                heading_line=line_index + 1,
                body_lines=body,
            )
        )
    return shots


def _visible_body_lines(shot: ShotBlock) -> list[tuple[int, str]]:
    visible: list[tuple[int, str]] = []
    active_fence: str | None = None
    for line_number, line in shot.body_lines:
        next_fence = _fence_transition(line, active_fence)
        if active_fence is None and next_fence is None:
            visible.append((line_number, line))
        active_fence = next_fence
    return visible


def _strip_list_marker(line: str) -> str:
    return re.sub(r"^\s*(?:(?:[-*+]\s+)|(?:\d+[.)]\s+))", "", line).strip()


def _parse_label(line: str) -> ParsedLabel | None:
    heading_match = FIELD_HEADING_RE.match(line)
    if heading_match:
        label = heading_match.group("label").strip(" *_`#")
        return ParsedLabel(label=label, value="", kind="heading")

    cleaned = _strip_list_marker(line).replace("**", "").replace("__", "")
    match = LABELED_LINE_RE.match(cleaned)
    if not match:
        return None
    label = match.group("label").strip(" *_`#")
    return ParsedLabel(label=label, value=match.group("value").strip(), kind="inline")


def _normalise_label(label: str) -> str:
    return re.sub(r"[\s*/／|｜&和及与、（）()【】\[\]_-]+", "", label.casefold())


def _field_category(label: str) -> str | None:
    normalised = _normalise_label(label)
    if "证据" in normalised or "不确定" in normalised:
        return "evidence_uncertainty"
    if "导演意图" in normalised or "叙事意图" in normalised:
        return "director_intent"
    if "剪辑" in normalised:
        return "editing"
    if "前后景" in normalised or "遮挡" in normalised or "遮罩" in normalised or "蒙版" in normalised:
        return "layers_masks"
    if "特效" in normalised or "画面处理" in normalised or "vfx" in normalised:
        return "vfx"
    if "表演" in normalised or "微表情" in normalised:
        return "performance"
    if "调度" in normalised or ("演员" in normalised and "运动" in normalised):
        return "blocking"
    if (
        "摄影机" in normalised
        or "摄影" in normalised
        or "运镜" in normalised
        or "机位" in normalised
        or normalised in {"镜头", "镜头运动"}
    ):
        return "camera"
    if (
        "声音" in normalised
        or "音频" in normalised
        or "声效" in normalised
        or "声画" in normalised
        or normalised in {"环境音", "音效", "配乐"}
    ):
        return "sound"
    if "画面" in normalised or "构图" in normalised or "景别" in normalised:
        return "visual_composition"
    if "场景" in normalised and ("人物" in normalised or "角色" in normalised):
        return "scene_people"
    return None


def _has_following_content(
    lines: list[tuple[int, str]], start_index: int
) -> bool:
    for _, line in lines[start_index + 1 :]:
        if not line.strip():
            continue
        parsed = _parse_label(line)
        if parsed is not None and _field_category(parsed.label) is not None:
            return False
        if re.match(r"^\s{0,3}#{1,6}\s+", line):
            return False
        return True
    return False


def _field_presence(
    lines: list[tuple[int, str]],
) -> dict[str, list[tuple[int, bool]]]:
    found: dict[str, list[tuple[int, bool]]] = {key: [] for key in REQUIRED_FIELDS}
    for index, (line_number, line) in enumerate(lines):
        parsed = _parse_label(line)
        if parsed is None:
            continue
        category = _field_category(parsed.label)
        if category not in found:
            continue
        has_content = bool(parsed.value.strip()) or _has_following_content(lines, index)
        found[category].append((line_number, has_content))
    return found


def _field_text(lines: list[tuple[int, str]], field: str) -> str:
    """Read one parent field plus its child labels, without borrowing other fields."""
    parts: list[str] = []
    active = False
    for _, line in lines:
        parsed = _parse_label(line)
        category = _field_category(parsed.label) if parsed else None
        if category is not None:
            active = category == field
        elif re.match(r"^\s{0,3}#{1,3}\s+", line):
            active = False
        if active:
            parts.append(line)
    return "\n".join(parts)


def _has_speech_content(sound: str) -> bool:
    # Accept literal dialogue, a separate script line, or a local inaudible span.
    if re.search(r"[\[【]听不清[\]】]|[\"“「『][^\"”」』\n]+[\"”」』]", sound):
        return True
    if re.search(r"台词\s*[:：]\s*\S", sound):
        return True
    for segment in re.split(r"[;；\n]", sound):
        match = SPEECH_RE.search(segment)
        if match and re.match(r"\s*[\]】）)]?\s*[:：]\s*\S", segment[match.end() :]):
            return True
    return False


def _prohibited_sections(markdown: str) -> list[dict[str, Any]]:
    """Check section/field labels only; words spoken by a character remain valid."""
    issues: list[dict[str, Any]] = []
    active_fence: str | None = None
    for line_number, line in enumerate(markdown.splitlines(), 1):
        next_fence = _fence_transition(line, active_fence)
        if active_fence is None and next_fence is None and not SHOT_HEADING_RE.match(line):
            heading = re.match(r"^\s{0,3}#{2,6}\s+(.+?)\s*#*\s*$", line)
            parsed = _parse_label(line)
            label = heading.group(1) if heading else (parsed.label if parsed else "")
            if PROHIBITED_SECTION_RE.search(label):
                issues.append(
                    _issue(
                        "prohibited_delivery_section",
                        f"成品只保留可执行分镜，请移除分析、来源或证据类专节/字段：{label}。",
                        line=line_number,
                    )
                )
        active_fence = next_fence
    return issues


def _parse_time_token(token: str) -> float:
    cleaned = token.strip().lower().replace("秒", "").replace("s", "")
    cleaned = cleaned.replace(",", ".").strip()
    parts = cleaned.split(":")
    if len(parts) == 1:
        value = float(parts[0])
    elif len(parts) == 2:
        minutes, seconds = float(parts[0]), float(parts[1])
        if seconds >= 60:
            raise ValueError("MM:SS 中 SS 必须小于 60")
        value = minutes * 60 + seconds
    elif len(parts) == 3:
        hours, minutes, seconds = (float(part) for part in parts)
        if minutes >= 60 or seconds >= 60:
            raise ValueError("HH:MM:SS 中 MM 和 SS 必须小于 60")
        value = hours * 3600 + minutes * 60 + seconds
    else:
        raise ValueError("无法识别时码")
    if value < 0:
        raise ValueError("时码不能为负数")
    return value


def _range_from_text(text: str, *, allow_bare: bool) -> tuple[float, float, str] | None:
    match = TIME_RANGE_RE.search(text)
    if match is None and allow_bare:
        match = BARE_RANGE_RE.search(text)
    if match is None:
        return None
    start = _parse_time_token(match.group("start"))
    end = _parse_time_token(match.group("end"))
    return start, end, match.group(0)


def _extract_timecode(shot: ShotBlock) -> Timecode | None:
    heading_range = _range_from_text(shot.heading, allow_bare=True)
    if heading_range is not None:
        return Timecode(*heading_range, line=shot.heading_line)

    visible_lines = _visible_body_lines(shot)
    for line_number, line in visible_lines:
        parsed = _parse_label(line)
        if parsed is None:
            continue
        normalised = _normalise_label(parsed.label)
        if not any(term in normalised for term in ("时码", "时间码", "timecode", "timeline")):
            continue
        marked_range = _range_from_text(parsed.value, allow_bare=True)
        if marked_range is not None:
            return Timecode(*marked_range, line=line_number)

    for line_number, line in visible_lines:
        fallback_range = _range_from_text(line, allow_bare=False)
        if fallback_range is not None:
            return Timecode(*fallback_range, line=line_number)
    return None


def _union_duration(timecodes: list[Timecode]) -> float:
    valid = sorted(
        ((item.start, item.end) for item in timecodes if item.end > item.start),
        key=lambda item: item[0],
    )
    if not valid:
        return 0.0
    total = 0.0
    current_start, current_end = valid[0]
    for start, end in valid[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    return total + current_end - current_start


def validate_markdown(
    markdown: str,
    *,
    source: str | None = None,
    require_timecodes: bool = False,
    strict_coverage: bool = False,
    expected_start: float | None = None,
    expected_end: float | None = None,
    time_tolerance: float = 0.05,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = _prohibited_sections(markdown)
    warnings: list[dict[str, Any]] = []
    shots = _parse_shots(markdown)

    if expected_start is not None and expected_end is not None and expected_end <= expected_start:
        errors.append(
            _issue(
                "invalid_expected_range",
                "--expected-end 必须大于 --expected-start。",
            )
        )

    if not shots:
        errors.append(
            _issue(
                "no_shots",
                "未找到 `### S001` 或 `### 镜头 S001` 形式的镜头块。",
            )
        )

    seen: dict[int, ShotBlock] = {}
    for shot in shots:
        if shot.number in seen:
            errors.append(
                _issue(
                    "duplicate_shot_number",
                    f"镜号 {shot.shot_id} 重复；首次出现于第 {seen[shot.number].heading_line} 行。",
                    shot=shot.shot_id,
                    line=shot.heading_line,
                )
            )
        else:
            seen[shot.number] = shot

    if shots and shots[0].number != 1:
        errors.append(
            _issue(
                "shot_sequence_start",
                f"镜号应从 S001 开始，实际从 {shots[0].shot_id} 开始。",
                shot=shots[0].shot_id,
                line=shots[0].heading_line,
            )
        )
    for previous, current in zip(shots, shots[1:]):
        expected = previous.number + 1
        if current.number != expected:
            errors.append(
                _issue(
                    "shot_sequence_gap",
                    f"{previous.shot_id} 之后应为 S{expected:03d}，实际为 {current.shot_id}。",
                    shot=current.shot_id,
                    line=current.heading_line,
                )
            )

    for shot in shots:
        visible_lines = _visible_body_lines(shot)
        fields = _field_presence(visible_lines)
        for key, display_name in REQUIRED_FIELDS.items():
            entries = fields[key]
            if not entries:
                errors.append(
                    _issue(
                        "missing_required_field",
                        f"缺少必备字段：{display_name}。",
                        shot=shot.shot_id,
                        line=shot.heading_line,
                    )
                )
            elif not any(has_content for _, has_content in entries):
                errors.append(
                    _issue(
                        "empty_required_field",
                        f"必备字段没有内容：{display_name}。",
                        shot=shot.shot_id,
                        line=entries[0][0],
                    )
                )
        blocking = _field_text(visible_lines, "blocking")
        if not all(re.search(rf"\b{state}\b", blocking, re.IGNORECASE) for state in ("IN", "CHANGE", "OUT")):
            errors.append(
                _issue(
                    "missing_blocking_states",
                    "演员、道具运动与调度须包含 IN、CHANGE、OUT 三个状态。",
                    shot=shot.shot_id,
                    line=shot.heading_line,
                )
            )
        sound = _field_text(visible_lines, "sound")
        full_silence = bool(FULL_SILENCE_RE.search(sound))
        if not full_silence and not DIALOGUE_CATEGORY_RE.search(sound):
            errors.append(
                _issue(
                    "missing_dialogue_category",
                    "声音字段缺少语音类别；请标注画内对白、旁白、画外音或无对白等类别。",
                    shot=shot.shot_id,
                    line=shot.heading_line,
                )
            )
        speech_text = re.sub(rf"(?:没有|无)(?:{SPEECH_RE.pattern})", "", sound, flags=re.IGNORECASE)
        if not full_silence and SPEECH_RE.search(speech_text) and not _has_speech_content(speech_text):
            errors.append(
                _issue(
                    "missing_speech_content",
                    "声音字段已标语音类别但缺少台词；听不清的局部写 [听不清]。",
                    shot=shot.shot_id,
                    line=shot.heading_line,
                )
            )
        for pattern, code, display in (
            (ENVIRONMENT_SOUND_RE, "missing_environment_sound", "环境声、拟音或音效"),
            (MUSIC_RE, "missing_music", "音乐/配乐"),
        ):
            if not full_silence and not pattern.search(sound):
                errors.append(
                    _issue(
                        code,
                        f"声音字段缺少{display}说明；没有该声音层时明确写无。",
                        shot=shot.shot_id,
                        line=shot.heading_line,
                    )
                )

    timecodes: list[tuple[ShotBlock, Timecode]] = []
    missing_timecodes: list[ShotBlock] = []
    for shot in shots:
        try:
            timecode = _extract_timecode(shot)
        except ValueError as exc:
            errors.append(
                _issue(
                    "invalid_timecode",
                    f"时码无法解析：{exc}",
                    shot=shot.shot_id,
                    line=shot.heading_line,
                )
            )
            continue
        if timecode is None:
            missing_timecodes.append(shot)
            continue
        timecodes.append((shot, timecode))
        if timecode.end <= timecode.start:
            errors.append(
                _issue(
                    "nonpositive_timecode",
                    f"时码结束值必须大于开始值：{timecode.raw}",
                    shot=shot.shot_id,
                    line=timecode.line,
                )
            )

    coverage_requested = (
        require_timecodes or expected_start is not None or expected_end is not None
    )
    for shot in missing_timecodes:
        target = errors if coverage_requested else warnings
        target.append(
            _issue(
                "missing_timecode",
                "该镜头未检测到时码。" if coverage_requested else "未检测到时码；已跳过该镜头的时码检查。",
                shot=shot.shot_id,
                line=shot.heading_line,
            )
        )

    previous_pair: tuple[ShotBlock, Timecode] | None = None
    for shot, timecode in timecodes:
        if previous_pair is not None:
            previous_shot, previous_timecode = previous_pair
            if timecode.start < previous_timecode.start - time_tolerance:
                errors.append(
                    _issue(
                        "timecode_out_of_order",
                        f"开始时码早于上一镜头 {previous_shot.shot_id} 的开始时码。",
                        shot=shot.shot_id,
                        line=timecode.line,
                    )
                )
            if timecode.start < previous_timecode.end - time_tolerance:
                errors.append(
                    _issue(
                        "timecode_overlap",
                        f"与上一镜头 {previous_shot.shot_id} 重叠 "
                        f"{previous_timecode.end - timecode.start:.3f} 秒。",
                        shot=shot.shot_id,
                        line=timecode.line,
                    )
                )
            elif timecode.start > previous_timecode.end + time_tolerance:
                gap = timecode.start - previous_timecode.end
                target = errors if strict_coverage else warnings
                target.append(
                    _issue(
                        "timecode_gap",
                        f"与上一镜头 {previous_shot.shot_id} 之间存在 {gap:.3f} 秒未覆盖区间。",
                        shot=shot.shot_id,
                        line=timecode.line,
                    )
                )
        previous_pair = (shot, timecode)

    if timecodes:
        first_shot, first_timecode = timecodes[0]
        last_shot, last_timecode = timecodes[-1]
        if expected_start is not None and abs(first_timecode.start - expected_start) > time_tolerance:
            errors.append(
                _issue(
                    "coverage_start_mismatch",
                    f"首个时码从 {first_timecode.start:.3f} 秒开始，预期为 {expected_start:.3f} 秒。",
                    shot=first_shot.shot_id,
                    line=first_timecode.line,
                )
            )
        if expected_end is not None and abs(last_timecode.end - expected_end) > time_tolerance:
            errors.append(
                _issue(
                    "coverage_end_mismatch",
                    f"末个时码在 {last_timecode.end:.3f} 秒结束，预期为 {expected_end:.3f} 秒。",
                    shot=last_shot.shot_id,
                    line=last_timecode.line,
                )
            )
    elif shots:
        warnings.append(
            _issue(
                "timecode_checks_skipped",
                "文档未包含可解析时码；顺序、重叠和覆盖检查未执行。",
            )
        )

    timecode_values = [timecode for _, timecode in timecodes]
    report: dict[str, Any] = {
        "status": "PASS" if not errors else "FAIL",
        "shot_count": len(shots),
        "errors": errors,
        "warnings": warnings,
        "source": source,
        "shot_ids": [shot.shot_id for shot in shots],
        "timecodes": {
            "present_count": len(timecodes),
            "missing_count": len(missing_timecodes),
            "all_shots_timecoded": bool(shots) and not missing_timecodes,
            "covered_seconds": _union_duration(timecode_values),
            "first_start": timecode_values[0].start if timecode_values else None,
            "last_end": timecode_values[-1].end if timecode_values else None,
            "tolerance_seconds": time_tolerance,
        },
        "required_fields": list(REQUIRED_FIELDS.values()),
        "pass_scope": PASS_SCOPE,
    }
    return report


def _failure_report(source: str, message: str) -> dict[str, Any]:
    return {
        "status": "FAIL",
        "shot_count": 0,
        "errors": [_issue("input_error", message)],
        "warnings": [],
        "source": source,
        "shot_ids": [],
        "timecodes": {
            "present_count": 0,
            "missing_count": 0,
            "all_shots_timecoded": False,
            "covered_seconds": 0.0,
            "first_start": None,
            "last_end": None,
            "tolerance_seconds": None,
        },
        "required_fields": list(REQUIRED_FIELDS.values()),
        "pass_scope": PASS_SCOPE,
    }


def _emit_report(report: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if output is None or str(output) == "-":
        sys.stdout.write(rendered)
        return
    destination = output.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    print(f"{report['status']}: {destination}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    configure_console_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    storyboard = args.storyboard.expanduser().resolve()
    try:
        markdown = storyboard.read_text(encoding="utf-8-sig")
        report = validate_markdown(
            markdown,
            source=str(storyboard),
            require_timecodes=args.require_timecodes,
            strict_coverage=args.strict_coverage,
            expected_start=args.expected_start,
            expected_end=args.expected_end,
            time_tolerance=args.time_tolerance,
        )
    except (OSError, UnicodeError) as exc:
        report = _failure_report(str(storyboard), f"无法读取 Markdown：{exc}")

    try:
        _emit_report(report, args.output)
    except OSError as exc:
        print(f"error: 无法写入 JSON 报告：{exc}", file=sys.stderr)
        return 2
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
