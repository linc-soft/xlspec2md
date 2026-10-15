# -*- coding: utf-8 -*-
"""共通仕様書方言: 番号付き節の切り分け + 行単位忠実転記。"""
from __future__ import annotations

import re

from ..models import CellRef, DocumentIR, Section
from ..wbutil import SheetView, norm_fullwidth
from ..sheets.verbatim import dump_verbatim


def parse_common_spec(wb, cfg: dict) -> DocumentIR:
    ir = DocumentIR(dialect="common_spec")
    warnings: list[str] = ir.warnings

    main_name = cfg["main_sheet"]
    known = set(cfg["sheet_roles"].keys())

    # メインシート以外の扱い
    for name in wb.sheetnames:
        role = cfg["sheet_roles"].get(name)
        if name == main_name:
            continue
        if role == "ignore":
            continue
        sv = SheetView(wb[name])
        ir.verbatims.append(dump_verbatim(sv))
        warnings.append(f"シート「{name}」は未構造化のまま転記しました（方言設定に無いため）")

    if main_name not in wb.sheetnames:
        warnings.append(f"メインシート「{main_name}」が存在しません")
        return ir

    sv = SheetView(wb[main_name])
    pat = re.compile(cfg["section"]["pattern"])
    hcols = cfg["section"]["heading_columns"]
    maxlen = cfg["section"]["max_len"]

    def is_heading(r: int, c: int, v) -> bool:
        if c not in hcols:
            return False
        s = str(v).strip()
        return bool(pat.match(s)) and len(s) <= maxlen

    # 節境界
    heads: list[tuple[int, int, str]] = []
    for r, c, v in sv.iter_nonempty(min_col=min(hcols), max_col=max(hcols)):
        if is_heading(r, c, v):
            heads.append((r, c, str(v).strip()))

    if not heads:
        warnings.append("共通仕様書: 節見出しが 1 つも検出できません（全行転記します）")
        ir.verbatims.append(dump_verbatim(sv))
        return ir

    # 先頭（節 1 より前）の中身は verbatim
    if heads[0][0] > 1:
        pre = Section(level=0, title="（前文）", source=sv.name)
        for r in range(1, heads[0][0]):
            cells = [CellRef(sv.coord(r, c), str(v)) for _, c, v in
                     sv.iter_nonempty(min_row=r, max_row=r)]
            if cells:
                pre.lines.append(cells)
        ir.sections.append(pre)

    for i, (r0, c0, title) in enumerate(heads):
        r1 = heads[i + 1][0] - 1 if i + 1 < len(heads) else sv.ws.max_row
        num = norm_fullwidth(pat.match(title).group(0))
        level = 2 if len(num.rstrip(".")) <= 2 else 3
        sec = Section(level=level, title=title, source=f"{sv.name}!B{r0}")
        for r in range(r0 + 1, r1 + 1):
            cells = [CellRef(sv.coord(r, c), str(v)) for _, c, v in
                     sv.iter_nonempty(min_row=r, max_row=r)]
            if cells:
                sec.lines.append(cells)
        ir.sections.append(sec)

    ir.meta["section_count"] = len(heads)
    return ir
