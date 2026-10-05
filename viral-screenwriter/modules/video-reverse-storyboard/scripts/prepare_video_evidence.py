#!/usr/bin/env python3
"""Export every selected video frame and every audio track for mandatory review.

Machine decoding, PTS indexing and change metrics do not constitute semantic
frame analysis or listening. The manifest leaves both review steps pending.
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
import shutil
import struct
import tempfile
import subprocess
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TOOL_NAME = "video-reverse-storyboard.prepare_video_evidence"
SCHEMA_VERSION = "2.0"
METRIC_SIZE = (160, 90)

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
        for path, role in sorted(
            self._roles.items(), key=lambda item: item[0].as_posix().lower()
        ):
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(self.output_root).as_posix()
            except ValueError:
                relative = str(path)
            entry = {
                    "path": relative,
                    "role": role,
                    "size_bytes": path.stat().st_size,
                    # Full frames were checked at export, are indexed by source
                    # PTS, and will be decoded again for semantic review. Hashing
                    # tens of thousands of native PNGs here is a redundant pass.
                    "sha256": None if role == "full_frame_visual_evidence" else sha256_file(path),
                }
            if role == "full_frame_visual_evidence":
                entry["note"] = "content hash omitted; frame decoded during downstream visual review"
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export all frames at original resolution with source PTS, auxiliary transition candidates, and mandatory audio tracks.",
        epilog="Every frame must subsequently receive semantic review, and all source audio must be listened to. Machine export does not complete analysis.",
    )
    parser.add_argument("video", help="input video path")
    parser.add_argument("output", help="new empty internal working directory")
    parser.add_argument("--start", type=nonnegative_float, default=0.0,
                        help="selected interval start relative to the first video PTS (default: 0)")
    parser.add_argument("--end", type=nonnegative_float, default=None,
                        help="exclusive selected interval end (default: all remaining frames)")
    parser.add_argument("--cut-percentile", type=percentile_float, default=97.0,
                        help="auxiliary candidate threshold percentile (default: 97)")
    parser.add_argument("--min-cut-gap", type=nonnegative_float, default=0.50,
                        help="auxiliary candidate peak suppression gap (default: 0.50)")
    parser.add_argument("--resume-export", action="store_true",
                        help="reuse an already exported complete native-frame set in output")
    parser.add_argument("--expected-video-sha256", default=None,
                        help="required with --resume-export; bind existing evidence to this video")
    parser.add_argument("--analysis-height", type=int, default=None,
                        help="export every frame at up to this pixel height, preserving aspect ratio and PTS")
    return parser


def load_optional_dependencies() -> Dependencies:
    try:
        import numpy as np
        import PIL
        from PIL import Image
    except ImportError as exc:
        raise EvidenceError("missing_python_dependencies", str(exc),
                            f"Install numpy and Pillow for {sys.executable} and retry; do not fall back to sampling.") from exc
    return Dependencies(np=np, Image=Image, pillow_version=PIL.__version__)


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
    try:
        import shlex

        return shlex.join(list(argv))
    except AttributeError:
        return " ".join(list(argv))


def run_process(
    argv: Sequence[str], command_kind: str, commands: List[Dict[str, Any]]
) -> subprocess.CompletedProcess:
    command_record: Dict[str, Any] = {
        "kind": command_kind,
        "argv": list(argv),
        "display": command_display(argv),
    }
    kwargs: Dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            **kwargs,
        )
    except OSError as exc:
        command_record.update(
            {
                "status": "launch_failed",
                "exception": f"{type(exc).__name__}: {exc}",
            }
        )
        commands.append(command_record)
        raise EvidenceError(
            f"{command_kind}_launch_failed",
            f"Could not launch {argv[0]!r}: {exc}",
            f"Confirm {argv[0]!r} is installed, executable, and available on PATH.",
        ) from exc

    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    command_record.update(
        {
            "status": "completed",
            "return_code": completed.returncode,
            "stdout_bytes": len(completed.stdout),
            "stderr": stderr[-8000:] if stderr else "",
        }
    )
    commands.append(command_record)
    return completed


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


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
    if not math.isfinite(result):
        return None
    return result


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


def probe_video(
    video_path: Path,
    ffprobe_executable: str,
    commands: List[Dict[str, Any]],
) -> Dict[str, Any]:
    argv = [
        ffprobe_executable,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-count_frames",
        "-print_format",
        "json",
        str(video_path),
    ]
    completed = run_process(argv, "ffprobe", commands)
    stdout_text = completed.stdout.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise EvidenceError(
            "ffprobe_failed",
            f"ffprobe could not inspect the input video (exit {completed.returncode}): "
            f"{stderr or 'no diagnostic text returned'}",
            "Confirm the file is a readable video, then run ffprobe on it directly to inspect codec errors.",
        )
    try:
        probe = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        raise EvidenceError(
            "ffprobe_invalid_json",
            f"ffprobe returned invalid JSON at character {exc.pos}: {exc.msg}",
            "Run ffprobe with -print_format json and check whether another wrapper is writing to stdout.",
        ) from exc
    if not isinstance(probe, dict):
        raise EvidenceError(
            "ffprobe_unexpected_json",
            "ffprobe JSON did not contain an object at the top level.",
            "Upgrade or reinstall ffprobe and retry the same command recorded in analysis_manifest.json.",
        )
    return probe


def summarize_probe(
    probe: Dict[str, Any], warnings: List[Dict[str, str]]
) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
    streams = probe.get("streams")
    if not isinstance(streams, list):
        streams = []
    video_streams = [
        stream
        for stream in streams
        if isinstance(stream, dict)
        and stream.get("codec_type") == "video"
        and not bool((stream.get("disposition") or {}).get("attached_pic"))
    ]
    audio_streams = [
        stream
        for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "audio"
    ]
    if not video_streams:
        raise EvidenceError(
            "no_video_stream",
            "ffprobe found no decodable moving-video stream in the input.",
            "Choose a file containing a video stream; attached cover art alone is not sufficient.",
        )
    if len(video_streams) > 1:
        warnings.append(
            issue(
                "multiple_video_streams",
                f"The container has {len(video_streams)} moving-video streams; this run explicitly exports the first moving-video stream.",
                "If a different stream is required, remux that stream into a single-video-stream file before analysis.",
            )
        )

    stream = video_streams[0]
    format_info = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    stream_duration = optional_float(stream.get("duration"))
    format_duration = optional_float(format_info.get("duration"))
    duration = stream_duration if stream_duration is not None else format_duration
    average_fps = fraction_rate(stream.get("avg_frame_rate"))
    nominal_fps = fraction_rate(stream.get("r_frame_rate"))
    fps = average_fps if average_fps is not None else nominal_fps
    if (
        average_fps is not None
        and nominal_fps is not None
        and abs(average_fps - nominal_fps) > max(0.01, nominal_fps * 0.001)
    ):
        warnings.append(
            issue(
                "variable_rate_signal",
                "ffprobe average and nominal frame rates differ; the complete source PTS list, rather than nominal FPS, determines selected frames.",
                "Use frame_index.csv source PTS to review every frame in presentation order.",
            )
        )

    summary: Dict[str, Any] = {
        "selected_video_stream_index": stream.get("index"),
        "video_stream_count": len(video_streams),
        "audio_stream_count": len(audio_streams),
        "codec_name": stream.get("codec_name"),
        "codec_long_name": stream.get("codec_long_name"),
        "pixel_format": stream.get("pix_fmt"),
        "width": optional_int(stream.get("width")),
        "height": optional_int(stream.get("height")),
        "duration_seconds": duration,
        "stream_duration_seconds": stream_duration,
        "format_duration_seconds": format_duration,
        "avg_frame_rate": stream.get("avg_frame_rate"),
        "r_frame_rate": stream.get("r_frame_rate"),
        "fps_used_initially": fps,
        "metadata_frame_count": optional_int(stream.get("nb_frames")),
        "ffprobe_counted_frame_count": optional_int(stream.get("nb_read_frames")),
        "time_base": stream.get("time_base"),
        "start_time_seconds": optional_float(stream.get("start_time")),
    }
    return summary, stream, bool(audio_streams)


def probe_frame_timestamps(video_path: Path, ffprobe_executable: str,
                           stream_index: int, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
    argv = [ffprobe_executable, "-v", "error", "-err_detect", "explode",
            "-select_streams", str(stream_index), "-show_frames", "-show_entries",
            "frame=pts,pts_time,pkt_duration,pkt_duration_time,width,height",
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
        raise EvidenceError("no_frame_timestamps", "ffprobe returned no video frames.", "Use a decodable video with source presentation timestamps.")
    return result


def select_frame_records(frame_probe: Dict[str, Any], stream: Dict[str, Any],
                         start_s: float, end_s: Optional[float],
                         counted_count: Optional[int]) -> List[Dict[str, Any]]:
    frames = frame_probe["frames"]
    if counted_count is not None and len(frames) != counted_count:
        raise EvidenceError("frame_count_mismatch", f"Frame timestamp list has {len(frames)} entries; full probe decoded {counted_count}.",
                            "Investigate incomplete decoding; do not reduce the frame set.")
    try:
        time_base = Fraction(str(stream["time_base"]))
        if time_base <= 0:
            raise ValueError("invalid time base")
        origin_pts = int(frames[0]["pts"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise EvidenceError("source_pts_unavailable", str(exc), "Use a source with valid original PTS; nominal FPS is not an acceptable substitute.") from exc
    selected: List[Dict[str, Any]] = []
    previous_pts = None
    start = Fraction(str(start_s))
    end = Fraction(str(end_s)) if end_s is not None else None
    for frame_index, frame in enumerate(frames):
        try:
            pts = int(frame["pts"])
        except (KeyError, TypeError, ValueError) as exc:
            raise EvidenceError("source_pts_missing", f"Source frame {frame_index} has no original PTS.", "Repair the timestamp issue before full-frame review; do not invent nominal timestamps.") from exc
        if previous_pts is not None and pts < previous_pts:
            raise EvidenceError("nonmonotonic_source_pts", f"Source PTS decreases at frame {frame_index}.", "Resolve presentation-order ambiguity before review.")
        previous_pts = pts
        timestamp = (pts - origin_pts) * time_base
        if timestamp < start or (end is not None and timestamp >= end):
            continue
        selected_index = len(selected)
        selected.append({
            "selected_index": selected_index,
            "source_frame_index": frame_index,
            "pts": pts,
            "time_base": str(time_base),
            "pts_time_s": float(pts * time_base),
            "timestamp_s": float(timestamp),
            "source_first_pts": origin_pts,
            "source_first_pts_time_s": float(origin_pts * time_base),
            "width": frame.get("width"),
            "height": frame.get("height"),
            "source_width": frame.get("width"),
            "source_height": frame.get("height"),
            "file": f"frames/full/frame_{selected_index:09d}.png",
            "export_status": "pending",
            "semantic_review_status": "pending",
        })
    if not selected:
        raise EvidenceError("empty_selection", "No source frames lie in the requested interval.", "Choose an interval containing at least one source frame.")
    return selected


def set_analysis_resolution(records: List[Dict[str, Any]], requested_height: Optional[int]) -> Tuple[int, int, int, int]:
    """Set spatial proxy dimensions without changing frame count or PTS."""
    source_width = int(records[0]["source_width"])
    source_height = int(records[0]["source_height"])
    if source_width < 1 or source_height < 1:
        raise EvidenceError("invalid_source_resolution", "Invalid source frame dimensions.",
                            "Use a video with a decodable picture stream.")
    if any((int(row["source_width"]), int(row["source_height"])) !=
           (source_width, source_height) for row in records):
        raise EvidenceError("variable_source_resolution", "Source frame dimensions vary within this video.",
                            "Use a video with one stable display resolution; do not silently warp frames.")
    analysis_height = min(source_height, requested_height) if requested_height else source_height
    analysis_width = max(1, round(source_width * analysis_height / source_height))
    for row in records:
        row["width"] = analysis_width
        row["height"] = analysis_height
    return source_width, source_height, analysis_width, analysis_height


def write_frame_index(output_root: Path, records: List[Dict[str, Any]], registry: OutputRegistry) -> None:
    path = output_root / "frame_index.csv"
    write_csv(path, list(records[0]), records)
    registry.add(path, "complete_frame_index_with_original_pts")


def check_png_header(path: Path, expected_size: Tuple[int, int]) -> None:
    """Check native dimensions without a second full-file PNG decode."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if (len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n"
            or header[12:16] != b"IHDR"):
        raise ValueError(f"Invalid PNG header: {path}")
    dimensions = struct.unpack(">II", header[16:24])
    if dimensions != expected_size:
        raise ValueError(f"Expected native size {expected_size}, got {dimensions}: {path}")


def reuse_export(output_root: Path, records: List[Dict[str, Any]],
                 frame_probe: Dict[str, Any], registry: OutputRegistry) -> Dict[str, Any]:
    """Resume only a complete, previously indexed frame export.

    The caller binds the cached probe/index to an explicitly verified source
    SHA-256. The existing index must say each frame was previously written;
    downstream page construction will decode every PNG again.
    """
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
            path = output_root / record["file"]
            if path.stat().st_size <= 24:
                raise ValueError("empty PNG")
            check_png_header(path, (int(record["width"]), int(record["height"])))
        except (KeyError, ValueError, OSError) as exc:
            raise EvidenceError("resume_frame_invalid", f"Frame {n}: {exc}",
                                "Do not resume an incomplete or altered export.") from exc
        record["export_status"] = "written"
        registry.add(path, "full_frame_visual_evidence")
    registry.add(index_path, "complete_frame_index_with_original_pts")
    return {
        "status": "complete", "method": "resume_verified_frame_export",
        "source_pts_mapped": True,
        "native_resolution": (records[0]["width"] == records[0]["source_width"] and
                              records[0]["height"] == records[0]["source_height"]),
        "source_width": records[0]["source_width"], "source_height": records[0]["source_height"],
        "analysis_width": records[0]["width"], "analysis_height": records[0]["height"],
        "frame_rate_conversion": False, "frame_deduplication": False,
        "source_frame_count": len(frame_probe["frames"]),
        "expected_frame_count": len(records), "exported_frame_count": len(records),
        "first_source_frame_index": records[0]["source_frame_index"],
        "last_source_frame_index": records[-1]["source_frame_index"],
        "frame_index_file": "frame_index.csv", "frame_directory": "frames/full",
        "semantic_review_performed": False,
    }


def export_all_frames(video_path: Path, output_root: Path,
                      records: List[Dict[str, Any]], stream_index: int,
                      ffmpeg_executable: str, deps: Dependencies,
                      commands: List[Dict[str, Any]], registry: OutputRegistry) -> Dict[str, Any]:
    frame_dir = output_root / "frames" / "full"
    frame_dir.mkdir(parents=True, exist_ok=True)
    first = records[0]["source_frame_index"]
    last = records[-1]["source_frame_index"]
    if last - first + 1 != len(records):
        raise EvidenceError("noncontiguous_frame_selection", "The selected source frame indices are not contiguous.", "Resolve the timestamp ordering before export; do not skip any intervening frame.")
    # select limits the explicitly requested interval only; every frame in that
    # interval is preserved, including duplicate images and duplicate PTS.
    selection = f"select=between(n\\,{first}\\,{last})"
    if (records[0]["width"], records[0]["height"]) != (records[0]["source_width"], records[0]["source_height"]):
        selection += f",scale={records[0]['width']}:{records[0]['height']}:flags=lanczos"
    argv = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-nostdin",
            "-xerror", "-err_detect", "explode", "-noautorotate", "-i", str(video_path),
            "-map", f"0:{stream_index}", "-an", "-sn", "-dn", "-vf", selection,
            "-fps_mode", "passthrough", "-start_number", "0", "-c:v", "png",
            "-compression_level", "3", str(frame_dir / "frame_%09d.png")]
    completed = run_process(argv, "ffmpeg_full_frame_export", commands)
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    produced = {p.name for p in frame_dir.glob("*.png")}
    expected = {Path(row["file"]).name for row in records}
    failures = []
    for row in records:
        path = output_root / row["file"]
        if not path.is_file():
            row["export_status"] = "missing"
            failures.append(row["selected_index"])
            continue
        registry.add(path, "full_frame_visual_evidence")
        try:
            check_png_header(path, (int(row["width"]), int(row["height"])))
            row["export_status"] = "written"
        except Exception as exc:
            row["export_status"] = "invalid"
            row["export_error"] = str(exc)
            failures.append(row["selected_index"])
    write_frame_index(output_root, records, registry)
    if completed.returncode != 0 or stderr or produced != expected or failures:
        raise EvidenceError("full_frame_export_incomplete",
                            f"Expected {len(expected)} consecutive frames; produced {len(produced)}; failed indices: {failures[:20]}; ffmpeg: {stderr or completed.returncode}",
                            "Resolve the export failure and rerun in a new directory. Missing frames must never be replaced with samples.")
    return {
        "status": "complete", "method": "ffmpeg_sequential_decode_passthrough_png",
        "source_pts_mapped": True,
        "native_resolution": (records[0]["width"] == records[0]["source_width"] and
                              records[0]["height"] == records[0]["source_height"]),
        "source_width": records[0]["source_width"], "source_height": records[0]["source_height"],
        "analysis_width": records[0]["width"], "analysis_height": records[0]["height"],
        "frame_rate_conversion": False, "frame_deduplication": False,
        "expected_frame_count": len(records), "exported_frame_count": len(records),
        "first_source_frame_index": first, "last_source_frame_index": last,
        "frame_index_file": "frame_index.csv", "frame_directory": "frames/full",
        "semantic_review_performed": False,
    }


def calculate_frame_metrics(records: List[Dict[str, Any]], output_root: Path,
                            deps: Dependencies) -> List[FrameMetric]:
    metrics: List[FrameMetric] = []
    previous_gray = previous_histogram = None
    np = deps.np
    for row in records:
        with deps.Image.open(output_root / row["file"]) as image:
            # Downscaling is ONLY an auxiliary numeric metric. The exported
            # native-resolution frame remains mandatory for semantic review.
            small = image.convert("RGB").resize(METRIC_SIZE, deps.Image.Resampling.BOX)
            gray = np.asarray(small.convert("L"), dtype=np.float64)
            hsv = np.asarray(small.convert("HSV"))
            histogram = np.histogram2d(hsv[:, :, 0].ravel(), hsv[:, :, 1].ravel(),
                                       bins=(32, 32), range=((0, 256), (0, 256)))[0]
            histogram = histogram / histogram.sum()
        gray_mean = normalized = distance = score = None
        if previous_gray is not None:
            gray_mean = float(np.mean(np.abs(gray - previous_gray)))
            normalized = gray_mean / 255.0
            distance = math.sqrt(max(0.0, 1.0 - float(np.sqrt(histogram * previous_histogram).sum())))
            score = 0.5 * normalized + 0.5 * distance
        previous = metrics[-1] if metrics else None
        metrics.append(FrameMetric(
            selected_index=row["selected_index"], frame_index=row["source_frame_index"],
            timestamp_s=row["timestamp_s"], timestamp_source="source_pts",
            backend_timestamp_s=row["pts_time_s"],
            previous_frame_index=previous.frame_index if previous else None,
            previous_timestamp_s=previous.timestamp_s if previous else None,
            gray_absdiff_mean=gray_mean, gray_absdiff_normalized=normalized,
            hsv_hist_distance=distance, combined_score=score,
        ))
        previous_gray, previous_histogram = gray, histogram
    return metrics


def calculate_frame_metrics_stream(video_path: Path, records: List[Dict[str, Any]],
                                   stream_index: int, ffmpeg_executable: str,
                                   deps: Dependencies,
                                   commands: List[Dict[str, Any]]) -> List[FrameMetric]:
    """Decode every selected source frame once at metric resolution.

    This auxiliary pass does not read the native PNG export. The same
    presentation-order source indices and source PTS stay in frame_index.csv.
    A short or extra raw frame is fatal, never silently sampled or padded.
    """
    first = int(records[0]["source_frame_index"])
    last = int(records[-1]["source_frame_index"])
    if last - first + 1 != len(records):
        raise EvidenceError("metrics_noncontiguous_selection", "Metric source indices are not contiguous.",
                            "Resolve the frame index before computing auxiliary metrics.")
    selection = (f"select=between(n\\,{first}\\,{last}),"
                 f"scale={METRIC_SIZE[0]}:{METRIC_SIZE[1]}:flags=area,showinfo")
    argv = [ffmpeg_executable, "-hide_banner", "-loglevel", "info", "-nostats", "-nostdin",
            "-xerror", "-err_detect", "explode", "-noautorotate", "-i", str(video_path),
            "-map", f"0:{stream_index}", "-an", "-sn", "-dn", "-vf", selection,
            "-fps_mode", "passthrough", "-pix_fmt", "rgb24", "-c:v", "rawvideo",
            "-f", "rawvideo", "pipe:1"]
    command_record: Dict[str, Any] = {"kind": "ffmpeg_all_frame_streamed_auxiliary_metrics",
                                      "argv": argv, "display": command_display(argv)}
    frame_bytes = METRIC_SIZE[0] * METRIC_SIZE[1] * 3
    np = deps.np
    metrics: List[FrameMetric] = []
    previous_gray = previous_histogram = None
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    with tempfile.TemporaryFile() as stderr_file:
        try:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=stderr_file, creationflags=creationflags)
        except OSError as exc:
            raise EvidenceError("metric_stream_launch_failed", str(exc), "Check the ffmpeg executable.") from exc
        try:
            assert process.stdout is not None
            for n, row in enumerate(records):
                raw = process.stdout.read(frame_bytes)
                if len(raw) != frame_bytes:
                    raise EvidenceError("metric_stream_short", f"Metric stream ended at frame {n}/{len(records)}.",
                                        "Investigate source decode; do not substitute sampled frames.")
                small = deps.Image.frombytes("RGB", METRIC_SIZE, raw)
                gray = np.asarray(small.convert("L"), dtype=np.float64)
                hsv = np.asarray(small.convert("HSV"))
                histogram = np.histogram2d(hsv[:, :, 0].ravel(), hsv[:, :, 1].ravel(),
                                           bins=(32, 32), range=((0, 256), (0, 256)))[0]
                histogram = histogram / histogram.sum()
                gray_mean = normalized = distance = score = None
                if previous_gray is not None:
                    gray_mean = float(np.mean(np.abs(gray - previous_gray)))
                    normalized = gray_mean / 255.0
                    distance = math.sqrt(max(0.0, 1.0 - float(np.sqrt(histogram * previous_histogram).sum())))
                    score = 0.5 * normalized + 0.5 * distance
                previous = metrics[-1] if metrics else None
                metrics.append(FrameMetric(
                    selected_index=row["selected_index"], frame_index=row["source_frame_index"],
                    timestamp_s=row["timestamp_s"], timestamp_source="source_pts",
                    backend_timestamp_s=row["pts_time_s"],
                    previous_frame_index=previous.frame_index if previous else None,
                    previous_timestamp_s=previous.timestamp_s if previous else None,
                    gray_absdiff_mean=gray_mean, gray_absdiff_normalized=normalized,
                    hsv_hist_distance=distance, combined_score=score,
                ))
                previous_gray, previous_histogram = gray, histogram
            if process.stdout.read(1):
                raise EvidenceError("metric_stream_extra_frame", "Metric stream produced extra frames.",
                                    "Investigate frame selection and source order before review.")
            return_code = process.wait()
            stderr_file.seek(0)
            stderr = stderr_file.read().decode("utf-8", errors="replace").strip()
            shown = []
            for line in stderr.splitlines():
                if "showinfo" not in line:
                    continue
                match = re.search(r"\bn:\s*(\d+)\s+pts:\s*(-?\d+)\b", line)
                if match:
                    shown.append((int(match.group(1)), int(match.group(2))))
            if len(shown) != len(records) or any(
                    frame_number != n or pts != int(records[n]["pts"])
                    for n, (frame_number, pts) in enumerate(shown)):
                raise EvidenceError("metric_stream_pts_mismatch",
                                    f"Metric PTS alignment {len(shown)}/{len(records)} failed.",
                                    "Investigate source presentation order; do not substitute approximate timestamps.")
            command_record.update(status="completed", return_code=return_code,
                                  streamed_frame_count=len(metrics), pts_verified_count=len(shown),
                                  stderr=stderr[-8000:])
            commands.append(command_record)
            if return_code != 0 or re.search(r"(?m)^\[.*\] (?:Error|error):", stderr):
                raise EvidenceError("metric_stream_failed", stderr or f"ffmpeg exit {return_code}",
                                    "Repair source decoding; auxiliary metrics must cover every selected frame.")
            return metrics
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def mark_candidates(
    metrics: List[FrameMetric], percentile: float, min_gap_s: float, np_module: Any
) -> Tuple[List[FrameMetric], Dict[str, Any]]:
    scored = [row for row in metrics if row.combined_score is not None]
    if not scored:
        return [], {
            "status": "no_transitions_available",
            "cut_percentile": percentile,
            "score_threshold": None,
            "threshold_candidate_count": 0,
            "min_gap_candidate_count": 0,
            "min_cut_gap_seconds": min_gap_s,
        }

    scores = np_module.asarray(
        [float(row.combined_score) for row in scored], dtype=np_module.float64
    )
    threshold = float(np_module.percentile(scores, percentile))
    raw_candidates = [
        row
        for row in scored
        if row.combined_score is not None
        and row.combined_score > 0.0
        and row.combined_score + 1e-15 >= threshold
    ]
    for row in raw_candidates:
        row.threshold_candidate = True

    selected: List[FrameMetric] = []
    if min_gap_s <= 0.0:
        selected = list(raw_candidates)
    else:
        occupied: Dict[int, List[float]] = {}
        by_strength = sorted(
            raw_candidates,
            key=lambda row: (
                -float(row.combined_score or 0.0),
                row.timestamp_s,
                row.frame_index,
            ),
        )
        for row in by_strength:
            bucket = int(math.floor(row.timestamp_s / min_gap_s))
            too_close = False
            for nearby_bucket in (bucket - 1, bucket, bucket + 1):
                if any(
                    abs(row.timestamp_s - kept_time) < min_gap_s - 1e-12
                    for kept_time in occupied.get(nearby_bucket, [])
                ):
                    too_close = True
                    break
            if too_close:
                continue
            occupied.setdefault(bucket, []).append(row.timestamp_s)
            selected.append(row)

    selected.sort(key=lambda row: (row.timestamp_s, row.frame_index))
    for index, row in enumerate(selected, start=1):
        row.min_gap_candidate = True
        row.candidate_id = f"C{index:04d}"

    return selected, {
        "status": "candidate_detection_complete",
        "label": "candidate",
        "claim": "machine_candidate_not_verified_boundary",
        "cut_percentile": percentile,
        "score_threshold": threshold,
        "min_cut_gap_seconds": min_gap_s,
        "threshold_candidate_count": len(raw_candidates),
        "min_gap_candidate_count": len(selected),
        "score_formula": "0.5 * gray_absdiff_normalized + 0.5 * hsv_hist_bhattacharyya_distance",
        "peak_deduplication": "descending-score non-maximum suppression within min_cut_gap_seconds",
    }


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return f"{value:.9f}"
    return value


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})


def write_frame_metrics(path: Path, metrics: List[FrameMetric]) -> None:
    fields = [
        "selected_index",
        "frame_index",
        "timestamp_s",
        "timestamp_source",
        "backend_timestamp_s",
        "previous_frame_index",
        "previous_timestamp_s",
        "gray_absdiff_mean",
        "gray_absdiff_normalized",
        "hsv_hist_bhattacharyya_distance",
        "combined_score",
        "threshold_candidate",
        "min_gap_candidate",
        "candidate_id",
        "result_label",
    ]
    rows = (
        {
            "selected_index": row.selected_index,
            "frame_index": row.frame_index,
            "timestamp_s": row.timestamp_s,
            "timestamp_source": row.timestamp_source,
            "backend_timestamp_s": row.backend_timestamp_s,
            "previous_frame_index": row.previous_frame_index,
            "previous_timestamp_s": row.previous_timestamp_s,
            "gray_absdiff_mean": row.gray_absdiff_mean,
            "gray_absdiff_normalized": row.gray_absdiff_normalized,
            "hsv_hist_bhattacharyya_distance": row.hsv_hist_distance,
            "combined_score": row.combined_score,
            "threshold_candidate": row.threshold_candidate,
            "min_gap_candidate": row.min_gap_candidate,
            "candidate_id": row.candidate_id,
            "result_label": "candidate" if row.min_gap_candidate else "",
        }
        for row in metrics
    )
    write_csv(path, fields, rows)


def build_candidate_references(metrics: List[FrameMetric], candidates: List[FrameMetric],
                               records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    candidate_manifest = []
    for candidate in candidates:
        images = {}
        for role, offset in (("pre2", -2), ("pre", -1), ("current", 0), ("post", 1), ("post2", 2)):
            index = candidate.selected_index + offset
            row = records[index] if 0 <= index < len(records) else None
            images[role] = {
                "status": "written" if row else "unavailable_selection_edge",
                "frame_index": row["source_frame_index"] if row else None,
                "timestamp_s": row["timestamp_s"] if row else None,
                "file": row["file"] if row else None,
            }
        candidate_manifest.append({
            "candidate_id": candidate.candidate_id, "status": "candidate",
            "claim": "auxiliary_machine_candidate_not_verified_boundary",
            "transition_from_frame_index": candidate.previous_frame_index,
            "frame_index": candidate.frame_index, "timestamp_s": candidate.timestamp_s,
            "gray_absdiff_mean": candidate.gray_absdiff_mean,
            "gray_absdiff_normalized": candidate.gray_absdiff_normalized,
            "hsv_hist_bhattacharyya_distance": candidate.hsv_hist_distance,
            "combined_score": candidate.combined_score, "images": images,
        })
    return candidate_manifest


def write_shot_candidates(
    path: Path,
    candidate_manifest: List[Dict[str, Any]],
    cut_percentile: float,
    score_threshold: Optional[float],
    min_gap_s: float,
) -> None:
    fields = [
        "candidate_id",
        "status",
        "claim",
        "transition_from_frame_index",
        "frame_index",
        "timestamp_s",
        "gray_absdiff_mean",
        "gray_absdiff_normalized",
        "hsv_hist_bhattacharyya_distance",
        "combined_score",
        "cut_percentile",
        "score_threshold",
        "min_cut_gap_seconds",
        "review_status",
        "verified_boundary",
        "transition_type",
        "review_notes",
        "pre2_frame_path",
        "pre2_frame_status",
        "pre_frame_path",
        "pre_frame_status",
        "current_frame_path",
        "current_frame_status",
        "post_frame_path",
        "post_frame_status",
        "post2_frame_path",
        "post2_frame_status",
    ]
    rows: List[Dict[str, Any]] = []
    for candidate in candidate_manifest:
        images = candidate["images"]
        rows.append(
            {
                **candidate,
                "cut_percentile": cut_percentile,
                "score_threshold": score_threshold,
                "min_cut_gap_seconds": min_gap_s,
                "review_status": "pending_human_review",
                "verified_boundary": "",
                "transition_type": "",
                "review_notes": "",
                "pre2_frame_path": images["pre2"].get("file"),
                "pre2_frame_status": images["pre2"].get("status"),
                "pre_frame_path": images["pre"].get("file"),
                "pre_frame_status": images["pre"].get("status"),
                "current_frame_path": images["current"].get("file"),
                "current_frame_status": images["current"].get("status"),
                "post_frame_path": images["post"].get("file"),
                "post_frame_status": images["post"].get("status"),
                "post2_frame_path": images["post2"].get("file"),
                "post2_frame_status": images["post2"].get("status"),
            }
        )
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
                              "scope": "entire_source_each_audio_stream",
                              "video_first_pts_time_s": video_origin_s}
    errors: List[Dict[str, str]] = []
    for ordinal, stream in enumerate(audio_streams):
        original = audio_dir / f"track_{ordinal:02d}_original.wav"
        asr = audio_dir / f"track_{ordinal:02d}_asr_16k_mono.wav"
        track = {
            "ordinal": ordinal, "source_stream_index": stream["index"],
            "source_sample_rate_hz": optional_int(stream.get("sample_rate")),
            "source_channels": optional_int(stream.get("channels")),
            "source_channel_layout": stream.get("channel_layout"),
            "source_start_time_s": optional_float(stream.get("start_time")),
            "offset_from_video_start_s": (optional_float(stream.get("start_time")) - video_origin_s
                                          if optional_float(stream.get("start_time")) is not None else None),
            "source_duration_s": optional_float(stream.get("duration")),
            "source_tags": stream.get("tags", {}), "original_status": "pending",
            "original_file": None, "asr_status": "pending", "asr_file": None,
            "listening_status": "pending",
        }
        result["tracks"].append(track)
        # No -ac or -ar on the listening master: retain channels and sample rate.
        argv = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-xerror", "-err_detect", "explode", "-i", str(video_path),
                "-map", f"0:{stream['index']}", "-vn", "-sn", "-dn",
                "-c:a", "pcm_f64le", "-rf64", "auto", str(original)]
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
        track["original_codec"] = "pcm_f64le"
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


def build_initial_manifest(args: argparse.Namespace, video_path: Path, output_root: Path) -> Dict[str, Any]:
    invocation = [sys.executable] + list(sys.argv)
    return {
        "schema_version": SCHEMA_VERSION, "tool": TOOL_NAME,
        "status": "preparing", "started_at_utc": utc_now(), "completed_at_utc": None,
        "command": {"argv": invocation, "display": command_display(invocation)},
        "parameters": {"video": str(video_path), "output": str(output_root),
                       "start_seconds": args.start, "requested_end_seconds": args.end,
                       "analysis_height": args.analysis_height,
                       "cut_percentile": args.cut_percentile, "min_cut_gap_seconds": args.min_cut_gap},
        "runtime": {"python_executable": sys.executable,
                    "python_version": platform.python_version(), "platform": platform.platform()},
        "input": {"path": str(video_path), "size_bytes": video_path.stat().st_size if video_path.is_file() else None},
        "probe_summary": None, "full_frame_export": {"status": "pending"},
        "candidate_detection": None, "audio": {"status": "pending"},
        "machine_preparation": {"status": "incomplete"},
        "semantic_review": {
            "status": "pending", "full_frame_review": "pending", "audio_listening": "pending",
            "reviewed_frame_count": 0, "reviewed_frame_ranges": [],
            "note": "Decoder output, source metadata, metrics, and saved images do not establish semantic analysis. Review every indexed native-resolution frame in order and listen to every source track; record actual reviewed ranges only after review.",
        },
        "external_commands": [], "warnings": [], "errors": [], "files": [],
        "evidence_claims": [
            {"id": "all_frames_required", "claim": "Every selected source frame is required, including repeated images and duplicate PTS. No temporal sampling, frame-rate reduction, deduplication, or thumbnail substitute is permitted."},
            {"id": "source_pts", "claim": "frame_index.csv maps each consecutive output image to its source presentation-order index and original integer PTS/time base; nominal FPS is never used to fill missing PTS."},
            {"id": "candidate_scope", "claim": "Candidate cuts and low-resolution numeric metrics are auxiliary only. They never select the frames that must be semantically reviewed."},
            {"id": "audio_scope", "claim": "All source audio streams are exported in full with their channel count and sample rate preserved. Mono 16 kHz files are ASR aids only; export is not listening or sound analysis."},
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
        raise EvidenceError("ffmpeg_tools_missing", "Both ffmpeg and ffprobe must be on PATH.", "Install both tools and retry; neither frame nor audio preparation may be skipped.")
    deps = load_optional_dependencies()
    manifest["runtime"].update({"numpy_version": deps.np.__version__, "pillow_version": deps.pillow_version,
                                "ffprobe_executable": ffprobe_executable, "ffmpeg_executable": ffmpeg_executable})
    probe_path = output_root / "media_probe.json"
    frame_probe_path = output_root / "frame_timestamps.json"
    if args.resume_export:
        if not args.expected_video_sha256 or len(args.expected_video_sha256) != 64:
            raise EvidenceError("resume_source_hash_required", "--resume-export needs --expected-video-sha256.",
                                "Supply the previously recorded source SHA-256.")
        digest = sha256_file(video_path)
        if digest.lower() != args.expected_video_sha256.lower():
            raise EvidenceError("resume_source_hash_mismatch", "The source video SHA-256 differs.",
                                "Do not reuse frame evidence from another source.")
        manifest["input"]["sha256"] = digest
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        if Path(probe.get("format", {}).get("filename", "")).resolve() != video_path:
            raise EvidenceError("resume_probe_source_mismatch", "Saved media probe points to a different source.",
                                "Use the matching original video and evidence directory.")
    else:
        manifest["input"]["sha256"] = sha256_file(video_path)
        probe = probe_video(video_path, ffprobe_executable, commands)
        write_json(probe_path, probe)
    registry.add(probe_path, "ffprobe_json")
    summary, stream, _has_audio = summarize_probe(probe, manifest["warnings"])
    manifest["probe_summary"] = summary
    audio_streams = [item for item in probe.get("streams", []) if item.get("codec_type") == "audio"]
    if not audio_streams:
        manifest["semantic_review"]["audio_listening"] = "not_applicable_no_audio_stream"
    if args.resume_export:
        frame_probe = json.loads(frame_probe_path.read_text(encoding="utf-8"))
    else:
        frame_probe = probe_frame_timestamps(video_path, ffprobe_executable, stream["index"], commands)
        write_json(frame_probe_path, frame_probe)
    registry.add(frame_probe_path, "complete_source_frame_pts_probe")
    records = select_frame_records(frame_probe, stream, args.start, args.end,
                                   summary.get("ffprobe_counted_frame_count"))
    source_width, source_height, analysis_width, analysis_height = set_analysis_resolution(
        records, args.analysis_height)
    if (source_width, source_height) != (int(summary["width"]), int(summary["height"])):
        raise EvidenceError("probe_frame_dimensions_mismatch", "Source frame dimensions differ from the video stream probe.",
                            "Resolve inconsistent media metadata before processing.")
    if not args.resume_export:
        write_frame_index(output_root, records, registry)
    manifest["full_frame_export"] = {"status": "incomplete", "expected_frame_count": len(records),
                                     "source_frame_count": len(frame_probe["frames"])}
    manifest["semantic_review"]["required_frame_count"] = len(records)
    manifest["semantic_review"]["required_audio_stream_count"] = len(audio_streams)
    export = (reuse_export(output_root, records, frame_probe, registry) if args.resume_export else
              export_all_frames(video_path, output_root, records, stream["index"],
                                ffmpeg_executable, deps, commands, registry))
    manifest["full_frame_export"].update(export)
    # Export the complete source audio before the optional visual cut metrics.
    # Independent semantic reviewers can begin with frame_index.csv and audio.
    audio_info, audio_errors = extract_audio(video_path, output_root, audio_streams,
                                             ffmpeg_executable, ffprobe_executable, records[0]["source_first_pts_time_s"], commands, registry)
    manifest["audio"] = audio_info
    manifest["errors"].extend(audio_errors)
    metrics = calculate_frame_metrics_stream(video_path, records, stream["index"],
                                             ffmpeg_executable, deps, commands)
    candidates, candidate_detection = mark_candidates(metrics, args.cut_percentile, args.min_cut_gap, deps.np)
    metrics_path = output_root / "frame_metrics.csv"
    write_frame_metrics(metrics_path, metrics)
    registry.add(metrics_path, "auxiliary_all_frame_change_metrics")
    candidate_manifest = build_candidate_references(metrics, candidates, records)
    candidate_detection["candidates"] = candidate_manifest
    candidate_detection["all_frames_still_require_semantic_review"] = True
    manifest["candidate_detection"] = candidate_detection
    candidates_path = output_root / "shot_candidates.csv"
    write_shot_candidates(candidates_path, candidate_manifest, args.cut_percentile,
                          candidate_detection.get("score_threshold"), args.min_cut_gap)
    registry.add(candidates_path, "auxiliary_candidate_cuts_referencing_full_frames")
    if sha256_file(video_path) != manifest["input"]["sha256"]:
        raise EvidenceError("source_changed_during_preparation", "The source video changed during preparation.",
                            "Discard mixed evidence and restart from a stable video file.")
    manifest["machine_preparation"]["status"] = "incomplete" if audio_errors else "complete"


def main(argv: Optional[Sequence[str]] = None) -> int:
    configure_console_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.resume_export and not args.expected_video_sha256:
        parser.error("--resume-export requires --expected-video-sha256")
    if args.expected_video_sha256 and not args.resume_export:
        parser.error("--expected-video-sha256 requires --resume-export")
    if args.analysis_height is not None and args.analysis_height < 1:
        parser.error("--analysis-height must be a positive pixel count")
    video_path = Path(args.video).expanduser().resolve()
    output_root = Path(args.output).expanduser().resolve()

    if output_root.exists() and not output_root.is_dir():
        print(
            f"ERROR [output_not_directory]: output exists and is not a directory: {output_root}\n"
            "Action: choose a directory path for the output argument.",
            file=sys.stderr,
        )
        return 2
    if output_root.is_dir():
        try:
            output_has_entries = next(output_root.iterdir(), None) is not None
        except OSError as exc:
            print(
                f"ERROR [output_inspect_failed]: could not inspect output directory {output_root}: {exc}\n"
                "Action: choose a readable, writable, empty output directory.",
                file=sys.stderr,
            )
            return 2
        if output_has_entries and not args.resume_export:
            print(
                f"ERROR [output_not_empty]: refusing to mix or overwrite evidence in: {output_root}\n"
                "Action: choose a new empty output directory, such as a versioned sibling folder.",
                file=sys.stderr,
            )
            return 2
    try:
        output_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(
            f"ERROR [output_create_failed]: could not create output directory {output_root}: {exc}\n"
            "Action: choose a writable output directory and rerun the command.",
            file=sys.stderr,
        )
        return 2

    manifest = build_initial_manifest(args, video_path, output_root)
    registry = OutputRegistry(output_root)
    completed_pipeline = False
    exit_code = 0
    try:
        prepare(args, manifest, registry)
        completed_pipeline = True
    except EvidenceError as exc:
        manifest["errors"].append(issue(exc.code, exc.message, exc.action))
        print(
            f"ERROR [{exc.code}]: {exc.message}\nAction: {exc.action}",
            file=sys.stderr,
        )
        exit_code = 2
    except Exception as exc:  # Keep a manifest for unexpected decoder/library failures.
        detail = traceback.format_exc()
        manifest["errors"].append(
            {
                "code": "unexpected_failure",
                "message": f"{type(exc).__name__}: {exc}",
                "action": "Inspect traceback_detail, confirm dependency versions, and rerun on a small known-good video before retrying this source.",
                "traceback_detail": detail,
            }
        )
        print(
            f"ERROR [unexpected_failure]: {type(exc).__name__}: {exc}\n"
            "Action: inspect analysis_manifest.json traceback_detail and dependency versions.",
            file=sys.stderr,
        )
        exit_code = 2

    if completed_pipeline:
        if manifest["errors"]:
            manifest["status"] = "preparation_incomplete"
            exit_code = max(exit_code, 1)
        elif manifest["warnings"]:
            manifest["status"] = "prepared_review_pending"
        else:
            manifest["status"] = "prepared_review_pending"
    else:
        manifest["status"] = "preparation_incomplete"
    manifest["completed_at_utc"] = utc_now()
    manifest["files"] = registry.entries()
    manifest["files"].append(
        {
            "path": "analysis_manifest.json",
            "role": "analysis_manifest",
            "size_bytes": None,
            "sha256": None,
            "note": "Self size/hash intentionally omitted to avoid a recursive manifest digest.",
        }
    )

    manifest_path = output_root / "analysis_manifest.json"
    try:
        write_json(manifest_path, manifest)
    except OSError as exc:
        print(
            f"ERROR [manifest_write_failed]: could not write {manifest_path}: {exc}",
            file=sys.stderr,
        )
        return 2

    if completed_pipeline:
        candidate_count = int(
            (manifest.get("candidate_detection") or {}).get(
                "min_gap_candidate_count", 0
            )
        )
        frame_count = int((manifest.get("full_frame_export") or {}).get("exported_frame_count", 0))
        print(
            f"Internal preparation: {manifest['machine_preparation']['status']}\n"
            f"Exported source frames (spatial proxy if configured): {frame_count}\n"
            f"Auxiliary transition candidates: {candidate_count}\n"
            f"Semantic full-frame review and audio listening: pending\n"
            f"Manifest: {manifest_path}"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
