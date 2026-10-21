#!/usr/bin/env python3
"""Maintain and package the compact viral-screenwriter skill using the stdlib.

Usage: python tools/package_viral_screenwriter.py --output release.zip [--refresh]
Without --refresh the source tree is read-only. Refresh updates EPUB section
locations and both hash inventories; it never rewrites a book's full.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import zipfile


MAX_FILES = 200
MAX_ZIP_BYTES = 5_000_000  # The archive must be strictly smaller.
ZIP_ROOT = "viral-screenwriter"
EPUB_BOOKS = ("B01", "B02", "B04", "B05", "B06", "B07", "B09", "B10", "B11")
HEADING = re.compile(r"^## 正文文件 ([1-9][0-9]*) · .+$")
HEADING_REFERENCE = re.compile(r"^## 正文文件 ([1-9][0-9]*)(?: · .+)?$")


class PackageError(Exception):
    """A failed precondition or package validation."""


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
    pending = [root]
    while pending:
        directory = pending.pop()
        for path in directory.iterdir():
            info = reject_link(path)
            if not path.resolve().is_relative_to(root):
                raise PackageError(f"Path leaves the package: {path}")
            if stat.S_ISDIR(info.st_mode):
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                relative = path.relative_to(root).as_posix()
                # A backslash is a filename on POSIX but a separator on Windows.
                if "\\" in relative or any(":" in part for part in path.relative_to(root).parts):
                    raise PackageError(f"Non-portable archive name: {relative}")
                files.append(path)
            else:
                raise PackageError(f"Non-regular file is forbidden: {path}")
    files.sort(key=lambda item: item.relative_to(root).as_posix())
    names = [path.relative_to(root).as_posix() for path in files]
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


def refreshed_epub_index(directory: Path) -> dict:
    value = read_object(directory / "index.json")
    lines = (directory / "full.md").read_text(encoding="utf-8-sig").splitlines()
    headings = [(line_no, line, int(match[1]))
                for line_no, line in enumerate(lines, 1)
                if (match := HEADING.fullmatch(line))]
    numbers = [entry[2] for entry in headings]
    if not numbers or numbers != list(range(1, len(numbers) + 1)):
        raise PackageError(f"Missing, duplicate or unordered EPUB headings: {directory.name}")
    locations = {}
    for index, (start, heading, number) in enumerate(headings):
        end = headings[index + 1][0] - 1 if index + 1 < len(headings) else len(lines)
        locations[number] = (heading, start, end)
    indexed_numbers = []
    for field in ("sections", "toc"):
        entries = value.get(field)
        if not isinstance(entries, list):
            raise PackageError(f"Missing {field} array: {directory.name}")
        for entry in entries:
            if not isinstance(entry, dict):
                raise PackageError(f"Invalid {field} entry: {directory.name}")
            reference = entry.get("full_md_heading", "")
            match = HEADING_REFERENCE.fullmatch(reference) if isinstance(reference, str) else None
            if not match or int(match[1]) not in locations:
                raise PackageError(f"Unresolvable full_md_heading in {directory.name}/{field}: {reference!r}")
            number = int(match[1])
            if field == "sections":
                if entry.get("number") != number:
                    raise PackageError(f"Section number disagrees with heading in {directory.name}: {number}")
                indexed_numbers.append(number)
            heading, start, end = locations[number]
            entry.update(full_md_heading=heading, full_md_start_line=start, full_md_end_line=end)
    if indexed_numbers != numbers:
        raise PackageError(f"Section index does not cover every real heading: {directory.name}")
    return value


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
    files = source_files(root)
    full_hashes = {path: digest(path) for path in files
                   if path.name == "full.md" and path.is_relative_to(root / "assets/books")}
    # Resolve every section before modifying any metadata. PDF indexes are untouched.
    replacements = [(root / "assets/books/library" / book / "index.json",
                     refreshed_epub_index(root / "assets/books/library" / book))
                    for book in EPUB_BOOKS]
    books = root / "assets/books"
    read_object(books / "inventory.json")
    read_object(root / "package-manifest.json")
    for path, value in replacements:
        write_object(path, value)
    files = source_files(root)
    refresh_inventory(books, books / "inventory.json",
                      [path for path in files if path.is_relative_to(books)])
    refresh_inventory(root, root / "package-manifest.json", source_files(root))
    if any(digest(path) != expected for path, expected in full_hashes.items()):
        raise PackageError("A book full.md changed during metadata refresh")


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / ZIP_ROOT)
    parser.add_argument("--output", type=Path, required=True, help="Explicit ZIP destination outside the skill directory")
    parser.add_argument("--refresh", action="store_true", help="Refresh EPUB locations and hash inventories before packaging")
    args = parser.parse_args()
    try:
        result = package(args.root, args.output, args.refresh)
    except (PackageError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
