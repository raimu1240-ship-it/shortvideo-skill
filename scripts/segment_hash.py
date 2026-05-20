#!/usr/bin/env python3
"""input.json の各 segment を hash 化して、変更検知 + cache 再利用に使う。

orchestrator (shortvideo-loop) は前ラウンドの hash と比較し、
変わっていない segment では fetch / TTS / caption 生成を skip して
work/cache/<segment_hash>/ から再利用する。

Usage:
    python3 segment_hash.py <input.json>            # 全 segment の hash を JSON 出力
    python3 segment_hash.py <input.json> --diff <prev.json>  # 前回比 changed/unchanged

Hash 入力フィールド (これらが同じなら cache 再利用可):
    - bg_query
    - illust_query
    - voice_text
    - duration_sec
    - caption_main (overlay positioning にも効くので含める)
    - sub_delay
    - bubble_text
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

# justification: これら 7 フィールドが asset fetch / TTS / overlay 結果を一意に決める。
# resolution と fps は global 設定なので segment hash には含めない (変わったら全 segment 無効化される)。
HASH_FIELDS = (
    "bg_query",
    "illust_query",
    "voice_text",
    "duration_sec",
    "caption_main",
    "sub_delay",
    "bubble_text",
)


def segment_hash(seg: dict) -> str:
    canonical = {k: seg.get(k) for k in HASH_FIELDS}
    blob = json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def all_hashes(data: dict) -> dict:
    return {seg["id"]: segment_hash(seg)
            for seg in data.get("scenario", {}).get("segments", [])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json")
    ap.add_argument("--diff", help="previous hash JSON to compare against")
    args = ap.parse_args()

    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    hashes = all_hashes(data)

    if not args.diff:
        print(json.dumps(hashes, ensure_ascii=False, indent=2))
        return 0

    prev = json.loads(Path(args.diff).read_text(encoding="utf-8"))
    changed = [sid for sid, h in hashes.items() if prev.get(sid) != h]
    unchanged = [sid for sid, h in hashes.items() if prev.get(sid) == h]
    removed = [sid for sid in prev if sid not in hashes]
    print(json.dumps({
        "changed": changed,
        "unchanged": unchanged,
        "removed": removed,
        "current": hashes,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
