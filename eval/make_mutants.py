#!/usr/bin/env python3
"""Generate and test isolated structural mutants for validate_delivery.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "eval" / "fixtures"
ARTIFACTS = ROOT / "eval" / ".artifacts" / "mutants"
VALIDATOR = ROOT / "script-generator" / "scripts" / "validate_delivery.py"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"expected one occurrence for mutation: {old!r}")
    return text.replace(old, new, 1)


def add_budget_block(text: str) -> str:
    block = """【时长与生成合同】
- 模式：contract-budget
- 合同来源：测试硬合同
- 总目标/上限：12
- GEN单元上限：8
- 数值性质：planned_budget

| GEN/场景 | CUT范围 | 计划预算 | 显式上限 | 对白/动作可行性 |
|---|---|---:|---:|---|
| GEN-001 | CUT-001—CUT-002 | 8 | 8 | D-ID=D-001；自然读演=保守估读可执行；不可并行=停笔后翻页；允许重叠=画外后半句与翻页；冷启动/反应余量=已保留；结论=PASS |
| GEN-002 | CUT-003—CUT-003 | 4 | 8 | D-ID=D-002；自然读演=保守估读可执行；不可并行=落句后放笔；允许重叠=退让与视线回应；冷启动/反应余量=已保留；结论=PASS |

求和复核：8 + 4 = 12

"""
    text = replace_once(
        text,
        "- timing_mode：silent-default",
        "- timing_mode：contract-budget",
    )
    return text.replace("【创作假设】", block + "【创作假设】", 1)


def mutate_punctuation(text: str) -> str:
    return replace_once(text, "文本=你先别签。", "文本=你先别签！")


def mutate_cut_sequence(text: str) -> str:
    return replace_once(text, "### CUT-003 | S01-B02", "### CUT-004 | S01-B02")


def mutate_missing_field(text: str) -> str:
    line = (
        "- 导演意图：先用客观责任镜确认林岚没有靠夺走文件替周诚决定，"
        "再允许观众进入周诚的注意方向。\n"
    )
    return replace_once(text, line, "")


def mutate_missing_director_field(text: str) -> str:
    line = "- 关键画面/戏点：笔尖停住；编号被手指压住；笔横放在附件上。\n"
    return replace_once(text, line, "")


def mutate_old_event_residue(text: str) -> str:
    return replace_once(
        text,
        "笔尖未落墨，林岚手已离开桌沿，交给CUT-002。",
        "笔尖未落墨，林岚手已离开桌沿，旧桥段残留标记，交给CUT-002。",
    )


def mutate_deprecated_asset(text: str) -> str:
    return replace_once(
        text,
        "签字未发生，笔横放，林岚退开，场景结束。",
        "签字未发生，笔横放，林岚退开，沿用X:\\deprecated\\old.png，场景结束。",
    )


def mutate_second_master(text: str) -> str:
    row = (
        "| SCN-001 | 会议室/EVT-001 | external://scene/meeting-room | "
        "长桌、窗、单一出入口的相对位置 | 文件、笔、两把椅子 | "
        "第二会议室、监控间、走廊替代景 | S01/CUT-001-CUT-003/GEN-001-GEN-002 |\n"
    )
    duplicate = (
        row
        + "| SCN-002 | 会议室/EVT-001 | external://scene/alternate-room | "
        "另一套长桌与门窗位置 | 文件、笔、两把椅子 | 无 | S01/CUT-003/GEN-002 |\n"
    )
    return replace_once(text, row, duplicate)


def mutate_early_pov(text: str) -> str:
    return replace_once(
        text,
        "模式=字面POV | 主人=周诚 | 人物在场=是",
        "模式=字面POV | 主人=周诚 | 人物在场=否",
    )


def mutate_timing_overage(text: str) -> str:
    text = replace_once(
        text,
        "| GEN-001 | CUT-001—CUT-002 | 8 | 8 |",
        "| GEN-001 | CUT-001—CUT-002 | 8.1 | 8 |",
    )
    text = replace_once(
        text,
        "| GEN-002 | CUT-003—CUT-003 | 4 | 8 |",
        "| GEN-002 | CUT-003—CUT-003 | 3.9 | 8 |",
    )
    return replace_once(text, "求和复核：8 + 4 = 12", "求和复核：8.1 + 3.9 = 12")


def mutate_mode_mismatch(text: str) -> str:
    return replace_once(
        text,
        "- timing_mode：silent-default",
        "- timing_mode：contract-budget",
    )


def add_rights_notice(text: str) -> str:
    return (
        text.rstrip()
        + """

【版权出处与使用声明】
| Rights-ID | 类型 | 命名来源/版本 | replication_level | rights_status | 素材来源状态 | 拟使用方式 | 需取得的权利 | 证据与适用范围 | 影响Scene/CUT/GEN/Asset | 授权后填入/替换动作 |
|---|---|---|---|---|---|---|---|---|---|---|
| RIGHTS-001 | 测试片段/歌词 | 命名测试来源 | exact-dependent | rights-asserted | AUTHORIZED-ASSET / AUTHORIZED-LYRIC | 保留完整生产槽 | 待取得 | 未核验 | S01/CUT-001-CUT-003 | 授权后填入 |

使用选择：保留并取得授权 / 使用用户提供或已核验素材 / 替换为原创或适当授权方案
"""
    )


def mutate_rights_not_last(text: str) -> str:
    return text.rstrip() + "\n\n【附加说明】\n该段故意放在版权声明之后。\n"


def run_validator(document: Path, contract: Path) -> tuple[int, dict]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--document",
            str(document),
            "--contract",
            str(contract),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )
    stream = result.stdout.strip() or result.stderr.strip()
    return result.returncode, json.loads(stream)


def main() -> int:
    shutil.rmtree(ARTIFACTS, ignore_errors=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    valid_text = (FIXTURES / "valid_delivery.md").read_text(encoding="utf-8")
    silent_contract = FIXTURES / "valid_silent_contract.json"
    budget_contract = FIXTURES / "valid_budget_contract.json"

    valid_code, valid_report = run_validator(FIXTURES / "valid_delivery.md", silent_contract)
    budget_text = add_budget_block(valid_text)
    budget_path = ARTIFACTS / "valid_budget_delivery.md"
    budget_path.write_text(budget_text, encoding="utf-8")
    budget_code, budget_report = run_validator(budget_path, budget_contract)

    rights_text = add_rights_notice(valid_text)
    rights_path = ARTIFACTS / "valid_rights_delivery.md"
    rights_path.write_text(rights_text, encoding="utf-8")
    rights_contract_data = json.loads(silent_contract.read_text(encoding="utf-8"))
    rights_contract_data["rights"] = {
        "notice_must_be_last": True,
        "required": True,
        "required_status": "rights-asserted",
        "required_tokens": [
            "RIGHTS-001",
            "exact-dependent",
            "AUTHORIZED-ASSET",
            "AUTHORIZED-LYRIC",
            "保留并取得授权",
        ],
        "semantic_review_required": False,
        "semantic_reviewed": False,
    }
    rights_contract_path = ARTIFACTS / "valid_rights.contract.json"
    rights_contract_path.write_text(
        json.dumps(rights_contract_data, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    rights_code, rights_report = run_validator(rights_path, rights_contract_path)

    bookish_line = (
        "鉴于当前合同附件中的编号体系可能存在足以影响签署效力的逻辑错误，"
        "我认为应当由我本人承担逐页复核并在确认无误后再完成签字的责任。"
    )
    if valid_text.count("哪一页有问题，我自己核。") != 3:
        raise RuntimeError("bookish dialogue fixture replacement count changed")
    bookish_path = ARTIFACTS / "bookish_dialogue.md"
    bookish_path.write_text(
        valid_text.replace("哪一页有问题，我自己核。", bookish_line),
        encoding="utf-8",
    )
    bookish_contract_data = json.loads(silent_contract.read_text(encoding="utf-8"))
    bookish_contract_data["dialogue"]["semantic_review_required"] = True
    bookish_contract_data["dialogue"]["semantic_reviewed"] = False
    bookish_contract_path = ARTIFACTS / "bookish_dialogue.contract.json"
    bookish_contract_path.write_text(
        json.dumps(bookish_contract_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    bookish_code, bookish_report = run_validator(bookish_path, bookish_contract_path)
    bookish_warning = any(
        item.get("code") == "DIALOGUE_SEMANTIC_REVIEW"
        for item in bookish_report.get("warnings", [])
    )

    cases: list[tuple[str, Callable[[str], str], Path, str, str]] = [
        ("dialogue_punctuation", mutate_punctuation, silent_contract, "DIALOGUE_TEXT_MISMATCH", "silent"),
        ("cut_gap", mutate_cut_sequence, silent_contract, "CUT_SEQUENCE", "silent"),
        ("missing_cut_field", mutate_missing_field, silent_contract, "CUT_SCHEMA", "silent"),
        (
            "missing_scene_director_field",
            mutate_missing_director_field,
            silent_contract,
            "SCENE_DIRECTOR_MAP_SCHEMA",
            "silent",
        ),
        ("old_event_residue", mutate_old_event_residue, silent_contract, "REVISION_RESIDUE", "silent"),
        ("deprecated_asset", mutate_deprecated_asset, silent_contract, "REVISION_RESIDUE", "silent"),
        ("second_scene_master", mutate_second_master, silent_contract, "SCN_DUPLICATE_MASTER", "silent"),
        ("early_literal_pov", mutate_early_pov, silent_contract, "POV_PRESENCE", "silent"),
        ("gen_over_by_point_one", mutate_timing_overage, budget_contract, "TIMING_GEN_LIMIT", "budget"),
        ("mode_mismatch", mutate_mode_mismatch, silent_contract, "MODE_TIMING_MISMATCH", "silent"),
        ("rights_notice_not_last", mutate_rights_not_last, rights_contract_path, "RIGHTS_NOTICE_NOT_LAST", "rights"),
    ]

    results = []
    for name, mutate, contract, expected_code, base_kind in cases:
        if base_kind == "budget":
            base = budget_text
        elif base_kind == "rights":
            base = rights_text
        else:
            base = valid_text
        path = ARTIFACTS / f"{name}.md"
        path.write_text(mutate(base), encoding="utf-8")
        exit_code, report = run_validator(path, contract)
        codes = {item["code"] for item in report.get("errors", [])}
        passed = exit_code == 1 and expected_code in codes
        results.append(
            {
                "caught": passed,
                "error_codes": sorted(codes),
                "expected_code": expected_code,
                "name": name,
            }
        )

    valid_pass = (
        valid_code == 0
        and valid_report.get("status") == "pass"
        and not valid_report.get("errors")
        and budget_code == 0
        and budget_report.get("status") == "pass"
        and not budget_report.get("errors")
        and rights_code == 0
        and rights_report.get("status") == "pass"
        and not rights_report.get("errors")
    )
    semantic_warning_pass = (
        bookish_code == 0
        and bookish_report.get("status") == "pass"
        and not bookish_report.get("errors")
        and bookish_warning
    )
    caught = sum(1 for item in results if item["caught"])
    payload = {
        "hard_mutants_caught": caught,
        "hard_mutants_total": len(results),
        "mutants": results,
        "semantic_warning_sample_pass": semantic_warning_pass,
        "status": (
            "pass"
            if valid_pass and semantic_warning_pass and caught == len(results)
            else "fail"
        ),
        "valid_samples_false_positive_free": valid_pass,
    }
    report_path = ARTIFACTS.parent / "mutant_report.json"
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
