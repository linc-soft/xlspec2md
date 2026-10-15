# xlspec2md

基本設計書（Excel）→ Markdown / JSON IR / mockup HTML を**決定論的に**変換するエンジン。
AI による要約・推論は一切行わず、ソース座標（`sheet!range`）付きで忠実に構造化する。

## 変換対象の方言

| 方言 | 対象ファイル | 構成 |
|---|---|---|
| `screen_book` | 基本設計書_*.xlsx | 画面イメージ（複数画面自動分割＋ピクセル座標）、機能仕様（項目定義＋特記事項）、機能処理（イベント）、データ更新表（行列/散文両形式） |
| `common_spec` | 01_共通仕様書.xlsx | 番号付き節の分割＋行単位転記 |

未知シートは `<details>` 付録として忠実転記し、変換警告（warnings.json）に記録する。
`メニュー` などの低密度ブロックは画面ではなく注釈ブロックとして転記する。

## インストール / 使い方

```bash
pip install -e .
xlspec2md convert 基本設計書_担当者マスタ.xlsx -o out/
xlspec2md inspect 01_共通仕様書.xlsx        # IR を stdout にダンプ
```

生成物（`out/<ファイル名>/`）:

- `<stem>.md` — 人/AI エージェント共读ドキュメント（主产物）
- `<stem>.ir.json` — 構造化中間表現（精确照会・差分・再レンダリング用）
- `<stem>.mockup.html` — 座標検証用モックアップ（1px=1px 絶対配置）
- `media/` — 埋め込み画像（EMF/WMF は LibreOffice 環境で PNG 変換）
- `<stem>.warnings.json` — 変換警告一覧

## アーキテクチャ

```
xlsx ──▶ dialect parser ──▶ DocumentIR (dataclass) ──▶ renderers (md / mockup / json)
                ▲
        dialects/*.yaml（アンカー・列キーワード・閾値の設定）
```

- 依存: openpyxl / PyYAML / Jinja2（IR は stdlib dataclass のみ）
- 座標規約: 1列=10px、1行=5px、列C=画面左端
- 画面境界: C 列の `タブ`/`メニュー` マーカ＋密度ヒューリスティクス（min_components=4, min_density=0.15）

## Docker（Web UI 版）

`web/` 配下（FastAPI + Vue3 + Element Plus + LibreOffice）を単一イメージにビルドする。
`docker build -t xlspec2md .` → `/data` にホストディレクトリをマウントして起動。

## テスト

`tests/fixtures/` の実ファイルでゴールデンテスト:

```bash
python tests/run_golden.py
```
