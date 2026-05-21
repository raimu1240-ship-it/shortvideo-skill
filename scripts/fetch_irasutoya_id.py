#!/usr/bin/env python3
"""いらすとや Atom feed (JSON) から検索して s800 PNG URL を返す。

Phase 4.C.1 で追加。fetch_irasutoya.py が「URL を引数」設計なので、
検索 → URL 抽出の責務をこの script に分離。

Usage:
  python3 fetch_irasutoya_id.py "<query>" [--max 6]
    → stdout JSON: {"query": "...", "title": "...", "image_url": "...", "page_url": "..."}
  python3 fetch_irasutoya_id.py "q1" "q2" "q3" --json-list
    → stdout JSON array
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from typing import Any

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36"


def search(query: str, max_results: int = 6) -> list[dict[str, Any]]:
    q = urllib.parse.quote(query)
    url = f"https://www.irasutoya.com/feeds/posts/default?q={q}&max-results={max_results}&alt=json"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    entries = data.get("feed", {}).get("entry", [])
    out = []
    for e in entries:
        title = e.get("title", {}).get("$t", "")
        link = next((l["href"] for l in e.get("link", []) if l.get("rel") == "alternate"), "")
        thumb = e.get("media$thumbnail", {}).get("url", "")
        # 2 形式の thumb URL を s800 に正規化:
        #   pattern 1: .../s72-c/thumbnail_xxx.jpg → .../s800/thumbnail_xxx.jpg
        #   pattern 2: .../<base>=s72-c              → .../<base>=s800
        img = thumb.replace("/s72-c/", "/s800/").rstrip(".")
        img = re.sub(r"=s\d+(-c)?$", "=s800", img)
        out.append({"title": title, "page_url": link, "image_url": img})
    return out


# V09 grid filter: title にこれらが含まれる entry は「複数キャラ contact sheet」の
# 可能性が高く、render すると 1 illust 内に 4-12 顔が並ぶ blocker を生む
# (Phase 4.B.1 round_2 で実観測、learning-loop.md フローで rubric V09 昇格)
GRID_KEYWORDS = ("いろいろな", "セット", "一覧", "種類", "5段階", "表情の", "色々な")


def is_grid_title(title: str) -> bool:
    return any(k in title for k in GRID_KEYWORDS)


def pick_best(results: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
    """query 単語の title 一致を優先、grid 誘発 title は deprioritize。"""
    if not results:
        return None
    words = [w for w in re.split(r"[\s　]+", query) if w]
    scored = []
    for r in results:
        title = r["title"]
        match_score = sum(1 for w in words if w in title)
        grid_penalty = -10 if is_grid_title(title) else 0
        scored.append((match_score + grid_penalty, r))
    scored.sort(key=lambda t: (-t[0],))
    return scored[0][1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="+")
    ap.add_argument("--max", type=int, default=6)
    ap.add_argument("--json-list", action="store_true")
    args = ap.parse_args()

    results: list[dict[str, Any]] = []
    for q in args.queries:
        try:
            candidates = search(q, args.max)
            best = pick_best(candidates, q)
            if best is None:
                results.append({"query": q, "error": "no results", "image_url": None})
            else:
                results.append({
                    "query": q,
                    "title": best["title"],
                    "image_url": best["image_url"],
                    "page_url": best["page_url"],
                })
        except Exception as e:
            results.append({"query": q, "error": str(e), "image_url": None})

    if args.json_list or len(args.queries) > 1:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(results[0], ensure_ascii=False, indent=2))
    return 0 if all(r.get("image_url") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
