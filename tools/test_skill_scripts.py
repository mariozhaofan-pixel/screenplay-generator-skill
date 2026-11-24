#!/usr/bin/env python3
"""Regression tests for the packaged helper scripts (standard library only).

Run: python -X utf8 -B tools/test_skill_scripts.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1] / "viral-screenwriter" / "scripts"
FIELDS = (
    ("场景与人物", "便利店收银台，夜班店员林岚独自值守"),
    ("画面与构图", "{n}号机位中景，收银台占画面下三分之一"),
    ("摄影机", "35mm，胸口高度，固定机位"),
    ("前后景与遮挡", "前景货架遮住左侧门口"),
    ("调度（IN/CHANGE/OUT）", "IN=林岚低头点货{n}；CHANGE=门铃响起她抬头；OUT=她把扫码枪握在手里{n}"),
    ("表演与微动作", "她停住数钱的手"),
    ("台词/旁白/屏幕文字", "林岚：欢迎光临。"),
    ("环境/拟音/音效/音乐", "冰柜低频嗡声"),
    ("剪辑与节奏", "门铃声上切"),
    ("钩子职责与回收", "H01 第{n}次提示同一件商品"),
    ("连续性与制作边界", "收银台灯光保持冷白，第{n}镜"),
)


def shot(number: int, start: str, end: str, seconds: str, role: str, skip: str = "") -> str:
    lines = [f"### CUT{number:03d}｜{start}–{end}｜{seconds}秒｜{role}"]
    for name, value in FIELDS:
        value = value.format(n=number)
        if name == skip:
            value = "林岚抬头看门口，没有写出调度状态"
        lines.append(f"- **{name}：** {value}")
    return "\n".join(lines)


def storyboard(skip: str = "") -> str:
    return "\n\n".join([
        "# 夜班\n\n## 方向确认摘要\n\n- 平台/时长/画幅：竖屏 6秒 9:16\n- 一句话故事：夜班店员发现每位顾客都买同一件商品\n"
        "- 开头承诺：第一位顾客的异常购买\n- 主角欲望与不可逆代价：林岚想弄清原因，代价是错过下班\n"
        "- 高潮选择与结局承诺：她决定自己也买一件\n- 用户确认：用户要求直接成稿",
        "## 当期研究与使用边界\n\n调研截止：2026-11-25；未执行当期核验。",
        "## 钩子链与回收表\n\n| H-ID | 钩子 | 首次 | 回收方式 | 回收 | 说明 |\n|---|---|---|---|---|---|\n"
        "| H01 | 同一件商品 | CUT001 | 揭示 | CUT002 | 两镜内回收 |",
        "## 人物、场景与关键道具\n\n- 林岚：夜班店员。",
        "## 逐镜分镜",
        shot(1, "00:00:00.000", "00:00:03.000", "3", "门铃打断点货"),
        shot(2, "00:00:03.000", "00:00:06.000", "3", "顾客放下同一件商品", skip),
        "## 终检\n\n- 结构完整。\n",
    ])


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-X", "utf8", "-B", str(SCRIPTS / script), *args],
                          capture_output=True, encoding="utf-8", errors="replace",
                          env=environment, timeout=120, check=False)


class ValidateOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="screenwriter-validate-")
        self.root = Path(self.temp.name)
        self.draft = self.root / "分镜主稿.md"
        self.draft.write_bytes(storyboard().encode("utf-8"))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_final_requires_expected_duration(self) -> None:
        completed = run("validate_output.py", str(self.draft), "--mode", "final")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--expected-duration", completed.stderr)

    def test_final_pass_and_module_style_aliases(self) -> None:
        report = self.root / "report.json"
        completed = run("validate_output.py", str(self.draft), "--mode", "final", "--expected-end", "6",
                        "--time-tolerance", "0.05", "-o", str(report))
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertTrue(json.loads(report.read_text(encoding="utf-8"))["ok"])
        completed = run("validate_output.py", str(self.draft), "--mode", "final", "--expected-duration", "6")
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_coverage_end_uses_given_duration_not_300(self) -> None:
        completed = run("validate_output.py", str(self.draft), "--mode", "final", "--expected-duration", "300")
        self.assertEqual(completed.returncode, 1)
        self.assertIn("coverage must end at 300.000s", completed.stdout)

    def test_missing_input_is_a_fail_report(self) -> None:
        completed = run("validate_output.py", str(self.root / "missing.md"), "--mode", "final",
                        "--expected-duration", "6")
        self.assertEqual(completed.returncode, 1)
        report = json.loads(completed.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("cannot read input file", report["errors"][0])

    def test_missing_blocking_state_is_reported_once_per_state(self) -> None:
        self.draft.write_bytes(storyboard(skip="调度（IN/CHANGE/OUT）").encode("utf-8"))
        completed = run("validate_output.py", str(self.draft), "--mode", "final", "--expected-duration", "6")
        self.assertEqual(completed.returncode, 1)
        errors = json.loads(completed.stdout)["errors"]
        self.assertNotIn("CUT002 blocking must contain IN/CHANGE/OUT", errors)
        for state in ("IN", "CHANGE", "OUT"):
            self.assertEqual(errors.count(f"CUT002 has empty or non-concrete {state} state"), 1)

    def test_revision_mode_still_checks_the_authorized_delta(self) -> None:
        baseline = self.root / "修改前基线.md"
        baseline.write_bytes(self.draft.read_bytes())
        self.draft.write_bytes(storyboard().replace("35mm，胸口高度，固定机位", "50mm，眼平高度，缓推", 1).encode("utf-8"))
        allowed = run("validate_output.py", str(self.draft), "--mode", "revision", "--baseline", str(baseline),
                      "--cuts", "CUT001", "--fields", "摄影机")
        self.assertEqual(allowed.returncode, 0, allowed.stdout)
        refused = run("validate_output.py", str(self.draft), "--mode", "revision", "--baseline", str(baseline),
                      "--cuts", "CUT002", "--fields", "摄影机")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("unauthorized change outside target cuts: CUT001", refused.stdout)

    def test_retired_modes_are_rejected(self) -> None:
        for mode in ("question", "confirmation"):
            self.assertEqual(run("validate_output.py", str(self.draft), "--mode", mode).returncode, 2)


class CheckEnvironmentTests(unittest.TestCase):
    def test_sync_mode_requires_python_311(self) -> None:
        completed = run("check_environment.py", "--mode", "sync")
        report = json.loads(completed.stdout)["modes"]["sync"]
        expected = sys.version_info >= (3, 11)
        self.assertEqual(report["ready"], expected)
        self.assertEqual(completed.returncode == 0, expected)

    def test_all_mode_keeps_media_scope(self) -> None:
        report = json.loads(run("check_environment.py", "--mode", "all").stdout)
        self.assertEqual(sorted(report["modes"]), ["asr", "ocr", "video", "writing"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
