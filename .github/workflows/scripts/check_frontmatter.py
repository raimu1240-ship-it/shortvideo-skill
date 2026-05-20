#!/usr/bin/env python3
"""CI: SKILL.md / agent / command の frontmatter 構造 + 必須キー (name,
description) の存在を assert する。"""
import re
import sys
from pathlib import Path


def main() -> int:
    fp = Path(sys.argv[1])
    text = fp.read_text()
    if not text.startswith("---"):
        print(f"::error file={fp}::missing frontmatter")
        return 1
    parts = text.split("---", 2)
    if len(parts) < 3:
        print(f"::error file={fp}::malformed frontmatter")
        return 1
    fm_body = parts[1]
    for key in ("name", "description"):
        if not re.search(rf"^{key}\s*:", fm_body, re.MULTILINE):
            print(f"::error file={fp}::frontmatter missing '{key}'")
            return 1
    print(f"  {fp}: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
