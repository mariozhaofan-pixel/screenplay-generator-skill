#!/usr/bin/env python3
"""Build and inspect both real editions; reject source drift and cloud leaks."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("builder", here / "package_viral_screenwriter.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    root = here.parent / "viral-screenwriter"
    rules = builder.read_object(here / "edition_rules.json")
    reports = {}
    book_hashes = {p.relative_to(root).as_posix(): builder.digest(p)
                   for p in builder.source_files(root) if p.is_relative_to(root / "assets/books")}
    for edition in ("local", "feishu"):
        output = args.output_dir / f"viral-screenwriter_{rules['version']}_{edition}_{rules['date']}.zip"
        report = builder.package_edition(root, output, edition)
        with zipfile.ZipFile(output) as archive:
            names = set(archive.namelist())
            prefix = "viral-screenwriter/"
            entrypoints = [name for name in names if Path(name).name.lower() == "skill.md"]
            assert entrypoints == [prefix + "SKILL.md"]
            assert report["bytes"] < 5_000_000
            for relative in rules["local_exclude"]:
                assert ((prefix + relative) in names) == (edition == "feishu")
            for name, expected in book_hashes.items():
                import hashlib
                assert hashlib.sha256(archive.read(prefix + name)).hexdigest() == expected
            manifest = json.loads(archive.read(prefix + "package-manifest.json"))
            assert manifest["workspace_edition"] == edition
        reports[edition] = report
    with tempfile.TemporaryDirectory(prefix="screenwriter-edition-tests-") as temporary:
        temporary_root = Path(temporary).resolve()
        assert temporary_root.is_relative_to(Path(tempfile.gettempdir()).resolve())
        # A maintainer may change a cloud paragraph without updating the local
        # alternative. The build must stop instead of shipping that paragraph.
        stage = temporary_root / "source-drift"
        shutil.copytree(root, stage)
        entrypoint = stage / "SKILL.md"
        text = entrypoint.read_text(encoding="utf-8")
        entrypoint.write_text(text.replace("## 开始时选择工作区", "## 工作区选择已改变", 1), encoding="utf-8")
        try:
            builder.apply_edition(stage, "local", rules)
        except builder.PackageError as exc:
            assert "source changed" in str(exc)
            reports["source_drift_rejected"] = True
        else:
            raise AssertionError("Changed edition source was silently accepted")
        # A new cloud-only integration must be classified explicitly before it
        # can appear in either edition's release rules.
        stage = temporary_root / "new-cloud-file"
        shutil.copytree(root, stage)
        (stage / "references/new-feishu-route.md").write_text("new integration", encoding="utf-8")
        try:
            builder.apply_edition(stage, "local", rules)
        except builder.PackageError as exc:
            assert "Unclassified cloud integration" in str(exc)
            reports["unclassified_cloud_file_rejected"] = True
        else:
            raise AssertionError("New cloud integration leaked into local edition")
        # An existing common route may acquire a cloud requirement under a
        # neutral filename; it must not evade the local edition check.
        stage = temporary_root / "new-cloud-prose"
        shutil.copytree(root, stage)
        (stage / "references/project-delivery.md").write_text("先完成飞书授权再开始。", encoding="utf-8")
        try:
            builder.apply_edition(stage, "local", rules)
        except builder.PackageError as exc:
            assert "Unclassified cloud workflow" in str(exc)
            reports["unclassified_cloud_prose_rejected"] = True
        else:
            raise AssertionError("Cloud prose leaked into local edition")
    assert book_hashes == {p.relative_to(root).as_posix(): builder.digest(p)
                          for p in builder.source_files(root) if p.is_relative_to(root / "assets/books")}
    reports.update(ok=True, book_library_unchanged=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "edition-validation.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
