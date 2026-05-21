#!/usr/bin/env python3
"""Mixkit free stock video から直 mp4 URL を確定抽出する。

Pexels が 0 hit / Cloudflare blocked / 海外混入過多の時に fallback
として使う (詳細は stock-sources.md 参照)。

Mixkit は Pexels と違って HTML 静的にビデオ URL を埋め込んでいる
ため、urllib + 正規表現で確実に抽出できる (Cloudflare BOT 対策なし)。

URL patterns (実走確認):
- search page : https://mixkit.co/free-stock-video/<query>/
- video page  : https://mixkit.co/free-stock-video/<slug>-<id>/
- direct mp4  : https://assets.mixkit.co/videos/<id>/<id>-<height>.mp4
                (height = 720 / 360、1080 は一部 video のみ)

Usage:
  python3 fetch_mixkit_id.py "<query>"
    → stdout JSON: {"query": "...", "page_id": "<id>", "best_url": "...", "all_urls": [...]}
  python3 fetch_mixkit_id.py "q1" "q2" --json-list
    → stdout JSON array
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from typing import Any

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}
PAGE_URL_RE = re.compile(r"/free-stock-video/([a-z0-9-]+)-(\d+)/")
MP4_RE = re.compile(r"https://assets\.mixkit\.co/videos/(\d+)/\1-(\d+)\.mp4")


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def search_videos(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Mixkit 検索ページ → video page URL のリスト (slug + id)。

    query は space → hyphen 連結が必要 (Mixkit URL 仕様、実機検証で確認)。
    URL-encode ではなく lowercase + hyphen にする。
    """
    q = "-".join(query.lower().split())
    html = _get(f"https://mixkit.co/free-stock-video/{q}/")
    seen: dict[str, dict[str, str]] = {}
    for m in PAGE_URL_RE.finditer(html):
        slug, vid = m.group(1), m.group(2)
        if vid not in seen:
            seen[vid] = {
                "id": vid,
                "slug": slug,
                "page_url": f"https://mixkit.co{m.group(0)}",
            }
        if len(seen) >= max_results:
            break
    return list(seen.values())


def extract_mp4_urls(video_id: str) -> list[tuple[str, int]]:
    """video page から (mp4_url, height) のリスト。height 降順。"""
    # slug を介さず id だけで video page を試す前に search で得た slug が必要だが、
    # 個別 page URL pattern が `slug-id` なので search 経由で page_url 渡される設計
    # ↑ extract は page_url を直接受ける版を別関数化する
    raise NotImplementedError("use extract_mp4_urls_from_page")


def extract_mp4_urls_from_page(page_url: str, video_id: str) -> list[tuple[str, int]]:
    """個別 video page → (mp4_url, height) リスト、height 降順。"""
    html = _get(page_url)
    seen: set[str] = set()
    out: list[tuple[str, int]] = []
    for m in MP4_RE.finditer(html):
        url = m.group(0)
        height = int(m.group(2))
        if m.group(1) != video_id:
            continue  # 関連動画の URL を除外
        if url in seen:
            continue
        seen.add(url)
        out.append((url, height))
    out.sort(key=lambda t: -t[1])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="+")
    ap.add_argument("--max", type=int, default=5)
    ap.add_argument("--json-list", action="store_true")
    args = ap.parse_args()

    results: list[dict[str, Any]] = []
    for q in args.queries:
        try:
            candidates = search_videos(q, args.max)
            if not candidates:
                results.append({"query": q, "error": "no search results",
                                "best_url": None, "all_urls": []})
                continue
            top = candidates[0]
            urls = extract_mp4_urls_from_page(top["page_url"], top["id"])
            best = urls[0][0] if urls else None
            results.append({
                "query": q,
                "page_id": top["id"],
                "page_url": top["page_url"],
                "slug": top["slug"],
                "best_url": best,
                "all_urls": [u for u, _ in urls],
                "count": len(urls),
            })
        except Exception as e:
            results.append({"query": q, "error": str(e), "best_url": None,
                            "all_urls": []})

    if args.json_list or len(args.queries) > 1:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(results[0], ensure_ascii=False, indent=2))
    return 0 if all(r.get("best_url") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
