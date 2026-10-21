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


def verify_book_locators(root: Path) -> dict:
    """Check exact EPUB boundaries, not just whether full.md exists."""
    def source_key(href: str) -> str:
        path = unquote(href.split('#', 1)[0])
        return path.removeprefix('OEBPS/')

    errors, books, records, sections = [], 0, 0, 0
    for index_path in sorted((root / 'assets/books/library').glob('B*/index.json')):
        data = json.loads(index_path.read_text(encoding='utf-8-sig'))
        if 'page_records' in data:
            continue  # PDF sources use their existing page_records, not EPUB fields.
        relative = index_path.relative_to(root).as_posix()
        if not data.get('sections') or not isinstance(data.get('toc'), list):
            errors.append({'kind': 'book_missing_section_index', 'path': relative})
            continue
        full_path = (index_path.parent / data.get('full_markdown', 'full.md')).resolve()
        if not full_path.is_relative_to(root) or not full_path.is_file():
            errors.append({'kind': 'book_full_path', 'path': relative})
            continue
        # Match editor/CLI LF line numbers; U+0085/U+2028 are not file newlines.
        lines = full_path.read_text(encoding='utf-8-sig').split('\n')
        if lines[-1] == '':
            lines.pop()
        headings = [(i + 1, int(match[1]), line) for i, line in enumerate(lines)
                    if (match := re.match(r'^## 正文文件 (\d+) · ', line))]
        positions = {number: (line, headings[i + 1][0] - 1 if i + 1 < len(headings) else len(lines), heading)
                     for i, (line, number, heading) in enumerate(headings)}
        source_numbers = {source_key(heading.split(' · ', 1)[1]): number
                          for _, number, heading in headings}
        if not headings or len(positions) != len(headings):
            errors.append({'kind': 'book_section_headings', 'path': relative})
        if len(source_numbers) != len(headings):
            errors.append({'kind': 'book_source_ambiguity', 'path': relative})
        numbers = [record.get('number') for record in data['sections']]
        if len(numbers) != len(set(numbers)) or set(numbers) != set(positions):
            errors.append({'kind': 'book_section_coverage', 'path': relative})
        for group in ('sections', 'toc'):
            for record in data.get(group, []):
                records += 1
                match = re.match(r'^## 正文文件 (\d+) · ', record.get('full_md_heading', ''))
                number = int(match[1]) if match else None
                actual = (record.get('full_md_start_line'), record.get('full_md_end_line'), record.get('full_md_heading'))
                expected = positions.get(number)
                if expected is None or actual != expected or (group == 'sections' and record.get('number') != number):
                    errors.append({'kind': 'book_section_locator', 'path': relative, 'group': group,
                                   'title': record.get('title'), 'number': record.get('number')})
                if source_numbers.get(source_key(record.get('epub_href', ''))) != number:
                    errors.append({'kind': 'book_source_locator', 'path': relative, 'group': group,
                                   'title': record.get('title'), 'number': record.get('number')})
                for key in ('file', 'href'):
                    if key in record and record[key] != 'full.md':
                        errors.append({'kind': 'book_section_target', 'path': relative, 'field': key})
        books += 1
        sections += len(positions)
    return {'epub_books': books, 'logical_sections': sections,
            'locator_records_checked': records, 'errors': errors}


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
    book_locators = verify_book_locators(root)
    errors.extend(book_locators.pop('errors'))
    return {'ok': not errors, 'files_checked': len(entries),
            'skill_entrypoints': skill_entrypoints,
            'local_markdown_links_checked': checked_links,
            'book_locators': book_locators, 'errors': errors}


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
