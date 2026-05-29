"""SQLite Database – connection management and schema.

Design:
- Single SQLite file at  projects_data/accelerator.db
  (overridable via PROJECTS_DATA_DIR env var)
- WAL mode for concurrent reads
- Thread-local connections (safe for the single-process HTTP server)
- All tables use TEXT primary keys matching existing JSON IDs
- JSON blobs used for flexible fields (metadata, findings, etc.)
- Dual-write mode is controlled by AdminConfig:
    sqlite_write_enabled  (default: True)
    file_write_enabled    (default: True)
"""

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

_DATA_DIR_OVERRIDE = os.environ.get("PROJECTS_DATA_DIR", "")
_BASE_DIR = Path(_DATA_DIR_OVERRIDE) if _DATA_DIR_OVERRIDE else Path("projects_data")

_DB_FILENAME = "accelerator.db"
_thread_local = threading.local()


def db_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    _BASE_DIR.mkdir(parents=True, exist_ok=True)
    return _BASE_DIR / _DB_FILENAME


def get_db() -> "Database":
    """Return a thread-local Database instance, initialising on first access."""
    if not hasattr(_thread_local, "db") or _thread_local.db is None:
        _thread_local.db = Database(db_path())
    return _thread_local.db


# ──────────────────────────────────────────────────────────────
# DDL – Schema
# ──────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ── Projects ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    phase       TEXT DEFAULT 'pre-sales',
    ai_backend  TEXT DEFAULT 'files_only',
    status      TEXT DEFAULT 'active',
    settings    TEXT DEFAULT '{}',      -- JSON
    files       TEXT DEFAULT '[]',      -- JSON list
    file_toggles TEXT DEFAULT '{}',     -- JSON
    iteration   TEXT DEFAULT '{}',      -- JSON
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    archived_at TEXT DEFAULT '',
    restored_at TEXT DEFAULT ''
);

-- ── Phases ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS phases (
    project_id  TEXT NOT NULL,
    phase_id    TEXT NOT NULL,
    label       TEXT NOT NULL,
    phase_order INTEGER DEFAULT 0,
    description TEXT DEFAULT '',
    entered_at  TEXT DEFAULT '',
    exited_at   TEXT DEFAULT '',
    is_current  INTEGER DEFAULT 0,      -- 0/1 boolean
    version_count INTEGER DEFAULT 0,
    review_count  INTEGER DEFAULT 0,
    PRIMARY KEY (project_id, phase_id)
);

-- ── Hierarchy Versions ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS versions (
    version_id          TEXT NOT NULL,
    project_id          TEXT NOT NULL,
    phase_id            TEXT DEFAULT 'pre-sales',
    label               TEXT DEFAULT '',
    persona             TEXT DEFAULT '',
    scope               TEXT DEFAULT '',
    ai_backend          TEXT DEFAULT 'files_only',
    included_artifacts  TEXT DEFAULT '[]',   -- JSON
    excluded_artifacts  TEXT DEFAULT '[]',   -- JSON
    stats               TEXT DEFAULT '{}',   -- JSON
    review_ids          TEXT DEFAULT '[]',   -- JSON list
    active_review_id    TEXT DEFAULT '',
    created_at          TEXT NOT NULL,
    PRIMARY KEY (project_id, version_id)
);
CREATE INDEX IF NOT EXISTS idx_versions_project ON versions(project_id);

-- ── Hierarchy Reviews ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reviews (
    review_id       TEXT NOT NULL,
    project_id      TEXT NOT NULL,
    version_id      TEXT NOT NULL,
    phase_id        TEXT DEFAULT 'pre-sales',
    persona         TEXT DEFAULT '',
    ai_backend      TEXT DEFAULT 'files_only',
    prompt_used     TEXT DEFAULT '',
    custom_prompt   TEXT DEFAULT '',
    output          TEXT DEFAULT '{}',   -- JSON
    findings        TEXT DEFAULT '{}',   -- JSON
    questions       TEXT DEFAULT '[]',   -- JSON
    summary         TEXT DEFAULT '',
    included_files  TEXT DEFAULT '[]',   -- JSON
    categories      TEXT DEFAULT '[]',   -- JSON
    ai_metadata     TEXT DEFAULT '{}',   -- JSON
    deep_dive       TEXT DEFAULT NULL,   -- JSON or NULL
    feedback        TEXT DEFAULT NULL,   -- JSON or NULL  (P9)
    created_at      TEXT NOT NULL,
    PRIMARY KEY (project_id, review_id)
);
CREATE INDEX IF NOT EXISTS idx_reviews_project  ON reviews(project_id);
CREATE INDEX IF NOT EXISTS idx_reviews_version  ON reviews(version_id);

-- ── Artifacts ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT NOT NULL,
    project_id  TEXT NOT NULL,
    type        TEXT DEFAULT 'file',
    file_name   TEXT DEFAULT '',
    title       TEXT DEFAULT '',
    category    TEXT DEFAULT 'project_artefact',
    metadata    TEXT DEFAULT '{}',  -- JSON
    include     INTEGER DEFAULT 1,
    status      TEXT DEFAULT 'ingested',
    raw_path    TEXT DEFAULT '',
    text_content TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    PRIMARY KEY (project_id, artifact_id)
);
CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);

-- ── Proposals ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS proposals (
    project_id      TEXT PRIMARY KEY,
    proposal_name   TEXT DEFAULT '',
    client          TEXT DEFAULT '',
    current_version TEXT DEFAULT '',
    total_versions  INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proposal_versions (
    version_id              TEXT NOT NULL,
    project_id              TEXT NOT NULL,
    version_number          INTEGER DEFAULT 1,
    label                   TEXT DEFAULT '',
    status                  TEXT DEFAULT 'draft',
    files                   TEXT DEFAULT '[]',   -- JSON
    notes                   TEXT DEFAULT '',
    changes_from_previous   TEXT DEFAULT '',
    context_version         TEXT DEFAULT '',
    feedback                TEXT DEFAULT NULL,   -- JSON  (P9)
    created_at              TEXT NOT NULL,
    PRIMARY KEY (project_id, version_id)
);

-- ── Jobs ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    job_id      TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    project_id  TEXT NOT NULL,
    status      TEXT DEFAULT 'queued',
    started_at  TEXT DEFAULT NULL,
    ended_at    TEXT DEFAULT NULL,
    error       TEXT DEFAULT NULL,
    created_at  TEXT NOT NULL
);

-- ── Pre-sales Feedback (P9) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS presales_feedback (
    feedback_id     TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    proposal_ver_id TEXT DEFAULT '',   -- links to proposal_versions
    review_id       TEXT DEFAULT '',   -- links to reviews
    source          TEXT DEFAULT 'internal',  -- 'internal' | 'external'
    responder_name  TEXT DEFAULT '',
    responder_email TEXT DEFAULT '',
    accepted        TEXT DEFAULT '[]', -- JSON list of accepted items
    rejected        TEXT DEFAULT '[]', -- JSON list of rejected items
    concerns        TEXT DEFAULT '[]', -- JSON list of concerns
    notes           TEXT DEFAULT '',
    next_action     TEXT DEFAULT '',
    status          TEXT DEFAULT 'open', -- open | actioned | closed
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_project ON presales_feedback(project_id);

-- ── External Feedback Tokens (P9) ────────────────────────────
CREATE TABLE IF NOT EXISTS feedback_tokens (
    token           TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    proposal_ver_id TEXT DEFAULT '',
    review_id       TEXT DEFAULT '',
    expires_at      TEXT DEFAULT '',
    used            INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);
"""


# ──────────────────────────────────────────────────────────────
# Database class
# ──────────────────────────────────────────────────────────────

class Database:
    """Thin wrapper around a sqlite3 connection with schema auto-init."""

    def __init__(self, path: Path):
        self.path = path
        self._conn: Optional[sqlite3.Connection] = None
        self._init()

    # ── Connection ──

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Schema ──

    def _init(self) -> None:
        """Create tables if they don't exist."""
        conn = self.conn
        conn.executescript(_SCHEMA_SQL)
        conn.commit()

    # ── Query helpers ──

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        return self.conn.executemany(sql, params_list)

    def commit(self) -> None:
        self.conn.commit()

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ── JSON helpers ──

    @staticmethod
    def jdump(val: Any) -> str:
        """Encode a Python object to a JSON string for storage."""
        if val is None:
            return "null"
        return json.dumps(val, ensure_ascii=False)

    @staticmethod
    def jload(s: Optional[str], default: Any = None) -> Any:
        """Decode a JSON string from storage, returning default on error."""
        if s is None or s == "null":
            return default
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return default
