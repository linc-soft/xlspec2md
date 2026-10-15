# -*- coding: utf-8 -*-
"""汎用シートの忠実転記（未知シートのフォールバック）。"""
from __future__ import annotations

from ..models import CellRef, VerbatimBlock
from ..wbutil import SheetView


def dump_verbatim(sv: SheetView) -> VerbatimBlock:
    blk = VerbatimBlock(sheet=sv.name, title=sv.name)
    for r in range(1, sv.ws.max_row + 1):
        cells = [CellRef(sv.coord(r, c), str(v)) for _, c, v in
                 sv.iter_nonempty(min_row=r, max_row=r, min_col=1)]
        if cells:
            blk.lines.append(cells)
    return blk
