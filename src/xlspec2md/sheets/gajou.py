# -*- coding: utf-8 -*-
"""画面イメージ解析: 縦に積まれた複数画面を切り分け、結合レンジをピクセル座標付きコンポーネントに変換。"""
from __future__ import annotations

import re

from ..models import Component, Screen
from ..wbutil import SheetView, col_px, row_px

FKEY_RE = re.compile(r"\((F\d{1,2}|ESC)\)")
GRID_ROW_RE = re.compile(r"^\d+\s*▶")


def classify(value) -> str:
    if value is None:
        return "block"
    s = str(value).strip()
    if not s:
        return "block"
    if s.startswith("■"):
        return "title"
    if s.startswith("⊟"):
        return "group"
    if FKEY_RE.search(s):
        return "button"
    if GRID_ROW_RE.match(s):
        return "grid-row"
    if s in ("▼", "▽", "▲", "△"):
        return "sort-or-dropdown"
    if s.startswith(("☐", "□")) and len(s) > 1:
        return "checkbox"
    return "text"


def parse_gajou(sv: SheetView, cfg: dict, warnings: list[str]) -> tuple[list[Screen], str, list[tuple[str, int, int]]]:
    """returns (screens, 機能名, annotations)"""
    # メタ: 機能名（"機能名"ラベルセルの右隣の結合レンジ値）
    func_name = ""
    hit = sv.find("機能名", max_row=cfg["header_end_row"])
    if hit:
        r, c = hit
        rng = sv.merge_of(r, c)
        next_col = (rng.max_col + 1) if rng else c + 1
        v = sv.value(r, next_col)
        if v:
            func_name = str(v).strip()

    # ---- 画面境界の検出 ----
    first_row = cfg["first_screen_row"]
    marker_col = cfg["screen_marker"]["column"]
    patterns = cfg["screen_marker"]["patterns"]
    min_components = cfg.get("min_screen_components", 4)
    last_content_row = max((r for r, _, _ in sv.iter_nonempty(min_row=first_row)), default=first_row)

    candidates = [(r, str(sv.value(r, marker_col)).strip())
                  for r in range(first_row + 1, sv.ws.max_row + 1)
                  if sv.value(r, marker_col) and sv.is_top_left(r, marker_col)
                  and any(p in str(sv.value(r, marker_col)) for p in patterns)]

    def count_merges(r0: int, r1: int) -> int:
        return sum(1 for rr in range(r0, r1 + 1) for cc in range(1, sv.ws.max_column + 1)
                   if sv.is_top_left(rr, cc) and sv.merge_of(rr, cc) is not None)

    # 候補ブロックを検査: コンポーネント数と密度の両方が閾値に達するものだけ画面とみなす。
    # 密度が低いブロック（例: 「メニュー」凡例）は注釈ブロックに格下げする。
    bounds: list[tuple[str, int]] = [("", first_row)]
    annotations: list[tuple[str, int, int]] = []  # (名前, 開始行, 終了行)
    cand_rows = [r for r, _ in candidates]
    following = cand_rows[1:] + [last_content_row + 1]
    min_density = cfg.get("min_screen_density", 0.15)
    for (r, name), nxt in zip(candidates, following):
        end = nxt - 1
        n = count_merges(r, end)
        density = n / max(1, end - r + 1)
        if n >= min_components and density >= min_density:
            bounds.append((name, r))
        else:
            annotations.append((name, r, end))
    ann_ranges = [(r0, r1) for _, r0, r1 in annotations]

    # 各画面の終了行 = 次境界-1、最後は内容のある最終行
    screens: list[Screen] = []
    legend = set(cfg["legend_values"])

    for i, (marker_name, start) in enumerate(bounds):
        end = (bounds[i + 1][1] - 1) if i + 1 < len(bounds) else last_content_row
        name = func_name if i == 0 else marker_name
        screen = Screen(name=name, start_row=start, end_row=end,
                        width_px=col_px(sv.ws.max_column + 1), height_px=row_px(end + 1, start))
        # ---- コンポーネント抽出 ----
        seen_ranges: set[str] = set()
        for r in range(start, end + 1):
            if any(r0 <= r <= r1 for r0, r1 in ann_ranges):
                continue  # 注釈ブロックは画面コンポーネントに含めない
            for c in range(1, sv.ws.max_column + 1):
                if not sv.is_top_left(r, c):
                    continue
                rng = sv.merge_of(r, c)
                if rng is None:
                    continue  # 単セル（罫線の名残）はコンポーネント化しない
                key = rng.coord
                if key in seen_ranges:
                    continue
                seen_ranges.add(key)
                v = sv.value(r, c)
                vs = str(v).strip() if v is not None else ""
                if vs in legend and r < start + 8:
                    continue  # 凡例
                comp = Component(
                    name=vs, type=classify(v),
                    x=col_px(rng.min_col), y=row_px(rng.min_row, start),
                    w=(rng.max_col - rng.min_col + 1) * 10,
                    h=(rng.max_row - rng.min_row + 1) * 5,
                    range=sv.range_str(rng), source=sv.name,
                )
                screen.components.append(comp)
        if screen.components:
            screens.append(screen)
        else:
            warnings.append(f"画面「{name}」(row {start}-{end}) にコンポーネントがありません")
    if not screens:
        warnings.append("画面イメージに画面が検出されませんでした")
    return screens, func_name, annotations
