#!/usr/bin/env python3
"""CI: scripts/*.py を importlib で読み込んで syntax/import エラー検出。"""
import importlib.util
import sys
from pathlib import Path


def main() -> int:
    fp = Path(sys.argv[1])
    spec = importlib.util.spec_from_file_location("_check_mod", fp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print(f"  {fp}: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
