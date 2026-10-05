#!/usr/bin/env python3
"""Verify this package's file hashes and local Markdown reference closure.

Uses Python's standard library, resolves all paths from the supplied package
root, and never searches the author's computer for a missing dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def markdown_targets(text: str):
    text = re.sub(r'```.*?```|~~~.*?~~~', '', text, flags=re.S)
    for match in re.finditer(r'\]\(', text):
        start = match.end()
        depth, cursor, escaped = 1, start, False
        while cursor < len(text) and depth:
            char = text[cursor]
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            cursor += 1
        if depth == 0:
            value = text[start:cursor - 1].strip()
            if value.startswith('<') and '>' in value:
                value = value[1:value.index('>')]
            else:
                value = re.sub(r'''\s+["'][^\n]*["']$''', '', value)
            yield value


def verify(root: Path) -> dict:
    errors = []
    skill_entrypoints = sorted(path.relative_to(root).as_posix()
                               for path in root.rglob('*')
                               if path.is_file() and path.name.casefold() == 'skill.md')
    if skill_entrypoints != ['SKILL.md']:
        errors.append({'kind': 'skill_entrypoint_layout',
                       'expected': ['SKILL.md'], 'found': skill_entrypoints})
    manifest_path = root / 'package-manifest.json'
    if not manifest_path.is_file():
        return {'ok': False, 'skill_entrypoints': skill_entrypoints,
                'errors': errors + [{'kind': 'missing_manifest'}]}
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    entries = manifest['files']
    known = set()
    for entry in entries:
        relative = entry['path']
        known.add(relative)
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            errors.append({'kind': 'outside_package', 'path': relative})
        elif not path.is_file():
            errors.append({'kind': 'missing_file', 'path': relative})
        elif path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            errors.append({'kind': 'content_mismatch', 'path': relative})

    actual = {path.relative_to(root).as_posix() for path in root.rglob('*')
              if path.is_file() and path != manifest_path}
    for relative in sorted(actual - known):
        errors.append({'kind': 'unlisted_file', 'path': relative})

    checked_links = 0
    machine_path = re.compile(r'(?<![A-Za-z0-9])(?:[A-Za-z]:[/\\]|file://)', re.I)
    for relative in sorted(known):
        path = root / relative
        if not path.is_file() or path.suffix.lower() not in {'.md', '.json', '.yaml', '.yml', '.py', '.ps1', '.txt', '.csv', '.jsonl'}:
            continue
        text = path.read_text(encoding='utf-8-sig', errors='replace')
        # The validator's own detection regex is not a runtime dependency.
        if path.name != 'verify_portable.py' and machine_path.search(text):
            errors.append({'kind': 'machine_absolute_path', 'path': relative})
        if path.suffix.lower() != '.md':
            continue
        for target in markdown_targets(text):
            if not target or target.startswith('#'):
                continue
            if urlsplit(target).scheme in {'http', 'https', 'mailto', 'data', 'tel'}:
                continue
            target_path = unquote(target.split('#', 1)[0].split('?', 1)[0])
            if not target_path:
                continue
            if machine_path.search(target_path) or target_path.startswith(('/', '~', '\\')):
                errors.append({'kind': 'absolute_link', 'path': relative, 'target': target})
                continue
            resolved = (path.parent / target_path).resolve()
            checked_links += 1
            if not resolved.is_relative_to(root):
                errors.append({'kind': 'link_leaves_package', 'path': relative, 'target': target})
            elif not resolved.exists():
                errors.append({'kind': 'missing_link', 'path': relative, 'target': target})
    return {'ok': not errors, 'files_checked': len(entries),
            'skill_entrypoints': skill_entrypoints,
            'local_markdown_links_checked': checked_links, 'errors': errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report', type=Path, help='Optional report outside the read-only package')
    args = parser.parse_args()
    root = args.root.resolve()
    result = verify(root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + '\n', encoding='utf-8')
    print(rendered)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
