#!/usr/bin/env python3
"""Maintain and package the compact viral-screenwriter skill using the stdlib.

Usage: python tools/package_viral_screenwriter.py --edition local --output release.zip [--refresh]
Without --refresh the source tree is read-only. Refresh updates the hash
inventory and the manifest release fields derived from tools/edition_rules.json.
Book texts are never packaged: a source tree that holds assets/books stops the build.
Stray files (caches, OS/editor junk, anything git ignores) stop the build.
The maintained source is the Feishu-capable edition. Both release editions are
built in an isolated temporary tree using guarded prose differences, one source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile


MAX_FILES = 200
MAX_ZIP_BYTES = 5_000_000  # The archive must be strictly smaller.
ZIP_ROOT = "viral-screenwriter"
EDITION_RULES = Path(__file__).with_name("edition_rules.json")
EDITION_LABELS = {"local": "本地版", "feishu": "飞书版"}
# Caches and OS/editor junk that must never reach a manifest or ZIP.
STRAY_DIRS = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                        ".ipynb_checkpoints", ".git", ".idea", ".vscode"})
STRAY_NAMES = frozenset({".ds_store", "thumbs.db", "ehthumbs.db", "desktop.ini"})
STRAY_SUFFIXES = (".pyc", ".pyo", ".swp", ".swo", ".swn", ".tmp", ".log", ".bak", ".orig", ".rej", "~")
STRAY_PREFIXES = ("._", ".#", "~$", ".~lock.")


class PackageError(Exception):
    """A failed precondition or package validation."""


def is_stray(name: str, directory: bool = False) -> bool:
    folded = name.casefold()
    if directory:
        return folded in STRAY_DIRS
    return folded in STRAY_NAMES or folded.endswith(STRAY_SUFFIXES) or folded.startswith(STRAY_PREFIXES)


def git_ignored(root: Path) -> set[str]:
    """Untracked files under root that git ignores; empty outside a work tree or without git."""
    try:
        completed = subprocess.run(["git", "-C", str(root), "ls-files", "--others", "--ignored",
                                    "--exclude-standard", "-z", "--", "."],
                                   capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return set()
    if completed.returncode != 0:
        return set()
    return {name for name in completed.stdout.decode("utf-8", errors="replace").split("\0") if name}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def reject_link(path: Path) -> os.stat_result:
    info = path.lstat()
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & reparse:
        raise PackageError(f"Symbolic links and reparse points are forbidden: {path}")
    return info


def source_files(root: Path) -> list[Path]:
    """Walk without following links; every included item must stay inside root."""
    reject_link(root)
    files = []
    stray = []
    pending = [root]
    while pending:
        directory = pending.pop()
        for path in directory.iterdir():
            info = reject_link(path)
            if not path.resolve().is_relative_to(root):
                raise PackageError(f"Path leaves the package: {path}")
            if is_stray(path.name, stat.S_ISDIR(info.st_mode)):
                stray.append(path.relative_to(root).as_posix())
            elif stat.S_ISDIR(info.st_mode):
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                relative = path.relative_to(root).as_posix()
                # A backslash is a filename on POSIX but a separator on Windows.
                if "\\" in relative or any(":" in part for part in path.relative_to(root).parts):
                    raise PackageError(f"Non-portable archive name: {relative}")
                files.append(path)
            else:
                raise PackageError(f"Non-regular file is forbidden: {path}")
    ignored = git_ignored(root)
    stray.extend(path.relative_to(root).as_posix() for path in files
                 if path.relative_to(root).as_posix() in ignored)
    if stray:
        raise PackageError("Stray files are never packaged; delete them and rerun: " + ", ".join(sorted(stray)))
    files.sort(key=lambda item: item.relative_to(root).as_posix())
    names = [path.relative_to(root).as_posix() for path in files]
    if any(name.startswith("assets/books/") for name in names):
        raise PackageError("Book texts are not packaged; move assets/books out of the skill directory")
    if len(names) != len({name.casefold() for name in names}):
        raise PackageError("Case-insensitive archive filename collision")
    if len(files) > MAX_FILES:
        raise PackageError(f"Package has {len(files)} files; maximum is {MAX_FILES}")
    entries = [name for name in names if Path(name).name.casefold() == "skill.md"]
    if entries != ["SKILL.md"]:
        raise PackageError(f"Exactly one root SKILL.md is required; found {entries}")
    return files


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise PackageError(f"Expected a JSON object: {path}")
    return value


def write_object(path: Path, value: dict) -> None:
    """Atomically replace one existing metadata file, leaving no package cache."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=".metadata-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def refresh_inventory(root: Path, inventory: Path, files: list[Path]) -> None:
    value = read_object(inventory)
    previous = {entry["path"]: entry for entry in value.get("files", [])}
    entries = []
    for path in files:
        if path == inventory:
            continue
        relative = path.relative_to(root).as_posix()
        entry = dict(previous.get(relative, {}))
        entry.update(path=relative, bytes=path.stat().st_size, sha256=digest(path))
        entries.append(entry)
    value["files"] = entries
    write_object(inventory, value)


def refresh_metadata(root: Path) -> None:
    read_object(root / "package-manifest.json")
    refresh_inventory(root, root / "package-manifest.json", source_files(root))


def verify_portable(root: Path) -> dict:
    verifier = root / "scripts/verify_portable.py"
    if not verifier.is_file():
        raise PackageError("Missing scripts/verify_portable.py")
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run([sys.executable, "-B", str(verifier), "--root", str(root)],
                               cwd=root, env=environment, capture_output=True,
                               encoding="utf-8", errors="replace", timeout=120, check=False)
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise PackageError(f"Verifier did not return JSON: {completed.stderr[-2000:]}") from exc
    if completed.returncode != 0 or not isinstance(result, dict) or result.get("ok") is not True:
        raise PackageError("Portable verification failed: " + json.dumps(result, ensure_ascii=False))
    return result


def package(root_argument: Path, output_argument: Path, refresh: bool = False) -> dict:
    # Check the named root before resolve() so a root link cannot disappear.
    reject_link(root_argument)
    root = root_argument.resolve(strict=True)
    if not root.is_dir():
        raise PackageError("--root must be a directory")
    output = output_argument.absolute()
    if output.suffix.lower() != ".zip":
        raise PackageError("--output must name a .zip file")
    if output.exists() or output.is_symlink():
        reject_link(output)
    if output.resolve().is_relative_to(root):
        raise PackageError("--output must be outside the skill directory")
    source_files(root)
    if refresh:
        refresh_metadata(root)
    files = source_files(root)
    before = {path.relative_to(root).as_posix(): (path.stat().st_size, digest(path)) for path in files}
    verification = verify_portable(root)
    after_files = source_files(root)
    after = {path.relative_to(root).as_posix(): (path.stat().st_size, digest(path)) for path in after_files}
    if before != after:
        raise PackageError("Source files changed during portable verification")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".viral-screenwriter-",
                                         suffix=".zip", delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9, allowZip64=False) as archive:
            for path in after_files:
                name = path.relative_to(root).as_posix()
                archive.write(path, f"{ZIP_ROOT}/{name}")
        size = temporary.stat().st_size
        if size >= MAX_ZIP_BYTES:
            raise PackageError(f"ZIP is {size} bytes; it must be < {MAX_ZIP_BYTES}")
        with zipfile.ZipFile(temporary, "r") as archive:
            expected_names = [f"{ZIP_ROOT}/{name}" for name in after]
            if archive.namelist() != expected_names or len(set(archive.namelist())) != len(after):
                raise PackageError("ZIP members differ from the validated source file list")
            bad = archive.testzip()
            if bad is not None:
                raise PackageError(f"ZIP CRC check failed: {bad}")
            for name, (expected_size, expected_hash) in after.items():
                member = archive.getinfo(f"{ZIP_ROOT}/{name}")
                with archive.open(member) as handle:
                    actual_hash = hashlib.file_digest(handle, "sha256").hexdigest()
                if member.file_size != expected_size or actual_hash != expected_hash:
                    raise PackageError(f"ZIP content differs from validated source: {name}")
        current_files = source_files(root)
        current = {path.relative_to(root).as_posix(): (path.stat().st_size, digest(path))
                   for path in current_files}
        if current != after:
            raise PackageError("Source files changed during ZIP creation")
        archive_hash = digest(temporary)
        # Only a fully verified archive can replace a previous successful output.
        os.replace(temporary, output)
        return {"ok": True, "output": str(output), "files": len(after), "bytes": size,
                "sha256": archive_hash, "refreshed": refresh, "verification": verification}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def relative_file(root: Path, name: str) -> Path:
    """Resolve only a portable regular file inside this exact edition tree."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise PackageError(f"Invalid edition path: {name!r}")
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise PackageError(f"Edition path is missing or outside root: {name}")
    reject_link(path)
    return path


def release_fields(rules: dict, edition: str) -> dict:
    """Manifest release metadata, derived from the edition rules instead of typed by hand."""
    return {"edition": f"{rules['date']}-{rules['version']}-{edition}",
            "workspace_edition": edition, "release_version": rules["version"],
            "release_date": rules["date"],
            "packaging_revision": f"{rules['date']}-{rules['version']}-dual-editions"}


def release_mismatch(manifest: dict, rules: dict, edition: str) -> dict:
    return {key: [manifest.get(key), expected] for key, expected in release_fields(rules, edition).items()
            if manifest.get(key) != expected}


def stamp_release(root: Path, rules: dict, edition: str) -> None:
    manifest = read_object(root / "package-manifest.json")
    manifest.update(release_fields(rules, edition))
    write_object(root / "package-manifest.json", manifest)


def check_install_version(root: Path, rules: dict, edition: str) -> None:
    """INSTALL.md carries one version line: date, version and edition only."""
    line = f"版本：{rules['date']} {rules['version']} {EDITION_LABELS[edition]}"
    if line not in relative_file(root, "INSTALL.md").read_text(encoding="utf-8-sig").splitlines():
        raise PackageError(f"INSTALL.md must contain the version line exactly: {line}")


def apply_edition(root: Path, edition: str, rules: dict) -> None:
    """Apply an explicit edition delta; changed source anchors fail closed."""
    if edition not in ("local", "feishu") or rules.get("source_edition") != "feishu":
        raise PackageError("Unsupported edition or edition rules")
    if edition == "local":
        for rule in rules["local_replacements"]:
            path = relative_file(root, rule["path"])
            text = path.read_text(encoding="utf-8-sig")
            old, new = rule["old"], rule["new"]
            if not old or text.count(old) != 1:
                raise PackageError(f"Edition source changed; update the matching local delta: {rule['path']}")
            path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
        for name in rules["local_exclude"]:
            # These exact files are removed only from our newly created build tree.
            relative_file(root, name).unlink()
        # Block future cloud integration files or prose from silently leaking into
        # local builds. Historical evidence records are not workflow rules.
        for path in source_files(root):
            name = path.relative_to(root).as_posix()
            if "feishu" in name.casefold():
                raise PackageError(f"Unclassified cloud integration file in local edition: {name}")
            if name == "package-manifest.json" or name.startswith("assets/evidence/"):
                continue
            if path.suffix.casefold() in (".md", ".yaml", ".py", ".json"):
                text = path.read_text(encoding="utf-8-sig")
                if re.search(r"飞书|feishu|lark-cli|OAuth", text, flags=re.IGNORECASE):
                    raise PackageError(f"Unclassified cloud workflow in local edition: {name}")
    stamp_release(root, rules, edition)
    check_install_version(root, rules, edition)


def package_edition(root_argument: Path, output_argument: Path, edition: str,
                    refresh: bool = False) -> dict:
    reject_link(root_argument)
    root = root_argument.resolve(strict=True)
    output = output_argument.absolute()
    if output.resolve().is_relative_to(root):
        raise PackageError("--output must be outside the maintained skill directory")
    source_files(root)
    rules = read_object(EDITION_RULES)
    source_edition = rules.get("source_edition")
    if source_edition != "feishu" or read_object(root / "package-manifest.json").get("workspace_edition") != source_edition:
        raise PackageError("The maintained source must be the Feishu-capable edition")
    if refresh:
        stamp_release(root, rules, source_edition)
        refresh_metadata(root)
    source_verification = verify_portable(root)
    mismatch = release_mismatch(read_object(root / "package-manifest.json"), rules, source_edition)
    if mismatch:
        raise PackageError("Source manifest release fields differ from tools/edition_rules.json; "
                           "rerun with --refresh: " + json.dumps(mismatch, ensure_ascii=False))
    source_snapshot = {p.relative_to(root).as_posix(): digest(p) for p in source_files(root)}
    with tempfile.TemporaryDirectory(prefix="viral-screenwriter-edition-") as temporary:
        temporary_root = Path(temporary).resolve()
        if not temporary_root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise PackageError("Build directory is outside the expected temporary parent")
        stage = temporary_root / ZIP_ROOT
        shutil.copytree(root, stage)
        apply_edition(stage, edition, rules)
        refresh_metadata(stage)
        result = package(stage, output)
        result.update(edition=edition, version=rules["version"], date=rules["date"],
                      refreshed=refresh, source_verification=source_verification)
    if source_snapshot != {p.relative_to(root).as_posix(): digest(p) for p in source_files(root)}:
        raise PackageError("Maintained source changed during edition build")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / ZIP_ROOT)
    parser.add_argument("--output", type=Path, required=True, help="Explicit ZIP destination outside the skill directory")
    parser.add_argument("--refresh", action="store_true", help="Refresh the hash inventory and release fields before packaging")
    parser.add_argument("--edition", choices=("local", "feishu"), default="feishu",
                        help="Release edition; both use the same skill name and method cards")
    args = parser.parse_args()
    try:
        result = package_edition(args.root, args.output, args.edition, args.refresh)
    except (PackageError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
