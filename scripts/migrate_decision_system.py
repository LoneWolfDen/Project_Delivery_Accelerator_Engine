#!/usr/bin/env python3
"""DS-01 – Decision System Schema Migration.

Idempotent: safe to run multiple times against the same database.
Each step checks whether the column/table already exists before acting.

What this script does
─────────────────────
1.  ADD new columns to `reviews`
        completeness_score, quality_status, completed_by, completed_at, decided_by

2.  ADD new columns to `proposal_versions`
        hierarchy_version_id, active_review_id, previous_version_id,
        feedback_applied, changes_summary, quality_status, quality_score,
        completed_by, completed_at, lock_status, lock_reason

3.  ADD new columns to `presales_feedback`
        feedback_items, raw_text, change_requested

4.  CREATE new tables (IF NOT EXISTS)
        proposal_documents, decision_log

5.  MIGRATE existing presales_feedback rows
        Convert flat accepted/rejected/concerns lists → structured feedback_items
        Each item gets: category, status=new, confidence=medium, mapped_to=null,
        is_critical=false, addressed_in_version=null

6.  MIGRATE existing reviews rows
        Set completeness_score based on findings coverage (pre-computed)
        Set quality_status = 'pending' (default – no existing review was gated)

Usage
─────
    python3 scripts/migrate_decision_system.py [--db PATH]

    --db PATH   Override path to accelerator.db (default: projects_data/accelerator.db)
"""

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_columns(conn: sqlite3.Connection, table: str) -> set:
    """Return the set of existing column names for a table."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def add_column_if_missing(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
    log: list,
) -> None:
    """ALTER TABLE … ADD COLUMN if the column is absent."""
    if column not in get_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        log.append(f"  + {table}.{column}")
    else:
        log.append(f"  ~ {table}.{column} already exists (skipped)")


def jload(s, default=None):
    if s is None or s == "null":
        return default
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default


def jdump(val) -> str:
    if val is None:
        return "null"
    return json.dumps(val, ensure_ascii=False)


# ──────────────────────────────────────────────────────────────
# Step helpers
# ──────────────────────────────────────────────────────────────

def step_reviews(conn: sqlite3.Connection, log: list) -> None:
    """Add DS-01 quality-gate columns to `reviews`."""
    log.append("\n[Step 1] reviews — adding quality gate columns")
    cols = [
        ("completeness_score", "INTEGER DEFAULT 0"),
        ("quality_status",     "TEXT DEFAULT 'pending'"),
        ("completed_by",       "TEXT DEFAULT ''"),
        ("completed_at",       "TEXT DEFAULT ''"),
        ("decided_by",         "TEXT DEFAULT ''"),
    ]
    for col, defn in cols:
        add_column_if_missing(conn, "reviews", col, defn, log)
    conn.commit()


def step_proposal_versions(conn: sqlite3.Connection, log: list) -> None:
    """Add DS-01 traceability + quality + lock columns to `proposal_versions`."""
    log.append("\n[Step 2] proposal_versions — adding traceability/quality/lock columns")
    cols = [
        ("hierarchy_version_id", "TEXT DEFAULT ''"),
        ("active_review_id",     "TEXT DEFAULT ''"),
        ("previous_version_id",  "TEXT DEFAULT ''"),
        ("feedback_applied",     "TEXT DEFAULT '[]'"),
        ("changes_summary",      "TEXT DEFAULT ''"),
        ("quality_status",       "TEXT DEFAULT 'draft'"),
        ("quality_score",        "INTEGER DEFAULT 0"),
        ("completed_by",         "TEXT DEFAULT ''"),
        ("completed_at",         "TEXT DEFAULT ''"),
        ("lock_status",          "TEXT DEFAULT 'unlocked'"),
        ("lock_reason",          "TEXT DEFAULT ''"),
    ]
    for col, defn in cols:
        add_column_if_missing(conn, "proposal_versions", col, defn, log)
    conn.commit()


def step_presales_feedback(conn: sqlite3.Connection, log: list) -> None:
    """Add DS-01 structured feedback columns to `presales_feedback`."""
    log.append("\n[Step 3] presales_feedback — adding structured feedback columns")
    cols = [
        ("feedback_items",   "TEXT DEFAULT '[]'"),
        ("raw_text",         "TEXT DEFAULT ''"),
        ("change_requested", "TEXT DEFAULT '[]'"),
    ]
    for col, defn in cols:
        add_column_if_missing(conn, "presales_feedback", col, defn, log)
    conn.commit()


def step_create_proposal_documents(conn: sqlite3.Connection, log: list) -> None:
    """Create `proposal_documents` table if it does not exist."""
    log.append("\n[Step 4a] proposal_documents — CREATE TABLE IF NOT EXISTS")
    if table_exists(conn, "proposal_documents"):
        log.append("  ~ table already exists (skipped)")
        return
    conn.execute("""
        CREATE TABLE IF NOT EXISTS proposal_documents (
            doc_id               TEXT PRIMARY KEY,
            project_id           TEXT NOT NULL,
            proposal_ver_id      TEXT NOT NULL,
            generated_at         TEXT NOT NULL,
            ai_backend           TEXT DEFAULT 'files_only',
            exec_summary         TEXT DEFAULT '',
            scope                TEXT DEFAULT '',
            delivery_phases      TEXT DEFAULT '[]',
            gantt_data           TEXT DEFAULT '[]',
            risks                TEXT DEFAULT '[]',
            assumptions          TEXT DEFAULT '[]',
            exclusions           TEXT DEFAULT '[]',
            responsibilities     TEXT DEFAULT '{}',
            acceptance_criteria  TEXT DEFAULT '[]',
            version_label        TEXT DEFAULT '',
            review_persona       TEXT DEFAULT '',
            hierarchy_version_id TEXT DEFAULT '',
            active_review_id     TEXT DEFAULT '',
            word_count           INTEGER DEFAULT 0
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_propdocs_project ON proposal_documents(project_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_propdocs_ver ON proposal_documents(proposal_ver_id)"
    )
    conn.commit()
    log.append("  + proposal_documents created")


def step_create_decision_log(conn: sqlite3.Connection, log: list) -> None:
    """Create `decision_log` table if it does not exist."""
    log.append("\n[Step 4b] decision_log — CREATE TABLE IF NOT EXISTS")
    if table_exists(conn, "decision_log"):
        log.append("  ~ table already exists (skipped)")
        return
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decision_log (
            log_id      TEXT PRIMARY KEY,
            project_id  TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id   TEXT NOT NULL,
            action      TEXT NOT NULL,
            actor       TEXT DEFAULT '',
            reason      TEXT DEFAULT '',
            metadata    TEXT DEFAULT '{}',
            created_at  TEXT NOT NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_declog_project ON decision_log(project_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_declog_entity ON decision_log(entity_id)"
    )
    conn.commit()
    log.append("  + decision_log created")


# ──────────────────────────────────────────────────────────────
# Data migrations
# ──────────────────────────────────────────────────────────────

def _build_feedback_items(
    accepted: list, rejected: list, concerns: list
) -> list:
    """Convert flat accepted/rejected/concerns lists into FeedbackItem dicts."""
    items = []
    mapping = [
        (accepted,  "accepted"),
        (rejected,  "rejected"),
        (concerns,  "concerns"),
    ]
    for lst, category in mapping:
        for text in lst:
            text = text.strip()
            if not text:
                continue
            items.append({
                "item_id":              f"fi_{uuid.uuid4().hex[:8]}",
                "text":                 text,
                "category":             category,
                "mapped_to":            None,
                "confidence":           "medium",
                "status":               "new",
                "is_critical":          False,
                "addressed_in_version": None,
                "created_at":           now_iso(),
            })
    return items


def step_migrate_feedback_rows(conn: sqlite3.Connection, log: list) -> None:
    """Populate feedback_items from existing flat lists where feedback_items is empty."""
    log.append("\n[Step 5] presales_feedback — migrating flat lists → feedback_items")

    rows = conn.execute(
        "SELECT feedback_id, accepted, rejected, concerns, feedback_items FROM presales_feedback"
    ).fetchall()

    migrated = 0
    skipped = 0
    for row in rows:
        fid        = row[0]
        accepted   = jload(row[1], [])
        rejected   = jload(row[2], [])
        concerns   = jload(row[3], [])
        existing   = jload(row[4], [])

        # Only migrate rows that haven't been converted yet (feedback_items is empty)
        if existing:
            skipped += 1
            continue

        items = _build_feedback_items(accepted, rejected, concerns)
        # Extract change_requested (none in legacy data — placeholder)
        change_req = [i for i in items if i["category"] == "change_requested"]

        conn.execute(
            "UPDATE presales_feedback SET feedback_items=?, change_requested=? WHERE feedback_id=?",
            (jdump(items), jdump(change_req), fid),
        )
        migrated += 1

    conn.commit()
    log.append(f"  + migrated {migrated} rows, skipped {skipped} (already converted)")


def _compute_completeness_score(findings_json: str) -> int:
    """Compute a 0-100 completeness score from review findings.

    Checks 5 standard categories. Each present category with ≥1 item = 20 points.
    """
    findings = jload(findings_json, {})
    if not findings:
        return 0
    standard = ["risks", "assumptions", "dependencies", "constraints", "action_items"]
    score = 0
    for cat in standard:
        items = findings.get(cat, [])
        if isinstance(items, list) and len(items) > 0:
            score += 20
    return score


def step_migrate_review_scores(conn: sqlite3.Connection, log: list) -> None:
    """Back-fill completeness_score for existing reviews where score is still 0."""
    log.append("\n[Step 6] reviews — back-filling completeness_score")

    rows = conn.execute(
        "SELECT review_id, project_id, findings, completeness_score FROM reviews"
    ).fetchall()

    updated = 0
    for row in rows:
        rid, pid, findings_raw, existing_score = row
        if existing_score and existing_score > 0:
            continue  # already computed
        score = _compute_completeness_score(findings_raw or "{}")
        conn.execute(
            "UPDATE reviews SET completeness_score=? WHERE project_id=? AND review_id=?",
            (score, pid, rid),
        )
        updated += 1

    conn.commit()
    log.append(f"  + updated completeness_score for {updated} reviews")


# ──────────────────────────────────────────────────────────────
# Verification
# ──────────────────────────────────────────────────────────────

EXPECTED_COLUMNS = {
    "reviews": {
        "completeness_score", "quality_status", "completed_by",
        "completed_at", "decided_by",
    },
    "proposal_versions": {
        "hierarchy_version_id", "active_review_id", "previous_version_id",
        "feedback_applied", "changes_summary", "quality_status", "quality_score",
        "completed_by", "completed_at", "lock_status", "lock_reason",
    },
    "presales_feedback": {
        "feedback_items", "raw_text", "change_requested",
    },
}

EXPECTED_TABLES = {"proposal_documents", "decision_log"}


def verify(conn: sqlite3.Connection, log: list) -> bool:
    log.append("\n[Verify] Checking schema…")
    ok = True

    for table, cols in EXPECTED_COLUMNS.items():
        existing = get_columns(conn, table)
        for col in cols:
            if col not in existing:
                log.append(f"  ✗ MISSING: {table}.{col}")
                ok = False
            else:
                log.append(f"  ✓ {table}.{col}")

    for table in EXPECTED_TABLES:
        if table_exists(conn, table):
            log.append(f"  ✓ table {table}")
        else:
            log.append(f"  ✗ MISSING table: {table}")
            ok = False

    # Spot-check data integrity: every presales_feedback row should parse
    rows = conn.execute(
        "SELECT feedback_id, feedback_items FROM presales_feedback"
    ).fetchall()
    for row in rows:
        items = jload(row[1], None)
        if items is None:
            log.append(f"  ✗ feedback_items unparseable for feedback_id={row[0]}")
            ok = False

    return ok


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

def run(db_file: Path) -> bool:
    log = []
    log.append(f"DS-01 Migration — {now_iso()}")
    log.append(f"Target DB: {db_file}")

    if not db_file.exists():
        log.append("  DB file not found — nothing to migrate (fresh install will use new schema)")
        print("\n".join(log))
        return True

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

    try:
        # Schema changes
        step_reviews(conn, log)
        step_proposal_versions(conn, log)
        step_presales_feedback(conn, log)
        step_create_proposal_documents(conn, log)
        step_create_decision_log(conn, log)

        # Data migrations
        step_migrate_feedback_rows(conn, log)
        step_migrate_review_scores(conn, log)

        # Verify
        ok = verify(conn, log)

        log.append("\n" + ("✅  Migration succeeded." if ok else "❌  Migration completed with errors — see above."))

    except Exception as exc:
        log.append(f"\n❌  Migration failed: {exc}")
        import traceback
        log.append(traceback.format_exc())
        ok = False
    finally:
        conn.close()

    print("\n".join(log))
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="DS-01 schema migration")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to accelerator.db (default: projects_data/accelerator.db)",
    )
    args = parser.parse_args()

    if args.db:
        db_file = args.db
    else:
        override = __import__("os").environ.get("PROJECTS_DATA_DIR", "")
        base = Path(override) if override else Path("projects_data")
        db_file = base / "accelerator.db"

    success = run(db_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
