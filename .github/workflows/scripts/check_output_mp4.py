#!/usr/bin/env python3
"""CI: examples/*/output.mp4 が ffprobe で読めて duration > 1s を assert する。"""
import subprocess
import sys
from pathlib import Path


def main() -> int:
    fp = Path(sys.argv[1])
    if not fp.exists():
        print(f"::error file={fp}::missing")
        return 1
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(fp)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"::error file={fp}::ffprobe failed: {r.stderr.strip()}")
        return 1
    dur = float(r.stdout.strip())
    if dur < 1.0:
        print(f"::error file={fp}::too short: {dur}s")
        return 1
    print(f"  {fp}: dur={dur:.2f}s ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
