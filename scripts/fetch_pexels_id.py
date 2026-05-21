#!/usr/bin/env python3
"""Pexels 個別 video page から直 mp4 URL を確定抽出する。

fetch_pexels.py が「URL を引数」設計なので、URL 抽出の責務をこの
script に分離している。WebFetch 経由は HTML → summary 変換で
50% 取りこぼしが出たため、urllib + 正規表現で page HTML を直接
grep する確定経路にしてある。

Usage:
  python3 fetch_pexels_id.py <video_id> [--prefer vertical|landscape]
    → stdout に JSON: {"id": ..., "best_url": "...", "all_urls": [...]}
  python3 fetch_pexels_id.py <id_1> <id_2> ... --json-list
    → stdout に JSON array
"""
import argparse
import json
import re
import sys
import urllib.request
from typing import Any

# Pexels の新しい video ID は Cloudflare BOT 対策で 403 を返すため、
# 正規ブラウザのフルヘッダ一式を送る (実機検証で確認)。
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
URL_RE = re.compile(r"https://videos\.pexels\.com/video-files/(\d+)/[^\"'\s]+?\.mp4")
DIM_RE = re.compile(r"_(\d+)_(\d+)_(\d+)fps\.mp4$")


def parse_dim(url: str) -> tuple[int, int, int] | None:
    m = DIM_RE.search(url)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def pick_best(urls: list[str], prefer: str = "vertical") -> str | None:
    """9:16 縦動画優先、なければ 16:9 横、それもなければ任意。同 aspect 内では中解像度を選ぶ。"""
    if not urls:
        return None
    scored = []
    for u in urls:
        dim = parse_dim(u)
        if dim is None:
            scored.append((u, 0, 0, 0))
            continue
        w, h, fps = dim
        is_vertical = h > w
        is_landscape = w > h
        if prefer == "vertical":
            aspect_bonus = 2 if is_vertical else (1 if is_landscape else 0)
        else:
            aspect_bonus = 2 if is_landscape else (1 if is_vertical else 0)
        # 中解像度: 1080-2560 を優遇
        long_edge = max(w, h)
        if 1080 <= long_edge <= 2560:
            res_bonus = 2
        elif long_edge < 1080:
            res_bonus = 0
        else:
            res_bonus = 1
        scored.append((u, aspect_bonus, res_bonus, long_edge))
    scored.sort(key=lambda t: (-t[1], -t[2], t[3]))
    return scored[0][0]


def extract_urls(video_id: int) -> list[str]:
    """Page video_id のみの URL を返す。関連動画の URL は除外。"""
    page_url = f"https://www.pexels.com/ja-jp/video/{video_id}/"
    req = urllib.request.Request(page_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")
    seen: set[str] = set()
    out: list[str] = []
    vid_str = str(video_id)
    for m in URL_RE.finditer(html):
        url = m.group(0)
        # URL path の最初の ID が page video_id と一致するもののみ採用
        # (videos.pexels.com/video-files/<video_id>/<file_id>_...)
        if m.group(1) != vid_str:
            continue
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+", type=int, help="Pexels video IDs")
    ap.add_argument("--prefer", choices=["vertical", "landscape"], default="vertical")
    ap.add_argument("--json-list", action="store_true", help="output JSON array for many IDs")
    args = ap.parse_args()

    results: list[dict[str, Any]] = []
    for vid in args.ids:
        try:
            urls = extract_urls(vid)
            best = pick_best(urls, args.prefer)
            results.append({
                "id": vid,
                "best_url": best,
                "all_urls": urls,
                "count": len(urls),
            })
        except Exception as e:
            results.append({"id": vid, "error": str(e), "best_url": None, "all_urls": [], "count": 0})

    if args.json_list or len(args.ids) > 1:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(results[0], ensure_ascii=False, indent=2))
    return 0 if all(r.get("best_url") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
