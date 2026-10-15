# -*- coding: utf-8 -*-
"""Golden test: tests/fixtures の実ファイルを変換し構造検証する。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from xlspec2md.engine import convert_file, parse_ir  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent / "golden_out"

EXPECT = {
    "基本設計書_担当者マスタ.xlsx": {"screens": 1, "items": 37, "events": 14, "dialect": "screen_book"},
    "基本設計書_検収データ取込.xlsx": {"screens": 1, "items": 1, "events": 1, "dialect": "screen_book"},
    "基本設計書_引合見積入力.xlsx": {"screens": 4, "items": 96, "events": 3, "dialect": "screen_book"},
    "01_共通仕様書.xlsx": {"sections": 20, "dialect": "common_spec"},
}


def main() -> int:
    failures = 0
    for xlsx in sorted(FIXTURES.glob("*.xlsx")):
        ir = parse_ir(str(xlsx))
        exp = EXPECT[xlsx.name]
        checks = {
            "dialect": (ir.dialect, exp["dialect"]),
            "screens": (len(ir.screens), exp.get("screens")),
            "items": (len(ir.item_defs), exp.get("items")),
            "events": (len(ir.events), exp.get("events")),
            "sections": (len(ir.sections), exp.get("sections")),
        }
        bad = {k: v for k, v in checks.items() if v[1] is not None and v[0] != v[1]}
        status = "OK " if not bad else "NG "
        if bad:
            failures += 1
        print(f"{status}{xlsx.name}: " + ", ".join(f"{k}={v[0]}" for k, v in checks.items()))
        for k, (got, want) in bad.items():
            print(f"    ✗ {k}: got {got}, want {want}")
        convert_file(str(xlsx), str(OUT / xlsx.stem))
    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FILE(S) FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
