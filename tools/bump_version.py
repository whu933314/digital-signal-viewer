#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本號 x.y.z 進位：`python3 tools/bump_version.py patch|minor|major`，或 `--set 0.9.1`。
規則（2026-10-23 使用者定）：每次小改動 z；x、y 只在使用者說「大改版」「中改版」時動（minor 把 z 歸零、major 把 y、z 歸零）。
改的地方：signal_viewer.py 的 APP_VERSION 與檔頭 docstring、README.md／README.en.md 的標題。印出 舊 → 新。"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SV = os.path.join(ROOT, "signal_viewer.py")


def current() -> str:
    with open(SV, encoding="utf-8") as f:
        for line in f:
            m = re.match(r'^APP_VERSION\s*=\s*"([^"]+)"', line)
            if m:
                return m.group(1)
    raise SystemExit("APP_VERSION not found")


def bumped(ver: str, part: str) -> str:
    nums = [int(re.match(r"\d+", p).group(0)) if re.match(r"\d+", p) else 0 for p in ver.split(".")]
    while len(nums) < 3:
        nums.append(0)
    x, y, z = nums[:3]
    if part == "major":
        return f"{x + 1}.0.0"
    if part == "minor":
        return f"{x}.{y + 1}.0"
    if part == "patch":
        return f"{x}.{y}.{z + 1}"
    raise SystemExit(f"unknown part {part!r}（patch／minor／major）")


def _sub(path: str, pattern: str, repl: str, count: int = 1) -> bool:
    with open(path, encoding="utf-8") as f:
        s = f.read()
    s2, n = re.subn(pattern, repl, s, count=count, flags=re.M)
    if n:
        with open(path, "w", encoding="utf-8") as f:
            f.write(s2)
    return bool(n)


def apply(new: str) -> None:
    ok = _sub(SV, r'^(APP_VERSION\s*=\s*)"[^"]+"', lambda m: f'{m.group(1)}"{new}"')
    if not ok:
        raise SystemExit("APP_VERSION 沒改到")
    _sub(SV, r"^(Digital Signal Viewer v)[0-9][0-9.]*( — )", lambda m: f"{m.group(1)}{new}{m.group(2)}")
    for name, pat in (("README.md", r"^(# Digital Signal Viewer v)[0-9][0-9.]*( 使用說明)"),
                      ("README.en.md", r"^(# Digital Signal Viewer v)[0-9][0-9.]*( User Guide)")):
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            _sub(p, pat, lambda m: f"{m.group(1)}{new}{m.group(2)}")


def main(argv) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("目前版本：", current())
        return 0
    old = current()
    if argv[0] == "--set":
        new = argv[1]
    elif argv[0] == "--show":
        print(old)
        return 0
    else:
        new = bumped(old, argv[0])
    apply(new)
    print(f"{old} → {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
