#!/usr/bin/env python3
"""Transcribe an audio file with faster-whisper and retain confidence evidence.

The generated transcript is machine evidence for a reverse-storyboard workflow.
It is deliberately labelled provisional and must not be treated as a verified
quotation without listening to the source audio.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import statistics
import sys
from typing import Any, Iterable


PROVISIONAL_STATUS = "ASR provisional"
PROVISIONAL_NOTICE = (
    "ASR PROVISIONAL：机器转写仅用于定位与初筛；人名、专有名词、同音词、"
    "说话人归属和逐字台词必须回听源音频核验。"
)


def configure_console_utf8() -> None:
    """Keep Chinese diagnostics readable in redirected Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (LookupError, OSError):
                pass


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是正整数") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须大于 0")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "使用 faster-whisper 转写音频，输出带分段与词级时间戳/置信度的 "
            "transcript_raw.json 和 transcript_timed.txt。"
        )
    )
    parser.add_argument("audio", type=Path, help="输入音频或含音轨的媒体文件")
    parser.add_argument("output", type=Path, help="输出目录")
    parser.add_argument(
        "--model",
        default="small",
        help="faster-whisper 模型名或本地模型目录（默认：small）",
    )
    parser.add_argument(
        "--language",
        default="auto",
        help="语言代码，如 zh、en；auto 时不向模型传 language 参数（默认：auto）",
    )
    parser.add_argument(
        "--initial-prompt",
        default=None,
        help="可选初始提示；脚本不会注入任何片名、人物名或源片词汇",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="CTranslate2 设备，如 auto、cpu、cuda（默认：auto）",
    )
    parser.add_argument(
        "--compute-type",
        default="default",
        help="计算类型，如 default、float16、int8、int8_float16（默认：default）",
    )
    parser.add_argument(
        "--no-vad",
        action="store_true",
        help="关闭默认语音活动检测；仅在 VAD 明显漏掉低电平对白时使用",
    )
    parser.add_argument(
        "--min-silence-ms",
        type=positive_int,
        default=250,
        help="VAD 判定分段的最短静音时长，毫秒（默认：250）",
    )
    return parser


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_timestamp(seconds: float | None) -> str:
    total_ms = max(0, round((seconds or 0.0) * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def _mean(values: Iterable[float]) -> float | None:
    materialized = list(values)
    return statistics.fmean(materialized) if materialized else None


def _segment_record(segment: Any) -> dict[str, Any]:
    words: list[dict[str, Any]] = []
    probabilities: list[float] = []

    for word in getattr(segment, "words", None) or []:
        probability = _as_float(getattr(word, "probability", None))
        if probability is not None:
            probabilities.append(probability)
        words.append(
            {
                "start": _as_float(getattr(word, "start", None)),
                "end": _as_float(getattr(word, "end", None)),
                "word": str(getattr(word, "word", "")),
                "probability": probability,
            }
        )

    raw_tokens = getattr(segment, "tokens", None)
    tokens = [_as_int(token) for token in raw_tokens] if raw_tokens is not None else []
    return {
        "id": _as_int(getattr(segment, "id", None)),
        "seek": _as_int(getattr(segment, "seek", None)),
        "start": _as_float(getattr(segment, "start", None)),
        "end": _as_float(getattr(segment, "end", None)),
        "text": str(getattr(segment, "text", "")),
        "tokens": tokens,
        "temperature": _as_float(getattr(segment, "temperature", None)),
        "avg_logprob": _as_float(getattr(segment, "avg_logprob", None)),
        "compression_ratio": _as_float(
            getattr(segment, "compression_ratio", None)
        ),
        "no_speech_prob": _as_float(getattr(segment, "no_speech_prob", None)),
        "mean_word_probability": _mean(probabilities),
        "words": words,
    }


def _language_probabilities(info: Any) -> list[dict[str, Any]] | None:
    probabilities = getattr(info, "all_language_probs", None)
    if probabilities is None:
        return None
    return [
        {"language": str(language), "probability": _as_float(probability)}
        for language, probability in probabilities
    ]


def _package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _timed_text(payload: dict[str, Any]) -> str:
    lines = [
        f"# {PROVISIONAL_NOTICE}",
        f"# detected_language={payload['language']['detected'] or 'unknown'} "
        f"probability={payload['language']['probability']}",
        "",
    ]
    for segment in payload["segments"]:
        confidence = segment["mean_word_probability"]
        confidence_text = "n/a" if confidence is None else f"{confidence:.4f}"
        lines.append(
            f"[{_format_timestamp(segment['start'])} --> "
            f"{_format_timestamp(segment['end'])}] "
            f"segment={segment['id']} mean_word_probability={confidence_text}"
        )
        lines.append(segment["text"].strip())
        if segment["words"]:
            rendered_words = []
            for word in segment["words"]:
                probability = word["probability"]
                probability_text = "n/a" if probability is None else f"{probability:.4f}"
                rendered_words.append(
                    f"[{_format_timestamp(word['start'])}-"
                    f"{_format_timestamp(word['end'])}]"
                    f"{word['word']!r}(p={probability_text})"
                )
            lines.append("WORDS " + " ".join(rendered_words))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run(args: argparse.Namespace) -> tuple[Path, Path, int]:
    audio = args.audio.expanduser().resolve()
    if not audio.is_file():
        raise FileNotFoundError(f"输入音频不存在或不是文件：{audio}")

    # Optional dependency is intentionally imported only after CLI parsing so
    # that `--help` remains usable in a lightweight environment.
    try:
        from faster_whisper import WhisperModel
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            "缺少可选依赖 faster-whisper；请先安装 `pip install faster-whisper`。"
        ) from exc

    output_dir = args.output.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    model = WhisperModel(
        args.model,
        device=args.device,
        compute_type=args.compute_type,
    )
    transcribe_options: dict[str, Any] = {
        "word_timestamps": True,
        "vad_filter": not args.no_vad,
    }
    if not args.no_vad:
        transcribe_options["vad_parameters"] = {
            "min_silence_duration_ms": args.min_silence_ms
        }
    requested_language = args.language.strip() if args.language else "auto"
    if requested_language.casefold() != "auto":
        transcribe_options["language"] = requested_language
    if args.initial_prompt is not None:
        transcribe_options["initial_prompt"] = args.initial_prompt

    segment_iterator, info = model.transcribe(str(audio), **transcribe_options)
    # faster-whisper returns a generator; consuming it is what performs the
    # transcription and guarantees complete output before files are written.
    segment_records = [_segment_record(segment) for segment in segment_iterator]

    payload: dict[str, Any] = {
        "status": PROVISIONAL_STATUS,
        "provisional": True,
        "notice": PROVISIONAL_NOTICE,
        "source_audio": str(audio),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": {
            "name": "faster-whisper",
            "version": _package_version("faster-whisper"),
            "model": args.model,
            "device": args.device,
            "compute_type": args.compute_type,
        },
        "language": {
            "requested": requested_language,
            "passed_to_model": transcribe_options.get("language"),
            "detected": getattr(info, "language", None),
            "probability": _as_float(getattr(info, "language_probability", None)),
            "all_probabilities": _language_probabilities(info),
        },
        "initial_prompt": args.initial_prompt,
        "word_timestamps": True,
        "vad": {
            "enabled": not args.no_vad,
            "min_silence_duration_ms": None if args.no_vad else args.min_silence_ms,
        },
        "duration": _as_float(getattr(info, "duration", None)),
        "duration_after_vad": _as_float(getattr(info, "duration_after_vad", None)),
        "segment_count": len(segment_records),
        "segments": segment_records,
    }

    json_path = output_dir / "transcript_raw.json"
    text_path = output_dir / "transcript_timed.txt"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    text_path.write_text(_timed_text(payload), encoding="utf-8")
    return json_path, text_path, len(segment_records)


def main(argv: list[str] | None = None) -> int:
    configure_console_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        json_path, text_path, segment_count = run(args)
    except Exception as exc:  # CLI boundary: concise error without hiding --help.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"{PROVISIONAL_STATUS}: wrote {segment_count} segments to "
        f"{json_path} and {text_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
