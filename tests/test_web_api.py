# -*- coding: utf-8 -*-
"""Web API 烟测: TestClient で全エンドポイントを通す。"""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from xlspec2md.web.app import create_app  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def wait_done(client: TestClient, bid: int, timeout: float = 60.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        b = client.get(f"/api/builds/{bid}").json()
        if b["status"] in ("done", "failed"):
            return b
        time.sleep(0.3)
    raise TimeoutError(f"build {bid} timeout")


def main() -> int:
    data_dir = Path(tempfile.mkdtemp(prefix="xlspec2md_webtest_"))
    try:
        app = create_app(str(data_dir))
        c = TestClient(app)

        # プロジェクト作成
        r = c.post("/api/projects", data={"name": "テスト案件"})
        assert r.status_code == 200, r.text
        pid = r.json()["id"]

        # 共通仕様書 + 設計書をアップロード（各 2 バージョン）
        def upload(kind, path):
            with open(path, "rb") as f:
                return c.post(f"/api/projects/{pid}/documents",
                              data={"kind": kind},
                              files={"file": (Path(path).name, f,
                                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})

        spec = FIXTURES / "01_共通仕様書.xlsx"
        book = FIXTURES / "基本設計書_担当者マスタ.xlsx"
        for _ in range(2):  # v1, v2
            assert upload("common_spec", spec).status_code == 200
            assert upload("design_book", book).status_code == 200

        detail = c.get(f"/api/projects/{pid}").json()
        assert len(detail["documents"]) == 2, detail["documents"]
        for d in detail["documents"]:
            assert d["current_version"] == 2 and d["version_count"] == 2, d
            assert d["current_version_id"] and not d["current_converted"], d

        # ビルド実行 → 完了待ち（未変換の最新版のみ変換される）
        b1 = c.post(f"/api/projects/{pid}/builds", data={}).json()
        r1 = wait_done(c, b1["id"])
        assert r1["status"] == "done", r1.get("error")
        docs = r1["result"]["documents"]
        assert len(docs) == 2, docs
        kinds = sorted(d["kind"] for d in docs)
        assert kinds == ["common_spec", "design_book"], kinds

        # 変換済みフラグが立つ / 2 回目ビルドは対象なし
        detail = c.get(f"/api/projects/{pid}").json()
        for d in detail["documents"]:
            assert d["current_converted"] == 1, d
        b1b = c.post(f"/api/projects/{pid}/builds", data={}).json()
        r1b = wait_done(c, b1b["id"])
        assert r1b["status"] == "done" and r1b["result"]["documents"] == [], r1b

        # 設計書 v3 アップロード → 未変換に戻る → 単一指定ビルドで v3 のみ変換
        assert upload("design_book", book).status_code == 200
        detail = c.get(f"/api/projects/{pid}").json()
        book_doc = next(d for d in detail["documents"] if d["kind"] == "design_book")
        assert book_doc["current_version"] == 3 and not book_doc["current_converted"], book_doc
        b2 = c.post(f"/api/projects/{pid}/builds",
                    data={"version_ids": str(book_doc["current_version_id"])}).json()
        r2 = wait_done(c, b2["id"])
        assert r2["status"] == "done" and len(r2["result"]["documents"]) == 1, r2

        # 産物ツリー / common_spec.md 固定名 / ファイル取得 / zip
        tree = c.get(f"/api/builds/{b1['id']}/tree").json()
        assert any(f == "docs/common_spec.md" for f in tree["files"]), tree["files"]
        md = c.get(f"/api/builds/{b1['id']}/file",
                   params={"path": "docs/common_spec.md"})
        assert "５．画面項目制御" in md.text
        zr = c.get(f"/api/builds/{b1['id']}/zip")
        assert zr.status_code == 200 and len(zr.content) > 1000

        # 版差分: 同一ドキュメントの v1 vs v2（同一内容 → 差分テキストは空だがファイル一覧は返る）
        vers = c.get(f"/api/documents/{book_doc['id']}/versions").json()
        assert len(vers) == 3 and all(v["converted"] in (0, 1) for v in vers), vers
        v1, v2 = vers[-1]["id"], vers[-2]["id"]
        diff = c.get(f"/api/documents/{book_doc['id']}/diff",
                     params={"va": v1, "vb": v2}).json()
        assert "files" in diff and diff["files"], diff
        assert any(f.endswith(".md") for f in diff["files"]), diff["files"]
        assert all(not d for d in diff["diffs"].values()), "同一内容なのに差分あり"
        # 別ドキュメントの版とは比較不可
        spec_doc = next(d for d in detail["documents"] if d["kind"] == "common_spec")
        spec_v = c.get(f"/api/documents/{spec_doc['id']}/versions").json()[0]
        r = c.get(f"/api/documents/{book_doc['id']}/diff",
                  params={"va": v1, "vb": spec_v["id"]})
        assert r.status_code == 400, r.text

        # プロジェクト削除
        assert c.delete(f"/api/projects/{pid}").status_code == 200

        print("WEB API SMOKE TEST: ALL PASS")
        print(f"  project={pid} builds={b1['id']},{b2['id']} "
              f"diff_files={len(diff['files'])}")
        return 0
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
