# -*- coding: utf-8 -*-
"""xlspec2md Web プラットフォーム: FastAPI アプリ。

起動: python -m xlspec2md.web.app  (環境変数 XLSPEC2MD_DATA でデータディレクトリ指定)
"""
from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db, jobs, storage
from .diffing import diff_builds

DOC_KINDS = {"common_spec", "design_book"}


def create_app(data_dir: str | None = None) -> FastAPI:
    storage.set_data_dir(data_dir or os.environ.get("XLSPEC2MD_DATA", storage.DATA_DIR))
    storage.get_data_dir().mkdir(parents=True, exist_ok=True)
    db.init_db(storage.db_path())

    app = FastAPI(title="xlspec2md", version="0.1.0")

    def conn():
        return db.connect(storage.db_path())

    # ---------------- プロジェクト ----------------
    @app.get("/api/projects")
    def list_projects():
        rows = db.q(conn(), "SELECT * FROM projects ORDER BY id DESC")
        return [dict(r) for r in rows]

    @app.post("/api/projects")
    def create_project(name: str = Form(...)):
        slug = storage.slugify(name)
        try:
            cur = db.execute(conn(), "INSERT INTO projects(name,slug,created_at) VALUES(?,?,?)",
                             (name, slug, db.now()))
        except Exception as e:
            raise HTTPException(409, f"プロジェクト作成失敗（同名あり?）: {e}")
        storage.project_dir(slug).mkdir(parents=True, exist_ok=True)
        return dict(db.one(conn(), "SELECT * FROM projects WHERE id=?", (cur.lastrowid,)))

    @app.delete("/api/projects/{pid}")
    def delete_project(pid: int):
        row = db.one(conn(), "SELECT * FROM projects WHERE id=?", (pid,))
        if not row:
            raise HTTPException(404)
        db.execute(conn(), "DELETE FROM projects WHERE id=?", (pid,))
        import shutil
        shutil.rmtree(storage.project_dir(row["slug"]), ignore_errors=True)
        return {"deleted": pid}

    @app.get("/api/projects/{pid}")
    def project_detail(pid: int):
        proj = db.one(conn(), "SELECT * FROM projects WHERE id=?", (pid,))
        if not proj:
            raise HTTPException(404)
        docs = db.q(conn(), """
          SELECT d.*, (SELECT MAX(version_no) FROM versions v WHERE v.document_id=d.id) AS current_version,
                        (SELECT COUNT(*) FROM versions v WHERE v.document_id=d.id) AS version_count
          FROM documents d WHERE d.project_id=? ORDER BY d.kind, d.name
        """, (pid,))
        builds = db.q(conn(), "SELECT * FROM builds WHERE project_id=? ORDER BY id DESC LIMIT 20", (pid,))
        return {"project": dict(proj), "documents": [dict(r) for r in docs],
                "builds": [dict(r) for r in builds]}

    # ---------------- ドキュメント & バージョン ----------------
    @app.post("/api/projects/{pid}/documents")
    async def upload_document(pid: int, kind: str = Form(...),
                              file: UploadFile = File(...)):
        if kind not in DOC_KINDS:
            raise HTTPException(400, f"kind は {sorted(DOC_KINDS)} のいずれか")
        if not file.filename.lower().endswith(".xlsx"):
            raise HTTPException(400, ".xlsx のみアップロード可")
        proj = db.one(conn(), "SELECT * FROM projects WHERE id=?", (pid,))
        if not proj:
            raise HTTPException(404)
        doc_name = Path(file.filename).stem
        row = db.one(conn(), "SELECT * FROM documents WHERE project_id=? AND kind=? AND name=?",
                     (pid, kind, doc_name))
        if not row:
            cur = db.execute(conn(), "INSERT INTO documents(project_id,kind,name,created_at) VALUES(?,?,?,?)",
                             (pid, kind, doc_name, db.now()))
            doc_id = cur.lastrowid
        else:
            doc_id = row["id"]
        path, ver_no = storage.next_version_path(proj["slug"], doc_name, file.filename)
        path.write_bytes(await file.read())
        cur = db.execute(conn(), "INSERT INTO versions(document_id,version_no,filename,stored_path,uploaded_at) VALUES(?,?,?,?,?)",
                         (doc_id, ver_no, file.filename, str(path), db.now()))
        return dict(db.one(conn(), "SELECT * FROM versions WHERE id=?", (cur.lastrowid,)))

    @app.get("/api/documents/{doc_id}/versions")
    def doc_versions(doc_id: int):
        rows = db.q(conn(), "SELECT * FROM versions WHERE document_id=? ORDER BY version_no DESC", (doc_id,))
        return [dict(r) for r in rows]

    # ---------------- ビルド ----------------
    @app.post("/api/projects/{pid}/builds")
    def create_build(pid: int, version_ids: str = Form(default="")):
        proj = db.one(conn(), "SELECT * FROM projects WHERE id=?", (pid,))
        if not proj:
            raise HTTPException(404)
        ids = [int(x) for x in version_ids.split(",") if x.strip()]
        cur = db.execute(conn(), "INSERT INTO builds(project_id,status,triggered_at,result_json) VALUES(?,?,?,?)",
                         (pid, "queued", db.now(), json.dumps({"version_ids": ids})))
        bid = cur.lastrowid

        def _run():
            db.execute(conn(), "UPDATE builds SET status='running' WHERE id=?", (bid,))
            jobs.run_build(bid)

        import threading
        threading.Thread(target=_run, daemon=True).start()
        return dict(db.one(conn(), "SELECT * FROM builds WHERE id=?", (bid,)))

    @app.get("/api/builds/{bid}")
    def build_status(bid: int):
        b = db.one(conn(), "SELECT * FROM builds WHERE id=?", (bid,))
        if not b:
            raise HTTPException(404)
        d = dict(b)
        d["result"] = json.loads(d.pop("result_json") or "{}")
        return d

    def _build_root(b) -> Path:
        proj = db.one(conn(), "SELECT * FROM projects WHERE id=?", (b["project_id"],))
        return storage.build_dir(proj["slug"], b["id"])

    @app.get("/api/builds/{bid}/tree")
    def build_tree(bid: int):
        b = db.one(conn(), "SELECT * FROM builds WHERE id=?", (bid,))
        if not b:
            raise HTTPException(404)
        root = _build_root(b)
        files = [p.relative_to(root).as_posix() for p in sorted(root.rglob("*")) if p.is_file()]
        return {"status": b["status"], "files": files}

    @app.get("/api/builds/{bid}/file")
    def build_file(bid: int, path: str, download: bool = False):
        b = db.one(conn(), "SELECT * FROM builds WHERE id=?", (bid,))
        if not b:
            raise HTTPException(404)
        root = _build_root(b)
        target = (root / path).resolve()
        if not str(target).startswith(str(root.resolve())) or not target.is_file():
            raise HTTPException(404)
        if download:
            return FileResponse(target, filename=target.name)
        if target.suffix in (".md", ".html", ".json", ".txt"):
            return target.read_text(encoding="utf-8", errors="replace")
        return FileResponse(target)

    @app.get("/api/builds/{bid}/zip")
    def build_zip(bid: int):
        b = db.one(conn(), "SELECT * FROM builds WHERE id=?", (bid,))
        if not b:
            raise HTTPException(404)
        root = _build_root(b)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in root.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(root).as_posix())
        proj = db.one(conn(), "SELECT * FROM projects WHERE id=?", (b["project_id"],))
        name = f"{proj['slug']}_build{bid}.zip"
        from urllib.parse import quote
        from starlette.responses import StreamingResponse
        buf.seek(0)
        return StreamingResponse(
            buf, media_type="application/zip",
            headers={"Content-Disposition":
                     f"attachment; filename=build{bid}.zip; filename*=UTF-8''{quote(name)}"})

    @app.get("/api/builds/{bid}/diff")
    def build_diff(bid: int, other: int):
        a = db.one(conn(), "SELECT * FROM builds WHERE id=?", (bid,))
        b = db.one(conn(), "SELECT * FROM builds WHERE id=?", (other,))
        if not a or not b:
            raise HTTPException(404)
        if a["project_id"] != b["project_id"]:
            raise HTTPException(400, "同一プロジェクトのビルド同士のみ比較可")
        diffs = diff_builds(_build_root(a), _build_root(b))
        return {"a": bid, "b": other, "files": sorted(diffs.keys()), "diffs": diffs}

    # ---------------- フロントエンド ----------------
    dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("xlspec2md.web.app:app", host="0.0.0.0", port=8000)
