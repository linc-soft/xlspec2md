# -*- coding: utf-8 -*-
"""SQLite 永続化層（stdlib sqlite3、依存最小化）。"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_local = threading.local()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: Path) -> sqlite3.Connection:
    key = str(db_path)
    if not hasattr(_local, key) or _local.__dict__[key] is None:
        conn = sqlite3.connect(key, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _local.__dict__[key] = conn
    return _local.__dict__[key]


def init_db(db_path: Path) -> None:
    conn = connect(db_path)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS projects(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      slug TEXT NOT NULL UNIQUE,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS documents(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      kind TEXT NOT NULL,               -- common_spec | design_book
      name TEXT NOT NULL,
      created_at TEXT NOT NULL,
      UNIQUE(project_id, kind, name)
    );
    CREATE TABLE IF NOT EXISTS versions(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      version_no INTEGER NOT NULL,
      filename TEXT NOT NULL,
      stored_path TEXT NOT NULL,
      uploaded_at TEXT NOT NULL,
      UNIQUE(document_id, version_no)
    );
    CREATE TABLE IF NOT EXISTS builds(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      status TEXT NOT NULL,             -- queued | running | done | failed
      triggered_at TEXT NOT NULL,
      finished_at TEXT,
      error TEXT,
      result_json TEXT
    );
    """)


def q(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


def one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()


def execute(conn, sql, params=()):
    cur = conn.execute(sql, params)
    conn.commit()
    return cur
