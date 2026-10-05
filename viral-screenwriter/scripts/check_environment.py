#!/usr/bin/env python3
"""Report target-computer media tools without installation or network access."""
from __future__ import annotations
import argparse
import importlib.util
import json
import shutil
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['writing', 'video', 'ocr', 'asr', 'all'], default='writing')
    args = parser.parse_args()
    requirements = {
        'writing': ([], []),
        'video': (['numpy', 'PIL'], ['ffmpeg', 'ffprobe']),
        'ocr': (['cv2'], ['ffprobe']),
        'asr': (['faster_whisper'], []),
    }
    modes = list(requirements) if args.mode == 'all' else [args.mode]
    report = {}
    for mode in modes:
        modules, executables = requirements[mode]
        items = {name: importlib.util.find_spec(name) is not None for name in modules}
        items.update({name: shutil.which(name) is not None for name in executables})
        if mode == 'ocr':
            items['rapidocr_or_rapidocr_onnxruntime'] = any(
                importlib.util.find_spec(name) is not None for name in ['rapidocr', 'rapidocr_onnxruntime'])
        report[mode] = {'dependencies': items, 'ready': all(items.values())}
    result = {
        'python_version': sys.version.split()[0],
        'python_compatible': sys.version_info >= (3, 10),
        'modes': report,
        'note': 'Media package presence does not verify model weights, playback, vision/hearing access, or successful semantic review. Writing from bundled Markdown needs no external media packages.'
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['python_compatible'] and all(item['ready'] for item in report.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
