#!/usr/bin/env python3
"""CI: render_video.py / make_captions.py が決定論レンダリング flag を保持しているか assert する。

決定論性 (同じ input.json + 同じフォント → 同じ output.mp4) を実 render の
md5 比較ではなく構造的に保証する。md5 比較は素材 (bg/illust/voice) が repo
に未 commit のため CI 単独では動かせない。代わりに「PIX_FMT, CRF, PRESET,
FPS が source code に hardcoded で残っている」を mechanical に確認し、
誰かが flag を緩めたら CI で fail させる。

意図: このスクリプト自体も「ものさし」の一部、baseline-sha256.txt の
sha256 監視と組み合わせて二重 gate になる。
"""
import re
import sys
from pathlib import Path

EXPECTED = [
    ("scripts/render_video.py", r'PIX_FMT\s*=\s*"yuv420p"', "pix_fmt=yuv420p"),
    ("scripts/render_video.py", r"CRF\s*=\s*23\b", "crf=23"),
    ("scripts/render_video.py", r'PRESET\s*=\s*"medium"', "preset=medium"),
    ("scripts/render_video.py", r"FASTCUT_CHUNK_SEC\s*=\s*2\.5", "fastcut_chunk=2.5"),
    ("scripts/render_video.py", r"ILLUST_H_RATIO\s*=\s*0\.22", "illust_h_ratio=0.22"),
    ("scripts/make_captions.py", r"ILLUST_H_RATIO\s*=\s*0\.22", "captions illust_h_ratio=0.22"),
    ("scripts/lint_recipe.py", r"VOICE_CAPTION_OVERLAP_WARN\s*=\s*0\.60", "T06 warn threshold"),
    ("scripts/lint_recipe.py", r"VOICE_CAPTION_OVERLAP_ERROR\s*=\s*0\.30", "T06 error threshold"),
]


def main() -> int:
    failed = 0
    for rel, pattern, label in EXPECTED:
        p = Path(rel)
        if not p.exists():
            print(f"::error file={rel}::missing")
            failed += 1
            continue
        text = p.read_text()
        if not re.search(pattern, text):
            print(f"::error file={rel}::determinism flag missing: {label} (pattern: {pattern})")
            failed += 1
        else:
            print(f"  ok: {rel} keeps {label}")
    if failed:
        print(f"::error::{failed} determinism flag(s) missing or weakened")
        return 1
    print(f"  all {len(EXPECTED)} determinism flags intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
