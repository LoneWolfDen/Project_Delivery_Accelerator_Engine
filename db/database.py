"""SQLite database — connection management and schema auto-init.

Dual-write mode controlled by AdminConfig (sqlite_write_enabled / file_write_enabled).
Migrations applied automatically on startup via _apply_migrations().
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
# DDL – Schema  (CREATE TABLE IF NOT EXISTS = safe to re-run)
# New columns are added via ALTER TABLE in the migration script;
# they appear here so fresh installs get the full schema immediately.
# ──────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ── Projects ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT DEFAULT '',
    phase        TEXT DEFAULT 'pre-sales',
    ai_backend   TEXT DEFAULT 'files_only',
    status       TEXT DEFAULT 'active',
    settings     TEXT DEFAULT '{}',
    files        TEXT DEFAULT '[]',
    file_toggles TEXT DEFAULT '{}',
    iteration    TEXT DEFAULT '{}',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    archived_at  TEXT DEFAULT '',
    restored_at  TEXT DEFAULT ''
);

-- ── Phases ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS phases (
    project_id    TEXT NOT NULL,
    phase_id      TEXT NOT NULL,
    label         TEXT NOT NULL,
    phase_order   INTEGER DEFAULT 0,
    description   TEXT DEFAULT '',
    entered_at    TEXT DEFAULT '',
    exited_at     TEXT DEFAULT '',
    is_current    INTEGER DEFAULT 0,
    version_count INTEGER DEFAULT 0,
    review_count  INTEGER DEFAULT 0,
    PRIMARY KEY (project_id, phase_id)
);

-- ── Hierarchy Versions ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS versions (
    version_id         TEXT NOT NULL,
    project_id         TEXT NOT NULL,
    phase_id           TEXT DEFAULT 'pre-sales',
    label              TEXT DEFAULT '',
    persona            TEXT DEFAULT '',
    scope              TEXT DEFAULT '',
    ai_backend         TEXT DEFAULT 'files_only',
    included_artifacts TEXT DEFAULT '[]',
    excluded_artifacts TEXT DEFAULT '[]',
    stats              TEXT DEFAULT '{}',
    review_ids         TEXT DEFAULT '[]',
    active_review_id   TEXT DEFAULT '',
    created_at         TEXT NOT NULL,
    PRIMARY KEY (project_id, version_id)
);
CREATE INDEX IF NOT EXISTS idx_versions_project ON versions(project_id);

-- ── Hierarchy Reviews ─────────────────────────────────────────
-- DS-01: added completeness_score, quality_status, completed_by,
--        completed_at, decided_by
CREATE TABLE IF NOT EXISTS reviews (
    review_id          TEXT NOT NULL,
    project_id         TEXT NOT NULL,
    version_id         TEXT NOT NULL,
    phase_id           TEXT DEFAULT 'pre-sales',
    persona            TEXT DEFAULT '',
    ai_backend         TEXT DEFAULT 'files_only',
    prompt_used        TEXT DEFAULT '',
    custom_prompt      TEXT DEFAULT '',
    output             TEXT DEFAULT '{}',
    findings           TEXT DEFAULT '{}',
    questions          TEXT DEFAULT '[]',
    summary            TEXT DEFAULT '',
    included_files     TEXT DEFAULT '[]',
    categories         TEXT DEFAULT '[]',
    ai_metadata        TEXT DEFAULT '{}',
    deep_dive          TEXT DEFAULT NULL,
    feedback           TEXT DEFAULT NULL,
    -- DS-01 quality gate fields
    completeness_score INTEGER DEFAULT 0,
    quality_status     TEXT DEFAULT 'pending',  -- pending | interim | complete
    completed_by       TEXT DEFAULT '',
    completed_at       TEXT DEFAULT '',
    decided_by         TEXT DEFAULT '',         -- who set this as active review
    -- S1: review chaining
    previous_review_id TEXT DEFAULT '',
    created_at         TEXT NOT NULL,
    PRIMARY KEY (project_id, review_id)
);
CREATE INDEX IF NOT EXISTS idx_reviews_project ON reviews(project_id);
CREATE INDEX IF NOT EXISTS idx_reviews_version  ON reviews(version_id);

-- ── Artifacts ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id  TEXT NOT NULL,
    project_id   TEXT NOT NULL,
    type         TEXT DEFAULT 'file',
    file_name    TEXT DEFAULT '',
    title        TEXT DEFAULT '',
    category     TEXT DEFAULT 'project_artefact',
    metadata     TEXT DEFAULT '{}',
    include      INTEGER DEFAULT 1,
    status       TEXT DEFAULT 'ingested',
    raw_path     TEXT DEFAULT '',
    text_content TEXT DEFAULT '',
    created_at   TEXT NOT NULL,
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

-- DS-01: added hierarchy_version_id, active_review_id, previous_version_id,
--        feedback_applied, quality_status, quality_score, completed_by,
--        completed_at, lock_status, lock_reason
CREATE TABLE IF NOT EXISTS proposal_versions (
    version_id           TEXT NOT NULL,
    project_id           TEXT NOT NULL,
    version_number       INTEGER DEFAULT 1,
    label                TEXT DEFAULT '',
    status               TEXT DEFAULT 'draft',
    files                TEXT DEFAULT '[]',
    notes                TEXT DEFAULT '',
    changes_from_previous TEXT DEFAULT '',
    context_version      TEXT DEFAULT '',
    feedback             TEXT DEFAULT NULL,
    -- DS-01 traceability
    hierarchy_version_id TEXT DEFAULT '',    -- FK → versions.version_id
    active_review_id     TEXT DEFAULT '',    -- FK → reviews.review_id
    previous_version_id  TEXT DEFAULT '',    -- FK → proposal_versions.version_id
    feedback_applied     TEXT DEFAULT '[]',  -- JSON list of feedback_ids resolved
    changes_summary      TEXT DEFAULT '',    -- human summary of what changed
    -- DS-01 quality + lock
    quality_status       TEXT DEFAULT 'draft',  -- draft | interim | complete
    quality_score        INTEGER DEFAULT 0,
    completed_by         TEXT DEFAULT '',
    completed_at         TEXT DEFAULT '',
    lock_status          TEXT DEFAULT 'unlocked',  -- unlocked | soft_locked
    lock_reason          TEXT DEFAULT '',
    created_at           TEXT NOT NULL,
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

-- ── Pre-sales Feedback ────────────────────────────────────────
-- DS-01: added feedback_items (structured), raw_text, change_requested.
--        accepted/rejected/concerns kept as backward-compat computed columns.
CREATE TABLE IF NOT EXISTS presales_feedback (
    feedback_id      TEXT PRIMARY KEY,
    project_id       TEXT NOT NULL,
    proposal_ver_id  TEXT DEFAULT '',
    review_id        TEXT DEFAULT '',
    source           TEXT DEFAULT 'internal',  -- internal | external
    responder_name   TEXT DEFAULT '',
    responder_email  TEXT DEFAULT '',
    -- DS-01 structured items (replaces flat lists as primary store)
    feedback_items   TEXT DEFAULT '[]',  -- JSON: List[FeedbackItem]
    raw_text         TEXT DEFAULT '',    -- original pasted text (hybrid tagger)
    change_requested TEXT DEFAULT '[]',  -- JSON: extracted for fast queries
    -- backward-compat flat lists (kept, populated from feedback_items on write)
    accepted         TEXT DEFAULT '[]',
    rejected         TEXT DEFAULT '[]',
    concerns         TEXT DEFAULT '[]',
    -- housekeeping
    notes            TEXT DEFAULT '',
    next_action      TEXT DEFAULT '',
    status           TEXT DEFAULT 'open',  -- open | actioned | closed
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_project ON presales_feedback(project_id);

-- ── External Feedback Tokens ──────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback_tokens (
    token           TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    proposal_ver_id TEXT DEFAULT '',
    review_id       TEXT DEFAULT '',
    expires_at      TEXT DEFAULT '',
    used            INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);

-- ── Proposal Documents (DS-01) ────────────────────────────────
-- Each row is a generated document for one proposal_version.
CREATE TABLE IF NOT EXISTS proposal_documents (
    doc_id              TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL,
    proposal_ver_id     TEXT NOT NULL,
    generated_at        TEXT NOT NULL,
    ai_backend          TEXT DEFAULT 'files_only',
    -- document sections (all JSON or plain text)
    exec_summary        TEXT DEFAULT '',
    scope               TEXT DEFAULT '',
    delivery_phases     TEXT DEFAULT '[]',  -- [{phase, description, duration_weeks}]
    gantt_data          TEXT DEFAULT '[]',  -- [{milestone, start_week, end_week, owner}]
    risks               TEXT DEFAULT '[]',  -- [{risk, category, impact, probability, mitigation}]
    assumptions         TEXT DEFAULT '[]',  -- [{category, assumption}]
    exclusions          TEXT DEFAULT '[]',  -- [str]
    responsibilities    TEXT DEFAULT '{}',  -- RACI matrix JSON
    acceptance_criteria TEXT DEFAULT '[]',  -- [str]
    -- metadata
    version_label       TEXT DEFAULT '',
    review_persona      TEXT DEFAULT '',
    hierarchy_version_id TEXT DEFAULT '',
    active_review_id    TEXT DEFAULT '',
    word_count          INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_propdocs_project ON proposal_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_propdocs_ver     ON proposal_documents(proposal_ver_id);

-- ── Decision Log (DS-01) ──────────────────────────────────────
-- Immutable audit trail: one row per gate pass, lock, or finalisation.
CREATE TABLE IF NOT EXISTS decision_log (
    log_id      TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    entity_type TEXT NOT NULL,  -- review | proposal_version | feedback_item | finalisation
    entity_id   TEXT NOT NULL,
    action      TEXT NOT NULL,  -- completed | set_active | generated | feedback_structured |
                                --  finalised | lock_overridden | gate_passed | gate_failed
    actor       TEXT DEFAULT '',
    reason      TEXT DEFAULT '',
    metadata    TEXT DEFAULT '{}',  -- JSON snapshot at time of decision
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_declog_project ON decision_log(project_id);
CREATE INDEX IF NOT EXISTS idx_declog_entity  ON decision_log(entity_id);
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
        """Create tables if they don't exist, then apply pending column migrations."""
        conn = self.conn
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        self._apply_migrations()

    def _apply_migrations(self) -> None:
        """Idempotent column migrations for schema upgrades on existing databases.

        SQLite does not support IF NOT EXISTS on ALTER TABLE ADD COLUMN, so we
        check PRAGMA table_info() first and skip columns that already exist.
        Safe to run on every startup against both fresh and upgraded databases.
        """
        conn = self.conn

        def _existing_cols(table: str) -> set:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return {r[1] for r in rows}

        # ── reviews: DS-01 quality-gate columns ──────────────────────────────
        rev_cols = _existing_cols("reviews")
        for col, definition in [
            ("completeness_score",  "INTEGER DEFAULT 0"),
            ("quality_status",      "TEXT DEFAULT 'pending'"),
            ("completed_by",        "TEXT DEFAULT ''"),
            ("completed_at",        "TEXT DEFAULT ''"),
            ("decided_by",          "TEXT DEFAULT ''"),
            ("deep_dive",           "TEXT DEFAULT NULL"),
            ("feedback",            "TEXT DEFAULT NULL"),
            # S1: review chaining
            ("previous_review_id",  "TEXT DEFAULT ''"),
            # S2: prompt builder state
            ("prompt_builder_state", "TEXT DEFAULT NULL"),
            # S4: weakness and gap intelligence
            ("weaknesses",          "TEXT DEFAULT '[]'"),
        ]:
            if col not in rev_cols:
                conn.execute(f"ALTER TABLE reviews ADD COLUMN {col} {definition}")

        # ── proposal_versions: DS-01 / DS-07 extended columns ────────────────
        pv_cols = _existing_cols("proposal_versions")
        for col, definition in [
            ("hierarchy_version_id", "TEXT DEFAULT ''"),
            ("active_review_id",     "TEXT DEFAULT ''"),
            ("previous_version_id",  "TEXT DEFAULT ''"),
            ("feedback_applied",     "TEXT DEFAULT '[]'"),   # was INTEGER — corrected
            ("changes_summary",      "TEXT DEFAULT ''"),     # missing from original migration
            ("quality_status",       "TEXT DEFAULT 'draft'"),
            ("quality_score",        "INTEGER DEFAULT 0"),
            ("completed_by",         "TEXT DEFAULT ''"),
            ("completed_at",         "TEXT DEFAULT ''"),
            ("lock_status",          "TEXT DEFAULT 'unlocked'"),
            ("lock_reason",          "TEXT DEFAULT ''"),
        ]:
            if col not in pv_cols:
                conn.execute(f"ALTER TABLE proposal_versions ADD COLUMN {col} {definition}")

        # ── presales_feedback: DS-01 structured feedback ──────────────────────
        pf_cols = _existing_cols("presales_feedback")
        for col, definition in [
            ("feedback_items",   "TEXT DEFAULT '[]'"),
            ("raw_text",         "TEXT DEFAULT ''"),
            ("change_requested", "INTEGER DEFAULT 0"),
        ]:
            if col not in pf_cols:
                conn.execute(f"ALTER TABLE presales_feedback ADD COLUMN {col} {definition}")

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
