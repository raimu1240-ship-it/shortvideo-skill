#!/usr/bin/env python3
"""input.json から決定論的に縦動画を 1 パス合成する。

前提: scripts/make_captions.py で work/captions/ に PNG が事前生成済み、
scripts/tts_elevenlabs.py で work/voice.mp3 が用意済み、
scripts/fetch_pexels.py / fetch_irasutoya.py で work/assets/ に素材 DL 済み。

Usage: python3 render_video.py <input.json> <work_dir> <output.mp4>
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

# justification: 公式 yuv420p / crf 23 / preset medium で
# Mac/Linux/WSL で再現性ある H.264 出力。fps は input.json で固定。
PIX_FMT = "yuv420p"
CRF = 23
PRESET = "medium"


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(str(c) for c in cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True)


def prepare_segment(seg: dict, work_dir: Path, w: int, h: int, fps: int) -> Path:
    """1 セグメント分の背景動画を target 解像度に整形して返す。"""
    sid = seg["id"]
    src = work_dir / "assets" / f"bg_{sid}.mp4"
    out = work_dir / "stages" / f"scene_{sid}_bg.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = seg["duration_sec"]
    # 縦長 (高さ >= 幅) ならそのまま scale、横長は scale+crop で中央寄せ
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
          f"crop={w}:{h},"
          f"eq=brightness=-0.05:saturation=0.92")
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-t", str(dur),
        "-vf", vf,
        "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
        "-pix_fmt", PIX_FMT, "-r", str(fps), "-an",
        str(out),
    ])
    return out


def overlay_segment(seg: dict, bg: Path, work_dir: Path, captions_dir: Path,
                    assets_dir: Path, w: int, h: int) -> Path:
    """1 セグメント分の overlay (illust + bubble + caption + scrim) を焼く。"""
    sid = seg["id"]
    out = work_dir / "stages" / f"scene_{sid}.mp4"
    illust = (assets_dir / f"illust_{sid}.png"
              if seg.get("illust") or seg.get("illust_query") else None)
    bubble = captions_dir / f"bubble_{sid}.png"
    cap_main = captions_dir / f"cap_main_{sid}.png"

    # build filter_complex chain
    inputs: list[str] = ["-i", str(bg)]
    chain_parts: list[str] = []
    prev = "[0:v]"
    next_idx = 1

    # ダーカン (scrim) を内部で生成しオーバーレイ
    chain_parts.append(
        f"color=c=black@0.35:s={w}x{h}:d={seg['duration_sec']}[scrim]"
    )
    chain_parts.append(f"{prev}[scrim]overlay=0:0[v_scrim]")
    prev = "[v_scrim]"

    if illust and illust.exists():
        inputs += ["-i", str(illust)]
        chain_parts.append(
            f"{prev}[{next_idx}:v]"
            f"overlay=(W-w)/2:{int(h * 0.30)}[v_il]"
        )
        prev = "[v_il]"
        next_idx += 1

    if bubble.exists():
        inputs += ["-i", str(bubble)]
        chain_parts.append(f"{prev}[{next_idx}:v]overlay=0:0[v_bb]")
        prev = "[v_bb]"
        next_idx += 1

    if cap_main.exists():
        inputs += ["-i", str(cap_main)]
        chain_parts.append(f"{prev}[{next_idx}:v]overlay=0:0[v_cap]")
        prev = "[v_cap]"
        next_idx += 1

    fc = ";".join(chain_parts)
    last_label = prev.strip("[]")

    run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", fc,
        "-map", f"[{last_label}]",
        "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
        "-pix_fmt", PIX_FMT,
        str(out),
    ])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json")
    ap.add_argument("work_dir")
    ap.add_argument("output_mp4")
    args = ap.parse_args()

    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    w, h = (int(x) for x in data["resolution"].split("x"))
    fps = int(data.get("fps", 24))
    work = Path(args.work_dir)
    captions_dir = work / "captions"
    assets_dir = work / "assets"
    work.mkdir(parents=True, exist_ok=True)

    segments = data["scenario"]["segments"]
    if not segments:
        print("[render] ERROR: no segments", file=sys.stderr)
        return 1

    # Stage A: 各シーンの bg trim+scale
    scene_videos = []
    for seg in segments:
        bg = prepare_segment(seg, work, w, h, fps)
        scene_v = overlay_segment(seg, bg, work, captions_dir, assets_dir, w, h)
        scene_videos.append(scene_v)

    # Stage B: concat
    concat_list = work / "concat.txt"
    # solve: concat demuxer は concat.txt のあるディレクトリ基準でパス解決するため、
    # write 側で絶対パスに揃える。相対パスのまま書くと二重パスで開けなくなる。
    concat_list.write_text("\n".join(f"file '{p.resolve()}'"
                                     for p in scene_videos) + "\n")
    bg_concat = work / "video_only.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(bg_concat),
    ])

    # Stage C: voice mux
    voice = work / "voice.mp3"
    if voice.exists():
        run([
            "ffmpeg", "-y",
            "-i", str(bg_concat),
            "-i", str(voice),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            args.output_mp4,
        ])
    else:
        # solve: voice 無ければ video_only をそのまま rename (無音 mp4)
        run([
            "ffmpeg", "-y", "-i", str(bg_concat),
            "-c", "copy", args.output_mp4,
        ])

    out_size = Path(args.output_mp4).stat().st_size
    print(json.dumps({"output": args.output_mp4, "size_bytes": out_size,
                      "segments": len(segments)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
