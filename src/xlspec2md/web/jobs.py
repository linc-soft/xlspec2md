# -*- coding: utf-8 -*-
"""変換ジョブ: プロジェクトの全現行バージョン（または指定版）を変換して産物を保存。"""
from __future__ import annotations

import json
from pathlib import Path

from ..engine import convert_file
from . import db, storage


def _current_versions(conn, project_id: int) -> list:
    """各ドキュメントの最新バージョンを 1 本ずつ返す。"""
    rows = db.q(conn, """
      SELECT v.id, v.filename, v.stored_path, d.kind, d.name AS doc_name, v.version_no, v.converted
      FROM versions v
      JOIN documents d ON d.id = v.document_id
      JOIN (SELECT document_id, MAX(version_no) AS mx FROM versions GROUP BY document_id) t
        ON t.document_id = v.document_id AND t.mx = v.version_no
      WHERE d.project_id = ?
    """, (project_id,))
    return rows


def _pending_versions(conn, project_id: int) -> list:
    """各ドキュメントの最新バージョンのうち、未変換のものだけ返す。"""
    return [r for r in _current_versions(conn, project_id) if not r["converted"]]


def _selected_versions(conn, version_ids: list[int]) -> list:
    if not version_ids:
        return []
    marks = ",".join("?" * len(version_ids))
    return db.q(conn, f"""
      SELECT v.id, v.filename, v.stored_path, d.kind, d.name AS doc_name, v.version_no, v.converted
      FROM versions v JOIN documents d ON d.id = v.document_id
      WHERE v.id IN ({marks})
    """, tuple(version_ids))


def run_build(build_id: int) -> None:
    """同期実行（FastAPI 側でスレッドプールへ投げる）。失敗は builds 行に記録。"""
    conn = db.connect(storage.db_path())
    b = db.one(conn, "SELECT * FROM builds WHERE id=?", (build_id,))
    proj = db.one(conn, "SELECT * FROM projects WHERE id=?", (b["project_id"],))
    req = json.loads(b["result_json"] or "{}")
    # 指定が無い場合は「未変換の最新バージョン」のみ変換対象
    versions = (_selected_versions(conn, req.get("version_ids", []))
                or _pending_versions(conn, b["project_id"]))

    out_root = storage.build_dir(proj["slug"], build_id)
    out_root.mkdir(parents=True, exist_ok=True)
    results = []
    try:
        for v in versions:
            src = Path(v["stored_path"])
            if not src.exists():
                raise FileNotFoundError(f"ソース不在: {src}")
            doc_out = out_root / storage.slugify(v["doc_name"])
            files = convert_file(str(src), str(doc_out), stem=v["doc_name"])
            md_rel = None
            if v["kind"] == "common_spec" and "markdown" in files:
                # SKILL 参照用の固定名: docs/common_spec.md
                md = Path(files["markdown"])
                docs_dir = out_root / "docs"
                docs_dir.mkdir(exist_ok=True)
                fixed = docs_dir / "common_spec.md"
                fixed.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
                md_rel = fixed.relative_to(out_root).as_posix()
            results.append({
                "version_id": v["id"], "doc_name": v["doc_name"], "kind": v["kind"],
                "version_no": v["version_no"], "files": files, "md": md_rel,
            })
            db.execute(conn, "UPDATE versions SET converted=1 WHERE id=?", (v["id"],))
        db.execute(conn, "UPDATE builds SET status='done', finished_at=?, result_json=? WHERE id=?",
                   (db.now(), json.dumps({"documents": results}, ensure_ascii=False), build_id))
    except Exception as e:
        db.execute(conn, "UPDATE builds SET status='failed', finished_at=?, error=? WHERE id=?",
                   (db.now(), str(e), build_id))
