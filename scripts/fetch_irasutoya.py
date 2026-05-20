#!/usr/bin/env python3
"""いらすとや の PNG イラストを urllib で DL。

blogger.googleusercontent.com の s800 サイズ URL は呼び出し側
(Claude / planner skill) が WebFetch で個別記事ページから抽出して
引数で渡す前提。検索は WebFetch で Atom feed を叩く方式。

Usage: python3 fetch_irasutoya.py <png_url> <output_path>
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{url_hash(url)}.png"
        if cache_file.exists():
            out_path.write_bytes(cache_file.read_bytes())
            return {"url": url, "output": str(out_path),
                    "size_bytes": out_path.stat().st_size, "cached": True}
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    out_path.write_bytes(data)
    if cache_dir:
        (cache_dir / f"{url_hash(url)}.png").write_bytes(data)
    return {"url": url, "output": str(out_path),
            "size_bytes": len(data), "cached": False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", help="blogger.googleusercontent.com s800 PNG URL")
    ap.add_argument("output")
    ap.add_argument("--cache", help="cache dir (e.g. work/cache/irasutoya)")
    args = ap.parse_args()

    if ("blogger.googleusercontent.com" not in args.url
            and "bp.blogspot.com" not in args.url):
        print(f"[fetch_irasutoya] WARNING: URL does not look like irasutoya image: {args.url}",
              file=sys.stderr)

    cache_dir = Path(args.cache) if args.cache else None
    result = fetch(args.url, Path(args.output), cache_dir)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
