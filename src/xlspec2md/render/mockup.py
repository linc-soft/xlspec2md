# -*- coding: utf-8 -*-
"""IR → mockup HTML（座標検証用。1px = 1px で絶対配置）。"""
from __future__ import annotations

import html

from ..models import DocumentIR

TYPE_COLOR = {
    "form": "#2c3e50", "title": "#1a5276", "group": "#117864", "panel": "#5d6d7e",
    "button": "#b9770e",
    "checkbox": "#7d3c98", "dropdown": "#a93226", "sort-or-dropdown": "#a93226",
    "grid-row": "#707b7c", "text": "#212f3c", "block": "#95a5a6", "legend": "#95a5a6",
}

_CSS = """
body { font-family: 'Meiryo','Yu Gothic','Noto Sans CJK JP',sans-serif; background:#f5f6f7; margin:0; }
nav { position:sticky; top:0; background:#2c3e50; padding:8px 16px; }
nav a { color:#ecf0f1; margin-right:14px; text-decoration:none; font-size:14px; }
nav a:hover { text-decoration:underline; }
.screen { position:relative; margin:24px; background:#fff; border:2px solid #2c3e50;
          box-shadow:0 2px 8px rgba(0,0,0,.15); }
.screen h2 { position:absolute; top:-30px; left:0; margin:0; font-size:14px; color:#2c3e50; }
.c { position:absolute; border:1px solid #999; font-size:10px; overflow:hidden;
     padding:1px 3px; box-sizing:border-box; background:rgba(255,255,255,.85); white-space:pre-wrap; }
.c .tag { position:absolute; top:0; right:2px; font-size:8px; opacity:.6; }
.gbox { position:absolute; border:2px solid #117864; border-radius:4px;
        background:rgba(17,120,100,.05); box-sizing:border-box; }
.glabel { position:absolute; font-size:10px; font-weight:bold; color:#117864;
          background:#fff; padding:0 4px; white-space:pre; }
"""

_PAGE = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><title>mockup — {title}</title>
<style>{css}</style></head><body>
<nav>{nav}</nav>
{screens}
</body></html>"""

_SCREEN = """
<div class="screen" id="{sid}" style="width:{w}px;height:{h}px">
<h2>{name}（{w}×{h}px, rows {r0}-{r1}）</h2>
{comps}
</div>
"""


def render_mockup(ir: DocumentIR, xlsx_path: str = "") -> str:
    nav_parts, screen_parts = [], []
    for i, s in enumerate(ir.screens):
        sid = f"s{i}"
        nav_parts.append(f'<a href="#{sid}">{html.escape(s.name)}</a>')
        comps = []
        for c in s.components:
            if c.type == "form":
                continue  # .screen 枠自体が Form
            if c.type == "group" and c.label_offset:
                # GroupBox: ラベル（ブロック頂点）+ 罫線枠（y+label_offset）
                off = c.label_offset
                comps.append(
                    f'<div class="gbox" title="{html.escape(c.range)} [group]" '
                    f'style="left:{c.x}px;top:{c.y + off}px;width:{c.w}px;height:{c.h}px"></div>')
                comps.append(
                    f'<div class="glabel" style="left:{c.x + 10}px;top:{c.y + 2}px">'
                    f'{html.escape(c.name)}</div>')
                continue
            color = TYPE_COLOR.get(c.type, "#212f3c")
            txt = html.escape(c.name) if c.name else ""
            style = f'left:{c.x}px;top:{c.y}px;width:{c.w}px;height:{c.h}px;'
            if c.type == "panel":
                style += 'border-style:dashed;'
            comps.append(
                f'<div class="c" title="{html.escape(c.range)} [{c.type}]" '
                f'style="{style}border-left:3px solid {color}">{txt}'
                f'<span class="tag">{c.type}</span></div>')
        screen_parts.append(_SCREEN.format(
            sid=sid, w=s.width_px, h=s.height_px, name=html.escape(s.name),
            r0=s.start_row, r1=s.end_row, comps="\n".join(comps)))
    title = ir.meta.get("機能名", "") or (xlsx_path.rsplit("/", 1)[-1] if xlsx_path else "mockup")
    return _PAGE.format(title=html.escape(title), css=_CSS,
                        nav="".join(nav_parts), screens="".join(screen_parts))
