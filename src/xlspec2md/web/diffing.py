# -*- coding: utf-8 -*-
"""産物 .md 同士の差分（unified diff）。片側にしか存在しないファイルも差分対象に含める。"""
from __future__ import annotations

import difflib
from pathlib import Path


def _md_files(root: Path) -> dict[str, Path]:
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*.md")}


def diff_md_dirs(dir_a: Path, dir_b: Path) -> dict[str, str]:
    """両ディレクトリの .md 相対パスの「和集合」→ unified diff テキスト。

    片側にしか存在しない .md は空テキストとの差分として扱い、ヘッダに
    ファイル追加（+++）／削除（---）が現れる。
    """
    a, b = _md_files(dir_a), _md_files(dir_b)
    out = {}
    for rel in sorted(a.keys() | b.keys()):
        ta = a[rel].read_text(encoding="utf-8", errors="replace").splitlines() if rel in a else []
        tb = b[rel].read_text(encoding="utf-8", errors="replace").splitlines() if rel in b else []
        out[rel] = "\n".join(difflib.unified_diff(
            ta, tb, fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm="", n=3))
    return out
