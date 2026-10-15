# -*- coding: utf-8 -*-
"""方言設定の読み込み。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

DIALECT_DIR = Path(__file__).parent / "dialects"


@lru_cache(maxsize=None)
def load_dialect(name: str) -> dict:
    path = DIALECT_DIR / f"{name}.yaml"
    if not path.exists():
        raise KeyError(f"unknown dialect: {name} (expected one of: "
                       f"{[p.stem for p in DIALECT_DIR.glob('*.yaml')]})")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def detect_dialect(wb) -> str:
    """シート名から方言を自動判定。"""
    names = set(wb.sheetnames)
    if "画面イメージ" in names and "機能仕様" in names:
        return "screen_book"
    if "共通仕様書" in names:
        return "common_spec"
    raise ValueError(f"cannot detect dialect from sheets: {sorted(names)}")
