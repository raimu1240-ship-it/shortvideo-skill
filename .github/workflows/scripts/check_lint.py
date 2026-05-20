#!/usr/bin/env python3
"""CI: lint_recipe.py の JSON 出力 shape を assert する。
exit code は CI fail にしない (examples は calibration material で error 含む)。"""
import json
import sys
from pathlib import Path


def main() -> int:
    json_path = Path(sys.argv[1])
    fp = sys.argv[2] if len(sys.argv) > 2 else "<unknown>"
    d = json.loads(json_path.read_text())
    assert "errors" in d and "warnings" in d, f"lint json shape broken for {fp}"
    print(f"  {fp}: errors={len(d['errors'])} warns={len(d['warnings'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
