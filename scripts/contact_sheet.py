#!/usr/bin/env python3
"""動画 or 画像群から contact sheet (tile 画像) を生成する。
海外ロケ混入の目視チェック用。Pillow で N x M grid。

Usage:
  python3 contact_sheet.py --videos a.mp4 b.mp4 c.mp4 --out sheet.jpg
  python3 contact_sheet.py --images a.jpg b.jpg ... --out sheet.jpg
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image

THUMB_W = 320  # 9:16 縦動画想定で 320x568
THUMB_H = 568
PAD = 8
COLS = 4


def extract_video_frame(video: Path, time_sec: float, out_jpg: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(time_sec), "-i", str(video),
         "-vframes", "1", "-q:v", "3",
         "-vf", f"scale={THUMB_W}:{THUMB_H}:force_original_aspect_ratio=increase,"
                f"crop={THUMB_W}:{THUMB_H}",
         str(out_jpg)],
        check=True, stderr=subprocess.DEVNULL,
    )


def tile_images(thumbs: list[Path], out_path: Path) -> tuple[int, int]:
    n = len(thumbs)
    cols = min(COLS, n)
    rows = (n + cols - 1) // cols
    sheet_w = cols * THUMB_W + (cols + 1) * PAD
    sheet_h = rows * THUMB_H + (rows + 1) * PAD
    sheet = Image.new("RGB", (sheet_w, sheet_h), (24, 24, 24))
    for i, t in enumerate(thumbs):
        img = Image.open(t).convert("RGB")
        img = img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
        x = PAD + (i % cols) * (THUMB_W + PAD)
        y = PAD + (i // cols) * (THUMB_H + PAD)
        sheet.paste(img, (x, y))
    sheet.save(out_path, quality=85)
    return cols, rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", nargs="*", default=[])
    ap.add_argument("--images", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--time", type=float, default=2.0,
                    help="frame extraction time in sec for videos")
    args = ap.parse_args()

    if not args.videos and not args.images:
        print("[contact_sheet] ERROR: --videos or --images required",
              file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        thumbs: list[Path] = []
        for i, v in enumerate(args.videos):
            t = td_path / f"thumb_v{i}.jpg"
            extract_video_frame(Path(v), args.time, t)
            thumbs.append(t)
        for i, img_path in enumerate(args.images):
            thumbs.append(Path(img_path))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        cols, rows = tile_images(thumbs, out)
    print(json.dumps({"output": str(out), "tile_count": len(thumbs),
                      "cols": cols, "rows": rows}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
