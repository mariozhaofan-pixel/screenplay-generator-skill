#!/usr/bin/env python3
"""Run cross-brief candidate documents through delivery contracts."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "script-generator" / "scripts" / "validate_delivery.py"


def resolved(base: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve(strict=False) if path.is_absolute() else (base / path).resolve(strict=False)


def run_validator(document: Path, contract: Path) -> tuple[int, dict[str, Any]]:
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
    output = result.stdout.strip() or result.stderr.strip()
    return result.returncode, json.loads(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate generic forward-test candidates from a JSON manifest."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest_path = args.manifest.resolve(strict=False)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise SystemExit("manifest.cases must be a non-empty list")

    results = []
    for case in cases:
        case_id = str(case["id"])
        document = resolved(manifest_path.parent, str(case["document"]))
        contract = resolved(manifest_path.parent, str(case["contract"]))
        text = document.read_text(encoding="utf-8")
        exit_code, report = run_validator(document, contract)
        assertion_errors = []
        for phrase in case.get("required_phrases", []):
            if str(phrase) not in text:
                assertion_errors.append(f"required phrase missing: {phrase}")
        for phrase in case.get("forbidden_phrases", []):
            if str(phrase) in text:
                assertion_errors.append(f"forbidden phrase present: {phrase}")
        expected_status = case.get("expected_status", "pass")
        passed = (
            report.get("status") == expected_status
            and ((expected_status == "pass" and exit_code == 0) or expected_status != "pass")
            and not assertion_errors
        )
        results.append(
            {
                "assertion_errors": assertion_errors,
                "case": case_id,
                "document_sha256": report.get("document_sha256"),
                "error_codes": sorted(
                    item.get("code", "") for item in report.get("errors", [])
                ),
                "passed": passed,
                "status": report.get("status"),
                "warning_codes": sorted(
                    item.get("code", "") for item in report.get("warnings", [])
                ),
            }
        )

    payload = {
        "cases_passed": sum(1 for item in results if item["passed"]),
        "cases_total": len(results),
        "results": results,
        "status": "pass" if all(item["passed"] for item in results) else "fail",
    }
    output = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        path = args.json_out.resolve(strict=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
