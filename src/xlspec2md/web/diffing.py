# -*- coding: utf-8 -*-
"""ビルド産物間の Markdown 差分（unified diff）。"""
from __future__ import annotations

import difflib
from pathlib import Path


def _md_files(root: Path) -> dict[str, Path]:
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*.md")}


def diff_builds(dir_a: Path, dir_b: Path) -> dict[str, str]:
    """両ビルドに共通する .md の相対パス → unified diff テキスト。"""
    a, b = _md_files(dir_a), _md_files(dir_b)
    out = {}
    for rel in sorted(a.keys() & b.keys()):
        ta = a[rel].read_text(encoding="utf-8", errors="replace").splitlines()
        tb = b[rel].read_text(encoding="utf-8", errors="replace").splitlines()
        out[rel] = "\n".join(difflib.unified_diff(
            ta, tb, fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm="", n=3))
    return out
