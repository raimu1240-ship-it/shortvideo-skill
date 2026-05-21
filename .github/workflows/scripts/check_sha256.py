#!/usr/bin/env python3
"""CI: baseline-sha256.txt と現在の sha256 を比較し、差分があれば warning 表示。

block しない (意図的更新を妨げない) が、PR で必ず可視化する。
意図: 評価基準 (lint / reviewer rubric / 参考事例) が改変されていないかを継続監視する。
"""
import hashlib
import sys
from pathlib import Path


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main() -> int:
    baseline_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".github/baseline-sha256.txt")
    if not baseline_path.exists():
        print(f"::error::baseline file not found: {baseline_path}")
        return 1

    expected: dict[str, str] = {}
    for line in baseline_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            print(f"::warning::bad baseline line: {line!r}")
            continue
        expected[parts[1].strip()] = parts[0].strip()

    if not expected:
        print("::error::baseline empty")
        return 1

    changed: list[tuple[str, str, str]] = []
    missing: list[str] = []
    for rel, want in expected.items():
        p = Path(rel)
        if not p.exists():
            missing.append(rel)
            continue
        got = sha256_of(p)
        if got != want:
            changed.append((rel, want, got))

    if not changed and not missing:
        print(f"  sha256 ok: {len(expected)} files unchanged")
        return 0

    for rel in missing:
        print(f"::warning file={rel}::tracked in baseline but missing on disk")
    for rel, want, got in changed:
        print(f"::warning file={rel}::sha256 changed (was {want[:16]}…, now {got[:16]}…)")
    print(f"  sha256 drift: {len(changed)} changed, {len(missing)} missing — update .github/baseline-sha256.txt after review")
    return 0  # do not fail CI; surface as warning only


if __name__ == "__main__":
    sys.exit(main())
