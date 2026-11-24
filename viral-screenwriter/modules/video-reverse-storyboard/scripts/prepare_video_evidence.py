#!/usr/bin/env python3
"""Prepare full-coverage video evidence for mandatory review.

Default outputs: a per-frame table (frame_index.csv) indexing every selected
frame with frame number, source PTS, change metrics and cut candidates, plus
labelled thumbnail sheets that tile every selected frame in order. Full-size
PNG frames are exported only on request (--export-full-frames, or --full-range
for hard-to-read ranges, also on an existing evidence directory). Every audio
track and every embedded subtitle track is exported.

Machine decoding, PTS indexing, change metrics and saved images do not
constitute review or listening. The manifest leaves both review steps pending.

Exit codes: 0 prepared (review pending); 1 finished, but some outputs failed
(see analysis_manifest.json errors); 2 not run or stopped (usage, input,
missing tools or packages, refused overwrite, decode or PTS mismatch).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TOOL_NAME = "video-reverse-storyboard.prepare_video_evidence"
SCHEMA_VERSION = "2.1"
EXIT_OK, EXIT_INCOMPLETE, EXIT_FATAL = 0, 1, 2
DEFAULT_SHEET_CELL = 160
DEFAULT_SHEET_COLUMNS = 10
DEFAULT_SHEET_ROWS = 6
# With --end, ffprobe reads only this far past the end so that frames reordered
# behind a later packet (B-frames) are still listed.
FRAME_PROBE_END_MARGIN_S = 3.0
FRAME_INDEX_FIELDS = [
    "selected_index", "source_frame_index", "pts", "time_base", "pts_time_s",
    "timestamp_s", "source_first_pts", "source_first_pts_time_s", "width", "height",
    "source_width", "source_height", "file", "export_status", "semantic_review_status",
    "timestamp_source", "duration_s", "sheet_file", "sheet_cell", "gray_absdiff_normalized",
    "hsv_hist_bhattacharyya_distance", "combined_score", "cut_candidate_id",
]
SUBTITLE_TO_SRT = {"subrip", "srt", "mov_text", "webvtt", "text"}
SUBTITLE_STYLED = {"ass", "ssa"}


def configure_console_utf8() -> None:
    """Keep Chinese diagnostics readable in redirected Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (LookupError, OSError):
                pass


class EvidenceError(RuntimeError):
    """An expected failure with an actionable recovery hint."""

    def __init__(self, code: str, message: str, action: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.action = action


@dataclass
class Dependencies:
    np: Any
    Image: Any
    ImageDraw: Any
    ImageFont: Any
    pillow_version: str


@dataclass
class FrameMetric:
    selected_index: int
    frame_index: int
    timestamp_s: float
    timestamp_source: str
    backend_timestamp_s: Optional[float]
    previous_frame_index: Optional[int]
    previous_timestamp_s: Optional[float]
    gray_absdiff_mean: Optional[float]
    gray_absdiff_normalized: Optional[float]
    hsv_hist_distance: Optional[float]
    combined_score: Optional[float]
    threshold_candidate: bool = False
    min_gap_candidate: bool = False
    candidate_id: str = ""


class OutputRegistry:
    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root
        self._roles: Dict[Path, str] = {}

    def add(self, path: Path, role: str) -> None:
        self._roles[path.resolve()] = role

    def entries(self) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for path, role in sorted(self._roles.items(), key=lambda item: item[0].as_posix().lower()):
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(self.output_root).as_posix()
            except ValueError:
                relative = str(path)
            entry: Dict[str, Any] = {"path": relative, "role": role, "size_bytes": path.stat().st_size}
            if role == "full_frame_visual_evidence":
                # Full frames are checked at export and indexed by source PTS.
                entry["sha256"] = None
                entry["note"] = "content hash omitted; frame decoded during downstream visual review"
            else:
                entry["sha256"] = sha256_file(path)
            entries.append(entry)
        return entries


def finite_float(value: str) -> float:
    try:
        result = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected a number, got {value!r}") from exc
    if not math.isfinite(result):
        raise argparse.ArgumentTypeError("value must be finite")
    return result


def nonnegative_float(value: str) -> float:
    result = finite_float(value)
    if result < 0.0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return result


def percentile_float(value: str) -> float:
    result = finite_float(value)
    if result < 0.0 or result > 100.0:
        raise argparse.ArgumentTypeError("value must be between 0 and 100")
    return result


def positive_int(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected a whole number, got {value!r}") from exc
    if result < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return result


def full_range(value: str) -> Tuple[str, float, float]:
    """Parse FIRST-LAST source frame numbers or STARTs-ENDs seconds."""
    text = value.strip().lower().replace("–", "-").replace("—", "-")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(s?)\s*-\s*(\d+(?:\.\d+)?)\s*(s?)", text)
    if not match:
        raise argparse.ArgumentTypeError(
            "use frame numbers FIRST-LAST (e.g. 120-180) or seconds STARTs-ENDs (e.g. 4.0s-6.5s)")
    start, end = float(match.group(1)), float(match.group(3))
    if match.group(2) or match.group(4):
        if end <= start:
            raise argparse.ArgumentTypeError("the end second must be greater than the start second")
        return ("seconds", start, end)
    if "." in match.group(1) or "." in match.group(3):
        raise argparse.ArgumentTypeError("frame numbers are whole numbers; add 's' for seconds")
    if end < start:
        raise argparse.ArgumentTypeError("the last frame must not precede the first frame")
    return ("frames", int(start), int(end))


def describe_range(item: Tuple[str, float, float]) -> str:
    kind, start, end = item
    return f"{start:g}s-{end:g}s" if kind == "seconds" else f"{int(start)}-{int(end)}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Index every selected frame with source PTS and change metrics (frame_index.csv), "
                     "tile every frame on labelled thumbnail sheets, and export every audio and subtitle "
                     "track. Full-size frames only on request."),
        epilog=("Review all sheets in order and listen to all audio; open full-size frames for hard-to-read "
                "ranges with --full-range (also on an existing evidence directory). Machine export does not "
                "complete analysis. Exit codes: 0 prepared, 1 finished with failed outputs, 2 stopped."),
    )
    parser.add_argument("video", help="input video path")
    parser.add_argument("output", help="new empty internal working directory, or an existing one with --full-range")
    parser.add_argument("--start", type=nonnegative_float, default=0.0,
                        help="selected interval start relative to the first video PTS (default: 0)")
    parser.add_argument("--end", type=nonnegative_float, default=None,
                        help="exclusive selected interval end (default: all remaining frames)")
    parser.add_argument("--cut-percentile", type=percentile_float, default=97.0,
                        help="auxiliary candidate threshold percentile (default: 97)")
    parser.add_argument("--min-cut-gap", type=nonnegative_float, default=0.50,
                        help="auxiliary candidate peak suppression gap (default: 0.50)")
    parser.add_argument("--resume-export", action="store_true",
                        help="reuse an already exported complete full-frame set in output")
    parser.add_argument("--expected-video-sha256", default=None,
                        help="required with --resume-export; bind existing evidence to this video")
    parser.add_argument("--analysis-height", type=int, default=None,
                        help="scale exported full-size frames to at most this height, preserving aspect ratio and PTS")
    parser.add_argument("--export-full-frames", action="store_true",
                        help="also export every selected frame as a full-size PNG (off by default)")
    parser.add_argument("--full-range", type=full_range, action="append", default=None, metavar="RANGE",
                        help=("export full-size PNGs for a hard-to-read range: source frame numbers FIRST-LAST "
                              "(inclusive) or seconds STARTs-ENDs (end exclusive, same origin as --start). "
                              "Repeatable. On an existing evidence directory it only adds these frames."))
    parser.add_argument("--sheet-columns", type=positive_int, default=DEFAULT_SHEET_COLUMNS,
                        help=f"thumbnail sheet columns (default: {DEFAULT_SHEET_COLUMNS})")
    parser.add_argument("--sheet-rows", type=positive_int, default=DEFAULT_SHEET_ROWS,
                        help=f"thumbnail sheet rows (default: {DEFAULT_SHEET_ROWS})")
    parser.add_argument("--sheet-cell", type=positive_int, default=DEFAULT_SHEET_CELL,
                        help=f"longest side of each thumbnail in pixels (default: {DEFAULT_SHEET_CELL})")
    return parser


def load_optional_dependencies() -> Dependencies:
    try:
        import numpy as np
        import PIL
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise EvidenceError("missing_python_dependencies", str(exc),
                            f"Install numpy and Pillow for {sys.executable} and retry; do not fall back to sampling.") from exc
    return Dependencies(np=np, Image=Image, ImageDraw=ImageDraw, ImageFont=ImageFont,
                        pillow_version=PIL.__version__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def issue(code: str, message: str, action: str = "") -> Dict[str, str]:
    result = {"code": code, "message": message}
    if action:
        result["action"] = action
    return result


def command_display(argv: Sequence[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(argv))
    return shlex.join(list(argv))


def creation_flags() -> int:
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def run_process(argv: Sequence[str], command_kind: str,
                commands: List[Dict[str, Any]]) -> subprocess.CompletedProcess:
    command_record: Dict[str, Any] = {"kind": command_kind, "argv": list(argv), "display": command_display(argv)}
    try:
        completed = subprocess.run(list(argv), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, check=False, creationflags=creation_flags())
    except OSError as exc:
        command_record.update({"status": "launch_failed", "exception": f"{type(exc).__name__}: {exc}"})
        commands.append(command_record)
        raise EvidenceError(f"{command_kind}_launch_failed", f"Could not launch {argv[0]!r}: {exc}",
                            f"Confirm {argv[0]!r} is installed, executable, and available on PATH.") from exc
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    command_record.update({"status": "completed", "return_code": completed.returncode,
                           "stdout_bytes": len(completed.stdout), "stderr": stderr[-8000:] if stderr else ""})
    commands.append(command_record)
    return completed


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def optional_float(value: Any) -> Optional[float]:
    if value in (None, "", "N/A"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def optional_int(value: Any) -> Optional[int]:
    if value in (None, "", "N/A"):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def fraction_rate(value: Any) -> Optional[float]:
    if value in (None, "", "N/A", "0/0"):
        return None
    try:
        rate = float(Fraction(str(value)))
    except (ValueError, ZeroDivisionError):
        return None
    if not math.isfinite(rate) or rate <= 0.0:
        return None
    return rate


def parse_ffmpeg_version(text: str) -> Optional[Tuple[int, int]]:
    """Return (major, minor) from `ffmpeg -version`; None for git or unknown builds."""
    match = re.search(r"version\s+n?(\d+)\.(\d+)", text)
    return (int(match.group(1)), int(match.group(2))) if match else None


def passthrough_args(version: Optional[Tuple[int, int]]) -> List[str]:
    """Keep every decoded frame: `-fps_mode` exists from FFmpeg 5.1, `-vsync` was removed later."""
    if version is not None and version < (5, 1):
        return ["-vsync", "passthrough"]
    return ["-fps_mode", "passthrough"]


def detect_ffmpeg(ffmpeg_executable: str, commands: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    completed = run_process([ffmpeg_executable, "-hide_banner", "-version"], "ffmpeg_version", commands)
    lines = completed.stdout.decode("utf-8", errors="replace").splitlines()
    first = lines[0].strip() if lines else ""
    return first, passthrough_args(parse_ffmpeg_version(first))


def select_video_streams(streams: Iterable[Any]) -> List[Dict[str, Any]]:
    """Moving-video streams in container order; attached pictures (cover art) are excluded."""
    return [stream for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "video"
            and not bool((stream.get("disposition") or {}).get("attached_pic"))]


def display_rotation(stream: Dict[str, Any]) -> float:
    """Rotation from the display matrix side data, or the legacy `rotate` tag."""
    for item in stream.get("side_data_list") or []:
        if isinstance(item, dict):
            value = optional_float(item.get("rotation"))
            if value is not None:
                return value
    value = optional_float((stream.get("tags") or {}).get("rotate"))
    return value if value is not None else 0.0


def right_angle(rotation: float) -> Optional[int]:
    """0/90/180/270 for right-angle rotations, None for any other angle."""
    turned = rotation % 360.0
    for angle in (0, 90, 180, 270, 360):
        if abs(turned - angle) < 1.0:
            return angle % 360
    return None


def sample_aspect_ratio(stream: Dict[str, Any]) -> Fraction:
    match = re.fullmatch(r"(\d+):(\d+)", str(stream.get("sample_aspect_ratio") or ""))
    if match and int(match.group(1)) > 0 and int(match.group(2)) > 0:
        return Fraction(int(match.group(1)), int(match.group(2)))
    return Fraction(1, 1)


def display_size(coded_width: int, coded_height: int, rotation: float) -> Tuple[int, int]:
    """FFmpeg autorotate transposes right-angle turns; other angles keep the canvas."""
    if right_angle(rotation) in (90, 270):
        return coded_height, coded_width
    return coded_width, coded_height


def thumbnail_size(coded_width: int, coded_height: int, rotation: float, sar: Fraction,
                   cell: int) -> Tuple[int, int]:
    """Thumbnail in display proportions (rotation and pixel aspect) with the long side = cell."""
    aspect = Fraction(coded_width) * sar / coded_height
    if right_angle(rotation) in (90, 270):
        aspect = 1 / aspect
    if aspect >= 1:
        return cell, max(2, round(cell / aspect))
    return max(2, round(cell * aspect)), cell


def probe_video(video_path: Path, ffprobe_executable: str, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Container and stream metadata only; frame-level data comes from probe_frame_timestamps."""
    argv = [ffprobe_executable, "-v", "error", "-show_format", "-show_streams",
            "-print_format", "json", str(video_path)]
    completed = run_process(argv, "ffprobe", commands)
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise EvidenceError("ffprobe_failed",
                            f"ffprobe could not inspect the input (exit {completed.returncode}): "
                            f"{stderr or 'no diagnostic text returned'}",
                            "Confirm the file is a readable video, then run ffprobe on it directly to inspect codec errors.")
    try:
        probe = json.loads(completed.stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise EvidenceError("ffprobe_invalid_json", f"ffprobe returned invalid JSON at character {exc.pos}: {exc.msg}",
                            "Run ffprobe with -print_format json and check whether another wrapper is writing to stdout.") from exc
    if not isinstance(probe, dict):
        raise EvidenceError("ffprobe_unexpected_json", "ffprobe JSON did not contain an object at the top level.",
                            "Upgrade or reinstall ffprobe and retry the same command recorded in analysis_manifest.json.")
    return probe


def summarize_probe(probe: Dict[str, Any], warnings: List[Dict[str, str]]
                    ) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    video_streams = select_video_streams(streams)
    audio_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
    subtitle_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "subtitle"]
    if not video_streams:
        raise EvidenceError("no_video_stream", "ffprobe found no decodable moving-video stream in the input.",
                            "Choose a file containing a video stream; attached cover art alone is not sufficient.")
    if len(video_streams) > 1:
        warnings.append(issue("multiple_video_streams",
                              f"The container has {len(video_streams)} moving-video streams; this run uses the first one.",
                              "If a different stream is required, remux that stream into a single-video-stream file before analysis."))
    stream = video_streams[0]
    format_info = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    stream_duration = optional_float(stream.get("duration"))
    format_duration = optional_float(format_info.get("duration"))
    average_fps = fraction_rate(stream.get("avg_frame_rate"))
    nominal_fps = fraction_rate(stream.get("r_frame_rate"))
    if (average_fps is not None and nominal_fps is not None
            and abs(average_fps - nominal_fps) > max(0.01, nominal_fps * 0.001)):
        warnings.append(issue("variable_rate_signal",
                              "ffprobe average and nominal frame rates differ; the complete source PTS list, rather than nominal FPS, determines selected frames.",
                              "Use frame_index.csv source PTS to review every frame in presentation order."))
    width, height = optional_int(stream.get("width")), optional_int(stream.get("height"))
    rotation = display_rotation(stream)
    sar = sample_aspect_ratio(stream)
    if right_angle(rotation) is None:
        warnings.append(issue("non_right_angle_rotation",
                              f"Display rotation {rotation:g} degrees is not a right angle; FFmpeg rotates inside the coded canvas and corners may be cropped.",
                              "Compare a sheet with the source player before judging screen edges."))
    if sar != 1:
        warnings.append(issue("non_square_pixels",
                              f"Sample aspect ratio {sar.numerator}:{sar.denominator}; sheets use display proportions, full-size PNGs keep coded pixels.",
                              "Judge proportions on the sheets or stretch full-size frames by the sample aspect ratio."))
    display_w, display_h = display_size(width or 0, height or 0, rotation)
    summary: Dict[str, Any] = {
        "selected_video_stream_index": stream.get("index"),
        "video_stream_count": len(video_streams),
        "audio_stream_count": len(audio_streams),
        "subtitle_stream_count": len(subtitle_streams),
        "codec_name": stream.get("codec_name"),
        "codec_long_name": stream.get("codec_long_name"),
        "pixel_format": stream.get("pix_fmt"),
        "width": width,
        "height": height,
        "display_rotation_degrees": rotation,
        "display_width": display_w,
        "display_height": display_h,
        "sample_aspect_ratio": f"{sar.numerator}:{sar.denominator}",
        "orientation": "frames and sheets are exported in display orientation (FFmpeg autorotate)",
        "duration_seconds": stream_duration if stream_duration is not None else format_duration,
        "stream_duration_seconds": stream_duration,
        "format_duration_seconds": format_duration,
        "avg_frame_rate": stream.get("avg_frame_rate"),
        "r_frame_rate": stream.get("r_frame_rate"),
        "fps_used_initially": average_fps if average_fps is not None else nominal_fps,
        "metadata_frame_count": optional_int(stream.get("nb_frames")),
        "time_base": stream.get("time_base"),
        "start_time_seconds": optional_float(stream.get("start_time")),
        "format_start_time_seconds": optional_float(format_info.get("start_time")),
        "subtitle_streams": [
            {"index": item.get("index"), "codec_name": item.get("codec_name"),
             "language": (item.get("tags") or {}).get("language"), "title": (item.get("tags") or {}).get("title"),
             "default": bool((item.get("disposition") or {}).get("default")),
             "forced": bool((item.get("disposition") or {}).get("forced"))}
            for item in subtitle_streams
        ],
    }
    return summary, stream, audio_streams, subtitle_streams


def probe_frame_timestamps(video_path: Path, ffprobe_executable: str, stream_index: int,
                           end_s: Optional[float], commands: List[Dict[str, Any]]) -> Dict[str, Any]:
    argv = [ffprobe_executable, "-v", "error", "-err_detect", "explode", "-select_streams", str(stream_index)]
    if end_s is not None:
        # Relative to the first packet of this stream: stop decoding well past --end.
        argv += ["-read_intervals", f"%+{end_s + FRAME_PROBE_END_MARGIN_S:.3f}"]
    argv += ["-show_frames", "-show_entries",
             "frame=pts,pts_time,best_effort_timestamp,best_effort_timestamp_time,"
             "duration,duration_time,pkt_duration,pkt_duration_time,width,height",
             "-print_format", "json", str(video_path)]
    completed = run_process(argv, "ffprobe_all_frame_timestamps", commands)
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    if completed.returncode != 0 or stderr:
        raise EvidenceError("frame_timestamp_probe_failed", stderr or "ffprobe failed.",
                            "Repair or replace the source and rerun; full-frame coverage cannot be replaced with sampling.")
    try:
        result = json.loads(completed.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise EvidenceError("invalid_frame_timestamps", str(exc), "Check ffprobe and retry.") from exc
    if not isinstance(result, dict) or not result.get("frames"):
        raise EvidenceError("no_frame_timestamps", "ffprobe returned no video frames.",
                            "Use a decodable video with source presentation timestamps.")
    result["probe_scope"] = "whole_stream" if end_s is None else f"until_end_plus_{FRAME_PROBE_END_MARGIN_S:g}s"
    return result


def frame_pts(frame: Dict[str, Any]) -> Tuple[Optional[int], str]:
    """The decoder's best-effort timestamp (what FFmpeg passes to filters), else the raw PTS."""
    for key in ("best_effort_timestamp", "pts"):
        value = frame.get(key)
        if value in (None, "", "N/A"):
            continue
        try:
            return int(value), key
        except (TypeError, ValueError):
            continue
    return None, ""


def frame_duration_seconds(frame: Dict[str, Any]) -> Optional[float]:
    """`duration_time` (FFmpeg 5+) or `pkt_duration_time` (older); None when absent or not positive."""
    for key in ("duration_time", "pkt_duration_time"):
        value = optional_float(frame.get(key))
        if value is not None and value > 0:
            return value
    return None


def select_frame_records(frame_probe: Dict[str, Any], stream: Dict[str, Any],
                         start_s: float, end_s: Optional[float]) -> List[Dict[str, Any]]:
    frames = frame_probe["frames"]
    try:
        time_base = Fraction(str(stream["time_base"]))
        if time_base <= 0:
            raise ValueError("invalid time base")
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise EvidenceError("source_pts_unavailable", str(exc),
                            "Use a source with valid original PTS; nominal FPS is not an acceptable substitute.") from exc
    origin_pts, _ = frame_pts(frames[0])
    if origin_pts is None:
        raise EvidenceError("source_pts_unavailable", "The first source frame has no PTS.",
                            "Use a source with valid original PTS; nominal FPS is not an acceptable substitute.")
    selected: List[Dict[str, Any]] = []
    previous_pts = None
    start = Fraction(str(start_s))
    end = Fraction(str(end_s)) if end_s is not None else None
    for frame_index, frame in enumerate(frames):
        pts, source = frame_pts(frame)
        if pts is None:
            raise EvidenceError("source_pts_missing", f"Source frame {frame_index} has no original PTS.",
                                "Repair the timestamp issue before full-frame review; do not invent nominal timestamps.")
        # A repeated PTS is kept (every decoded frame counts); only going backwards is rejected.
        if previous_pts is not None and pts < previous_pts:
            raise EvidenceError("nonmonotonic_source_pts", f"Source PTS decreases at frame {frame_index}.",
                                "Resolve presentation-order ambiguity before review.")
        previous_pts = pts
        timestamp = (pts - origin_pts) * time_base
        if timestamp < start or (end is not None and timestamp >= end):
            continue
        selected.append({
            "selected_index": len(selected),
            "source_frame_index": frame_index,
            "pts": pts,
            "time_base": str(time_base),
            "pts_time_s": float(pts * time_base),
            "timestamp_s": float(timestamp),
            "source_first_pts": origin_pts,
            "source_first_pts_time_s": float(origin_pts * time_base),
            "coded_width": frame.get("width"),
            "coded_height": frame.get("height"),
            "file": "",
            "export_status": "not_exported",
            "semantic_review_status": "pending",
            "timestamp_source": source,
            "duration_s": frame_duration_seconds(frame),
        })
    if not selected:
        raise EvidenceError("empty_selection", "No source frames lie in the requested interval.",
                            "Choose an interval containing at least one source frame.")
    return selected


def apply_frame_geometry(records: List[Dict[str, Any]], summary: Dict[str, Any],
                         requested_height: Optional[int]) -> Tuple[int, int, int, int]:
    """Record display and full-size export dimensions without changing frame count or PTS."""
    try:
        coded = {(int(row["coded_width"]), int(row["coded_height"])) for row in records}
    except (TypeError, ValueError) as exc:
        raise EvidenceError("invalid_source_resolution", "Invalid source frame dimensions.",
                            "Use a video with a decodable picture stream.") from exc
    if len(coded) != 1:
        raise EvidenceError("variable_source_resolution", "Source frame dimensions vary within this video.",
                            "Use a video with one stable display resolution; do not silently warp frames.")
    coded_width, coded_height = coded.pop()
    if coded_width < 1 or coded_height < 1:
        raise EvidenceError("invalid_source_resolution", "Invalid source frame dimensions.",
                            "Use a video with a decodable picture stream.")
    if (coded_width, coded_height) != (summary.get("width"), summary.get("height")):
        raise EvidenceError("probe_frame_dimensions_mismatch", "Source frame dimensions differ from the video stream probe.",
                            "Resolve inconsistent media metadata before processing.")
    source_width, source_height = display_size(coded_width, coded_height, summary["display_rotation_degrees"])
    analysis_height = min(source_height, requested_height) if requested_height else source_height
    analysis_width = max(1, round(source_width * analysis_height / source_height))
    for row in records:
        row.update(source_width=source_width, source_height=source_height,
                   width=analysis_width, height=analysis_height)
    return source_width, source_height, analysis_width, analysis_height


def frame_file(selected_index: int) -> str:
    return f"frames/full/frame_{selected_index:09d}.png"


def resolve_full_ranges(ranges: Optional[Sequence[Tuple[str, float, float]]],
                        records: Sequence[Dict[str, Any]]) -> List[int]:
    """Selected indices covered by --full-range items (frame numbers are source frame indices)."""
    chosen: set = set()
    for item in ranges or []:
        kind, start, end = item
        if kind == "frames":
            hits = [n for n, row in enumerate(records) if start <= int(row["source_frame_index"]) <= end]
        else:
            hits = [n for n, row in enumerate(records) if start <= float(row["timestamp_s"]) < end]
        if not hits:
            raise EvidenceError("full_range_outside_selection",
                                f"--full-range {describe_range(item)} selects no analysed frame.",
                                "Use frame numbers or seconds shown on the sheets and in frame_index.csv.")
        chosen.update(hits)
    return sorted(chosen)


def contiguous_runs(indices: Sequence[int]) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    for index in sorted(set(indices)):
        if runs and index == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], index)
        else:
            runs.append((index, index))
    return runs


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return f"{value:.9f}"
    return value


def write_frame_index(output_root: Path, records: List[Dict[str, Any]], registry: OutputRegistry) -> None:
    path = output_root / "frame_index.csv"
    write_csv(path, FRAME_INDEX_FIELDS, records)
    registry.add(path, "complete_frame_index_with_original_pts")


def check_png_header(path: Path, expected_size: Tuple[int, int]) -> None:
    """Check dimensions without a second full-file PNG decode."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"Invalid PNG header: {path}")
    dimensions = struct.unpack(">II", header[16:24])
    if dimensions != expected_size:
        raise ValueError(f"Expected size {expected_size}, got {dimensions}: {path}")


def reuse_export(output_root: Path, records: List[Dict[str, Any]], source_frame_count: int,
                 registry: OutputRegistry) -> Dict[str, Any]:
    """Resume only a complete, previously indexed full-frame export bound to a verified source SHA-256."""
    index_path = output_root / "frame_index.csv"
    with index_path.open("r", encoding="utf-8-sig", newline="") as handle:
        indexed = list(csv.DictReader(handle))
    if len(indexed) != len(records):
        raise EvidenceError("resume_index_count_mismatch", f"Index {len(indexed)} / source {len(records)}.",
                            "Do not resume; repair the missing frame evidence first.")
    frame_dir = output_root / "frames" / "full"
    actual = {path.name for path in frame_dir.glob("*.png")}
    expected = {Path(row["file"]).name for row in records}
    if actual != expected:
        raise EvidenceError("resume_frame_set_mismatch", f"PNG set {len(actual)} / source {len(expected)}.",
                            "Do not resume a partial or extra-frame export.")
    for n, (record, old) in enumerate(zip(records, indexed)):
        path = output_root / record["file"]
        try:
            if (int(old["selected_index"]) != n
                    or int(old["source_frame_index"]) != record["source_frame_index"]
                    or int(old["pts"]) != record["pts"]
                    or old["time_base"] != record["time_base"]
                    or abs(float(old["timestamp_s"]) - record["timestamp_s"]) > 1e-6
                    or int(old["width"]) != record["width"]
                    or int(old["height"]) != record["height"]
                    or int(old.get("source_width") or old["width"]) != record["source_width"]
                    or int(old.get("source_height") or old["height"]) != record["source_height"]
                    or old["file"] != record["file"]
                    or old["export_status"] != "written"):
                raise ValueError("indexed PTS, order, path, or export status differs")
            if path.stat().st_size <= 24:
                raise ValueError("empty PNG")
            check_png_header(path, (int(record["width"]), int(record["height"])))
        except (KeyError, ValueError, OSError) as exc:
            raise EvidenceError("resume_frame_invalid", f"Frame {n}: {exc}",
                                "Do not resume an incomplete or altered export.") from exc
        record["export_status"] = "written"
        registry.add(path, "full_frame_visual_evidence")
    return {
        "status": "complete", "method": "resume_verified_frame_export", "scope": "all_selected_frames",
        "source_pts_mapped": True,
        "native_resolution": (records[0]["width"], records[0]["height"]) == (records[0]["source_width"], records[0]["source_height"]),
        "source_width": records[0]["source_width"], "source_height": records[0]["source_height"],
        "analysis_width": records[0]["width"], "analysis_height": records[0]["height"],
        "frame_rate_conversion": False, "frame_deduplication": False,
        "source_frame_count": source_frame_count,
        "expected_frame_count": len(records), "exported_frame_count": len(records),
        "first_source_frame_index": records[0]["source_frame_index"],
        "last_source_frame_index": records[-1]["source_frame_index"],
        "frame_index_file": "frame_index.csv", "frame_directory": "frames/full",
        "semantic_review_performed": False,
    }


def export_full_frames(video_path: Path, output_root: Path, records: List[Dict[str, Any]],
                       indices: Sequence[int], stream_index: int, ffmpeg_executable: str,
                       passthrough: Sequence[str], commands: List[Dict[str, Any]],
                       registry: OutputRegistry) -> Dict[str, Any]:
    """Export full-size PNGs for the given selected indices, one decode per contiguous run.

    Files are named by selected index (frame_index.csv `file`). Every frame of a
    run is kept, including repeated images and duplicate PTS; decoding stops at
    the end of each run.
    """
    frame_dir = output_root / "frames" / "full"
    frame_dir.mkdir(parents=True, exist_ok=True)
    failures: List[int] = []
    diagnostics: List[str] = []
    runs = contiguous_runs(indices)
    for first, last in runs:
        first_source = int(records[first]["source_frame_index"])
        last_source = int(records[last]["source_frame_index"])
        if last_source - first_source != last - first:
            raise EvidenceError("noncontiguous_frame_selection", "The selected source frame indices are not contiguous.",
                                "Resolve the timestamp ordering before export; do not skip any intervening frame.")
        selection = f"select=between(n\\,{first_source}\\,{last_source})"
        width, height = int(records[first]["width"]), int(records[first]["height"])
        if (width, height) != (int(records[first]["source_width"]), int(records[first]["source_height"])):
            selection += f",scale={width}:{height}:flags=lanczos"
        argv = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-nostdin",
                "-xerror", "-err_detect", "explode", "-i", str(video_path),
                "-map", f"0:{stream_index}", "-an", "-sn", "-dn", "-vf", selection, *passthrough,
                "-frames:v", str(last - first + 1), "-start_number", str(first),
                "-c:v", "png", "-compression_level", "3", str(frame_dir / "frame_%09d.png")]
        completed = run_process(argv, "ffmpeg_full_frame_export", commands)
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        if completed.returncode != 0 or stderr:
            diagnostics.append(stderr or f"exit {completed.returncode}")
        for n in range(first, last + 1):
            row = records[n]
            row["file"] = frame_file(n)
            path = output_root / row["file"]
            if not path.is_file():
                row["export_status"] = "missing"
                failures.append(n)
                continue
            registry.add(path, "full_frame_visual_evidence")
            try:
                check_png_header(path, (int(row["width"]), int(row["height"])))
                row["export_status"] = "written"
            except (OSError, ValueError) as exc:
                row["export_status"] = "invalid"
                failures.append(n)
                diagnostics.append(str(exc))
    write_frame_index(output_root, records, registry)
    if failures or diagnostics:
        raise EvidenceError("full_frame_export_incomplete",
                            f"Expected {len(indices)} frames; failed selected indices: {failures[:20]}; ffmpeg: {'; '.join(diagnostics)[:2000]}",
                            "Resolve the export failure and rerun. Missing frames must never be replaced with samples.")
    every = len(indices) == len(records)
    return {
        "status": "complete", "method": "ffmpeg_sequential_decode_passthrough_png",
        "scope": "all_selected_frames" if every else "requested_ranges",
        "requested_runs": [{"first_source_frame_index": int(records[a]["source_frame_index"]),
                            "last_source_frame_index": int(records[b]["source_frame_index"])} for a, b in runs],
        "source_pts_mapped": True,
        "native_resolution": (int(records[0]["width"]), int(records[0]["height"])) ==
                             (int(records[0]["source_width"]), int(records[0]["source_height"])),
        "source_width": int(records[0]["source_width"]), "source_height": int(records[0]["source_height"]),
        "analysis_width": int(records[0]["width"]), "analysis_height": int(records[0]["height"]),
        "frame_rate_conversion": False, "frame_deduplication": False,
        "expected_frame_count": len(indices), "exported_frame_count": len(indices),
        "frame_index_file": "frame_index.csv", "frame_directory": "frames/full",
        "semantic_review_performed": False,
    }


def parse_showinfo(stderr: str) -> List[Tuple[int, int]]:
    """(n, pts) pairs from FFmpeg showinfo log lines."""
    shown: List[Tuple[int, int]] = []
    for line in stderr.splitlines():
        if "showinfo" not in line:
            continue
        match = re.search(r"\bn:\s*(\d+)\s+pts:\s*(-?\d+)\b", line)
        if match:
            shown.append((int(match.group(1)), int(match.group(2))))
    return shown


def pts_alignment(shown: Sequence[Tuple[int, int]], expected_pts: Sequence[int]) -> Optional[str]:
    """'exact' or 'relative_offset' when the decoded frames match the indexed ones, else None.

    A relative match tolerates a constant container offset (start_time != 0)
    in case a FFmpeg build shifts timestamps despite -copyts.
    """
    if len(shown) != len(expected_pts) or any(number != n for n, (number, _) in enumerate(shown)):
        return None
    decoded = [pts for _, pts in shown]
    if decoded == list(expected_pts):
        return "exact"
    if decoded and all(d - decoded[0] == e - expected_pts[0] for d, e in zip(decoded, expected_pts)):
        return "relative_offset"
    return None


class SheetWriter:
    """Tile every selected frame, in order, on labelled JPEG sheets."""

    GAP = 2
    BACKGROUND = (16, 16, 16)
    LABEL = (40, 40, 40)
    CUT = (200, 0, 0)
    TEXT = (255, 255, 255)

    def __init__(self, deps: Dependencies, output_root: Path, records: List[Dict[str, Any]],
                 thumb: Tuple[int, int], columns: int, rows: int, registry: OutputRegistry) -> None:
        self.deps, self.output_root, self.records, self.registry = deps, output_root, records, registry
        self.thumb_w, self.thumb_h = thumb
        self.columns, self.rows = columns, rows
        self.per_sheet = columns * rows
        self.sheet_count = math.ceil(len(records) / self.per_sheet)
        self.font = deps.ImageFont.load_default()
        box = deps.ImageDraw.Draw(deps.Image.new("RGB", (8, 8))).textbbox((0, 0), "#0123456789s.", font=self.font)
        self.text_offset = box[1]
        self.label_h = box[3] - box[1] + 4
        self.cell_h = self.thumb_h + self.label_h
        self.header_h = self.label_h + 2
        self.image: Any = None
        self.draw: Any = None
        self.current = -1
        self.name = ""
        self.sheets: List[Dict[str, Any]] = []
        (output_root / "sheets").mkdir(parents=True, exist_ok=True)

    def _text(self, draw: Any, xy: Tuple[int, int], text: str, width: int) -> None:
        while text and draw.textlength(text, font=self.font) > width:
            text = text[:-1]
        draw.text((xy[0], xy[1] - self.text_offset), text, fill=self.TEXT, font=self.font)

    def _label(self, draw: Any, n: int, x: int, y: int, cut: bool) -> None:
        row = self.records[n]
        top = y + self.thumb_h
        draw.rectangle((x, top, x + self.thumb_w - 1, top + self.label_h - 1), fill=self.CUT if cut else self.LABEL)
        text = f"{row['source_frame_index']} {float(row['timestamp_s']):.2f}s"
        if draw.textlength(text, font=self.font) > self.thumb_w - 4:
            text = str(row["source_frame_index"])
        self._text(draw, (x + 2, top + 2), text, self.thumb_w - 4)

    def _open(self, sheet: int) -> None:
        first = sheet * self.per_sheet
        last = min(len(self.records), first + self.per_sheet) - 1
        used_rows = math.ceil((last - first + 1) / self.columns)
        width = self.columns * (self.thumb_w + self.GAP) + self.GAP
        height = self.header_h + used_rows * (self.cell_h + self.GAP) + self.GAP
        self.image = self.deps.Image.new("RGB", (width, height), self.BACKGROUND)
        self.draw = self.deps.ImageDraw.Draw(self.image)
        head, tail = self.records[first], self.records[last]
        self._text(self.draw, (self.GAP, 2),
                   f"sheet {sheet + 1}/{self.sheet_count} | frames {head['source_frame_index']}-"
                   f"{tail['source_frame_index']} | {float(head['timestamp_s']):.3f}-{float(tail['timestamp_s']):.3f}s",
                   width - 2 * self.GAP)
        self.name = (f"sheets/sheet_{sheet + 1:04d}_f{head['source_frame_index']:06d}"
                     f"-{tail['source_frame_index']:06d}.jpg")
        self.current = sheet
        self.sheets.append({"file": self.name, "first_source_frame_index": head["source_frame_index"],
                            "last_source_frame_index": tail["source_frame_index"],
                            "first_timestamp_s": head["timestamp_s"], "last_timestamp_s": tail["timestamp_s"],
                            "frame_count": last - first + 1, "cut_candidate_ids": []})

    def _flush(self) -> None:
        if self.image is not None:
            path = self.output_root / self.name
            self.image.save(path, "JPEG", quality=90)
            self.registry.add(path, "labelled_thumbnail_sheet_every_frame")
            self.image = self.draw = None

    def add(self, n: int, thumbnail: Any) -> None:
        sheet, slot = divmod(n, self.per_sheet)
        if sheet != self.current:
            self._flush()
            self._open(sheet)
        row, column = divmod(slot, self.columns)
        x = self.GAP + column * (self.thumb_w + self.GAP)
        y = self.header_h + self.GAP + row * (self.cell_h + self.GAP)
        self.image.paste(thumbnail, (x, y))
        self._label(self.draw, n, x, y, cut=False)
        record = self.records[n]
        record["sheet_file"] = self.name
        record["sheet_cell"] = f"r{row + 1}c{column + 1}"
        record["_cell_xy"] = (x, y)

    def close(self) -> None:
        self._flush()

    def mark_cuts(self, candidates: Sequence[FrameMetric]) -> None:
        """Outline candidate-cut cells in red and colour their labels (re-saves only affected sheets)."""
        by_sheet: Dict[str, List[FrameMetric]] = {}
        for candidate in candidates:
            by_sheet.setdefault(self.records[candidate.selected_index]["sheet_file"], []).append(candidate)
        for name, items in by_sheet.items():
            path = self.output_root / name
            with self.deps.Image.open(path) as opened:
                image = opened.convert("RGB")
            draw = self.deps.ImageDraw.Draw(image)
            for candidate in items:
                x, y = self.records[candidate.selected_index]["_cell_xy"]
                draw.rectangle((x, y, x + self.thumb_w - 1, y + self.thumb_h - 1), outline=self.CUT, width=2)
                self._label(draw, candidate.selected_index, x, y, cut=True)
            image.save(path, "JPEG", quality=90)
            for sheet in self.sheets:
                if sheet["file"] == name:
                    sheet["cut_candidate_ids"] = [item.candidate_id for item in items]


def frame_change(np: Any, image: Any, previous: Optional[Tuple[Any, Any]]
                 ) -> Tuple[Tuple[Any, Any], Optional[float], Optional[float], Optional[float], Optional[float]]:
    gray = np.asarray(image.convert("L"), dtype=np.float64)
    hsv = np.asarray(image.convert("HSV"))
    histogram = np.histogram2d(hsv[:, :, 0].ravel(), hsv[:, :, 1].ravel(),
                               bins=(32, 32), range=((0, 256), (0, 256)))[0]
    histogram = histogram / histogram.sum()
    if previous is None:
        return (gray, histogram), None, None, None, None
    gray_mean = float(np.mean(np.abs(gray - previous[0])))
    normalized = gray_mean / 255.0
    distance = math.sqrt(max(0.0, 1.0 - float(np.sqrt(histogram * previous[1]).sum())))
    return (gray, histogram), gray_mean, normalized, distance, 0.5 * normalized + 0.5 * distance


def stream_sheets_and_metrics(video_path: Path, records: List[Dict[str, Any]], stream_index: int,
                              ffmpeg_executable: str, passthrough: Sequence[str], deps: Dependencies,
                              sheets: SheetWriter, commands: List[Dict[str, Any]]
                              ) -> Tuple[List[FrameMetric], str]:
    """Decode every selected frame once: verify order and PTS, tile the sheets, compute metrics.

    -copyts keeps source PTS so they compare with frame_index.csv even when the
    container start_time is not 0; -frames:v stops decoding after --end.
    """
    first = int(records[0]["source_frame_index"])
    last = int(records[-1]["source_frame_index"])
    if last - first + 1 != len(records):
        raise EvidenceError("metrics_noncontiguous_selection", "Selected source indices are not contiguous.",
                            "Resolve the frame index before building sheets and metrics.")
    filters = (f"select=between(n\\,{first}\\,{last}),showinfo,"
               f"scale={sheets.thumb_w}:{sheets.thumb_h}:flags=area,format=rgb24")
    argv = [ffmpeg_executable, "-hide_banner", "-loglevel", "info", "-nostats", "-nostdin",
            "-xerror", "-err_detect", "explode", "-copyts", "-i", str(video_path),
            "-map", f"0:{stream_index}", "-an", "-sn", "-dn", "-vf", filters, *passthrough,
            "-frames:v", str(len(records)), "-pix_fmt", "rgb24", "-c:v", "rawvideo", "-f", "rawvideo", "pipe:1"]
    command_record: Dict[str, Any] = {"kind": "ffmpeg_all_frame_sheets_and_metrics",
                                      "argv": argv, "display": command_display(argv)}
    frame_bytes = sheets.thumb_w * sheets.thumb_h * 3
    metrics: List[FrameMetric] = []
    previous: Optional[Tuple[Any, Any]] = None
    with tempfile.TemporaryFile() as stderr_file:
        try:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=stderr_file, creationflags=creation_flags())
        except OSError as exc:
            raise EvidenceError("metric_stream_launch_failed", str(exc), "Check the ffmpeg executable.") from exc
        try:
            assert process.stdout is not None
            for n, row in enumerate(records):
                raw = process.stdout.read(frame_bytes)
                if len(raw) != frame_bytes:
                    raise EvidenceError("metric_stream_short", f"Frame stream ended at frame {n}/{len(records)}.",
                                        "Investigate source decode; do not substitute sampled frames.")
                thumbnail = deps.Image.frombytes("RGB", (sheets.thumb_w, sheets.thumb_h), raw)
                previous, gray_mean, normalized, distance, score = frame_change(deps.np, thumbnail, previous)
                sheets.add(n, thumbnail)
                before = metrics[-1] if metrics else None
                metrics.append(FrameMetric(
                    selected_index=row["selected_index"], frame_index=row["source_frame_index"],
                    timestamp_s=row["timestamp_s"], timestamp_source="source_pts",
                    backend_timestamp_s=row["pts_time_s"],
                    previous_frame_index=before.frame_index if before else None,
                    previous_timestamp_s=before.timestamp_s if before else None,
                    gray_absdiff_mean=gray_mean, gray_absdiff_normalized=normalized,
                    hsv_hist_distance=distance, combined_score=score,
                ))
            sheets.close()
            if process.stdout.read(1):
                raise EvidenceError("metric_stream_extra_frame", "Frame stream produced extra frames.",
                                    "Investigate frame selection and source order before review.")
            return_code = process.wait()
            stderr_file.seek(0)
            stderr = stderr_file.read().decode("utf-8", errors="replace").strip()
            shown = parse_showinfo(stderr)
            alignment = pts_alignment(shown, [int(row["pts"]) for row in records])
            command_record.update(status="completed", return_code=return_code, streamed_frame_count=len(metrics),
                                  pts_verified_count=len(shown), pts_alignment=alignment, stderr=stderr[-8000:])
            commands.append(command_record)
            if alignment is None:
                raise EvidenceError("metric_stream_pts_mismatch",
                                    f"Decoded frames do not match the indexed frames ({len(shown)}/{len(records)} PTS checked).",
                                    "Investigate source presentation order; do not substitute approximate timestamps.")
            if return_code != 0 or re.search(r"(?m)^\[.*\] (?:Error|error):", stderr):
                raise EvidenceError("metric_stream_failed", stderr[-2000:] or f"ffmpeg exit {return_code}",
                                    "Repair source decoding; sheets and metrics must cover every selected frame.")
            return metrics, alignment
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def mark_candidates(metrics: List[FrameMetric], percentile: float, min_gap_s: float,
                    np_module: Any) -> Tuple[List[FrameMetric], Dict[str, Any]]:
    scored = [row for row in metrics if row.combined_score is not None]
    if not scored:
        return [], {"status": "no_transitions_available", "cut_percentile": percentile, "score_threshold": None,
                    "threshold_candidate_count": 0, "min_gap_candidate_count": 0, "min_cut_gap_seconds": min_gap_s}
    scores = np_module.asarray([float(row.combined_score) for row in scored], dtype=np_module.float64)
    threshold = float(np_module.percentile(scores, percentile))
    raw_candidates = [row for row in scored
                      if row.combined_score is not None and row.combined_score > 0.0
                      and row.combined_score + 1e-15 >= threshold]
    for row in raw_candidates:
        row.threshold_candidate = True
    selected: List[FrameMetric] = []
    if min_gap_s <= 0.0:
        selected = list(raw_candidates)
    else:
        occupied: Dict[int, List[float]] = {}
        for row in sorted(raw_candidates, key=lambda r: (-float(r.combined_score or 0.0), r.timestamp_s, r.frame_index)):
            bucket = int(math.floor(row.timestamp_s / min_gap_s))
            if any(abs(row.timestamp_s - kept) < min_gap_s - 1e-12
                   for nearby in (bucket - 1, bucket, bucket + 1) for kept in occupied.get(nearby, [])):
                continue
            occupied.setdefault(bucket, []).append(row.timestamp_s)
            selected.append(row)
    selected.sort(key=lambda row: (row.timestamp_s, row.frame_index))
    for index, row in enumerate(selected, start=1):
        row.min_gap_candidate = True
        row.candidate_id = f"C{index:04d}"
    return selected, {
        "status": "candidate_detection_complete", "label": "candidate",
        "claim": "machine_candidate_not_verified_boundary",
        "cut_percentile": percentile, "score_threshold": threshold, "min_cut_gap_seconds": min_gap_s,
        "threshold_candidate_count": len(raw_candidates), "min_gap_candidate_count": len(selected),
        "score_formula": "0.5 * gray_absdiff_normalized + 0.5 * hsv_hist_bhattacharyya_distance",
        "peak_deduplication": "descending-score non-maximum suppression within min_cut_gap_seconds",
    }


def write_frame_metrics(path: Path, metrics: List[FrameMetric]) -> None:
    fields = ["selected_index", "frame_index", "timestamp_s", "timestamp_source", "backend_timestamp_s",
              "previous_frame_index", "previous_timestamp_s", "gray_absdiff_mean", "gray_absdiff_normalized",
              "hsv_hist_bhattacharyya_distance", "combined_score", "threshold_candidate", "min_gap_candidate",
              "candidate_id", "result_label"]
    rows = ({
        "selected_index": row.selected_index, "frame_index": row.frame_index, "timestamp_s": row.timestamp_s,
        "timestamp_source": row.timestamp_source, "backend_timestamp_s": row.backend_timestamp_s,
        "previous_frame_index": row.previous_frame_index, "previous_timestamp_s": row.previous_timestamp_s,
        "gray_absdiff_mean": row.gray_absdiff_mean, "gray_absdiff_normalized": row.gray_absdiff_normalized,
        "hsv_hist_bhattacharyya_distance": row.hsv_hist_distance, "combined_score": row.combined_score,
        "threshold_candidate": row.threshold_candidate, "min_gap_candidate": row.min_gap_candidate,
        "candidate_id": row.candidate_id, "result_label": "candidate" if row.min_gap_candidate else "",
    } for row in metrics)
    write_csv(path, fields, rows)


def build_candidate_references(candidates: List[FrameMetric], records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    manifest = []
    for candidate in candidates:
        images = {}
        for role, offset in (("pre2", -2), ("pre", -1), ("current", 0), ("post", 1), ("post2", 2)):
            index = candidate.selected_index + offset
            row = records[index] if 0 <= index < len(records) else None
            full = bool(row) and row.get("export_status") == "written"
            images[role] = {
                "status": ("written" if full else "on_sheet") if row else "unavailable_selection_edge",
                "frame_index": row["source_frame_index"] if row else None,
                "timestamp_s": row["timestamp_s"] if row else None,
                "file": row["file"] if full else None,
                "sheet_file": row.get("sheet_file") if row else None,
                "sheet_cell": row.get("sheet_cell") if row else None,
            }
        manifest.append({
            "candidate_id": candidate.candidate_id, "status": "candidate",
            "claim": "auxiliary_machine_candidate_not_verified_boundary",
            "transition_from_frame_index": candidate.previous_frame_index,
            "frame_index": candidate.frame_index, "timestamp_s": candidate.timestamp_s,
            "gray_absdiff_mean": candidate.gray_absdiff_mean,
            "gray_absdiff_normalized": candidate.gray_absdiff_normalized,
            "hsv_hist_bhattacharyya_distance": candidate.hsv_hist_distance,
            "combined_score": candidate.combined_score, "images": images,
        })
    return manifest


def write_shot_candidates(path: Path, candidate_manifest: List[Dict[str, Any]], cut_percentile: float,
                          score_threshold: Optional[float], min_gap_s: float) -> None:
    roles = ("pre2", "pre", "current", "post", "post2")
    fields = ["candidate_id", "status", "claim", "transition_from_frame_index", "frame_index", "timestamp_s",
              "gray_absdiff_mean", "gray_absdiff_normalized", "hsv_hist_bhattacharyya_distance", "combined_score",
              "cut_percentile", "score_threshold", "min_cut_gap_seconds", "review_status", "verified_boundary",
              "transition_type", "review_notes", "current_sheet_file", "current_sheet_cell"]
    for role in roles:
        fields += [f"{role}_frame_path", f"{role}_frame_status"]
    rows: List[Dict[str, Any]] = []
    for candidate in candidate_manifest:
        images = candidate["images"]
        row = {**candidate, "cut_percentile": cut_percentile, "score_threshold": score_threshold,
               "min_cut_gap_seconds": min_gap_s, "review_status": "pending_human_review",
               "verified_boundary": "", "transition_type": "", "review_notes": "",
               "current_sheet_file": images["current"]["sheet_file"],
               "current_sheet_cell": images["current"]["sheet_cell"]}
        for role in roles:
            row[f"{role}_frame_path"] = images[role]["file"]
            row[f"{role}_frame_status"] = images[role]["status"]
        rows.append(row)
    write_csv(path, fields, rows)


def extract_audio(video_path: Path, output_root: Path, audio_streams: List[Dict[str, Any]],
                  ffmpeg_executable: str, ffprobe_executable: str, video_origin_s: float,
                  commands: List[Dict[str, Any]], registry: OutputRegistry) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    if not audio_streams:
        return {"status": "no_audio_stream", "source_audio_stream_count": 0,
                "tracks": [], "listening_status": "not_applicable_no_audio_stream"}, []
    audio_dir = output_root / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    result: Dict[str, Any] = {"status": "running", "source_audio_stream_count": len(audio_streams),
                              "tracks": [], "listening_status": "pending",
                              "scope": "entire_source_each_audio_stream", "video_first_pts_time_s": video_origin_s}
    errors: List[Dict[str, str]] = []
    for ordinal, stream in enumerate(audio_streams):
        original = audio_dir / f"track_{ordinal:02d}_original.wav"
        asr = audio_dir / f"track_{ordinal:02d}_asr_16k_mono.wav"
        start_time = optional_float(stream.get("start_time"))
        track = {
            "ordinal": ordinal, "source_stream_index": stream["index"],
            "source_sample_rate_hz": optional_int(stream.get("sample_rate")),
            "source_channels": optional_int(stream.get("channels")),
            "source_channel_layout": stream.get("channel_layout"),
            "source_start_time_s": start_time,
            "offset_from_video_start_s": start_time - video_origin_s if start_time is not None else None,
            "source_duration_s": optional_float(stream.get("duration")),
            "source_tags": stream.get("tags", {}), "original_status": "pending",
            "original_file": None, "asr_status": "pending", "asr_file": None, "listening_status": "pending",
        }
        result["tracks"].append(track)
        # No -ac or -ar on the listening master: keep channels and sample rate.
        # 32-bit float holds any source sample format without clipping.
        argv = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-xerror", "-err_detect", "explode", "-i", str(video_path),
                "-map", f"0:{stream['index']}", "-vn", "-sn", "-dn",
                "-c:a", "pcm_f32le", "-rf64", "auto", str(original)]
        completed = run_process(argv, "ffmpeg_original_audio_track_export", commands)
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        if completed.returncode != 0 or stderr or not original.is_file() or original.stat().st_size <= 80:
            track["original_status"] = "failed"
            track["asr_status"] = "blocked_original_export_failed"
            errors.append(issue("audio_original_export_failed",
                                f"Audio stream {stream['index']} export failed: {stderr or completed.returncode}",
                                "Repair and export this entire track before listening; audio analysis cannot be omitted."))
            continue
        registry.add(original, "full_source_audio_native_channels_and_rate")
        audio_probe = probe_video(original, ffprobe_executable, commands)
        exported_streams = [item for item in audio_probe.get("streams", []) if item.get("codec_type") == "audio"]
        exported = exported_streams[0] if len(exported_streams) == 1 else {}
        track["exported_sample_rate_hz"] = optional_int(exported.get("sample_rate"))
        track["exported_channels"] = optional_int(exported.get("channels"))
        track["exported_channel_layout"] = exported.get("channel_layout")
        track["exported_duration_s"] = optional_float(exported.get("duration"))
        if (track["exported_sample_rate_hz"] != track["source_sample_rate_hz"]
                or track["exported_channels"] != track["source_channels"]):
            track["original_status"] = "failed_native_audio_format_mismatch"
            track["asr_status"] = "blocked_original_export_failed"
            errors.append(issue("audio_format_changed", f"Audio stream {stream['index']} changed sample rate or channel count.",
                                "Preserve the complete original audio format before listening."))
            continue
        track["original_status"] = "exported"
        track["original_file"] = original.relative_to(output_root).as_posix()
        track["original_codec"] = "pcm_f32le"
        argv = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-xerror", "-i", str(original), "-vn", "-ac", "1", "-ar", "16000",
                "-c:a", "pcm_s16le", str(asr)]
        completed = run_process(argv, "ffmpeg_asr_audio_auxiliary", commands)
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        if completed.returncode != 0 or stderr or not asr.is_file() or asr.stat().st_size <= 44:
            track["asr_status"] = "failed"
            errors.append(issue("audio_asr_export_failed",
                                f"Audio stream {stream['index']} ASR helper failed: {stderr or completed.returncode}",
                                "Retry the helper export. Listen to the preserved original track, not the mono ASR file."))
            continue
        registry.add(asr, "asr_only_16khz_mono_auxiliary_not_listening_master")
        track["asr_status"] = "exported"
        track["asr_file"] = asr.relative_to(output_root).as_posix()
    result["status"] = "incomplete" if errors else "exported_all_tracks"
    result["semantic_audio_analysis_performed"] = False
    return result, errors


def subtitle_export_plan(codec_name: Optional[str]) -> Tuple[str, List[str], str]:
    """(extension, codec arguments, method) for one embedded subtitle stream."""
    codec = (codec_name or "").lower()
    if codec in SUBTITLE_TO_SRT:
        return ".srt", ["-c:s", "srt"], "converted_to_srt"
    if codec in SUBTITLE_STYLED:
        return ".ass", ["-c:s", "copy"], "copied_styled_text"
    return ".mks", ["-c:s", "copy"], "copied_into_matroska_bitmap_or_other"


def export_subtitles(video_path: Path, output_root: Path, subtitle_streams: List[Dict[str, Any]],
                     ffmpeg_executable: str, commands: List[Dict[str, Any]],
                     registry: OutputRegistry) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    if not subtitle_streams:
        return {"status": "no_subtitle_stream", "tracks": []}, []
    subtitle_dir = output_root / "subtitles"
    subtitle_dir.mkdir(parents=True, exist_ok=True)
    tracks: List[Dict[str, Any]] = []
    warnings: List[Dict[str, str]] = []
    for ordinal, stream in enumerate(subtitle_streams):
        extension, codec_args, method = subtitle_export_plan(stream.get("codec_name"))
        target = subtitle_dir / f"track_{ordinal:02d}{extension}"
        argv = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(video_path),
                "-map", f"0:{stream['index']}", "-vn", "-an", "-dn", *codec_args, str(target)]
        completed = run_process(argv, "ffmpeg_subtitle_track_export", commands)
        ok = completed.returncode == 0 and target.is_file() and target.stat().st_size > 0
        tags = stream.get("tags") or {}
        tracks.append({"ordinal": ordinal, "source_stream_index": stream.get("index"),
                       "codec_name": stream.get("codec_name"), "language": tags.get("language"),
                       "title": tags.get("title"), "method": method,
                       "file": target.relative_to(output_root).as_posix() if ok else None,
                       "status": "exported" if ok else "failed", "verification_status": "pending"})
        if ok:
            registry.add(target, "embedded_subtitle_track_export")
        else:
            warnings.append(issue("subtitle_export_failed",
                                  f"Subtitle stream {stream.get('index')} ({stream.get('codec_name')}) was not exported.",
                                  "Inspect it with ffprobe/ffmpeg; it still has to be checked against picture and sound."))
    return {"status": "incomplete" if warnings else "exported_all_tracks", "tracks": tracks}, warnings


def build_initial_manifest(args: argparse.Namespace, video_path: Path, output_root: Path) -> Dict[str, Any]:
    invocation = [sys.executable] + list(sys.argv)
    return {
        "schema_version": SCHEMA_VERSION, "tool": TOOL_NAME,
        "status": "preparing", "started_at_utc": utc_now(), "completed_at_utc": None,
        "command": {"argv": invocation, "display": command_display(invocation)},
        "parameters": {"video": str(video_path), "output": str(output_root),
                       "start_seconds": args.start, "requested_end_seconds": args.end,
                       "analysis_height": args.analysis_height, "export_full_frames": args.export_full_frames,
                       "full_ranges": [describe_range(item) for item in args.full_range or []],
                       "sheet_columns": args.sheet_columns, "sheet_rows": args.sheet_rows,
                       "sheet_cell": args.sheet_cell,
                       "cut_percentile": args.cut_percentile, "min_cut_gap_seconds": args.min_cut_gap},
        "runtime": {"python_executable": sys.executable,
                    "python_version": platform.python_version(), "platform": platform.platform()},
        "input": {"path": str(video_path), "size_bytes": video_path.stat().st_size if video_path.is_file() else None},
        "probe_summary": None, "frame_sheets": {"status": "pending"},
        "full_frame_export": {"status": "pending"}, "candidate_detection": None,
        "audio": {"status": "pending"}, "subtitles": {"status": "pending"},
        "machine_preparation": {"status": "incomplete"},
        "semantic_review": {
            "status": "pending", "full_frame_review": "pending", "audio_listening": "pending",
            "reviewed_frame_count": 0, "reviewed_frame_ranges": [],
            "note": ("Decoder output, metadata, metrics and saved images do not establish review. Review every "
                     "sheet in order (every frame), open full-size frames for hard-to-read ranges with "
                     "--full-range, and listen to every source track; record reviewed ranges only after review."),
        },
        "external_commands": [], "warnings": [], "errors": [], "files": [],
        "evidence_claims": [
            {"id": "all_frames_required", "claim": "Every selected source frame is indexed in frame_index.csv and tiled in order on the labelled sheets, including repeated images and duplicate PTS. No temporal sampling, frame-rate reduction or deduplication."},
            {"id": "source_pts", "claim": "frame_index.csv maps each frame to its source presentation-order index and original integer PTS/time base; the sheet pass re-decodes the same frames and checks their PTS. Nominal FPS is never used to fill missing PTS."},
            {"id": "candidate_scope", "claim": "Candidate cuts and change metrics are auxiliary only. They never select the frames that must be reviewed."},
            {"id": "audio_scope", "claim": "All source audio streams are exported in full with their channel count and sample rate preserved. Mono 16 kHz files are ASR aids only; export is not listening or sound analysis."},
            {"id": "subtitle_scope", "claim": "Embedded subtitle streams are exported for checking against picture and sound; burned-in text needs OCR or visual review."},
        ],
    }


def prepare(args: argparse.Namespace, manifest: Dict[str, Any], registry: OutputRegistry) -> None:
    video_path = Path(manifest["parameters"]["video"])
    output_root = registry.output_root
    commands = manifest["external_commands"]
    if not video_path.is_file():
        raise EvidenceError("input_not_file", f"Input is not a readable video file: {video_path}", "Pass an existing video file.")
    if args.end is not None and args.end <= args.start:
        raise EvidenceError("invalid_interval", "--end must be greater than --start.", "Choose a non-empty interval.")
    ffprobe_executable = shutil.which("ffprobe")
    ffmpeg_executable = shutil.which("ffmpeg")
    if not ffprobe_executable or not ffmpeg_executable:
        raise EvidenceError("ffmpeg_tools_missing", "Both ffmpeg and ffprobe must be on PATH.",
                            "Install both tools and retry; neither frame nor audio preparation may be skipped.")
    deps = load_optional_dependencies()
    ffmpeg_version, passthrough = detect_ffmpeg(ffmpeg_executable, commands)
    manifest["runtime"].update({"numpy_version": deps.np.__version__, "pillow_version": deps.pillow_version,
                                "ffprobe_executable": ffprobe_executable, "ffmpeg_executable": ffmpeg_executable,
                                "ffmpeg_version": ffmpeg_version, "frame_passthrough_option": passthrough[0]})
    source_stat = video_path.stat()
    probe_path = output_root / "media_probe.json"
    frame_probe_path = output_root / "frame_timestamps.json"
    digest = sha256_file(video_path)
    manifest["input"]["sha256"] = digest
    if args.resume_export:
        if digest.lower() != (args.expected_video_sha256 or "").lower():
            raise EvidenceError("resume_source_hash_mismatch", "The source video SHA-256 differs.",
                                "Do not reuse frame evidence from another source.")
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        if Path(probe.get("format", {}).get("filename", "")).resolve() != video_path:
            raise EvidenceError("resume_probe_source_mismatch", "Saved media probe points to a different source.",
                                "Use the matching original video and evidence directory.")
    else:
        probe = probe_video(video_path, ffprobe_executable, commands)
        write_json(probe_path, probe)
    registry.add(probe_path, "ffprobe_json")
    summary, stream, audio_streams, subtitle_streams = summarize_probe(probe, manifest["warnings"])
    manifest["probe_summary"] = summary
    if not audio_streams:
        manifest["semantic_review"]["audio_listening"] = "not_applicable_no_audio_stream"
    if args.resume_export:
        frame_probe = json.loads(frame_probe_path.read_text(encoding="utf-8"))
    else:
        frame_probe = probe_frame_timestamps(video_path, ffprobe_executable, stream["index"], args.end, commands)
        write_json(frame_probe_path, frame_probe)
    registry.add(frame_probe_path, "complete_source_frame_pts_probe")
    records = select_frame_records(frame_probe, stream, args.start, args.end)
    summary["probed_frame_count"] = len(frame_probe["frames"])
    summary["frame_probe_scope"] = frame_probe.get("probe_scope", "whole_stream")
    if (args.end is None and summary["metadata_frame_count"] is not None
            and summary["metadata_frame_count"] != len(frame_probe["frames"])):
        manifest["warnings"].append(issue(
            "metadata_frame_count_differs",
            f"Container metadata lists {summary['metadata_frame_count']} frames; decoding found {len(frame_probe['frames'])}.",
            "The decoded list is authoritative; check the sheets for gaps around edits."))
    source_width, source_height, analysis_width, analysis_height = apply_frame_geometry(
        records, summary, args.analysis_height)
    full_indices = (list(range(len(records))) if args.export_full_frames or args.resume_export
                    else resolve_full_ranges(args.full_range, records))
    for n in full_indices:
        records[n]["file"] = frame_file(n)
        records[n]["export_status"] = "pending"
    if not args.resume_export:
        write_frame_index(output_root, records, registry)
    manifest["semantic_review"]["required_frame_count"] = len(records)
    manifest["semantic_review"]["required_audio_stream_count"] = len(audio_streams)
    # A resumed full-frame set is validated before anything in the directory is rewritten.
    resumed = reuse_export(output_root, records, len(frame_probe["frames"]), registry) if args.resume_export else None

    # 1. One decode of the selection: order/PTS check, every-frame sheets, change metrics.
    thumb = thumbnail_size(int(summary["width"]), int(summary["height"]), summary["display_rotation_degrees"],
                           sample_aspect_ratio(stream), args.sheet_cell)
    sheets = SheetWriter(deps, output_root, records, thumb, args.sheet_columns, args.sheet_rows, registry)
    metrics, alignment = stream_sheets_and_metrics(video_path, records, stream["index"], ffmpeg_executable,
                                                   passthrough, deps, sheets, commands)
    candidates, candidate_detection = mark_candidates(metrics, args.cut_percentile, args.min_cut_gap, deps.np)
    sheets.mark_cuts(candidates)
    for metric in metrics:
        records[metric.selected_index].update(
            gray_absdiff_normalized=metric.gray_absdiff_normalized,
            hsv_hist_bhattacharyya_distance=metric.hsv_hist_distance,
            combined_score=metric.combined_score, cut_candidate_id=metric.candidate_id)
    manifest["frame_sheets"] = {
        "status": "complete", "covers_every_selected_frame": True, "pts_alignment": alignment,
        "sheet_count": len(sheets.sheets), "columns": args.sheet_columns, "rows": args.sheet_rows,
        "thumbnail_width": thumb[0], "thumbnail_height": thumb[1],
        "label": "source frame number and seconds from the first video frame; red = machine cut candidate",
        "sheets": sheets.sheets,
    }

    # 2. Optional full-size frames.
    if resumed is not None:
        export = resumed
    elif full_indices:
        export = export_full_frames(video_path, output_root, records, full_indices, stream["index"],
                                    ffmpeg_executable, passthrough, commands, registry)
    else:
        export = {"status": "not_requested", "reason": "sheets cover every frame; use --full-range for hard-to-read ranges",
                  "source_width": source_width, "source_height": source_height,
                  "analysis_width": analysis_width, "analysis_height": analysis_height}
    export["source_frame_count"] = len(frame_probe["frames"])
    manifest["full_frame_export"] = export

    # 3. Tables.
    metrics_path = output_root / "frame_metrics.csv"
    write_frame_metrics(metrics_path, metrics)
    registry.add(metrics_path, "auxiliary_all_frame_change_metrics")
    candidate_manifest = build_candidate_references(candidates, records)
    candidate_detection["candidates"] = candidate_manifest
    candidate_detection["all_frames_still_require_semantic_review"] = True
    manifest["candidate_detection"] = candidate_detection
    candidates_path = output_root / "shot_candidates.csv"
    write_shot_candidates(candidates_path, candidate_manifest, args.cut_percentile,
                          candidate_detection.get("score_threshold"), args.min_cut_gap)
    registry.add(candidates_path, "auxiliary_candidate_cuts_referencing_sheets_and_frames")
    write_frame_index(output_root, records, registry)

    # 4. Audio and subtitle tracks.
    audio_info, audio_errors = extract_audio(video_path, output_root, audio_streams, ffmpeg_executable,
                                             ffprobe_executable, records[0]["source_first_pts_time_s"], commands, registry)
    manifest["audio"] = audio_info
    manifest["errors"].extend(audio_errors)
    subtitle_info, subtitle_warnings = export_subtitles(video_path, output_root, subtitle_streams,
                                                        ffmpeg_executable, commands, registry)
    manifest["subtitles"] = subtitle_info
    manifest["warnings"].extend(subtitle_warnings)
    end_stat = video_path.stat()
    if (end_stat.st_size, end_stat.st_mtime_ns) != (source_stat.st_size, source_stat.st_mtime_ns):
        raise EvidenceError("source_changed_during_preparation", "The source video changed during preparation.",
                            "Discard mixed evidence and restart from a stable video file.")
    manifest["machine_preparation"]["status"] = "incomplete" if audio_errors else "complete"


def append_full_ranges(args: argparse.Namespace, video_path: Path, output_root: Path) -> int:
    """Add full-size frames for --full-range items to an existing evidence directory."""
    manifest_path = output_root / "analysis_manifest.json"
    try:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            with (output_root / "frame_index.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        except (OSError, ValueError) as exc:
            raise EvidenceError("append_evidence_unreadable", str(exc),
                                "Run a complete preparation in a new directory first.") from exc
        if (manifest.get("tool") != TOOL_NAME or manifest.get("schema_version") != SCHEMA_VERSION
                or (manifest.get("frame_sheets") or {}).get("status") != "complete" or not rows):
            raise EvidenceError("append_manifest_incompatible",
                                "The directory was not completely prepared by this script version.",
                                "Run a complete preparation with this version in a new directory.")
        recorded = manifest.get("input") or {}
        if (Path(str(recorded.get("path"))) != video_path or recorded.get("size_bytes") != video_path.stat().st_size
                or recorded.get("sha256") != sha256_file(video_path)):
            raise EvidenceError("append_source_mismatch", "The video differs from the one this evidence was prepared from.",
                                "Pass the same source video, or prepare the new video in a new directory.")
        ffmpeg_executable = shutil.which("ffmpeg")
        if not ffmpeg_executable:
            raise EvidenceError("ffmpeg_tools_missing", "ffmpeg must be on PATH.", "Install ffmpeg and retry.")
        commands: List[Dict[str, Any]] = []
        _, passthrough = detect_ffmpeg(ffmpeg_executable, commands)
        indices = resolve_full_ranges(args.full_range, rows)
        missing: List[int] = []
        for n in indices:
            path = output_root / frame_file(n)
            if path.is_file():
                try:
                    check_png_header(path, (int(rows[n]["width"]), int(rows[n]["height"])))
                except (OSError, ValueError) as exc:
                    raise EvidenceError("append_existing_frame_invalid", str(exc),
                                        "Remove the damaged file by hand and rerun; existing files are never overwritten.") from exc
            else:
                missing.append(n)
        registry = OutputRegistry(output_root)
        if missing:
            stream_index = int(manifest["probe_summary"]["selected_video_stream_index"])
            export_full_frames(video_path, output_root, rows, missing, stream_index, ffmpeg_executable,
                               passthrough, commands, registry)
        export = manifest.setdefault("full_frame_export", {})
        export.setdefault("range_exports", []).append({
            "at_utc": utc_now(), "ranges": [describe_range(item) for item in args.full_range],
            "frames_in_ranges": len(indices), "newly_exported": len(missing)})
        export["exported_frame_count"] = sum(1 for row in rows if row.get("export_status") == "written")
        if export.get("status") in (None, "not_requested", "pending"):
            export["status"] = "partial_ranges"
        manifest.setdefault("external_commands", []).extend(commands)
        known = {entry.get("path") for entry in manifest.get("files", [])}
        manifest.setdefault("files", []).extend(entry for entry in registry.entries() if entry["path"] not in known)
        write_json(manifest_path, manifest)
    except EvidenceError as exc:
        print(f"ERROR [{exc.code}]: {exc.message}\nAction: {exc.action}", file=sys.stderr)
        return EXIT_FATAL
    print(f"Full-size frames in requested ranges: {len(indices)} ({len(missing)} newly exported)\n"
          f"Directory: {output_root / 'frames' / 'full'}\nIndex: {output_root / 'frame_index.csv'}")
    return EXIT_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    configure_console_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.resume_export and not args.expected_video_sha256:
        parser.error("--resume-export requires --expected-video-sha256")
    if args.expected_video_sha256 and not args.resume_export:
        parser.error("--expected-video-sha256 requires --resume-export")
    if args.expected_video_sha256 and len(args.expected_video_sha256) != 64:
        parser.error("--expected-video-sha256 must be a 64-character hex digest")
    if args.analysis_height is not None and args.analysis_height < 1:
        parser.error("--analysis-height must be a positive pixel count")
    video_path = Path(args.video).expanduser().resolve()
    output_root = Path(args.output).expanduser().resolve()

    if output_root.exists() and not output_root.is_dir():
        print(f"ERROR [output_not_directory]: output exists and is not a directory: {output_root}\n"
              "Action: choose a directory path for the output argument.", file=sys.stderr)
        return EXIT_FATAL
    if output_root.is_dir():
        try:
            output_has_entries = next(output_root.iterdir(), None) is not None
        except OSError as exc:
            print(f"ERROR [output_inspect_failed]: could not inspect output directory {output_root}: {exc}\n"
                  "Action: choose a readable, writable, empty output directory.", file=sys.stderr)
            return EXIT_FATAL
        if output_has_entries and args.full_range and not args.resume_export \
                and (output_root / "analysis_manifest.json").is_file():
            if args.export_full_frames or args.start or args.end is not None:
                parser.error("on an existing evidence directory pass only --full-range "
                             "(the saved frame index fixes the interval)")
            if not video_path.is_file():
                print(f"ERROR [input_not_file]: Input is not a readable video file: {video_path}", file=sys.stderr)
                return EXIT_FATAL
            return append_full_ranges(args, video_path, output_root)
        if output_has_entries and not args.resume_export:
            print(f"ERROR [output_not_empty]: refusing to mix or overwrite evidence in: {output_root}\n"
                  "Action: choose a new empty output directory, such as a versioned sibling folder; "
                  "to add full-size frames to prepared evidence, pass only --full-range.", file=sys.stderr)
            return EXIT_FATAL
    try:
        output_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"ERROR [output_create_failed]: could not create output directory {output_root}: {exc}\n"
              "Action: choose a writable output directory and rerun the command.", file=sys.stderr)
        return EXIT_FATAL

    manifest = build_initial_manifest(args, video_path, output_root)
    registry = OutputRegistry(output_root)
    completed_pipeline = False
    exit_code = EXIT_OK
    try:
        prepare(args, manifest, registry)
        completed_pipeline = True
    except EvidenceError as exc:
        manifest["errors"].append(issue(exc.code, exc.message, exc.action))
        print(f"ERROR [{exc.code}]: {exc.message}\nAction: {exc.action}", file=sys.stderr)
        exit_code = EXIT_FATAL
    except Exception as exc:  # Keep a manifest for unexpected decoder/library failures.
        manifest["errors"].append({
            "code": "unexpected_failure", "message": f"{type(exc).__name__}: {exc}",
            "action": "Inspect traceback_detail, confirm dependency versions, and rerun on a small known-good video before retrying this source.",
            "traceback_detail": traceback.format_exc(),
        })
        print(f"ERROR [unexpected_failure]: {type(exc).__name__}: {exc}\n"
              "Action: inspect analysis_manifest.json traceback_detail and dependency versions.", file=sys.stderr)
        exit_code = EXIT_FATAL

    if completed_pipeline and not manifest["errors"]:
        manifest["status"] = "prepared_review_pending"
    else:
        manifest["status"] = "preparation_incomplete"
        if completed_pipeline:
            exit_code = EXIT_INCOMPLETE
    manifest["completed_at_utc"] = utc_now()
    manifest["files"] = registry.entries()
    manifest["files"].append({"path": "analysis_manifest.json", "role": "analysis_manifest", "size_bytes": None,
                              "sha256": None, "note": "Self size/hash intentionally omitted to avoid a recursive manifest digest."})
    manifest_path = output_root / "analysis_manifest.json"
    try:
        write_json(manifest_path, manifest)
    except OSError as exc:
        print(f"ERROR [manifest_write_failed]: could not write {manifest_path}: {exc}", file=sys.stderr)
        return EXIT_FATAL

    if completed_pipeline:
        candidate_count = int((manifest.get("candidate_detection") or {}).get("min_gap_candidate_count", 0))
        sheets = manifest.get("frame_sheets") or {}
        export = manifest.get("full_frame_export") or {}
        print(f"Internal preparation: {manifest['machine_preparation']['status']}\n"
              f"Indexed frames (frame_index.csv): {manifest['semantic_review'].get('required_frame_count', 0)}\n"
              f"Thumbnail sheets covering every frame: {sheets.get('sheet_count', 0)}\n"
              f"Full-size frames exported: {export.get('exported_frame_count', 0)}\n"
              f"Auxiliary transition candidates: {candidate_count}\n"
              f"Frame review and audio listening: pending\n"
              f"Manifest: {manifest_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
