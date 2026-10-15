# -*- coding: utf-8 -*-
"""画面設計書方言: 4 シート + 未知シート転記を統括。"""
from __future__ import annotations

from ..models import CellRef, DocumentIR, VerbatimBlock
from ..wbutil import SheetView
from ..sheets.gajou import parse_gajou
from ..sheets.shiyou import parse_shiyou
from ..sheets.shori import parse_shori
from ..sheets.koushin import parse_koushin
from ..sheets.verbatim import dump_verbatim
from ..media import extract_media


def parse_screen_book(wb, cfg: dict, xlsx_path: str = "") -> DocumentIR:
    ir = DocumentIR(dialect="screen_book")
    warnings: list[str] = ir.warnings
    roles = cfg["sheet_roles"]

    for name in wb.sheetnames:
        role = roles.get(name, "verbatim")
        sv = SheetView(wb[name])
        if role == "ignore":
            continue
        if role == "gajou":
            screens, func_name, annotations = parse_gajou(sv, cfg["gajou"], warnings)
            ir.screens = screens
            ir.meta["機能名"] = func_name
            ir.meta["screen_count"] = len(screens)
            for ann_name, r0, r1 in annotations:
                blk = VerbatimBlock(sheet=sv.name, title=f"画面イメージ注釈: {ann_name}")
                for r in range(r0, r1 + 1):
                    cells = [CellRef(sv.coord(r, c), str(v)) for _, c, v in
                             sv.iter_nonempty(min_row=r, max_row=r, min_col=3)]
                    if cells:
                        blk.lines.append(cells)
                ir.verbatims.append(blk)
                warnings.append(f"画面イメージ: 「{ann_name}」(row {r0}-{r1}) は"
                                f"コンポーネント数が閾値未満のため注釈ブロックとして転記しました")
        elif role == "shiyou":
            ir.item_defs, ir.notes_lines = parse_shiyou(sv, cfg["shiyou"], warnings)
        elif role == "shori":
            ir.events = parse_shori(sv, cfg["shori"], warnings)
        elif role == "koushin":
            ir.data_updates = parse_koushin(sv, cfg["koushin"], warnings)
        else:
            ir.verbatims.append(dump_verbatim(sv))
            warnings.append(f"シート「{name}」は未構造化のまま転記しました")

    # 埋め込み画像の抽出（EMF 変換は export 時）
    if xlsx_path:
        try:
            ir.images = extract_media(xlsx_path)
        except Exception as e:  # zip 異常等でも解析自体は壊さない
            warnings.append(f"埋め込み画像の抽出に失敗: {e}")
    return ir
