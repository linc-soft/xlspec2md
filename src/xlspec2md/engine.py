# -*- coding: utf-8 -*-
"""変換エンジン: xlsx → IR → 各種产物。"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import detect_dialect, load_dialect
from .dialects.common_spec import parse_common_spec
from .dialects.screen_book import parse_screen_book
from .media import export_media
from .models import DocumentIR
from .render.markdown import render_markdown
from .render.mockup import render_mockup
from .wbutil import load_wb


def parse_ir(xlsx_path: str, dialect: str | None = None) -> DocumentIR:
    wb = load_wb(xlsx_path)
    dialect = dialect or detect_dialect(wb)
    cfg = load_dialect(dialect)
    if dialect == "screen_book":
        return parse_screen_book(wb, cfg, xlsx_path)
    if dialect == "common_spec":
        return parse_common_spec(wb, cfg)
    raise ValueError(f"unsupported dialect: {dialect}")


def convert_file(xlsx_path: str, out_dir: str, dialect: str | None = None,
                 stem: str | None = None) -> dict:
    """xlsx を変換し out_dir に产物を書き出す。生成物のパス一覧を返す。"""
    xlsx_path = str(Path(xlsx_path).resolve())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    ir = parse_ir(xlsx_path, dialect)
    stem = stem or Path(xlsx_path).stem

    files: dict[str, str] = {}

    md = render_markdown(ir, xlsx_path)
    p_md = out / f"{stem}.md"
    p_md.write_text(md, encoding="utf-8")
    files["markdown"] = str(p_md)

    ir_dict = ir.to_dict()
    ir_dict["_xlsx"] = xlsx_path
    p_ir = out / f"{stem}.ir.json"
    p_ir.write_text(json.dumps(ir_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    files["ir"] = str(p_ir)

    if ir.screens:
        p_mock = out / f"{stem}.mockup.html"
        p_mock.write_text(render_mockup(ir, xlsx_path), encoding="utf-8")
        files["mockup"] = str(p_mock)

    media_dir = out / "media"
    try:
        written = export_media(xlsx_path, media_dir, ir.warnings)
        if written:
            files["media"] = str(media_dir)
    except Exception as e:
        ir.warnings.append(f"メディア展開に失敗: {e}")

    # warnings はメディア処理後にも追記されるので最終書き出し
    p_warn = out / f"{stem}.warnings.json"
    p_warn.write_text(json.dumps(ir.warnings, ensure_ascii=False, indent=2), encoding="utf-8")
    files["warnings"] = str(p_warn)

    return files
