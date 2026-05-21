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
# justification: ユーザー提示の正解レイアウト (Image #1, 2026-05-20) に合わせ、
# illust=h*0.22 / illust_top=h*0.32 と整合させて bubble は illust 真下、
# main caption は画面中央〜やや下に置く。明朝細字 + stroke 無しで柔らかく。
ILLUST_H_RATIO = 0.22
ILLUST_TOP_Y_RATIO = 0.32
Y_TABLE = {
    "720x1280":  {"main_y": 810, "sub_y": 1080, "main_size": 44, "sub_size": 38},
    "1080x1920": {"main_y": 1215, "sub_y": 1620, "main_size": 66, "sub_size": 56},
}


def resolve_font() -> str:
    """フォント解決順:
    1. repo bundle (fonts/NotoSansCJKjp-Regular.otf) — v5 と同じ font で再現性確保
    2. fc-match で Noto Sans CJK JP / Noto Sans JP
    3. システム明朝 fallback

    justification: v5 で実績ある NotoSansCJKjp-Regular を最優先にして全社員で
    同一の見た目を担保する。Mac には標準で入っていないので bundle 必須。"""
    bundled = (Path(__file__).resolve().parent.parent / "fonts"
               / "NotoSansCJKjp-Regular.otf")
    if bundled.exists():
        return str(bundled)
    candidates = [
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "Hiragino Sans W4",
        "Hiragino Mincho ProN W3",
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
    raise FileNotFoundError("no usable Japanese font; bundle fonts/NotoSansCJKjp-Regular.otf")


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
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.alpha_composite(img, shadow)
    draw = ImageDraw.Draw(img)
    y = y_top
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        # 明朝細字なので stroke を打つと AI 臭。白文字 + 影だけで成立させる
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_h
    img.save(out_path)


def make_bubble_png(out_path: Path, text: str, y_center: int,
                    font_path: str, w: int, h: int) -> None:
    """いらすとや の下に置く半透明グレー角丸吹き出し。

    テキストは枠の上下左右中央に anchor="mm" で配置する。
    旧実装の `draw.text((..., by + pad_y - 2), ...)` は Pillow `textbbox` の
    bbox[1] オフセット (ascent 上の余白) を補正しておらず、フォントによって
    枠内で文字が下寄りに表示されるバグがあった (test-001 Round 4 で fix)。"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fs = max(28, int(w / 22))
    font = ImageFont.truetype(font_path, fs)
    bbox = draw.textbbox((0, 0), text, font=font, anchor="lt")
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 26, 14
    bx = (w - tw) // 2 - pad_x
    by = y_center - (th // 2) - pad_y
    bx2 = bx + tw + pad_x * 2
    by2 = by + th + pad_y * 2
    draw.rounded_rectangle([bx, by, bx2, by2], radius=16,
                            fill=(245, 245, 245, 230))
    cy = (by + by2) // 2
    draw.text((w // 2, cy), text, font=font, anchor="mm",
              fill=(40, 40, 40, 255))
    img.save(out_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json")
    ap.add_argument("output_dir")
    ap.add_argument("--font",
                    help="override font (absolute path to .ttc/.otf/.ttf)")
    args = ap.parse_args()

    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    res = data["resolution"]
    if res not in Y_TABLE:
        print(f"[make_captions] ERROR: resolution {res} not in Y_TABLE",
              file=sys.stderr)
        return 1
    w, h = (int(x) for x in res.split("x"))
    yconf = Y_TABLE[res]
    font_path = args.font if args.font else resolve_font()

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
            # bubble は illust の真下に密着 (illust_top + illust_h + 30px)
            illust_bottom = int(h * ILLUST_TOP_Y_RATIO) + int(h * ILLUST_H_RATIO)
            bubble_y = illust_bottom + 30
            make_bubble_png(p, seg["bubble_text"], bubble_y,
                            font_path, w, h)
            written.append(str(p))
    print(json.dumps({"written": written, "font": font_path}))
    return 0


def font_size_default(h: int) -> int:
    return max(28, int(h / 38))


if __name__ == "__main__":
    sys.exit(main())
