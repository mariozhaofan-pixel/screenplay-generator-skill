#!/usr/bin/env python3
"""Regression check for LF line numbers in book indexes (standard library)."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill-root', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'viral-screenwriter')
    args = parser.parse_args()
    builder = load('builder', Path(__file__).with_name('package_viral_screenwriter.py'))
    verifier = load('verifier', args.skill_root / 'scripts/verify_portable.py')
    cases = []
    with tempfile.TemporaryDirectory(prefix='screenwriter-lines-') as temp:
        # Only this newly created directory under the explicit temp root is removed.
        root = Path(temp).resolve()
        assert root.is_relative_to(Path(tempfile.gettempdir()).resolve())
        directory = root / 'assets/books/library/B11'
        directory.mkdir(parents=True)
        records = [dict(number=n, epub_href=f'OEBPS/{n}.html', file='full.md', href='full.md',
                        full_md_heading=f'## 正文文件 {n} · OEBPS/{n}.html') for n in (1, 2)]
        for label, newline, final_newline in [('lf', '\n', True), ('crlf', '\r\n', True), ('no_final_lf', '\n', False)]:
            text = ('## 正文文件 1 · OEBPS/1.html\n\n'
                    '正文\u0085同一行\u2028仍同一行\u2029末尾\n'
                    '## 正文文件 2 · OEBPS/2.html\n下一节')
            if final_newline:
                text += '\n'
            (directory / 'full.md').write_bytes(text.replace('\n', newline).encode('utf-8'))
            index = {'full_markdown': 'full.md', 'sections': records,
                     'toc': [dict(item) for item in records]}
            path = directory / 'index.json'
            path.write_text(json.dumps(index, ensure_ascii=False), encoding='utf-8')
            rebuilt = builder.refreshed_epub_index(directory)
            assert [(r['full_md_start_line'], r['full_md_end_line']) for r in rebuilt['sections']] == [(1, 3), (4, 5)]
            path.write_text(json.dumps(rebuilt, ensure_ascii=False), encoding='utf-8')
            assert verifier.verify_book_locators(root)['errors'] == []
            rebuilt['sections'][1]['full_md_start_line'] = 7  # Old splitlines() result.
            path.write_text(json.dumps(rebuilt, ensure_ascii=False), encoding='utf-8')
            assert any(e['kind'] == 'book_section_locator' for e in verifier.verify_book_locators(root)['errors'])
            cases.append({'case': label, 'actual_line_ranges': [[1, 3], [4, 5]], 'stale_range_rejected': True})
    print(json.dumps({'ok': True, 'cases': cases}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
