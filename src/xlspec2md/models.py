# -*- coding: utf-8 -*-
"""IR（中間表現）データモデル。依存なし（dataclass only）。"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class CellRef:
    coord: str          # e.g. "C11"（ソース追跡用）
    text: str


@dataclass
class Component:
    name: str
    type: str           # title/group/button/checkbox/dropdown/sort/grid-row/text/block/legend
    x: int              # px（画面左上原点）
    y: int
    w: int
    h: int
    range: str          # sheet!C11:D15
    source: str = ""    # sheet 名


@dataclass
class Screen:
    name: str
    start_row: int
    end_row: int
    width_px: int
    height_px: int
    components: list[Component] = field(default_factory=list)


@dataclass
class ItemDef:
    category: str = ""
    item_group: str = ""         # 項目グループ（オプション列）
    item_id: str = ""            # 項目ID（オプション列）
    name: str = ""
    modes: dict[str, str] = field(default_factory=dict)  # 新規/修正/照会/選択 → I/O
    required: str = ""
    initial: str = ""
    datasource: str = ""
    list_setting: str = ""
    remark: str = ""
    source: str = ""


@dataclass
class EventDef:
    name: str
    source: str = ""
    steps: list[CellRef] = field(default_factory=list)


@dataclass
class DataUpdate:
    kind: str                    # matrix | prose
    table: str = ""
    action: str = ""             # 登録 / 取込 ...
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, str]] = field(default_factory=list)
    lines: list[list[CellRef]] = field(default_factory=list)  # prose 用
    source: str = ""


@dataclass
class Section:
    """共通仕様書などの節"""
    level: int
    title: str
    source: str = ""
    lines: list[list[CellRef]] = field(default_factory=list)


@dataclass
class VerbatimBlock:
    sheet: str
    title: str
    lines: list[list[CellRef]] = field(default_factory=list)


@dataclass
class ImageAsset:
    name: str            # media ファイル名
    kind: str            # png | jpg | emf | wmf
    note: str = ""


@dataclass
class DocumentIR:
    dialect: str
    meta: dict[str, Any] = field(default_factory=dict)
    screens: list[Screen] = field(default_factory=list)
    item_defs: list[ItemDef] = field(default_factory=list)
    notes_lines: list[list[CellRef]] = field(default_factory=list)  # 特記事項
    events: list[EventDef] = field(default_factory=list)
    data_updates: list[DataUpdate] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)           # 共通仕様書
    verbatims: list[VerbatimBlock] = field(default_factory=list)
    images: list[ImageAsset] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
