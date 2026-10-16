# -*- coding: utf-8 -*-
"""罫線矩形検出: セルの border スタイルから閉じた長方形フレームを検出する。

設計書の「画面イメージ」シートでは、画面外枠・GroupBox・ボタン領域などが
セルの罫線（border スタイル）で描かれている。

検出アプローチ（辺の網羅的な組合せではなく、垂直辺の交差から検出）:
  1. 垂直罫線（列の左辺 or 左隣列の右辺）のある列を抽出し、各行runを求める
  2. 2 つの垂直辺列の run 交差部分 = ボックスの縦方向区間の候補
     （ボックス同士の間では必ずどちらかの辺が途切れるため、区間は自然に分離される）
  3. 区間の上下（±1行の描き方の個体差を許容）に水平罫線が通っていれば矩形確定

幾何規約（1列=10px、1行=5px、列C=0px）:
  - BorderRect(r1, r2, c1, c2): 上辺=行r1の上端、下辺=行r2の上端、左辺=列c1の左端、右辺=列c2の左端
    → x=(c1-3)*10、y=(r1-origin)*5、w=(c2-c1)*10、h=(r2-r1)*5
    （例: D19:DZ32 → x=10, y=40, w=1260, h=65。下辺は行31の下端に描かれ、
      行32の上端として検出されるため r2=32。呼び出し側は下端に +1 行余分に取ること）

矩形の後処理（gajou 側）:
  - ⊟ ラベルブロックと矩形を照合して GroupBox 確定（セクション内コンポーネントを
    すべて内包する最小面積の矩形を採用）
  - 確定した GroupBox に内包される矩形（入力欄・Grid枠・帯状罫線）は破棄
  - 残ったラベル無し矩形のうち、コンポーネントを複数内包する最小面積のものを
    パネル（ボタン領域など）とする
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BorderRect:
    r1: int   # 上辺の行
    r2: int   # 下辺の行（内容の最終行 = r2-1。高さ = (r2-r1) 行分）
    c1: int   # 左辺の列
    c2: int   # 右辺の列（右辺は列c2の左端 = 列c2-1の右端。幅 = (c2-c1) 列分）

    @property
    def area(self) -> int:
        return (self.r2 - self.r1) * (self.c2 - self.c1)


def _style(side) -> bool:
    return side is not None and bool(side.style)


def detect_rectangles(ws, r0: int, r1: int, c0: int, c1: int, *,
                      side_coverage: float = 0.8,
                      min_w_cols: int = 6, min_h_rows: int = 4) -> list[BorderRect]:
    """(r0..r1, c0..c1) 領域内の罫線矩形を検出する（面積降順）。

    下端・右端の罫線検出のため、呼び出し側は r1/c1 に +1 余分に取ること
    （下辺が「最終行の下端」に描かれている場合、その検出は r1+1 行目の上端として現れる）。"""

    rows = list(range(r0, r1 + 1))
    cols = list(range(c0, c1 + 1))

    # ---- 罫線マトリクスと累積和（カバレッジ O(1) 計算用）----
    H: dict[int, list[int]] = {}   # 行 -> 列方向の水平罫線有無（上端基準）
    hpre: dict[int, list[int]] = {}
    V: dict[int, list[int]] = {}   # 列 -> 行方向の垂直罫線有無（左端基準）
    for r in rows:
        flags = []
        for c in cols:
            b = ws.cell(row=r, column=c).border
            f = _style(b.top)
            if not f and r > 1:
                f = _style(ws.cell(row=r - 1, column=c).border.bottom)
            flags.append(1 if f else 0)
        H[r] = flags
        acc = [0]
        for f in flags:
            acc.append(acc[-1] + f)
        hpre[r] = acc
    for c in cols:
        flags = []
        for r in rows:
            b = ws.cell(row=r, column=c).border
            f = _style(b.left)
            if not f and c > 1:
                f = _style(ws.cell(row=r, column=c - 1).border.right)
            flags.append(1 if f else 0)
        V[c] = flags

    def h_cov(r: int, ca: int, cb: int) -> float:
        """行 r の上端の水平罫線が、セル列 ca..cb-1（ボックス幅全体）をどれだけ覆うか。"""
        i, j = ca - c0, cb - c0
        return (hpre[r][j] - hpre[r][i]) / (j - i)

    # ---- 1. 垂直罫線のある列とその行run ----
    vruns: dict[int, list[tuple[int, int]]] = {}
    for idx, c in enumerate(cols):
        flags = V[c]
        runs: list[tuple[int, int]] = []
        start: int | None = None
        for off, f in enumerate(flags):
            if f:
                if start is None:
                    start = off
            elif start is not None:
                runs.append((start, off - 1))
                start = None
        if start is not None:
            runs.append((start, len(flags) - 1))
        if runs:
            vruns[c] = [(r0 + a, r0 + b) for a, b in runs]

    # ---- 2. 垂直辺ペアの run 交差 → ボックス縦区間 ----
    def intersect(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> list[tuple[int, int]]:
        out = []
        i = j = 0
        while i < len(a) and j < len(b):
            lo = max(a[i][0], b[j][0])
            hi = min(a[i][1], b[j][1])
            if lo <= hi:
                out.append((lo, hi))
            if a[i][1] < b[j][1]:
                i += 1
            else:
                j += 1
        return out

    rects: set[BorderRect] = set()
    col_list = sorted(vruns)
    for i, ca in enumerate(col_list):
        for cb in col_list[i + 1:]:
            if cb - ca < min_w_cols:
                continue
            for a, b in intersect(vruns[ca], vruns[cb]):
                # 3. 上下の水平辺を確認（描き方の個体差 ±1 行を許容）
                r1c: int | None = None
                for cand in (a - 1, a):
                    if cand >= r0 and h_cov(cand, ca, cb) >= side_coverage:
                        r1c = cand
                        break
                if r1c is None:
                    continue
                r2c: int | None = None
                for cand in (b + 1, b):
                    if cand <= r1 and h_cov(cand, ca, cb) >= side_coverage:
                        r2c = cand
                        break
                if r2c is None or r2c - r1c < min_h_rows:
                    continue
                rects.add(BorderRect(r1c, r2c, ca, cb))
    return sorted(rects, key=lambda r: -r.area)


def strictly_inside(a: BorderRect, b: BorderRect) -> bool:
    """a が b に（小さな罫線のずれも許容して）内包されるか。"""
    return (b.r1 <= a.r1 and a.r2 <= b.r2
            and b.c1 <= a.c1 and a.c2 <= b.c2
            and (a.r1, a.r2, a.c1, a.c2) != (b.r1, b.r2, b.c1, b.c2))
