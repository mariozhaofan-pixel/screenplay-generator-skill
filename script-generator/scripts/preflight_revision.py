#!/usr/bin/env python3
"""Protect a source canon and allocate an unused revision path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION_TOKEN_RE = re.compile(r"(?i)(?<![A-Za-z0-9])V(?P<number>\d+)(?!\d)")


class ConstraintError(Exception):
    """A valid invocation that violates a revision constraint."""


class ParseError(Exception):
    """An input or serialization failure."""


def normalized_path(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def read_utf8_nfc(path: Path) -> bytes:
    try:
        data = path.read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ParseError(f"cannot read UTF-8 source: {exc}") from exc
    if unicodedata.normalize("NFC", text) != text:
        raise ConstraintError("source document is not Unicode NFC")
    return data


def parse_version_parts(path: Path) -> tuple[int | None, dict[str, Any] | None]:
    matches = list(VERSION_TOKEN_RE.finditer(path.stem))
    if not matches:
        return None, None
    match = matches[-1]
    return int(match.group("number")), {
        "prefix": path.stem[: match.start()],
        "tag": path.stem[match.start() : match.start() + 1],
        "width": len(match.group("number")),
        "suffix": path.stem[match.end() :],
    }


def occupied_versions(directory: Path, prefix: str, extension: str) -> set[int]:
    occupied: set[int] = set()
    for path in directory.iterdir():
        if not path.is_file() or path.suffix.casefold() != extension.casefold():
            continue
        version, parts = parse_version_parts(path)
        if version is not None and parts and parts["prefix"].casefold() == prefix.casefold():
            occupied.add(version)
    return occupied


def allocate_output(source: Path, versions_dir: Path | None) -> tuple[Path, int | None]:
    parent_version, parts = parse_version_parts(source)
    target_dir = (versions_dir or source.parent).resolve(strict=False)
    if not target_dir.exists() or not target_dir.is_dir():
        raise ConstraintError(f"versions directory does not exist: {target_dir}")

    if parts:
        occupied = occupied_versions(target_dir, parts["prefix"], source.suffix)
        candidate_version = parent_version + 1 if parent_version is not None else 1
        while candidate_version in occupied:
            candidate_version += 1
        while True:
            candidate_stem = (
                f"{parts['prefix']}{parts['tag']}"
                f"{candidate_version:0{parts['width']}d}{parts['suffix']}"
            )
            candidate = target_dir / f"{candidate_stem}{source.suffix}"
            if not candidate.exists():
                return candidate, candidate_version
            candidate_version += 1

    candidate_version = 2
    while True:
        candidate = target_dir / f"{source.stem}_V{candidate_version}{source.suffix}"
        if not candidate.exists():
            return candidate, candidate_version
        candidate_version += 1


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    path.write_text(unicodedata.normalize("NFC", serialized) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a source canon and choose a non-overwriting revision path."
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--versions-dir", type=Path)
    parser.add_argument("--locked-invariant", action="append", default=[])
    parser.add_argument("--explicit-delete", action="append", default=[])
    parser.add_argument("--explicit-add", action="append", default=[])
    parser.add_argument("--json-out", type=Path)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    source = args.source.resolve(strict=False)
    if not source.exists() or not source.is_file():
        raise ConstraintError(f"source document does not exist: {source}")

    source_bytes = read_utf8_nfc(source)
    parent_version, _ = parse_version_parts(source)
    output_lane_occupied = False

    if args.output:
        output = args.output.resolve(strict=False)
        output_version, output_parts = parse_version_parts(output)
        output_lane_occupied = bool(
            output_version is not None
            and output_parts
            and output.parent.exists()
            and output_version
            in occupied_versions(output.parent, output_parts["prefix"], output.suffix)
        )
    else:
        output, output_version = allocate_output(source, args.versions_dir)

    if normalized_path(source) == normalized_path(output):
        raise ConstraintError("source and output resolve to the same path")
    if output.exists():
        raise ConstraintError(f"output path is already occupied: {output}")
    if output_lane_occupied:
        raise ConstraintError(f"output version lane V{output_version} is already occupied")
    if not output.parent.exists() or not output.parent.is_dir():
        raise ConstraintError(f"output directory does not exist: {output.parent}")
    if (
        parent_version is not None
        and output_version is not None
        and output_version <= parent_version
    ):
        raise ConstraintError(
            f"output version V{output_version} must be higher than parent V{parent_version}"
        )

    return {
        "explicit_add": [unicodedata.normalize("NFC", item) for item in args.explicit_add],
        "explicit_delete": [
            unicodedata.normalize("NFC", item) for item in args.explicit_delete
        ],
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "locked_invariants": [
            unicodedata.normalize("NFC", item) for item in args.locked_invariant
        ],
        "output_candidate": str(output),
        "output_version": output_version,
        "parent_version": parent_version,
        "source_canon_path": str(source),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "status": "pass",
    }


def main() -> int:
    parser = build_parser()
    try:
        args = parser.parse_args()
        result = run(args)
        if args.json_out:
            write_json(args.json_out.resolve(strict=False), result)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except ConstraintError as exc:
        payload = {"error": str(exc), "status": "constraint_failed"}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    except (ParseError, OSError, ValueError, TypeError) as exc:
        payload = {"error": str(exc), "status": "parse_failed"}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
