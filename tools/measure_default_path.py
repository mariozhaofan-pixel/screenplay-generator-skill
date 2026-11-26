#!/usr/bin/env python3
"""Measure the default drafting path of viral-screenwriter (standard library).

The default path is SKILL.md plus the pages SKILL.md tells the model to read for
every seed-to-draft request. Every other page is read only when a specific gap
shows up. The total, counted in characters, must stay within BUDGET in both
editions, and the package must not carry any book text.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

BUDGET = 20_000
DEFAULT_PATH = (
    "SKILL.md",
    "references/coffee-break-method.md",
    "references/soul-questioning.md",
    "references/screenplay-format.md",
    "references/project-delivery.md",
    "references/exercise-orchestration.md",
)


def load_builder():
    path = Path(__file__).with_name("package_viral_screenwriter.py")
    spec = importlib.util.spec_from_file_location("builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def count(root: Path) -> dict:
    sizes = {}
    for name in DEFAULT_PATH:
        text = (root / name).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        sizes[name] = len(text)
    return sizes


def missing_from_entry(root: Path) -> list:
    """Every default page must be linked from the SKILL.md drafting section."""
    skill = (root / "SKILL.md").read_text(encoding="utf-8-sig")
    return [name for name in DEFAULT_PATH[1:] if f"]({name})" not in skill]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path,
                        default=Path(__file__).resolve().parents[1] / "viral-screenwriter")
    args = parser.parse_args()
    builder = load_builder()
    root = args.skill_root.resolve()
    rules = builder.read_object(builder.EDITION_RULES)
    report = {"budget": BUDGET, "editions": {}, "errors": []}
    if (root / "assets/books").exists():
        report["errors"].append("assets/books must not be part of the package")
    report["errors"] += [f"SKILL.md does not link default page {name}" for name in missing_from_entry(root)]
    with tempfile.TemporaryDirectory(prefix="screenwriter-budget-") as temp:
        for edition in ("feishu", "local"):
            stage = Path(temp).resolve() / edition / builder.ZIP_ROOT
            shutil.copytree(root, stage)
            builder.apply_edition(stage, edition, rules)
            sizes = count(stage)
            total = sum(sizes.values())
            report["editions"][edition] = {"total": total, "files": sizes}
            if total > BUDGET:
                report["errors"].append(f"{edition} default path is {total} characters; budget is {BUDGET}")
    report["ok"] = not report["errors"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
