#!/usr/bin/env python3
"""OCR every decoded video frame and retain a complete provisional frame ledger."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from difflib import SequenceMatcher
import importlib.metadata
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys
from typing import Any


PROVISIONAL_STATUS = "OCR provisional"
PROVISIONAL_NOTICE = (
    "OCR PROVISIONAL：机器字幕观察仅用于定位与交叉核验；漏字、错字、断句、"
    "说话人归属及画面内非字幕文字必须回看证据帧和源视频确认。"
)
CLUSTER_SIMILARITY_THRESHOLD = 0.88


def configure_console_utf8() -> None:
    """Keep Chinese diagnostics readable in redirected Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (LookupError, OSError):
                pass


def _ratio(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是 0..1 之间的小数") from exc
    if not 0.0 <= parsed <= 1.0:
        raise argparse.ArgumentTypeError("必须位于 0..1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "用 RapidOCR 对视频每一帧执行 OCR（不抽帧、不跳过重复画面），"
            "输出 ocr_frames.jsonl 全帧记录、字幕聚合表和 ocr_manifest.json。"
        )
    )
    parser.add_argument("video", type=Path, help="输入视频")
    parser.add_argument("output", type=Path, help="输出目录")
    parser.add_argument(
        "--ffprobe",
        default="ffprobe",
        help="FFprobe 可执行文件；用于核对全部视频帧及实际 PTS（默认：ffprobe）",
    )
    parser.add_argument(
        "--crop-top",
        type=_ratio,
        default=0.0,
        help="裁剪上边界占画面高度比例（默认：0）",
    )
    parser.add_argument(
        "--crop-bottom",
        type=_ratio,
        default=1.0,
        help="裁剪下边界占画面高度比例（默认：1）",
    )
    parser.add_argument(
        "--crop-left",
        type=_ratio,
        default=0.0,
        help="裁剪左边界占画面宽度比例（默认：0）",
    )
    parser.add_argument(
        "--crop-right",
        type=_ratio,
        default=1.0,
        help="裁剪右边界占画面宽度比例（默认：1）",
    )
    parser.add_argument(
        "--language-hint",
        default=None,
        help="仅写入 manifest 的人工语言提示；不会传给 RapidOCR",
    )
    return parser


def _package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _load_optional_dependencies() -> tuple[Any, Any, str, str | None]:
    try:
        import cv2
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            "缺少可选依赖 OpenCV；请先安装 `pip install opencv-python`。"
        ) from exc

    import_errors: list[str] = []
    try:
        from rapidocr import RapidOCR

        return cv2, RapidOCR(), "rapidocr", _package_version("rapidocr")
    except (ImportError, ModuleNotFoundError) as exc:
        import_errors.append(f"rapidocr: {exc}")

    try:
        from rapidocr_onnxruntime import RapidOCR

        return (
            cv2,
            RapidOCR(),
            "rapidocr-onnxruntime",
            _package_version("rapidocr-onnxruntime"),
        )
    except (ImportError, ModuleNotFoundError) as exc:
        import_errors.append(f"rapidocr-onnxruntime: {exc}")

    detail = "; ".join(import_errors)
    raise RuntimeError(
        "缺少 RapidOCR 可选依赖；请安装 `pip install rapidocr` 或 "
        f"`pip install rapidocr-onnxruntime`。检测详情：{detail}"
    )


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "tolist"):
        return _json_value(value.tolist())
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _line_sort_key(line: dict[str, Any]) -> tuple[float, float]:
    box = line.get("box")
    if not isinstance(box, list) or not box:
        return (float("inf"), float("inf"))
    points = [point for point in box if isinstance(point, list) and len(point) >= 2]
    if not points:
        return (float("inf"), float("inf"))
    return (
        min(float(point[1]) for point in points),
        min(float(point[0]) for point in points),
    )


def _normalise_ocr_output(raw_result: Any) -> list[dict[str, Any]]:
    """Normalize current RapidOCR objects and legacy tuple/list results."""
    result = raw_result
    if isinstance(result, tuple) and len(result) == 2:
        # rapidocr-onnxruntime returns (detections, elapsed); current RapidOCR
        # may also be wrapped by callers, so inspect the first value below.
        result = result[0]

    lines: list[dict[str, Any]] = []
    if result is None:
        return lines

    texts = getattr(result, "txts", None)
    scores = getattr(result, "scores", None)
    boxes = getattr(result, "boxes", None)
    if texts is None and isinstance(result, dict):
        texts = result.get("txts") or result.get("texts")
        scores = result.get("scores")
        boxes = result.get("boxes")

    if texts is not None:
        text_items = list(texts)
        score_items = list(scores) if scores is not None else [None] * len(text_items)
        box_items = list(boxes) if boxes is not None else [None] * len(text_items)
        for index, text in enumerate(text_items):
            cleaned = str(text).strip()
            if not cleaned:
                continue
            lines.append(
                {
                    "text": cleaned,
                    "confidence": _float_or_none(
                        score_items[index] if index < len(score_items) else None
                    ),
                    "box": _json_value(
                        box_items[index] if index < len(box_items) else None
                    ),
                }
            )
    elif isinstance(result, (list, tuple)):
        for item in result:
            if not isinstance(item, (list, tuple)):
                continue
            if len(item) >= 3:
                box, text, score = item[0], item[1], item[2]
            elif len(item) == 2 and isinstance(item[0], str):
                box, text, score = None, item[0], item[1]
            else:
                continue
            cleaned = str(text).strip()
            if not cleaned:
                continue
            lines.append(
                {
                    "text": cleaned,
                    "confidence": _float_or_none(score),
                    "box": _json_value(box),
                }
            )

    lines.sort(key=_line_sort_key)
    return lines


def _normalise_text(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.casefold(), flags=re.UNICODE)


def _same_subtitle(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    shorter, longer = sorted((left, right), key=len)
    containment = shorter in longer and len(shorter) / max(len(longer), 1) >= 0.8
    return containment or SequenceMatcher(None, left, right).ratio() >= CLUSTER_SIMILARITY_THRESHOLD


def _mean_confidence(lines: list[dict[str, Any]]) -> float | None:
    values = [line["confidence"] for line in lines if line["confidence"] is not None]
    return statistics.fmean(values) if values else None


def _new_cluster(observation: dict[str, Any], frame: Any) -> dict[str, Any]:
    confidence = observation["confidence"]
    return {
        "first_time": observation["timestamp"],
        "last_time": observation["timestamp"],
        "first_frame_index": observation["frame_index"],
        "last_frame_index": observation["frame_index"],
        "frame_count": 1,
        "confidences": [] if confidence is None else [confidence],
        "variants": {observation["text"]: 1},
        "normalised_text": observation["normalised_text"],
        "best": observation,
        "best_frame": frame.copy(),
    }


def _add_to_cluster(
    cluster: dict[str, Any], observation: dict[str, Any], frame: Any
) -> None:
    cluster["last_time"] = observation["timestamp"]
    cluster["last_frame_index"] = observation["frame_index"]
    cluster["frame_count"] += 1
    cluster["variants"][observation["text"]] = (
        cluster["variants"].get(observation["text"], 0) + 1
    )
    if observation["confidence"] is not None:
        cluster["confidences"].append(observation["confidence"])

    best_confidence = cluster["best"]["confidence"]
    candidate_confidence = observation["confidence"]
    best_key = (
        -1.0 if best_confidence is None else best_confidence,
        len(cluster["best"]["normalised_text"]),
    )
    candidate_key = (
        -1.0 if candidate_confidence is None else candidate_confidence,
        len(observation["normalised_text"]),
    )
    if candidate_key > best_key:
        cluster["best"] = observation
        cluster["best_frame"] = frame.copy()
        cluster["normalised_text"] = observation["normalised_text"]


def _save_cluster(
    cluster: dict[str, Any],
    output: list[dict[str, Any]],
    observations_dir: Path,
    cv2: Any,
    end_time: float,
) -> None:
    observation_id = f"O{len(output) + 1:04d}"
    representative = cluster["best"]
    timestamp_ms = round(representative["timestamp"] * 1000)
    filename = f"{observation_id}_{timestamp_ms:012d}.jpg"
    evidence_path = observations_dir / filename
    ok, encoded = cv2.imencode(".jpg", cluster["best_frame"])
    if not ok:
        raise RuntimeError(f"证据帧 JPEG 编码失败：{evidence_path}")
    evidence_path.write_bytes(encoded.tobytes())

    confidences = cluster["confidences"]
    variants = [
        {"text": text, "frame_count": count}
        for text, count in sorted(
            cluster["variants"].items(), key=lambda item: (-item[1], item[0])
        )
    ]
    output.append(
        {
            "observation_id": observation_id,
            "status": PROVISIONAL_STATUS,
            "start": cluster["first_time"],
            "end": end_time,
            "duration": max(0.0, end_time - cluster["first_time"]),
            "first_frame_index": cluster["first_frame_index"],
            "last_frame_index": cluster["last_frame_index"],
            "representative_timestamp": representative["timestamp"],
            "representative_frame_index": representative["frame_index"],
            "text": representative["text"],
            "confidence": representative["confidence"],
            "mean_frame_confidence": (
                statistics.fmean(confidences) if confidences else None
            ),
            "min_frame_confidence": min(confidences) if confidences else None,
            "max_frame_confidence": max(confidences) if confidences else None,
            "frame_count": cluster["frame_count"],
            "variants": variants,
            "lines": representative["lines"],
            "evidence_frame": f"subtitle_evidence/{filename}",
        }
    )


def _write_csv(path: Path, observations: list[dict[str, Any]]) -> None:
    fieldnames = [
        "observation_id",
        "status",
        "start",
        "end",
        "duration",
        "first_frame_index",
        "last_frame_index",
        "representative_timestamp",
        "representative_frame_index",
        "text",
        "confidence",
        "mean_frame_confidence",
        "min_frame_confidence",
        "max_frame_confidence",
        "frame_count",
        "variant_count",
        "evidence_frame",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for observation in observations:
            row = {key: observation.get(key) for key in fieldnames}
            row["variant_count"] = len(observation["variants"])
            writer.writerow(row)


def _probe_frame_timeline(video: Path, executable: str) -> list[dict[str, float]]:
    """Decode the selected stream with FFprobe and retain every presentation time."""
    result = subprocess.run(
        [
            executable, "-v", "error", "-select_streams", "v:0", "-show_frames",
            "-show_entries", "frame=best_effort_timestamp_time,pkt_duration_time",
            "-of", "json", str(video),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode or result.stderr.strip():
        raise RuntimeError(
            "FFprobe 全帧核验失败，不能声明覆盖完整："
            + (result.stderr.strip() or f"exit {result.returncode}")
        )
    frames = json.loads(result.stdout).get("frames", [])
    if not frames:
        raise RuntimeError("FFprobe 没有返回可核验的视频帧")
    timeline: list[dict[str, float]] = []
    for index, frame in enumerate(frames):
        pts = _float_or_none(frame.get("best_effort_timestamp_time"))
        if pts is None or not math.isfinite(pts):
            raise RuntimeError(f"第 {index} 帧缺少有效 PTS，无法建立连续映射")
        if timeline and pts <= timeline[-1]["pts_seconds"]:
            raise RuntimeError(f"第 {index} 帧 PTS 不递增，须先核验时间轴")
        duration = _float_or_none(frame.get("pkt_duration_time"))
        timeline.append(
            {
                "pts_seconds": pts,
                "duration": duration if duration and math.isfinite(duration) and duration > 0 else 0.0,
            }
        )
    return timeline


def run(args: argparse.Namespace) -> tuple[Path, Path, Path, int]:
    video = args.video.expanduser().resolve()
    if not video.is_file():
        raise FileNotFoundError(f"输入视频不存在或不是文件：{video}")
    if args.crop_top >= args.crop_bottom:
        raise ValueError("--crop-top 必须小于 --crop-bottom")
    if args.crop_left >= args.crop_right:
        raise ValueError("--crop-left 必须小于 --crop-right")

    timeline = _probe_frame_timeline(video, args.ffprobe)
    source_start_pts = timeline[0]["pts_seconds"]
    expected_frame_count = len(timeline)

    # Optional packages are loaded only after argparse has handled --help.
    cv2, ocr_engine, engine_name, engine_version = _load_optional_dependencies()

    output_dir = args.output.expanduser().resolve()
    for filename in ("ocr_frames.jsonl", "ocr_observations.json", "ocr_observations.csv", "ocr_manifest.json"):
        if (output_dir / filename).exists():
            raise FileExistsError(f"OCR 输出已存在，请使用新的输出目录：{output_dir / filename}")
    observations_dir = output_dir / "subtitle_evidence"
    observations_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV 无法打开视频：{video}")

    source_fps = float(capture.get(cv2.CAP_PROP_FPS))
    if not math.isfinite(source_fps) or source_fps <= 0:
        capture.release()
        raise RuntimeError("视频未提供有效帧率")
    expected_frame_count_raw = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    metadata_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    metadata_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    metadata_duration = (
        expected_frame_count_raw / source_fps if expected_frame_count_raw > 0 else None
    )
    final_frame_duration = timeline[-1]["duration"] or 1.0 / source_fps
    final_duration_source = (
        "ffprobe pkt_duration_time" if timeline[-1]["duration"] else "estimated 1 / source_fps"
    )
    timeline_end = timeline[-1]["pts_seconds"] - source_start_pts + final_frame_duration
    decoded_frames = 0
    successful_ocr_calls = 0
    no_text_frames = 0
    ocr_errors: list[dict[str, Any]] = []
    ocr_error_count = 0
    observations: list[dict[str, Any]] = []
    current_cluster: dict[str, Any] | None = None
    first_crop_pixels: dict[str, int] | None = None
    frame_records_path = output_dir / "ocr_frames.jsonl"

    try:
        with frame_records_path.open("w", encoding="utf-8") as frame_records:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frame_index = decoded_frames
                decoded_frames += 1
                mapped = frame_index < expected_frame_count
                pts = timeline[frame_index]["pts_seconds"] if mapped else None
                timestamp = pts - source_start_pts if pts is not None else None
                height, width = frame.shape[:2]
                top = min(height - 1, int(round(args.crop_top * height)))
                bottom = max(top + 1, min(height, int(round(args.crop_bottom * height))))
                left = min(width - 1, int(round(args.crop_left * width)))
                right = max(left + 1, min(width, int(round(args.crop_right * width))))
                crop_pixels = {"top": top, "bottom": bottom, "left": left, "right": right}
                if first_crop_pixels is None:
                    first_crop_pixels = crop_pixels
                cropped = frame[top:bottom, left:right]
                frame_record: dict[str, Any] = {
                    "frame_index": frame_index,
                    "pts_seconds": pts,
                    "timestamp": timestamp,
                    "mapping_status": "mapped" if mapped else "missing_ffprobe_frame",
                    "crop_pixels": crop_pixels,
                    "ocr_status": "pending",
                    "text": "",
                    "lines": [],
                    "observation_id": None,
                }
                # Every decoded frame reaches the engine, including duplicate images.
                try:
                    lines = _normalise_ocr_output(ocr_engine(cropped))
                    successful_ocr_calls += 1
                    frame_record["ocr_status"] = "text" if lines else "no_text_detected"
                    frame_record["text"] = "\n".join(line["text"] for line in lines)
                    frame_record["lines"] = lines
                    if not lines:
                        no_text_frames += 1
                except Exception as exc:
                    lines = []
                    ocr_error_count += 1
                    frame_record["ocr_status"] = "error"
                    frame_record["error"] = f"{type(exc).__name__}: {exc}"
                    if len(ocr_errors) < 100:
                        ocr_errors.append(
                            {"frame_index": frame_index, "timestamp": timestamp, "error": frame_record["error"]}
                        )

                text = frame_record["text"]
                normalised = _normalise_text(text) or text
                continues_cluster = (
                    current_cluster is not None
                    and mapped
                    and bool(lines)
                    and _same_subtitle(current_cluster["normalised_text"], normalised)
                )
                if current_cluster is not None and not continues_cluster:
                    _save_cluster(
                        current_cluster, observations, observations_dir, cv2,
                        timestamp if timestamp is not None else timeline_end,
                    )
                    current_cluster = None
                if lines and mapped:
                    observation = {
                        "frame_index": frame_index,
                        "timestamp": timestamp,
                        "text": text,
                        "normalised_text": normalised,
                        "confidence": _mean_confidence(lines),
                        "lines": lines,
                    }
                    if current_cluster is None:
                        current_cluster = _new_cluster(observation, cropped)
                    else:
                        _add_to_cluster(current_cluster, observation, cropped)
                    frame_record["observation_id"] = f"O{len(observations) + 1:04d}"
                frame_records.write(json.dumps(frame_record, ensure_ascii=False) + "\n")
    finally:
        capture.release()

    if current_cluster is not None:
        _save_cluster(
            current_cluster, observations, observations_dir, cv2,
            timeline[decoded_frames]["pts_seconds"] - source_start_pts
            if decoded_frames < expected_frame_count else timeline_end,
        )

    observations_json_path = output_dir / "ocr_observations.json"
    observations_csv_path = output_dir / "ocr_observations.csv"
    manifest_path = output_dir / "ocr_manifest.json"
    decode_complete = decoded_frames == expected_frame_count
    full_frame_ocr_complete = decode_complete and successful_ocr_calls == decoded_frames

    observations_payload = {
        "status": PROVISIONAL_STATUS,
        "provisional": True,
        "full_frame_ocr_complete": full_frame_ocr_complete,
        "notice": PROVISIONAL_NOTICE,
        "source_video": str(video),
        "frame_ledger": "ocr_frames.jsonl",
        "observation_count": len(observations),
        "observations": observations,
    }
    observations_json_path.write_text(
        json.dumps(observations_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(observations_csv_path, observations)

    manifest = {
        "status": PROVISIONAL_STATUS,
        "execution_status": "complete" if full_frame_ocr_complete else "incomplete",
        "provisional": True,
        "notice": PROVISIONAL_NOTICE,
        "source_video": str(video),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": {"name": engine_name, "version": engine_version},
        "language_hint": args.language_hint,
        "language_hint_usage": "manifest only; not passed to RapidOCR",
        "full_frame_coverage": {
            "method": "OCR on every sequentially decoded frame; no frame or duplicate skipping",
            "timestamp_source": "FFprobe best_effort_timestamp_time matched by sequential frame index",
            "source_start_pts_seconds": source_start_pts,
            "source_fps": source_fps,
            "decoded_frame_count": decoded_frames,
            "expected_frame_count": expected_frame_count,
            "decode_complete_by_ffprobe_frame_count": decode_complete,
            "full_frame_ocr_complete": full_frame_ocr_complete,
            "visual_analysis_complete": False,
            "audio_analysis_complete": False,
            "scope": "OCR coverage only; does not prove visual inspection or audio analysis",
        },
        "video": {
            "width": metadata_width,
            "height": metadata_height,
            "metadata_duration": metadata_duration,
            "timeline_duration": timeline_end,
            "final_frame_duration_source": final_duration_source,
        },
        "crop": {
            "ratios": {
                "top": args.crop_top,
                "bottom": args.crop_bottom,
                "left": args.crop_left,
                "right": args.crop_right,
            },
            "pixels_on_first_frame": first_crop_pixels,
            "ocr_box_coordinate_space": "cropped evidence frame",
        },
        "duplicate_clustering": {
            "similarity_threshold": CLUSTER_SIMILARITY_THRESHOLD,
            "method": "aggregate only contiguous recognized frames after each frame has been OCRed",
            "representative_images_are_navigation_only": True,
        },
        "counts": {
            "successful_ocr_calls": successful_ocr_calls,
            "no_text_detected_frame_count": no_text_frames,
            "ocr_error_count": ocr_error_count,
            "logged_ocr_error_count": len(ocr_errors),
            "observation_count": len(observations),
        },
        "ocr_errors": ocr_errors,
        "outputs": {
            "evidence_frames": "subtitle_evidence/",
            "csv": "ocr_observations.csv",
            "json": "ocr_observations.json",
            "frame_ledger": "ocr_frames.jsonl",
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not full_frame_ocr_complete:
        raise RuntimeError(
            f"全帧 OCR 未完成：FFprobe {expected_frame_count} 帧，解码 {decoded_frames} 帧，"
            f"OCR 成功 {successful_ocr_calls} 帧，失败 {ocr_error_count} 帧；"
            f"已保存逐帧记录及未完成状态：{manifest_path}"
        )
    return observations_json_path, observations_csv_path, manifest_path, len(observations)


def main(argv: list[str] | None = None) -> int:
    configure_console_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        json_path, csv_path, manifest_path, count = run(args)
    except Exception as exc:  # Keep command-line failures concise and actionable.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"{PROVISIONAL_STATUS}: OCR covered every verified frame; wrote ocr_frames.jsonl "
        f"and {count} clustered observations to "
        f"{json_path}, {csv_path}, and {manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
