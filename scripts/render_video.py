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

# justification: ユーザー提示の正解レイアウト (Image #1) に合わせ、illust は
# 動画高さの 22% に縮小 + 上端 32% に配置。bubble と caption は make_captions.py
# 側で同じ ILLUST_*_RATIO を使って真下に置く。両モジュールで定数共有しないため
# ここで揃える必要がある — 変える時は make_captions.py も合わせて変える。
ILLUST_H_RATIO = 0.22
ILLUST_TOP_Y_RATIO = 0.32

# justification: v5 build script の "Two-line captions get multiple background
# changes while the caption stays on-screen" を移植。同じ src を 2-3 ヶ所から
# 切り出して concat することで「同じ素材でも視覚的変化」を出す。本番運用で
# bg が静止しすぎていると視聴維持率が落ちる。2.5 秒目安で chunk 分割。
FASTCUT_CHUNK_SEC = 2.5


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(str(c) for c in cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True)


def _src_duration(path: Path) -> float:
    """ffprobe で src の duration を返す。"""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def prepare_segment(seg: dict, work_dir: Path, w: int, h: int, fps: int) -> Path:
    """1 セグメント分の背景動画を fastcut (2-3 秒ごとに切替) で生成する。
    同じ src の異なる time offset から chunk を切り出して concat することで
    視覚的変化を出す。src が短ければ可能な範囲で offset を分散。"""
    sid = seg["id"]
    src = work_dir / "assets" / f"bg_{sid}.mp4"
    out = work_dir / "stages" / f"scene_{sid}_bg.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = float(seg["duration_sec"])
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
          f"crop={w}:{h},"
          f"eq=brightness=-0.05:saturation=0.92")

    # chunk 数: 2.5 秒目安で割る、最低 2 chunks
    n_chunks = max(2, round(dur / FASTCUT_CHUNK_SEC))
    chunk_dur = dur / n_chunks

    # src 内の offset を均等分散。src が短ければ available=0 で全 chunk 同一 offset。
    try:
        src_dur = _src_duration(src)
    except Exception:
        src_dur = dur  # 取れなければ chunk_dur ぴったり前提
    available = max(0.0, src_dur - chunk_dur)
    if available <= 0.01 or n_chunks == 1:
        offsets = [0.0] * n_chunks
    else:
        offsets = [i * (available / (n_chunks - 1)) for i in range(n_chunks)]

    chunk_files = []
    for i, offset in enumerate(offsets):
        chunk_out = work_dir / "stages" / f"scene_{sid}_chunk{i}.mp4"
        run([
            "ffmpeg", "-y", "-ss", f"{offset:.3f}", "-i", str(src),
            "-t", f"{chunk_dur:.3f}",
            "-vf", vf,
            "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
            "-pix_fmt", PIX_FMT, "-r", str(fps), "-an",
            str(chunk_out),
        ])
        chunk_files.append(chunk_out)

    # chunks を concat (絶対パス指定で demuxer 二重解決バグ回避)
    concat_list = work_dir / "stages" / f"scene_{sid}_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in chunk_files) + "\n"
    )
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(out),
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

    # 弱い scrim — 背景の色味は活かしつつ caption 可読性だけ確保。
    # justification: 強い scrim (0.35) は背景の質感を殺すためユーザー指摘の正解では
    # 公園の色彩が活きている。0.15 で薄めに敷くだけにする。
    chain_parts.append(
        f"color=c=black@0.15:s={w}x{h}:d={seg['duration_sec']}[scrim]"
    )
    chain_parts.append(f"{prev}[scrim]overlay=0:0[v_scrim]")
    prev = "[v_scrim]"

    if illust and illust.exists():
        inputs += ["-i", str(illust)]
        target_h = int(h * ILLUST_H_RATIO)
        top_y = int(h * ILLUST_TOP_Y_RATIO)
        chain_parts.append(
            f"[{next_idx}:v]scale=-1:{target_h}[il_{sid}]"
        )
        chain_parts.append(
            f"{prev}[il_{sid}]overlay=(W-w)/2:{top_y}[v_il]"
        )
        prev = "[v_il]"
        next_idx += 1

    if bubble.exists():
        inputs += ["-i", str(bubble)]
        # bubble は sub_delay 秒後にフェードイン (= main caption と同時表示を避ける)
        # justification: ffmpeg overlay filter は timeline 'enable' 公式サポート
        # (`ffmpeg -h filter=overlay` で "support for timeline through 'enable'")。
        # sub_delay=0 のときは enable 無しで先頭から表示。
        sub_delay = float(seg.get("sub_delay", 0) or 0)
        enable_clause = f":enable='gte(t,{sub_delay})'" if sub_delay > 0 else ""
        chain_parts.append(
            f"{prev}[{next_idx}:v]overlay=0:0{enable_clause}[v_bb]"
        )
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
    voices_dir = work / "voices"
    work.mkdir(parents=True, exist_ok=True)

    segments = data["scenario"]["segments"]
    if not segments:
        print("[render] ERROR: no segments", file=sys.stderr)
        return 1

    # per-segment TTS が走っていれば voice 実測 duration で segment.duration_sec を
    # 上書きして A/V を時間軸で揃える。justification: voice 6.89s / segment 5s の
    # ような時間軸ズレを根本解消する。durations.json が無ければ legacy 動作。
    durations_json = voices_dir / "durations.json"
    per_segment_voice = durations_json.exists()
    if per_segment_voice:
        durations = json.loads(durations_json.read_text(encoding="utf-8"))
        for seg in segments:
            if seg["id"] in durations:
                seg["duration_sec"] = float(durations[seg["id"]])
        print(f"[render] per-segment voice mode: durations={durations}",
              file=sys.stderr)

    # Stage A: 各シーンの bg fastcut + overlay
    scene_videos = []
    for seg in segments:
        bg = prepare_segment(seg, work, w, h, fps)
        scene_v = overlay_segment(seg, bg, work, captions_dir, assets_dir, w, h)
        scene_videos.append(scene_v)

    # Stage B: per-segment voice mux (or single mux fallback)
    if per_segment_voice:
        # 各 scene に対応する voice をそれぞれ mux してから concat
        av_scenes = []
        for seg, scene_v in zip(segments, scene_videos):
            voice_mp3 = voices_dir / f"voice_{seg['id']}.mp3"
            av_out = work / "stages" / f"scene_{seg['id']}_av.mp4"
            if voice_mp3.exists():
                run([
                    "ffmpeg", "-y",
                    "-i", str(scene_v),
                    "-i", str(voice_mp3),
                    "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(av_out),
                ])
            else:
                # voice 無い segment は無音 padding (segment.duration_sec ぶん)
                run([
                    "ffmpeg", "-y",
                    "-i", str(scene_v),
                    "-f", "lavfi",
                    "-i", f"anullsrc=channel_layout=mono:sample_rate=44100",
                    "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    str(av_out),
                ])
            av_scenes.append(av_out)
        # concat (全 scene が同じ codec/sample_rate なので -c copy OK)
        concat_list = work / "concat.txt"
        concat_list.write_text("\n".join(f"file '{p.resolve()}'"
                                         for p in av_scenes) + "\n")
        run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list), "-c", "copy", args.output_mp4,
        ])
    else:
        # legacy: video のみ concat → 全体 voice.mp3 を mux
        concat_list = work / "concat.txt"
        concat_list.write_text("\n".join(f"file '{p.resolve()}'"
                                         for p in scene_videos) + "\n")
        bg_concat = work / "video_only.mp4"
        run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list), "-c", "copy", str(bg_concat),
        ])
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
            run([
                "ffmpeg", "-y", "-i", str(bg_concat),
                "-c", "copy", args.output_mp4,
            ])

    out_size = Path(args.output_mp4).stat().st_size
    print(json.dumps({"output": args.output_mp4, "size_bytes": out_size,
                      "segments": len(segments),
                      "per_segment_voice": per_segment_voice}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
