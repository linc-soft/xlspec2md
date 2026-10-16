# -*- coding: utf-8 -*-
"""IR → Markdown レンダリング（Jinja2）。"""
from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, BaseLoader

from ..models import DocumentIR

TEMPLATE = """\
# {{ meta.filename }}

{% if meta.機能名 %}**機能名**: {{ meta.機能名 }}
{% endif %}
- 方言: `{{ ir.dialect }}`
- 画面数: {{ ir.screens | length }}、項目定義: {{ ir.item_defs | length }} 件、イベント: {{ ir.events | length }} 件

{% if ir.screens %}
{% for s in ir.screens %}
## 画面: {{ s.name }}

`{{ s.source if s.source else '画面イメージ' }}!行 {{ s.start_row }}-{{ s.end_row }}` ｜ サイズ: {{ s.width_px }}x{{ s.height_px }}px

| # | コンポーネント | 種別 | x | y | w | h | コンテナ | rx | ry | ソース |
|---|----------------|------|---|---|---|---|----------|----|----|--------|
{% for c in s.components %}| {{ loop.index }} | {{ c.name | replace('|', '｜') | truncate(40) }} | {{ c.type }} | {{ c.x }} | {{ c.y }} | {{ c.w }} | {{ c.h }} | {{ c.container }} | {{ c.rx }} | {{ c.ry }} | `{{ c.range }}` |
{% endfor %}
{% endfor %}
{% endif %}

{% if ir.item_defs %}
## 項目定義

| {% if has_group %}項目グループ | {% endif %}{% if has_id %}項目ID | {% endif %}分類 | 項目名 | {% for m in mode_cols %}{{ m }} | {% endfor %}必須 | 初期値 | データソース | リスト設定 | 備考 |
|{% if has_group %}---|{% endif %}{% if has_id %}---|{% endif %}------|--------|{% for m in mode_cols %}---|{% endfor %}---|---|---|---|---|
{% for d in ir.item_defs %}| {% if has_group %}{{ d.item_group }} | {% endif %}{% if has_id %}{{ d.item_id }} | {% endif %}{{ d.category }} | {{ d.name | replace('|','｜') }} | {% for m in mode_cols %}{{ d.modes.get(m, '') }} | {% endfor %}{{ d.required }} | {{ d.initial | replace('|','｜') | truncate(30) }} | {{ d.datasource | replace('|','｜') | truncate(40) }} | {{ d.list_setting | replace('|','｜') | truncate(30) }} | {{ d.remark | replace('|','｜') | truncate(50) }} |
{% endfor %}
{% endif %}

{% if ir.notes_lines %}
## 特記事項

{% for line in ir.notes_lines %}{% for c in line %} - {{ c.text | replace('|','｜') }} (`{{ c.coord }}`) {% endfor %}{{ '\n' }}{% endfor %}
{% endif %}

{% if ir.events %}
## 機能処理（イベント）

{% for e in ir.events %}
### {{ e.name }}

`{{ e.source }}`
{% for s in e.steps %}{{ '\n' }}- {{ s.text | replace('|','｜') }} `{{ s.coord }}`{% endfor %}
{% endfor %}
{% endif %}

{% if ir.data_updates %}
## データ更新表

{% for du in ir.data_updates %}
### {{ du.action }} {% if du.table %}→ `{{ du.table }}`{% endif %}（{{ du.kind }}形式）

{% if du.kind == 'matrix' %}
| {{ du.columns | join(' | ') }} |
|{% for c in du.columns %}---|{% endfor %}{{ '\n' }}{% for row in du.rows %}| {% for col in du.columns %}{{ row.get(col, '') | replace('|','｜') | replace('\n', '<br>') | truncate(50) }} | {% endfor %}{{ '\n' }}{% endfor %}
{% else %}
{% for line in du.lines %}{% for c in line %} {{ c.text | replace('|','｜') }} {% endfor %}{{ '\n' }}{% endfor %}
{% endif %}
{% endfor %}
{% endif %}

{% if ir.sections %}
{% for sec in ir.sections %}
{{ '#' * sec.level }} {{ sec.title }}

{% for line in sec.lines %}{% for c in line %} {{ c.text | replace('|','｜') }} {% endfor %}{{ '\n' }}{% endfor %}
{% endfor %}
{% endif %}

{% if ir.verbatims %}
## 付録: 未構造化シート転記

{% for v in ir.verbatims %}
<details><summary>シート: {{ v.sheet }}{% if v.title != v.sheet %} — {{ v.title }}{% endif %}</summary>

{% for line in v.lines %}{% for c in line %} {{ c.text | replace('|','｜') }} {% endfor %}{{ '\n' }}{% endfor %}
</details>
{% endfor %}
{% endif %}

{% if ir.warnings %}
## 変換警告

{% for w in ir.warnings %}- ⚠️ {{ w }}
{% endfor %}
{% endif %}
"""

_env = Environment(loader=BaseLoader(), autoescape=False,
                   trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)


def render_markdown(ir: DocumentIR, xlsx_path: str = "") -> str:
    mode_cols: list[str] = []
    for d in ir.item_defs:
        for m in d.modes:
            if m not in mode_cols:
                mode_cols.append(m)
    meta = dict(ir.meta)
    # ストレージ上のバージョン接頭辞（v3__foo.xlsx）は見出しから除く
    meta.setdefault("filename", re.sub(r"^v\d+__", "", Path(xlsx_path).name) if xlsx_path else "")
    return _env.from_string(TEMPLATE).render(
        ir=ir, meta=meta, mode_cols=mode_cols,
        has_group=any(d.item_group for d in ir.item_defs),
        has_id=any(d.item_id for d in ir.item_defs))
