from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DURATION = 300.0
ID_PATTERN = r"(?:CUT|S)\d{3,}[A-Z]*"
TIME_RE = re.compile(r"^(?P<h>\d{2}):(?P<m>[0-5]\d):(?P<s>[0-5]\d)\.(?P<ms>\d{3})$")
SHOT_RE = re.compile(
    r"^###[ \t]+(?P<id>(?P<prefix>CUT|S)(?P<num>\d{3,})(?P<suffix>[A-Z]*))｜(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})"
    r"[–-](?P<end>\d{2}:\d{2}:\d{2}\.\d{3})｜(?P<dur>\d+(?:\.\d+)?)秒｜(?P<role>.+)$",
    re.MULTILINE,
)

FINAL_HEADINGS = (
    "## 方向确认摘要",
    "## 当期研究与使用边界",
    "## 钩子链与回收表",
    "## 人物、场景与关键道具",
    "## 逐镜分镜",
    "## 终检",
)

SHOT_FIELDS = (
    "场景与人物",
    "画面与构图",
    "摄影机",
    "前后景与遮挡",
    "调度（IN/CHANGE/OUT）",
    "表演与微动作",
    "台词/旁白/屏幕文字",
    "环境/拟音/音效/音乐",
    "剪辑与节奏",
    "钩子职责与回收",
    "连续性与制作边界",
)

CRITICAL_UNIQUENESS_FIELDS = (
    "画面与构图",
    "调度（IN/CHANGE/OUT）",
    "钩子职责与回收",
    "连续性与制作边界",
)

GENERIC_SHOT_ROLES = {"推进剧情", "过渡", "转场", "镜头", "冲突", "反转", "高潮"}
PLACEHOLDER_RE = re.compile(r"(?:TBD|TODO|待补|待生成|待完善|按需填写|<[^>\n]{1,40}>)", re.I)
CHALLENGE_FIELDS = ("观看焦点与目标", "挑战契约", "升级与最终兑现")
CHALLENGE_CONTRACT_LABELS = ("参赛", "机制", "限制", "出局", "胜负奖励", "失败后果")
OPTION_RE = re.compile(
    r"^[ \t]*(?:-[ \t]*)?(?:"
    r"\*\*选项[ \t]*[A-Z0-9一二三四①②③④][^\r\n]*?\*\*[ \t]*(?:[：:][ \t]*)?"
    r"|选项[ \t]*[A-Z0-9一二三四①②③④][^\r\n：:]*[：:][ \t]*"
    r")(?P<body>[^\r\n]*)\r?$",
    re.MULTILINE,
)
DECISION_STATES = ("明确锁定", "当前采用", "探索候选", "尚未决定")
DECISION_PERMISSION_FIELDS = ("允许改动范围", "用户授权代定")
STAGE_CONFIRMATION_FIELDS = (
    "当前阶段",
    "本次审阅产物",
    "沿用与锁定",
    "新增待确认",
    "本次确认范围",
    "下一交付",
    "允许改动范围",
)
FULL_STORYBOARD_HEADING_RE = re.compile(
    r"^##[ \t]+(?:逐镜分镜|完整分镜(?:主稿)?)[ \t]*\r?$", re.MULTILINE
)
# Chinese prose may touch an ID; only ASCII identifier characters delimit it.
HOOK_ID_RE = re.compile(r"(?<![A-Za-z0-9_])H\d{2,3}(?![A-Za-z0-9_])")
GENERIC_CRITICAL_VALUES = {
    "无",
    "同上",
    "保持一致",
    "延续前镜",
    "承接前镜",
    "按前镜",
    "略",
    "...",
    "……",
    "—",
}


@dataclass(frozen=True)
class Shot:
    number: int
    start: float
    end: float
    labelled_duration: float
    role: str
    body: str
    identifier: str = ""
    prefix: str = "S"
    suffix: str = ""
    raw_start: int = 0
    raw_end: int = 0
    header: str = ""


def parse_timecode(value: str) -> float:
    match = TIME_RE.match(value)
    if not match:
        raise ValueError(f"invalid timecode: {value}")
    return (
        int(match.group("h")) * 3600
        + int(match.group("m")) * 60
        + int(match.group("s"))
        + int(match.group("ms")) / 1000
    )


def visible_markdown(text: str) -> str:
    """Mask fenced examples while retaining offsets into the original document."""
    result: list[str] = []
    fence = ""
    fence_length = 0
    for line in text.splitlines(keepends=True):
        opening = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})", line)
        if fence:
            result.append(re.sub(r"[^\r\n]", " ", line))
            if re.match(rf"^[ \t]{{0,3}}{re.escape(fence)}{{{fence_length},}}[ \t]*(?:\r?\n)?$", line):
                fence = ""
        elif opening:
            fence = opening.group(1)[0]
            fence_length = len(opening.group(1))
            result.append(re.sub(r"[^\r\n]", " ", line))
        else:
            result.append(line)
    return "".join(result)


def parse_shots(text: str) -> list[Shot]:
    visible = visible_markdown(text)
    matches = list(SHOT_RE.finditer(visible))
    shots: list[Shot] = []
    for match in matches:
        next_heading = re.search(r"^#{1,3}[ \t]+", visible[match.end():], re.MULTILINE)
        body_end = match.end() + next_heading.start() if next_heading else len(text)
        shots.append(
            Shot(
                number=int(match.group("num")),
                start=parse_timecode(match.group("start")),
                end=parse_timecode(match.group("end")),
                labelled_duration=float(match.group("dur")),
                role=match.group("role").strip(),
                body=text[match.end() : body_end],
                identifier=match.group("id"),
                prefix=match.group("prefix"),
                suffix=match.group("suffix"),
                raw_start=match.start(),
                raw_end=body_end,
                header=text[match.start():match.end()],
            )
        )
    return shots


def shot_identity_errors(text: str, shots: list[Shot]) -> list[str]:
    errors: list[str] = []
    headings = re.findall(r"^###[ \t]+(?:CUT|S)\d[^\n]*$", visible_markdown(text), re.MULTILINE)
    if len(headings) != len(shots):
        errors.append("malformed CUT/S heading; every shot must use the complete timecode format")
    if len({shot.prefix for shot in shots}) > 1:
        errors.append("mixed CUT and S identifiers are not allowed in one storyboard")
    keys: list[tuple[int, int]] = []
    for shot in shots:
        rank = 0
        for char in shot.suffix:
            rank = rank * 26 + ord(char) - ord("A") + 1
        keys.append((shot.number, rank))
        if shot.number <= 0:
            errors.append(f"invalid shot identifier: {shot.identifier}")
    if len(keys) != len(set(keys)):
        errors.append("duplicate shot identifier")
    if keys != sorted(keys):
        errors.append("shot identifiers must remain in numeric and insertion-suffix order")
    return errors


def extract_field(body: str, field: str) -> str:
    match = re.search(
        rf"^-[ \t]*\*\*{re.escape(field)}：\*\*[ \t]*(?P<value>[^\r\n]*)\r?$",
        body,
        re.MULTILINE,
    )
    return match.group("value").strip() if match else ""


def normalized_value(value: str) -> str:
    return re.sub(r"\s+", "", value).strip("。；;，,")


def challenge_direction_section(text: str, heading: str) -> str:
    visible = visible_markdown(text)
    match = re.search(rf"^##[ \t]+{re.escape(heading)}[ \t]*\r?$", visible, re.MULTILINE)
    if not match:
        return ""
    next_heading = re.search(r"^#{1,2}[ \t]+", visible[match.end():], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(visible)
    section = visible[match.end():end]
    if not re.search(r"^- 创作模式：挑战综艺[ \t]*\r?$", section, re.MULTILINE):
        return ""
    return section


def has_full_storyboard(text: str) -> bool:
    """Return whether a recognized complete-storyboard heading is present."""
    return bool(FULL_STORYBOARD_HEADING_RE.search(visible_markdown(text)))


def decision_ledger_errors(text: str) -> list[str]:
    """Validate the current four-state ledger without breaking legacy ledgers."""
    errors: list[str] = []
    state_matches = {
        state: re.search(
            rf"^-[ \t]*{re.escape(state)}：[ \t]*(?P<value>[^\r\n]+)\r?$",
            text,
            re.MULTILINE,
        )
        for state in DECISION_STATES
    }
    present_states = [state for state, match in state_matches.items() if match]
    if present_states:
        for state, match in state_matches.items():
            if match is None or not match.group("value").strip():
                errors.append(f"decision ledger missing concrete state: {state}")
        permission_present = False
        for field in DECISION_PERMISSION_FIELDS:
            match = re.search(
                rf"^-[ \t]*{re.escape(field)}：[ \t]*(?P<value>[^\r\n]+)\r?$",
                text,
                re.MULTILINE,
            )
            if match and match.group("value").strip():
                permission_present = True
        if not permission_present:
            errors.append("decision ledger missing independent permission line: 允许改动范围/用户授权代定")
        return errors

    # Older accepted transcripts use 已锁/待定. Keep them readable and valid.
    for state in ("已锁", "待定"):
        if not re.search(rf"^-[ \t]*{state}：[ \t]*\S.+$", text, re.MULTILINE):
            errors.append(f"decision ledger missing state: {state}")
    return errors


def validate_challenge_fields(section: str) -> list[str]:
    errors: list[str] = []
    values: dict[str, str] = {}
    for field in CHALLENGE_FIELDS:
        match = re.search(rf"^-[ \t]*{field}：[ \t]*([^\r\n]*)\r?$", section, re.MULTILINE)
        value = match.group(1).strip() if match else ""
        if not value:
            errors.append(f"challenge mode missing concrete field: {field}")
            continue
        values[field] = value
        if PLACEHOLDER_RE.search(value):
            errors.append(f"challenge mode field contains a placeholder: {field}")
    focus = values.get("观看焦点与目标", "")
    if focus and not focus.startswith(("群体淘汰", "群像选手", "单一主角")):
        errors.append("观看焦点与目标 must start with 群体淘汰, 群像选手, or 单一主角")
    contract = values.get("挑战契约", "")
    if contract:
        for label in CHALLENGE_CONTRACT_LABELS:
            match = re.search(rf"【{label}】([^【\r\n]*)", contract)
            if not match or not normalized_value(match.group(1)):
                errors.append(f"挑战契约 missing non-empty subvalue: 【{label}】")
    return errors


def validate_question(text: str) -> tuple[list[str], list[str], dict[str, object]]:
    """Check choice-question structure, not source use or creative maturity."""
    errors: list[str] = []
    warnings: list[str] = []
    visible = visible_markdown(text)
    option_lines = [match.group("body") for match in OPTION_RE.finditer(visible)]
    option_count = len(option_lines)
    if option_count < 2:
        errors.append(f"need at least 2 answer options; found {option_count}")
    if has_full_storyboard(text):
        errors.append("question mode must not contain a full storyboard")
    unresolved_re = re.compile(
        r"^[ \t]*(?:-[ \t]*)?(?:\*\*)?(?:还没想清楚的一个问题|还需决定|当前未决问题|先选一个关键方向)"
        r"[：:](?:\*\*)?[ \t]*(?P<body>[^\r\n]*)\r?$",
        re.MULTILINE,
    )
    unresolved = list(unresolved_re.finditer(visible))
    if len(unresolved) != 1:
        errors.append("each turn must isolate exactly one unresolved question")

    def unfinished(value: str) -> bool:
        normalized = normalized_value(value).strip("*`_ ")
        return (
            not re.search(r"\w", normalized)
            or normalized in GENERIC_CRITICAL_VALUES
            or bool(PLACEHOLDER_RE.search(value))
        )

    if any(unfinished(match.group("body")) for match in unresolved):
        errors.append("current unresolved question is empty or unfinished")
    for index, body in enumerate(option_lines, 1):
        if unfinished(body):
            errors.append(f"option {index} is empty or unfinished")
    normalized_options = [normalized_value(body).strip("*`_ ") for body in option_lines]
    if len(normalized_options) != len(set(normalized_options)):
        errors.append("two or more direction options are textually identical")
    if "换一批" not in visible:
        errors.append("missing way to request another batch of answers: 换一批")
    if "自定义" not in visible and "组合" not in visible:
        errors.append("missing way to customize or combine answers: 自定义/组合")
    metrics: dict[str, object] = {
        "option_count": option_count,
        "unresolved_question_count": len(unresolved),
        "validation_scope": "question/options structure only; not source use, beat checks, or creative maturity",
    }
    return errors, warnings, metrics


def validate_confirmation(text: str) -> tuple[list[str], list[str], dict[str, object]]:
    errors: list[str] = []
    warnings: list[str] = []
    has_stage_card = bool(re.search(r"^##[ \t]+阶段确认卡[ \t]*\r?$", text, re.MULTILINE))
    has_direction_card = bool(re.search(r"^##[ \t]+方向确认卡[ \t]*\r?$", text, re.MULTILINE))
    if not has_stage_card and not has_direction_card:
        errors.append("missing heading: ## 阶段确认卡 or ## 方向确认卡")
    actions = ("确认本阶段", "修改一项", "换一批") if has_stage_card else ("确认方向", "修改一项", "换一批")
    for value in actions:
        if value not in text:
            errors.append(f"missing confirmation action: {value}")
    if has_full_storyboard(text):
        errors.append("full storyboard appeared before explicit confirmation")
    if has_stage_card:
        required = STAGE_CONFIRMATION_FIELDS
        challenge = challenge_direction_section(text, "阶段确认卡")
    else:
        required = (
            "一句话故事",
            "开头承诺",
            "世界规则",
            "主角欲望",
            "核心冲突",
            "不可逆代价",
            "高潮选择",
            "结局与评论分歧",
            "平台/时长/形式",
            "热点/IP使用边界",
            "仍由模型代定的次要项",
        )
        challenge = challenge_direction_section(text, "方向确认卡")
        if challenge:
            required = tuple(value for value in required if value not in ("主角欲望", "不可逆代价", "高潮选择"))
    if challenge:
        errors.extend(validate_challenge_fields(challenge))
    for value in required:
        match = re.search(rf"^-[ \t]*{re.escape(value)}：[ \t]*(?P<body>\S+.*)$", text, re.MULTILINE)
        if not match:
            errors.append(f"confirmation card missing concrete field: {value}")
        elif PLACEHOLDER_RE.search(match.group("body")):
            errors.append(f"confirmation card field contains a placeholder: {value}")
    return errors, warnings, {"card_type": "stage"} if has_stage_card else {}


def validate_final(
    text: str,
    expected_duration: float | None,
    tolerance: float,
    min_shots: int | None,
) -> tuple[list[str], list[str], dict[str, object]]:
    errors: list[str] = []
    warnings: list[str] = []
    expected_duration = DEFAULT_DURATION if expected_duration is None else expected_duration
    if not math.isfinite(expected_duration) or expected_duration <= 0:
        return ["expected duration must be finite and positive"], [], {}
    if not math.isfinite(tolerance) or tolerance < 0:
        return ["tolerance must be finite and non-negative"], [], {}
    if min_shots is not None and (not isinstance(min_shots, int) or min_shots < 1):
        return ["minimum shots must be a positive integer"], [], {}
    for heading in FINAL_HEADINGS:
        if heading not in text:
            errors.append(f"missing heading: {heading}")

    required = (
        "平台/时长/画幅",
        "一句话故事",
        "开头承诺",
        "主角欲望与不可逆代价",
        "高潮选择与结局承诺",
        "用户确认",
    )
    challenge = challenge_direction_section(text, "方向确认摘要")
    if challenge:
        required = tuple(value for value in required if value not in ("主角欲望与不可逆代价", "高潮选择与结局承诺"))
        errors.extend(validate_challenge_fields(challenge))
    for value in required:
        if not re.search(rf"^-\s*{re.escape(value)}：\s*\S.+$", text, re.MULTILINE):
            errors.append(f"direction confirmation summary missing concrete value: {value}")

    try:
        shots = parse_shots(text)
    except ValueError as exc:
        return [str(exc)], warnings, {}
    errors.extend(shot_identity_errors(text, shots))
    if not shots:
        errors.append("full storyboard has no parseable shot blocks")
    if min_shots is not None and len(shots) < min_shots:
        errors.append(
            f"need at least {min_shots} shots as explicitly requested; "
            f"found {len(shots)}"
        )

    uniqueness_values: dict[str, list[str]] = {
        field: [] for field in CRITICAL_UNIQUENESS_FIELDS
    }
    for shot in shots:
        if shot.end <= shot.start:
            errors.append(f"{shot.identifier} end must be after start")
        measured = shot.end - shot.start
        if abs(measured - shot.labelled_duration) > max(tolerance, 0.011):
            errors.append(
                f"{shot.identifier} duration label {shot.labelled_duration:.3f}s "
                f"does not match timecodes {measured:.3f}s"
            )
        for field in SHOT_FIELDS:
            if f"**{field}：**" not in shot.body:
                errors.append(f"{shot.identifier} missing field: {field}")
            else:
                value = extract_field(shot.body, field)
                if not value:
                    errors.append(f"{shot.identifier} has empty field: {field}")
        if "IN=" not in shot.body or "CHANGE=" not in shot.body or "OUT=" not in shot.body:
            errors.append(f"{shot.identifier} blocking must contain IN/CHANGE/OUT")
        if not shot.role:
            errors.append(f"{shot.identifier} missing hook/beat role")
        elif shot.role in GENERIC_SHOT_ROLES:
            errors.append(
                f"{shot.identifier} uses generic role '{shot.role}' instead of a shot-specific beat"
            )
        placeholder = PLACEHOLDER_RE.search(shot.body)
        if placeholder:
            errors.append(
                f"{shot.identifier} contains unresolved placeholder: {placeholder.group(0)}"
            )
        for state in ("IN", "CHANGE", "OUT"):
            match = re.search(rf"`?{state}=`?\s*([^；;\n]+)", shot.body)
            if not match or len(normalized_value(match.group(1))) < 2:
                errors.append(f"{shot.identifier} has empty or non-concrete {state} state")
        for field in CRITICAL_UNIQUENESS_FIELDS:
            value = extract_field(shot.body, field)
            if value:
                normalized = normalized_value(value)
                uniqueness_values[field].append(normalized)
                if normalized in GENERIC_CRITICAL_VALUES or len(normalized) < 6:
                    errors.append(
                        f"{shot.identifier} field '{field}' is generic or too thin: {value}"
                    )

        hook_value = extract_field(shot.body, "钩子职责与回收")
        if hook_value and not HOOK_ID_RE.search(hook_value):
            errors.append(
                f"{shot.identifier} hook duty must reference a declared H-ID"
            )

    if len(shots) >= 8:
        unique_role_ratio = len({shot.role for shot in shots}) / len(shots)
        if unique_role_ratio < 0.50:
            errors.append(
                f"shot-role diversity is only {unique_role_ratio:.1%}; beat labels appear templated"
            )
    duplicate_limit = max(3, math.ceil(len(shots) * 0.35))
    for field, values in uniqueness_values.items():
        if not values:
            continue
        value, count = collections.Counter(values).most_common(1)[0]
        if count >= duplicate_limit:
            errors.append(
                f"field '{field}' repeats one identical value in {count}/{len(shots)} shots"
            )

    if shots:
        if abs(shots[0].start) > tolerance:
            errors.append(f"coverage must start at 0.000s; found {shots[0].start:.3f}s")
        for left, right in zip(shots, shots[1:]):
            gap = right.start - left.end
            if abs(gap) > tolerance:
                kind = "gap" if gap > 0 else "overlap"
                errors.append(
                    f"{kind} between {left.identifier} and {right.identifier}: {gap:+.3f}s"
                )
        if expected_duration is not None and abs(shots[-1].end - expected_duration) > tolerance:
            errors.append(
                f"coverage must end at {expected_duration:.3f}s; found {shots[-1].end:.3f}s"
            )

    if not re.search(r"调研截止：\s*20\d{2}-\d{2}-\d{2}", text):
        errors.append("missing dated research cutoff: 调研截止：YYYY-MM-DD")
    link_count = len(re.findall(r"https?://[^\s)>]+", text))
    if link_count < 1 and "未执行当期核验" not in text:
        warnings.append("no direct research source URL found")

    hook_rows = re.findall(
        rf"^\|\s*(H\d{{2,3}})\s*\|[^\n]*\|\s*({ID_PATTERN})\s*\|[^\n]*\|\s*({ID_PATTERN})\s*\|[^\n]*$",
        text,
        re.MULTILINE,
    )
    declared_hooks = {row[0] for row in hook_rows}
    if not declared_hooks:
        errors.append("hook chain table has no parseable H-ID row")
    valid_shot_ids = {shot.identifier for shot in shots}
    for hook_id, first_shot, recovery_shot in hook_rows:
        if first_shot not in valid_shot_ids:
            errors.append(f"{hook_id} first-shot reference does not exist: {first_shot}")
        if recovery_shot not in valid_shot_ids:
            errors.append(f"{hook_id} recovery-shot reference does not exist: {recovery_shot}")
        if not any(
            hook_id in extract_field(shot.body, "钩子职责与回收")
            for shot in shots
        ):
            errors.append(f"declared hook never appears in a shot duty: {hook_id}")

    shot_hook_ids = {
        hook_id
        for shot in shots
        for hook_id in HOOK_ID_RE.findall(extract_field(shot.body, "钩子职责与回收"))
    }
    for hook_id in sorted(shot_hook_ids - declared_hooks):
        errors.append(f"shot duty references undeclared hook: {hook_id}")

    return errors, warnings, {
        "shot_count": len(shots),
        "expected_duration": expected_duration,
        "coverage_start": shots[0].start if shots else None,
        "coverage_end": shots[-1].end if shots else None,
        "mean_shot_length": (
            round((shots[-1].end - shots[0].start) / len(shots), 3) if shots else None
        ),
        "effective_min_shots": min_shots,
        "research_link_count": link_count,
        "declared_hook_count": len(declared_hooks),
    }


def without_revision_section(text: str) -> tuple[str, list[str]]:
    headings = list(re.finditer(r"^##[ \t]+版本与修订[ \t]*\r?$", text, re.MULTILINE))
    if len(headings) > 1:
        return text, ["only one version/revision section is allowed"]
    if not headings:
        return text, []
    heading = headings[0]
    next_heading = re.search(r"^#{1,2}[ \t]+", text[heading.end():], re.MULTILINE)
    end = heading.end() + next_heading.start() if next_heading else len(text)
    first_shot = SHOT_RE.search(visible_markdown(text))
    if first_shot and end > first_shot.start():
        return text, ["version/revision section must precede all shot blocks"]
    return text[:heading.start()] + text[end:], []


def validate_revision(
    text: str,
    baseline: str,
    cuts: list[str],
    fields: list[str],
) -> tuple[list[str], list[str], dict[str, object]]:
    """Check only the authorized delta, without applying new-draft requirements."""
    errors: list[str] = []
    if not cuts or len(set(cuts)) != len(cuts):
        errors.append("revision requires a non-empty unique list of target cuts")
    if not fields or len(set(fields)) != len(fields):
        errors.append("revision requires a non-empty unique list of fields")
    unknown = sorted(set(fields) - set(SHOT_FIELDS))
    if unknown:
        errors.append(f"unknown revision fields: {unknown}")
    current, current_errors = without_revision_section(text)
    original, baseline_errors = without_revision_section(baseline)
    errors.extend(current_errors + baseline_errors)
    try:
        new_shots, old_shots = parse_shots(current), parse_shots(original)
    except ValueError as exc:
        return errors + [str(exc)], [], {}
    if not old_shots:
        errors.append("baseline has no parseable shot blocks")
    errors.extend(shot_identity_errors(current, new_shots))
    errors.extend(shot_identity_errors(original, old_shots))
    old_ids = [shot.identifier for shot in old_shots]
    new_ids = [shot.identifier for shot in new_shots]
    if old_ids != new_ids:
        errors.append("shot IDs/order changed; structural edits require final validation")
    missing = sorted(set(cuts) - set(old_ids))
    if missing:
        errors.append(f"target cuts do not exist in baseline: {missing}")
    if errors:
        return errors, [], {"changed_cut_ids": []}

    new_parts: list[str] = []
    old_parts: list[str] = []
    new_cursor = old_cursor = 0
    changed: list[str] = []
    for old, new in zip(old_shots, new_shots):
        old_raw = original[old.raw_start:old.raw_end]
        new_raw = current[new.raw_start:new.raw_end]
        if old_raw != new_raw:
            changed.append(old.identifier)
        if old.header != new.header:
            errors.append(f"{old.identifier} header/timecodes changed; use final validation for structural edits")
        if old.identifier not in cuts:
            if old_raw != new_raw:
                errors.append(f"unauthorized change outside target cuts: {old.identifier}")
        else:
            for field in fields:
                pattern = re.compile(
                    rf"(^-[ \t]*\*\*{re.escape(field)}：\*\*[ \t]*)([^\r\n]*)(\r?$)",
                    re.MULTILINE,
                )
                old_matches, new_matches = list(pattern.finditer(old_raw)), list(pattern.finditer(new_raw))
                if len(old_matches) != 1 or len(new_matches) != 1:
                    errors.append(f"{old.identifier} must retain exactly one field: {field}")
                    continue
                value = new_matches[0].group(2).strip()
                if not value or PLACEHOLDER_RE.search(value):
                    errors.append(f"{old.identifier} changed field is empty or unfinished: {field}")
                elif field in CRITICAL_UNIQUENESS_FIELDS and (
                    normalized_value(value) in GENERIC_CRITICAL_VALUES or len(normalized_value(value)) < 6
                ):
                    errors.append(f"{old.identifier} changed field is non-concrete: {field}")
                if field == "调度（IN/CHANGE/OUT）":
                    for state in ("IN", "CHANGE", "OUT"):
                        state_match = re.search(rf"`?{state}=`?[ \t]*([^；;\n]+)", value)
                        if not state_match or len(normalized_value(state_match.group(1))) < 2:
                            errors.append(f"{old.identifier} changed blocking lacks concrete {state}")
                if field == "钩子职责与回收":
                    old_hooks = set(HOOK_ID_RE.findall(old_matches[0].group(2)))
                    if set(HOOK_ID_RE.findall(value)) != old_hooks:
                        errors.append(f"{old.identifier} hook dependencies changed; use final validation")
                old_raw = pattern.sub(lambda m: m.group(1) + "[AUTHORIZED_VALUE]" + m.group(3), old_raw)
                new_raw = pattern.sub(lambda m: m.group(1) + "[AUTHORIZED_VALUE]" + m.group(3), new_raw)
            if old_raw != new_raw:
                errors.append(f"{old.identifier} contains an unauthorized field/format change")
        old_parts.extend((original[old_cursor:old.raw_start], old_raw))
        new_parts.extend((current[new_cursor:new.raw_start], new_raw))
        old_cursor, new_cursor = old.raw_end, new.raw_end
    old_parts.append(original[old_cursor:])
    new_parts.append(current[new_cursor:])
    if "".join(old_parts) != "".join(new_parts):
        errors.append("protected text differs outside authorized values and version/revision metadata")
    return errors, [], {
        "shot_count": len(new_shots),
        "changed_cut_ids": changed,
        "authorized_cut_ids": cuts,
        "authorized_fields": fields,
        "coverage_end": new_shots[-1].end if new_shots else None,
        "validation_scope": "requested field delta only; no new-draft density or creative grading",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a co-creation question, an explicit confirmation card, or an explicitly requested full storyboard/revision.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--mode", choices=("question", "confirmation", "final", "revision"), required=True)
    parser.add_argument("--expected-duration", type=float, default=DEFAULT_DURATION)
    parser.add_argument("--tolerance", type=float, default=0.05)
    parser.add_argument("--min-shots", type=int, default=None, help="check a visible shot minimum only when explicitly requested; no default density floor")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--cuts", nargs="+")
    parser.add_argument("--fields", nargs="+")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input.is_file():
        print(json.dumps({"ok": False, "errors": [f"file not found: {args.input}"]}, ensure_ascii=False))
        return 2
    text = args.input.read_text(encoding="utf-8-sig")
    if args.mode == "question":
        errors, warnings, metrics = validate_question(text)
    elif args.mode == "confirmation":
        errors, warnings, metrics = validate_confirmation(text)
    elif args.mode == "revision":
        if args.baseline is None or not args.baseline.is_file():
            errors, warnings, metrics = ["revision requires an existing --baseline file"], [], {}
        else:
            errors, warnings, metrics = validate_revision(
                text, args.baseline.read_text(encoding="utf-8-sig"), args.cuts or [], args.fields or []
            )
    else:
        errors, warnings, metrics = validate_final(
            text,
            expected_duration=args.expected_duration,
            tolerance=args.tolerance,
            min_shots=args.min_shots,
        )
    report = {
        "ok": not errors,
        "mode": args.mode,
        "file": str(args.input.resolve()),
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
