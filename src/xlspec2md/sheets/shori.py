# -*- coding: utf-8 -*-
"""機能処理解析: 画面イベント定義アンカー以下、B 列イベント名でブロック分割し内容を忠実転記。"""
from __future__ import annotations

from ..models import CellRef, EventDef
from ..wbutil import SheetView


def parse_shori(sv: SheetView, cfg: dict, warnings: list[str]) -> list[EventDef]:
    events: list[EventDef] = []
    anchor = sv.find(cfg["anchor"])
    if anchor is None:
        warnings.append(f"機能処理: 「{cfg['anchor']}」アンカーが見つかりません")
        return events
    a_row, ev_col = anchor[0], cfg["event_column"]

    # イベント名候補: アンカー行より下の ev_col 列の非空セル
    marks = [r for r, c, _ in sv.iter_nonempty(min_row=a_row + 1, min_col=ev_col, max_col=ev_col)]
    if not marks:
        warnings.append("機能処理: イベント定義が 1 件もありません")
        return events

    for i, r0 in enumerate(marks):
        r1 = (marks[i + 1] - 1) if i + 1 < len(marks) else sv.ws.max_row
        ev = EventDef(name=str(sv.value(r0, ev_col)).strip(),
                      source=f"{sv.name}!B{r0}")
        for r in range(r0, r1 + 1):
            cells = [CellRef(sv.coord(r, c), str(v)) for _, c, v in
                     sv.iter_nonempty(min_row=r, max_row=r, min_col=ev_col + 1)]
            ev.steps.extend(cells)
        events.append(ev)
    return events
