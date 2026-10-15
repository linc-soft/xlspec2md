# -*- coding: utf-8 -*-
"""CLI: xlspec2md convert <file.xlsx> -o outdir"""
from __future__ import annotations

import argparse
import sys

from .engine import convert_file, parse_ir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="xlspec2md",
                                 description="基本設計書(xlsx) → Markdown/IR/mockup 変換")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert", help="1 ファイルを変換して产物を書き出す")
    c.add_argument("xlsx")
    c.add_argument("-o", "--out", default="out", help="出力ディレクトリ (default: out)")
    c.add_argument("--dialect", choices=["screen_book", "common_spec"], default=None)

    p = sub.add_parser("inspect", help="IR を stdout にダンプ（デバッグ用）")
    p.add_argument("xlsx")
    p.add_argument("--dialect", choices=["screen_book", "common_spec"], default=None)

    args = ap.parse_args(argv)
    if args.cmd == "convert":
        files = convert_file(args.xlsx, args.out, args.dialect)
        ir = parse_ir(args.xlsx, args.dialect)
        print("生成物:")
        for k, v in files.items():
            print(f"  {k}: {v}")
        print(f"警告 {len(ir.warnings)} 件" + (":" if ir.warnings else ""))
        for w in ir.warnings:
            print(f"  ⚠️ {w}")
        return 0
    if args.cmd == "inspect":
        import json
        ir = parse_ir(args.xlsx, args.dialect)
        print(json.dumps(ir.to_dict(), ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
