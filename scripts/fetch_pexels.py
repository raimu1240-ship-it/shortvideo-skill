#!/usr/bin/env python3
"""Pexels の動画 mp4 直リンクを urllib で DL する。

Pexels API key 不要。URL は呼び出し側 (Claude / planner skill) が
WebFetch で個別ページから抽出して引数で渡す前提。
これにより curl 権限不要、決定論的、cache 可能。

Usage: python3 fetch_pexels.py <mp4_url> <output_path>
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36"


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def fetch(url: str, out_path: Path, cache_dir: Path | None = None) -> dict:
    """URL を DL。cache_dir があれば url_hash で cache を利用。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{url_hash(url)}.mp4"
        if cache_file.exists():
            out_path.write_bytes(cache_file.read_bytes())
            return {"url": url, "output": str(out_path),
                    "size_bytes": out_path.stat().st_size, "cached": True}
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    out_path.write_bytes(data)
    if cache_dir:
        (cache_dir / f"{url_hash(url)}.mp4").write_bytes(data)
    return {"url": url, "output": str(out_path),
            "size_bytes": len(data), "cached": False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", help="direct mp4 URL from Pexels videos.pexels.com/video-files/...")
    ap.add_argument("output", help="output mp4 path")
    ap.add_argument("--cache", help="cache directory (e.g. work/cache/pexels)")
    args = ap.parse_args()

    if "videos.pexels.com" not in args.url and "pexels.com" not in args.url:
        print(f"[fetch_pexels] WARNING: URL does not look like Pexels: {args.url}",
              file=sys.stderr)

    cache_dir = Path(args.cache) if args.cache else None
    result = fetch(args.url, Path(args.output), cache_dir)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
