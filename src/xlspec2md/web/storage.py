# -*- coding: utf-8 -*-
"""ストレージ: DATA_DIR 配下のファイル配置を管理。"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[4] / "data"  # リポジトリ/data（Docker では /data に上書き）


def set_data_dir(p: str | Path) -> None:
    global DATA_DIR
    DATA_DIR = Path(p)


def get_data_dir() -> Path:
    return DATA_DIR


def db_path() -> Path:
    return DATA_DIR / "xlspec2md.db"


def slugify(name: str) -> str:
    s = re.sub(r"[^\w一-鿿-]+", "_", name.strip())
    return s.strip("_") or "project"


def project_dir(slug: str) -> Path:
    return DATA_DIR / "projects" / slug


def sources_dir(slug: str, doc_name: str) -> Path:
    return project_dir(slug) / "sources" / slugify(doc_name)


def build_dir(slug: str, build_id: int) -> Path:
    return project_dir(slug) / "builds" / str(build_id)


def next_version_path(slug: str, doc_name: str, filename: str) -> tuple[Path, int]:
    """sources/<doc>/vN__<filename> のパスと N を返す。"""
    d = sources_dir(slug, doc_name)
    d.mkdir(parents=True, exist_ok=True)
    n = 1
    for p in sorted(d.glob("v*__*")):
        try:
            n = max(n, int(p.name.split("__", 1)[0][1:]) + 1)
        except ValueError:
            continue
    return d / f"v{n}__{filename}", n


def list_versions(slug: str, doc_name: str) -> list[Path]:
    d = sources_dir(slug, doc_name)
    return sorted(d.glob("v*__*")) if d.exists() else []
