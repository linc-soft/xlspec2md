# -*- coding: utf-8 -*-
"""データ更新表解析: 行列形式（フィールド×INSERT/UPDATE/DELETE）と散文形式の両対応。"""
from __future__ import annotations

from ..models import CellRef, DataUpdate
from ..wbutil import SheetView


def parse_koushin(sv: SheetView, cfg: dict, warnings: list[str]) -> list[DataUpdate]:
    result: list[DataUpdate] = []

    # 先頭メタ（例: C5='登録' V5='m担当者' / C6='取込'）を行単位で拾う
    action, table = "", ""
    for r in range(4, min(10, sv.ws.max_row) + 1):
        cells = [str(v).strip() for _, _, v in sv.iter_nonempty(min_row=r, max_row=r, min_col=3, max_col=30)]
        if len(cells) >= 2:
            action, table = cells[0], cells[1]
            break

    fhit = sv.find(cfg["field_header"])
    if fhit is None:
        # ---- 散文形式: 全文忠実転記 ----
        du = DataUpdate(kind="prose", action=action, table=table, source=sv.name)
        blank = 0
        for r in range(5, sv.ws.max_row + 1):
            cells = [CellRef(sv.coord(r, c), str(v)) for _, c, v in
                     sv.iter_nonempty(min_row=r, max_row=r, min_col=3)]
            if cells:
                blank = 0
                du.lines.append(cells)
            else:
                blank += 1
                if blank >= cfg["max_blank_break"]:
                    break
        result.append(du)
        return result

    # ---- 行列形式（ヘッダ前に散文手順があれば別エントリで保持）----
    if fhit[0] > 6:
        prose = DataUpdate(kind="prose", action=action, table=table, source=sv.name)
        for r in range(5, fhit[0]):
            cells = [CellRef(sv.coord(r, c), str(v)) for _, c, v in
                     sv.iter_nonempty(min_row=r, max_row=r, min_col=3)]
            if cells:
                prose.lines.append(cells)
        if prose.lines:
            result.append(prose)

    # ---- 行列形式 ----
    h_row, f_col = fhit
    # DML 列ヘッダの検出（同じヘッダブロック内、フィールド名列より右）
    dml_cols: list[tuple[str, int]] = []  # (表示名, 開始列)
    for r, c, v in sv.iter_nonempty(min_row=h_row - 1, max_row=h_row, min_col=f_col + 1):
        s = str(v)
        if any(k in s for k in cfg["dml_keywords"]):
            dml_cols.append((s.strip(), c))
    if not dml_cols:
        warnings.append("データ更新表: DML 列（INSERT/UPDATE/DELETE）が検出できません")

    du = DataUpdate(kind="matrix", action=action, table=table, source=sv.name)
    du.columns = ["フィールド名"] + [n for n, _ in dml_cols]
    blank = 0
    for r in range(h_row + 1, sv.ws.max_row + 1):
        fname = sv.value(r, f_col)
        row_cells = {n: "" for n, _ in dml_cols}
        has = False
        for n, c in dml_cols:
            v = sv.value(r, c)
            if v is not None and str(v).strip():
                row_cells[n] = str(v).strip()
                has = True
        if fname is None and not has:
            blank += 1
            if blank >= cfg["max_blank_break"]:
                break
            continue
        blank = 0
        if fname is None:
            continue
        du.rows.append({"フィールド名": str(fname).strip(), **row_cells})
    result.append(du)
    return result
