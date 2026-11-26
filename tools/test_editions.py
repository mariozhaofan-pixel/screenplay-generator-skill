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
            # Book texts stay out of every release package.
            assert not [name for name in names if name.startswith(prefix + "assets/books/")]
            manifest = json.loads(archive.read(prefix + "package-manifest.json"))
            assert manifest["workspace_edition"] == edition
            # Release metadata comes from the rules, not from hand edits.
            assert builder.release_mismatch(manifest, rules, edition) == {}
            assert manifest["packaging_revision"] == f"{rules['date']}-{rules['version']}-dual-editions"
            install = archive.read(prefix + "INSTALL.md").decode("utf-8-sig")
            assert f"版本：{rules['date']} {rules['version']}" in install
            assert f"版本：{rules['date']} {rules['version']} {builder.EDITION_LABELS[edition]}" in install.splitlines()
            assert not [name for name in names if builder.is_stray(Path(name).name)
                        or any(builder.is_stray(part, True) for part in Path(name).parts[:-1])]
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
        # Caches, OS and editor junk must stop the build before --refresh can
        # write them into the manifest or a ZIP.
        stage = temporary_root / "stray-files"
        shutil.copytree(root, stage)
        manifest_before = (stage / "package-manifest.json").read_bytes()
        (stage / ".DS_Store").write_bytes(b"junk")
        (stage / "scripts/__pycache__").mkdir()
        (stage / "scripts/__pycache__/check_environment.cpython-312.pyc").write_bytes(b"junk")
        (stage / "references/.method-cards.md.swp").write_bytes(b"junk")
        (stage / "references/method-cards.md~").write_bytes(b"junk")
        for action in (builder.source_files, builder.refresh_metadata):
            try:
                action(stage)
            except builder.PackageError as exc:
                for name in (".DS_Store", "scripts/__pycache__", "references/.method-cards.md.swp",
                             "references/method-cards.md~"):
                    assert name in str(exc), (name, str(exc))
            else:
                raise AssertionError("Stray files were accepted")
        assert (stage / "package-manifest.json").read_bytes() == manifest_before
        reports["stray_files_rejected"] = True
        # A version bump that forgets the INSTALL version line must not build.
        stage = temporary_root / "stale-version-line"
        shutil.copytree(root, stage)
        install = stage / "INSTALL.md"
        install.write_bytes(install.read_bytes().replace(
            f"版本：{rules['date']} {rules['version']} ".encode("utf-8"), "版本：2000-01-01 v0 ".encode("utf-8"), 1))
        for edition in ("local", "feishu"):
            try:
                builder.check_install_version(stage, rules, edition)
            except builder.PackageError as exc:
                assert "version line" in str(exc)
            else:
                raise AssertionError("Stale INSTALL version line was accepted")
        reports["stale_install_version_rejected"] = True
        # A stale manifest revision is reported, and --refresh stamps it from the rules.
        manifest = builder.read_object(stage / "package-manifest.json")
        manifest["packaging_revision"] = "2000-01-01-v0-dual-editions"
        assert set(builder.release_mismatch(manifest, rules, "feishu")) == {"packaging_revision"}
        builder.write_object(stage / "package-manifest.json", manifest)
        builder.stamp_release(stage, rules, "feishu")
        assert builder.release_mismatch(builder.read_object(stage / "package-manifest.json"), rules, "feishu") == {}
        reports["stale_packaging_revision_restamped"] = True
    # A book text dropped back into the source tree must stop the build.
    with tempfile.TemporaryDirectory(prefix="screenwriter-book-guard-") as temporary:
        stage = Path(temporary).resolve() / "viral-screenwriter"
        shutil.copytree(root, stage)
        (stage / "assets/books").mkdir()
        (stage / "assets/books/full.md").write_text("text", encoding="utf-8")
        try:
            builder.source_files(stage)
        except builder.PackageError as exc:
            assert "Book texts are not packaged" in str(exc)
        else:
            raise AssertionError("Book text was accepted into the package")
    reports.update(ok=True, book_texts_rejected=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "edition-validation.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
