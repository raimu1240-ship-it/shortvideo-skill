#!/usr/bin/env python3
"""Pillow でテロップ PNG を事前生成する。Homebrew ffmpeg は drawtext 非搭載のため
overlay 方式が必要。生成物は input.json の解像度に合わせた透過 PNG。

Usage: python3 make_captions.py <input.json> <output_dir>

input.json の `segments[].captions` をループして PNG を吐く。
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Y-coordinate table for letterbox-positioned captions.
# justification: brand-name v5 で実測したテロップ Y 座標。
# main: 映像領域下の暗幕、sub: フッター帯の上
Y_TABLE = {
    "720x1280":  {"main_y": 820, "sub_y": 1020, "main_size": 52, "sub_size": 44},
    "1080x1920": {"main_y": 1230, "sub_y": 1530, "main_size": 78, "sub_size": 66},
}


def resolve_font() -> str:
    """fc-match で日本語太字を解決。フォールバック多段。"""
    candidates = [
        "Hiragino Sans W7",
        "Hiragino Kaku Gothic ProN W6",
        "Noto Sans CJK JP Bold",
        "Noto Sans JP Bold",
    ]
    for name in candidates:
        try:
            r = subprocess.run(["fc-match", "-f", "%{file}", name],
                               capture_output=True, text=True, timeout=5)
            path = r.stdout.strip()
            if path and Path(path).exists():
                return path
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    # ultimate fallback
    fallback = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
    if Path(fallback).exists():
        return fallback
    raise FileNotFoundError("no Japanese bold font found")


def make_caption_png(out_path: Path, lines: list[str], y_top: int,
                     font_size: int, font_path: str, w: int, h: int) -> None:
    """白文字 + 黒シャドー + 細 stroke の下部メインテロップ。"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    font = ImageFont.truetype(font_path, font_size)
    y = y_top
    line_h = int(font_size * 1.35)
    for line in lines:
        bbox = sdraw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        sdraw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 180))
        y += line_h
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))
    img = Image.alpha_composite(img, shadow)
    draw = ImageDraw.Draw(img)
    y = y_top
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255),
                  stroke_width=2, stroke_fill=(0, 0, 0, 200))
        y += line_h
    img.save(out_path)


def make_bubble_png(out_path: Path, text: str, y_center: int,
                    font_path: str, w: int, h: int) -> None:
    """いらすとや の下に置く半透明グレー角丸吹き出し。"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fs = max(28, int(w / 22))
    font = ImageFont.truetype(font_path, fs)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 26, 14
    bx = (w - tw) // 2 - pad_x
    by = y_center - (th // 2) - pad_y
    bx2 = bx + tw + pad_x * 2
    by2 = by + th + pad_y * 2
    draw.rounded_rectangle([bx, by, bx2, by2], radius=16,
                            fill=(245, 245, 245, 230))
    draw.text(((w - tw) // 2, by + pad_y - 2), text, font=font,
              fill=(40, 40, 40, 255))
    img.save(out_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json")
    ap.add_argument("output_dir")
    args = ap.parse_args()

    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    res = data["resolution"]
    if res not in Y_TABLE:
        print(f"[make_captions] ERROR: resolution {res} not in Y_TABLE",
              file=sys.stderr)
        return 1
    w, h = (int(x) for x in res.split("x"))
    yconf = Y_TABLE[res]
    font_path = resolve_font()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for seg in data["scenario"]["segments"]:
        sid = seg["id"]
        if seg.get("caption_main"):
            lines = (seg["caption_main"] if isinstance(seg["caption_main"], list)
                     else [seg["caption_main"]])
            p = out_dir / f"cap_main_{sid}.png"
            make_caption_png(p, lines, yconf["main_y"], yconf["main_size"],
                             font_path, w, h)
            written.append(str(p))
        if seg.get("bubble_text"):
            p = out_dir / f"bubble_{sid}.png"
            # bubble の中心 Y は main の上 (illust と重ねる位置)
            bubble_y = yconf["main_y"] - int(font_size_default(h) * 1.6)
            make_bubble_png(p, seg["bubble_text"], bubble_y,
                            font_path, w, h)
            written.append(str(p))
    print(json.dumps({"written": written, "font": font_path}))
    return 0


def font_size_default(h: int) -> int:
    return max(28, int(h / 38))


if __name__ == "__main__":
    sys.exit(main())
