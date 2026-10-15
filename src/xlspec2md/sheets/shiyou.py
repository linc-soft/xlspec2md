# -*- coding: utf-8 -*-
"""機能仕様解析: ⅱ．項目定義 表 + ⅲ．特記事項（忠実転記）。"""
from __future__ import annotations

from ..models import CellRef, ItemDef
from ..wbutil import SheetView


def parse_shiyou(sv: SheetView, cfg: dict, warnings: list[str]):
    item_defs: list[ItemDef] = []
    notes_lines: list[list[CellRef]] = []

    a_item = sv.find(cfg["anchors"]["item_def"])
    a_notes = sv.find(cfg["anchors"]["notes"])
    if a_item is None:
        warnings.append(f"機能仕様: 「{cfg['anchors']['item_def']}」アンカーが見つかりません")
        return item_defs, notes_lines

    item_row, item_col = a_item
    kw = cfg["header_keywords"]
    table_end = (a_notes[0] - 1) if a_notes else sv.ws.max_row

    # ---- ヘッダ行の特定: アンカーの次以降で最も非空セルが多い行 ----
    best_row, best_cnt = None, 3
    for r in range(item_row + 1, min(item_row + 8, table_end) + 1):
        cnt = sum(1 for _, _, v in sv.iter_nonempty(min_row=r, max_row=r, min_col=2))
        if cnt > best_cnt:
            best_row, best_cnt = r, cnt
    if best_row is None:
        warnings.append("機能仕様: 項目定義のヘッダ行が特定できません")
        return item_defs, notes_lines

    # ---- キーワード→列スパンのマッピング ----
    def spans_of(words: list[str]) -> list[tuple[int, int]]:
        out = []
        for r, c, v in sv.iter_nonempty(min_row=best_row, max_row=best_row, min_col=2):
            if any(w == str(v).strip() or w in str(v) for w in words):
                rng = sv.merge_of(r, c)
                out.append((c, rng.max_col if rng else c))
        return out

    colmap = {
        "item_group": spans_of(kw.get("item_group", ["項目グループ"])),
        "item_id": spans_of(kw.get("item_id", ["項目ID"])),
        "category": spans_of(kw["category"]),
        "name": spans_of(kw["name"]),
        "modes": {m: spans_of([m]) for m in kw["modes"]},
        "required": spans_of(kw["required"]),
        "initial": spans_of(kw["initial"]),
        "datasource": spans_of(kw["datasource"]),
        "list_setting": spans_of(kw["list_setting"]),
        "remark": spans_of(kw["remark"]),
    }
    if not colmap["name"]:
        warnings.append("機能仕様: 項目定義の「項目名」列が見つかりません")

    def read_in(spans: list[tuple[int, int]], r: int) -> str:
        for c1, c2 in spans:
            v = sv.value(r, c1)
            if v is not None and str(v).strip():
                return str(v).strip()
        return ""

    # ---- データ行 ----
    blank_run = 0
    for r in range(best_row + 1, table_end + 1):
        if not any(True for _ in sv.iter_nonempty(min_row=r, max_row=r, min_col=2)):
            blank_run += 1
            if blank_run >= 2:
                break
            continue
        blank_run = 0
        name = read_in(colmap["name"], r)
        if not name:
            continue  # ヘッダ repeat 等
        d = ItemDef(source=f"{sv.name}!{r}行")
        d.name = name
        d.item_group = read_in(colmap["item_group"], r)
        d.item_id = read_in(colmap["item_id"], r)
        d.category = read_in(colmap["category"], r)  # 縦結合は value() が左上値を返す
        for m, spans in colmap["modes"].items():
            v = read_in(spans, r)
            if v:
                d.modes[m] = v
        d.required = read_in(colmap["required"], r)
        d.initial = read_in(colmap["initial"], r)
        d.datasource = read_in(colmap["datasource"], r)
        d.list_setting = read_in(colmap["list_setting"], r)
        d.remark = read_in(colmap["remark"], r)
        item_defs.append(d)

    # ---- 特記事項: 忠実転記 ----
    if a_notes:
        n_row = a_notes[0]
        for r in range(n_row + 1, sv.ws.max_row + 1):
            cells = [CellRef(sv.coord(r, c), str(v)) for r2, c, v in
                     sv.iter_nonempty(min_row=r, max_row=r, min_col=2)]
            if cells:
                notes_lines.append(cells)

    return item_defs, notes_lines
