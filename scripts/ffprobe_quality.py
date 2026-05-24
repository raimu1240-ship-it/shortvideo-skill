#!/usr/bin/env python3
"""output.mp4 を ffprobe + loudnorm analyze で検証、JSON で品質レポート出力。
shortvideo-reviewer が読む mechanical 観点の根拠ファイル。

Usage: python3 ffprobe_quality.py <output.mp4> <input.json> [--out report.json]
Exit: 0 = pass / 1 = fail acceptance_criteria / 2 = warn
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def ffprobe_json(path: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)


def loudnorm_analyze(path: Path) -> dict:
    """ffmpeg loudnorm pass1 (analyze only) で LUFS 測定。"""
    r = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af",
         "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    # ffmpeg は loudnorm json を stderr 末尾に吐く
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def evaluate(probe: dict, loud: dict, ac: dict) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warns: list[str] = []
    metrics: dict = {}

    v = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)
    duration = float(probe.get("format", {}).get("duration", 0))
    metrics["duration_sec"] = duration

    if v:
        metrics["width"] = v.get("width")
        metrics["height"] = v.get("height")
        metrics["fps_str"] = v.get("r_frame_rate")
        metrics["pix_fmt"] = v.get("pix_fmt")
        metrics["codec_v"] = v.get("codec_name")

    if a:
        metrics["codec_a"] = a.get("codec_name")
        metrics["audio_duration"] = float(a.get("duration", duration))

    if loud:
        try:
            metrics["loudnorm_I"] = float(loud.get("input_i", "nan"))
            metrics["loudnorm_TP"] = float(loud.get("input_tp", "nan"))
            metrics["loudnorm_LRA"] = float(loud.get("input_lra", "nan"))
        except (ValueError, TypeError):
            pass

    # acceptance check
    target_dur = ac.get("duration_target_sec")
    tol = ac.get("duration_tolerance_sec", 0.5)
    if target_dur is not None and abs(duration - target_dur) > tol:
        errors.append(f"[Q-dur] duration {duration:.2f}s not within "
                      f"{target_dur}±{tol}s")

    res = ac.get("resolution")
    if v and res:
        want_w, want_h = (int(x) for x in res.split("x"))
        if v["width"] != want_w or v["height"] != want_h:
            errors.append(f"[Q-res] resolution {v['width']}x{v['height']} != {res}")

    want_fps = ac.get("fps")
    if v and want_fps:
        actual = v.get("r_frame_rate", "0/1")
        if actual != f"{want_fps}/1":
            errors.append(f"[Q-fps] fps {actual} != {want_fps}/1")

    av_drift_max = ac.get("av_drift_max_sec", 0.1)
    if a:
        drift = abs(metrics.get("audio_duration", duration) - duration)
        metrics["av_drift_sec"] = drift
        if drift > av_drift_max:
            errors.append(f"[Q01] A/V drift {drift:.3f}s > {av_drift_max}s")

    lufs_range = ac.get("loudnorm_lufs_range")
    if lufs_range and "loudnorm_I" in metrics:
        lo, hi = lufs_range
        if not (lo <= metrics["loudnorm_I"] <= hi):
            warns.append(f"[A01] loudnorm I={metrics['loudnorm_I']} not in "
                         f"[{lo}, {hi}] LUFS")

    if v and v.get("pix_fmt") not in {"yuv420p", "yuvj420p"}:
        warns.append(f"[Q04] pix_fmt {v.get('pix_fmt')} not yuv420p")

    return errors, warns, metrics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("output_mp4")
    ap.add_argument("input_json")
    ap.add_argument("--out", help="write JSON report to this path")
    args = ap.parse_args()

    output = Path(args.output_mp4)
    if not output.exists():
        print(f"[ffprobe_quality] ERROR: {output} not found", file=sys.stderr)
        return 1

    probe = ffprobe_json(output)
    loud = loudnorm_analyze(output)
    ac = json.loads(Path(args.input_json).read_text(encoding="utf-8")).get(
        "acceptance_criteria", {})

    errors, warns, metrics = evaluate(probe, loud, ac)
    report = {
        "output": str(output),
        "metrics": metrics,
        "errors": errors,
        "warnings": warns,
        "acceptance_criteria": ac,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    if errors:
        return 1
    if warns:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
