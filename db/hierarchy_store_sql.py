"""SQLite-backed HierarchyStore – drop-in replacement for models/hierarchy.py HierarchyStore.

Dual-write: when both sqlite_write_enabled and file_write_enabled are True (default)
the store writes to both SQLite and the flat-file layout so the existing code paths
remain intact.

Read preference: SQLite when sqlite_write_enabled, else file fallback.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from db.database import get_db, Database

PROJECTS_DIR = Path("projects_data")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dual_write_flags() -> tuple[bool, bool]:
    """Return (sqlite_enabled, file_enabled) from AdminConfig."""
    try:
        from admin.config import load_config
        cfg = load_config()
        return getattr(cfg, "sqlite_write_enabled", True), getattr(cfg, "file_write_enabled", True)
    except Exception:
        return True, True


# ── Standard phases seeded on first access ────────────────────
STANDARD_PHASES = [
    {"id": "pre-sales", "label": "Pre-sales",  "order": 1, "description": "Client engagement, proposals, scoping"},
    {"id": "design",    "label": "Design",      "order": 2, "description": "Architecture, solution design, planning"},
    {"id": "delivery",  "label": "Delivery",    "order": 3, "description": "Execution, development, implementation"},
    {"id": "support",   "label": "Support",     "order": 4, "description": "Operations, maintenance, handover"},
]


class HierarchyStoreSQLite:
    """Phase → Version → Review persistence backed by SQLite with optional file dual-write."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.base_dir = PROJECTS_DIR / project_id / "hierarchy"
        self._ensure_phases()

    # ── Internal helpers ──────────────────────────────────────

    @property
    def _db(self) -> Database:
        return get_db()

    def _ensure_phases(self) -> None:
        """Seed standard phases for this project if not present."""
        db = self._db
        rows = db.fetchall(
            "SELECT phase_id FROM phases WHERE project_id=?", (self.project_id,)
        )
        if rows:
            return
        for sp in STANDARD_PHASES:
            db.execute(
                """INSERT OR IGNORE INTO phases
                   (project_id, phase_id, label, phase_order, description,
                    entered_at, exited_at, is_current, version_count, review_count)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    self.project_id, sp["id"], sp["label"], sp["order"],
                    sp["description"], "", "", 1 if sp["id"] == "pre-sales" else 0, 0, 0,
                ),
            )
        db.commit()
        self._file_seed_phases()

    def _file_seed_phases(self) -> None:
        """Write initial phases.json for file fallback."""
        _, file_on = _dual_write_flags()
        if not file_on:
            return
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "versions").mkdir(exist_ok=True)
        (self.base_dir / "reviews").mkdir(exist_ok=True)
        phases_file = self.base_dir / "phases.json"
        if phases_file.exists():
            return
        phases = []
        for sp in STANDARD_PHASES:
            phases.append({
                **sp,
                "entered_at": "", "exited_at": "",
                "is_current": sp["id"] == "pre-sales",
                "version_count": 0, "review_count": 0,
            })
        with open(phases_file, "w") as f:
            json.dump(phases, f, indent=2)

    # ── Phase operations ──────────────────────────────────────

    def get_phases(self) -> List[Dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT * FROM phases WHERE project_id=? ORDER BY phase_order", (self.project_id,)
        )
        if not rows:
            self._ensure_phases()
            rows = self._db.fetchall(
                "SELECT * FROM phases WHERE project_id=? ORDER BY phase_order", (self.project_id,)
            )
        return [self._phase_row_to_dict(r) for r in rows]

    def get_current_phase(self) -> str:
        row = self._db.fetchone(
            "SELECT phase_id FROM phases WHERE project_id=? AND is_current=1 LIMIT 1",
            (self.project_id,),
        )
        return row["phase_id"] if row else "pre-sales"

    def set_current_phase(self, phase_id: str, reason: str = "") -> Dict[str, Any]:
        db = self._db
        now = _now_iso()
        db.execute(
            "UPDATE phases SET is_current=0, exited_at=? WHERE project_id=? AND is_current=1",
            (now, self.project_id),
        )
        db.execute(
            "UPDATE phases SET is_current=1, entered_at=? WHERE project_id=? AND phase_id=?",
            (now, self.project_id, phase_id),
        )
        db.commit()
        self._file_save_phases()
        return {"phase_id": phase_id, "transitioned_at": now, "reason": reason}

    def _increment_phase_count(self, phase_id: str, field: str) -> None:
        col = "version_count" if field == "version_count" else "review_count"
        self._db.execute(
            f"UPDATE phases SET {col}={col}+1 WHERE project_id=? AND phase_id=?",
            (self.project_id, phase_id),
        )
        self._db.commit()
        self._file_save_phases()

    def _decrement_phase_count(self, phase_id: str, field: str) -> None:
        col = "version_count" if field == "version_count" else "review_count"
        self._db.execute(
            f"UPDATE phases SET {col}=MAX(0,{col}-1) WHERE project_id=? AND phase_id=?",
            (self.project_id, phase_id),
        )
        self._db.commit()
        self._file_save_phases()

    def _file_save_phases(self) -> None:
        _, file_on = _dual_write_flags()
        if not file_on:
            return
        phases_file = self.base_dir / "phases.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with open(phases_file, "w") as f:
            json.dump(self.get_phases(), f, indent=2)

    # ── Version operations ────────────────────────────────────

    def create_version(
        self,
        included_artifacts: List[Dict[str, Any]],
        excluded_artifacts: Optional[List[Dict[str, Any]]] = None,
        persona: str = "",
        scope: str = "",
        ai_backend: str = "files_only",
        label: str = "",
        stats: Optional[Dict[str, int]] = None,
    ):
        from models.hierarchy import Version  # noqa: PLC0415 – avoid circular
        db = self._db
        phase_id = self.get_current_phase()

        # Derive version number from existing count
        count = db.fetchone(
            "SELECT COUNT(*) as cnt FROM versions WHERE project_id=?", (self.project_id,)
        )
        version_num = (count["cnt"] if count else 0) + 1
        version_id = f"v{version_num}"
        now = _now_iso()

        db.execute(
            """INSERT OR REPLACE INTO versions
               (version_id, project_id, phase_id, label, persona, scope, ai_backend,
                included_artifacts, excluded_artifacts, stats, review_ids, active_review_id, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                version_id, self.project_id, phase_id,
                label or f"Version {version_num}",
                persona, (scope or "")[:2000], ai_backend,
                Database.jdump(included_artifacts or []),
                Database.jdump(excluded_artifacts or []),
                Database.jdump(stats or {}),
                Database.jdump([]),
                "", now,
            ),
        )
        db.commit()
        self._increment_phase_count(phase_id, "version_count")

        version = Version(
            version_id=version_id,
            project_id=self.project_id,
            phase_id=phase_id,
            label=label or f"Version {version_num}",
            created_at=now,
            included_artifacts=included_artifacts or [],
            excluded_artifacts=excluded_artifacts or [],
            persona=persona,
            scope=(scope or "")[:2000],
            ai_backend=ai_backend,
            stats=stats or {},
        )
        self._file_save_version(version)
        return version

    def get_version(self, version_id: str):
        from models.hierarchy import Version  # noqa: PLC0415
        row = self._db.fetchone(
            "SELECT * FROM versions WHERE project_id=? AND version_id=?",
            (self.project_id, version_id),
        )
        if not row:
            return None
        return self._row_to_version(row)

    def list_versions(self, phase_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if phase_id:
            rows = self._db.fetchall(
                "SELECT * FROM versions WHERE project_id=? AND phase_id=? ORDER BY created_at DESC",
                (self.project_id, phase_id),
            )
        else:
            rows = self._db.fetchall(
                "SELECT * FROM versions WHERE project_id=? ORDER BY created_at DESC",
                (self.project_id,),
            )
        grouped = self._reviews_by_version()
        return [self._enrich_version_summary(self._row_to_version(r).to_summary(), grouped) for r in rows]

    # ── Review operations ─────────────────────────────────────

    def create_review(
        self,
        version_id: str,
        persona: str,
        ai_backend: str = "files_only",
        prompt_used: str = "",
        custom_prompt: str = "",
        output: Optional[Dict[str, Any]] = None,
        findings: Optional[Dict[str, List[str]]] = None,
        questions: Optional[List[str]] = None,
        summary: str = "",
        included_files: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        ai_metadata: Optional[Dict[str, Any]] = None,
        deep_dive: Optional[Dict[str, Any]] = None,
    ):
        from models.hierarchy import Review  # noqa: PLC0415
        db = self._db
        phase_id = self.get_current_phase()

        count = db.fetchone(
            "SELECT COUNT(*) as cnt FROM reviews WHERE project_id=?", (self.project_id,)
        )
        review_num = (count["cnt"] if count else 0) + 1
        review_id = f"r{review_num}"
        now = _now_iso()

        db.execute(
            """INSERT OR REPLACE INTO reviews
               (review_id, project_id, version_id, phase_id, persona, ai_backend,
                prompt_used, custom_prompt, output, findings, questions, summary,
                included_files, categories, ai_metadata,
                deep_dive, feedback, completeness_score, quality_status,
                completed_by, completed_at, decided_by, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                review_id, self.project_id, version_id, phase_id, persona, ai_backend,
                prompt_used, custom_prompt,
                Database.jdump(output or {}),
                Database.jdump(findings or {}),
                Database.jdump(questions or []),
                summary,
                Database.jdump(included_files or []),
                Database.jdump(categories or []),
                Database.jdump(ai_metadata or {}),
                Database.jdump(deep_dive) if deep_dive is not None else None,
                None,  # feedback – empty initially
                0, "pending", "", "", "",  # DS-02 quality gate defaults
                now,
            ),
        )

        # Link review to version
        version = self.get_version(version_id)
        if version:
            version.review_ids.append(review_id)
            version.active_review_id = review_id
            db.execute(
                "UPDATE versions SET review_ids=?, active_review_id=? WHERE project_id=? AND version_id=?",
                (Database.jdump(version.review_ids), review_id, self.project_id, version_id),
            )

        db.commit()
        self._increment_phase_count(phase_id, "review_count")

        review = Review(
            review_id=review_id, version_id=version_id, project_id=self.project_id,
            phase_id=phase_id, persona=persona, ai_backend=ai_backend,
            created_at=now, prompt_used=prompt_used, custom_prompt=custom_prompt,
            output=output or {}, findings=findings or {}, questions=questions or [],
            summary=summary, included_files=included_files or [],
            categories=categories or [], ai_metadata=ai_metadata or {},
            deep_dive=deep_dive,
        )
        self._file_save_review(review)
        if version:
            self._file_save_version(version)
        return review

    def get_review(self, review_id: str):
        row = self._db.fetchone(
            "SELECT * FROM reviews WHERE project_id=? AND review_id=?",
            (self.project_id, review_id),
        )
        if not row:
            return None
        return self._row_to_review(row)

    def list_reviews(
        self, version_id: Optional[str] = None, phase_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM reviews WHERE project_id=?"
        params: list = [self.project_id]
        if version_id:
            sql += " AND version_id=?"
            params.append(version_id)
        if phase_id:
            sql += " AND phase_id=?"
            params.append(phase_id)
        sql += " ORDER BY created_at DESC"
        rows = self._db.fetchall(sql, tuple(params))
        return [self._row_to_review(r).to_summary() for r in rows]

    def set_active_review(self, version_id: str, review_id: str) -> Dict[str, Any]:
        version = self.get_version(version_id)
        if version is None:
            return {"error": f"Version not found: {version_id}"}
        if review_id not in version.review_ids:
            return {"error": f"Review {review_id} not linked to version {version_id}"}
        self._db.execute(
            "UPDATE versions SET active_review_id=? WHERE project_id=? AND version_id=?",
            (review_id, self.project_id, version_id),
        )
        self._db.commit()
        self._file_save_version(version)
        return {"version_id": version_id, "active_review_id": review_id, "status": "updated"}

    def delete_review(self, review_id: str) -> Dict[str, Any]:
        review = self.get_review(review_id)
        if review is None:
            return {"error": f"Review not found: {review_id}"}
        version_id = review.version_id

        self._db.execute(
            "DELETE FROM reviews WHERE project_id=? AND review_id=?",
            (self.project_id, review_id),
        )
        version = self.get_version(version_id)
        if version and review_id in version.review_ids:
            version.review_ids.remove(review_id)
            if version.active_review_id == review_id:
                version.active_review_id = version.review_ids[-1] if version.review_ids else ""
            self._db.execute(
                "UPDATE versions SET review_ids=?, active_review_id=? WHERE project_id=? AND version_id=?",
                (Database.jdump(version.review_ids), version.active_review_id, self.project_id, version_id),
            )
        self._db.commit()
        self._decrement_phase_count(review.phase_id, "review_count")

        # File cleanup
        _, file_on = _dual_write_flags()
        if file_on:
            review_file = self.base_dir / "reviews" / f"{review_id}.json"
            if review_file.exists():
                review_file.unlink()
            self._rebuild_review_index()
            if version:
                self._file_save_version(version)

        return {"review_id": review_id, "deleted": True, "version_id": version_id}

    def get_active_review_for_version(self, version_id: str):
        version = self.get_version(version_id)
        if version is None:
            return None
        reviews = self.list_reviews(version_id=version_id)
        if not reviews:
            return None
        active_id = version.active_review_id
        ids = [r["review_id"] for r in reviews]
        if active_id not in ids:
            active_id = ids[0] if ids else ""
        return self.get_review(active_id) if active_id else None

    # ── Metrics ───────────────────────────────────────────────

    def get_metrics(
        self, version_id: Optional[str] = None, review_id: Optional[str] = None
    ) -> Dict[str, Any]:
        # Delegate entirely to the original HierarchyStore logic
        # (avoids duplicating the complex metrics assembly)
        from models.hierarchy import HierarchyStore as _FS  # noqa: PLC0415
        orig = _FS.__new__(_FS)
        orig.project_id = self.project_id
        orig.base_dir = self.base_dir
        # Patch list/get methods to use SQLite
        orig.list_versions  = self.list_versions    # type: ignore[method-assign]
        orig.get_version    = self.get_version      # type: ignore[method-assign]
        orig.list_reviews   = self.list_reviews     # type: ignore[method-assign]
        orig.get_review     = self.get_review       # type: ignore[method-assign]
        orig.get_current_phase = self.get_current_phase  # type: ignore[method-assign]
        orig.get_phases     = self.get_phases       # type: ignore[method-assign]
        orig.get_active_review_for_version = self.get_active_review_for_version  # type: ignore[method-assign]
        return orig.get_metrics(version_id=version_id, review_id=review_id)

    def get_hierarchy(self) -> Dict[str, Any]:
        phases = self.get_phases()
        versions = self.list_versions()
        reviews = self.list_reviews()
        tree: List[Dict[str, Any]] = []
        for phase in sorted(phases, key=lambda p: p.get("order", 0)):
            phase_versions = [v for v in versions if v.get("phase_id") == phase["id"]]
            phase_node = {**phase, "versions": []}
            for ver in phase_versions:
                ver_reviews = [r for r in reviews if r.get("version_id") == ver["version_id"]]
                phase_node["versions"].append({**ver, "reviews": ver_reviews})
            tree.append(phase_node)
        return {
            "project_id": self.project_id,
            "current_phase": self.get_current_phase(),
            "tree": tree,
            "total_versions": len(versions),
            "total_reviews": len(reviews),
        }

    # ── Enrichment helpers (mirrored from file store) ─────────

    def _reviews_by_version(self) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in self.list_reviews():
            grouped.setdefault(r.get("version_id", ""), []).append(r)
        return grouped

    def _enrich_version_summary(
        self, summary: Dict[str, Any], grouped: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        vid = summary.get("version_id", "")
        v_reviews = grouped.get(vid, [])
        review_ids = [r.get("review_id") for r in v_reviews if r.get("review_id")]
        active_id = summary.get("active_review_id", "")
        if active_id not in review_ids:
            active_id = review_ids[0] if review_ids else ""
        active_review = next((r for r in v_reviews if r.get("review_id") == active_id), None)
        enriched = dict(summary)
        enriched["review_count"] = len(v_reviews)
        enriched["active_review_id"] = active_id
        enriched["active_review"] = active_review
        return enriched

    # ── Row converters ────────────────────────────────────────

    @staticmethod
    def _phase_row_to_dict(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["phase_id"],
            "label": row["label"],
            "order": row["phase_order"],
            "description": row["description"],
            "entered_at": row["entered_at"],
            "exited_at": row["exited_at"],
            "is_current": bool(row["is_current"]),
            "version_count": row["version_count"],
            "review_count": row["review_count"],
        }

    @staticmethod
    def _row_to_version(row: Dict[str, Any]):
        from models.hierarchy import Version  # noqa: PLC0415
        return Version(
            version_id=row["version_id"],
            project_id=row["project_id"],
            phase_id=row["phase_id"],
            label=row["label"],
            created_at=row["created_at"],
            included_artifacts=Database.jload(row.get("included_artifacts"), []),
            excluded_artifacts=Database.jload(row.get("excluded_artifacts"), []),
            persona=row["persona"],
            scope=row["scope"],
            ai_backend=row["ai_backend"],
            stats=Database.jload(row.get("stats"), {}),
            review_ids=Database.jload(row.get("review_ids"), []),
            active_review_id=row.get("active_review_id", ""),
        )

    @staticmethod
    def _row_to_review(row: Dict[str, Any]):
        from models.hierarchy import Review  # noqa: PLC0415
        return Review(
            review_id=row["review_id"],
            version_id=row["version_id"],
            project_id=row["project_id"],
            phase_id=row["phase_id"],
            persona=row["persona"],
            ai_backend=row["ai_backend"],
            created_at=row["created_at"],
            prompt_used=row["prompt_used"],
            custom_prompt=row["custom_prompt"],
            output=Database.jload(row.get("output"), {}),
            findings=Database.jload(row.get("findings"), {}),
            questions=Database.jload(row.get("questions"), []),
            summary=row["summary"],
            included_files=Database.jload(row.get("included_files"), []),
            categories=Database.jload(row.get("categories"), []),
            ai_metadata=Database.jload(row.get("ai_metadata"), {}),
            deep_dive=Database.jload(row.get("deep_dive"), None),
            feedback=Database.jload(row.get("feedback"), None),
            completeness_score=row.get("completeness_score", 0),
            quality_status=row.get("quality_status", "pending"),
            completed_by=row.get("completed_by", ""),
            completed_at=row.get("completed_at", ""),
            decided_by=row.get("decided_by", ""),
        )

    # ── File dual-write helpers ───────────────────────────────

    def _file_save_version(self, version) -> None:
        import dataclasses  # noqa: PLC0415
        _, file_on = _dual_write_flags()
        if not file_on:
            return
        versions_dir = self.base_dir / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        version_file = versions_dir / f"{version.version_id}.json"
        with open(version_file, "w") as f:
            json.dump(dataclasses.asdict(version), f, indent=2)
        self._rebuild_version_index()

    def _file_save_review(self, review) -> None:
        import dataclasses  # noqa: PLC0415
        _, file_on = _dual_write_flags()
        if not file_on:
            return
        reviews_dir = self.base_dir / "reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)
        review_file = reviews_dir / f"{review.review_id}.json"
        with open(review_file, "w") as f:
            json.dump(dataclasses.asdict(review), f, indent=2)
        self._rebuild_review_index()

    def _rebuild_version_index(self) -> None:
        versions_dir = self.base_dir / "versions"
        index = []
        for vf in sorted(versions_dir.glob("v*.json")):
            try:
                with open(vf) as f:
                    data = json.load(f)
                from models.hierarchy import Version  # noqa: PLC0415
                v = Version(**{k: data[k] for k in Version.__dataclass_fields__ if k in data})
                index.append(v.to_summary())
            except Exception:
                pass
        with open(versions_dir / "index.json", "w") as f:
            json.dump(index, f, indent=2)

    def _rebuild_review_index(self) -> None:
        reviews_dir = self.base_dir / "reviews"
        index = []
        for rf in sorted(reviews_dir.glob("r*.json")):
            try:
                with open(rf) as f:
                    data = json.load(f)
                from models.hierarchy import Review  # noqa: PLC0415
                r = Review(**{k: data[k] for k in Review.__dataclass_fields__ if k in data})
                index.append(r.to_summary())
            except Exception:
                pass
        with open(reviews_dir / "index.json", "w") as f:
            json.dump(index, f, indent=2)
