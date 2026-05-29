"""Project Hierarchy Model – Version ↔ Review Relationship.

Establishes the core relationship:
    Project → Phase → Version → Review

Definitions:
- Version: Snapshot of selected artefacts, metadata, persona, scope
- Review: Execution on a version (prompt used, output generated, timestamp)

This enables:
- Traceability (what inputs generated what outputs)
- Historical context (navigate by phase → version → review)
- Learning over time (compare reviews, track evolution)
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────
# Phase Model
# ──────────────────────────────────────────────────────────────

# Standard phases (first-class entities)
STANDARD_PHASES = [
    {"id": "pre-sales", "label": "Pre-sales", "order": 1,
     "description": "Client engagement, proposals, scoping"},
    {"id": "design", "label": "Design", "order": 2,
     "description": "Architecture, solution design, planning"},
    {"id": "delivery", "label": "Delivery", "order": 3,
     "description": "Execution, development, implementation"},
    {"id": "support", "label": "Support", "order": 4,
     "description": "Operations, maintenance, handover"},
]


@dataclass
class Phase:
    """Phase entity – first-class project lifecycle stage."""

    id: str = ""
    label: str = ""
    order: int = 0
    description: str = ""
    entered_at: str = ""
    exited_at: str = ""
    is_current: bool = False
    version_count: int = 0
    review_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ──────────────────────────────────────────────────────────────
# Version Model (Snapshot)
# ──────────────────────────────────────────────────────────────

@dataclass
class Version:
    """Version = Snapshot of project state at a point in time.

    Contains:
    - Selected artefacts (with include states)
    - Metadata (file toggles, category info)
    - Persona used
    - Scope text
    - Phase it belongs to
    """

    version_id: str = ""
    project_id: str = ""
    phase_id: str = ""
    label: str = ""
    created_at: str = ""

    # Snapshot data
    included_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    excluded_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    persona: str = ""
    scope: str = ""
    ai_backend: str = "files_only"

    # Intelligence summary at time of version creation
    stats: Dict[str, int] = field(default_factory=dict)

    # Reviews executed against this version
    review_ids: List[str] = field(default_factory=list)

    # Active review for this version (defaults to latest)
    active_review_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["review_count"] = len(self.review_ids)
        d["artifact_count"] = len(self.included_artifacts)
        return d

    def to_summary(self) -> Dict[str, Any]:
        """Lightweight summary for list views."""
        return {
            "version_id": self.version_id,
            "phase_id": self.phase_id,
            "label": self.label,
            "created_at": self.created_at,
            "review_count": len(self.review_ids),
            "artifact_count": len(self.included_artifacts),
            "persona": self.persona,
            "stats": self.stats,
            "active_review_id": self.active_review_id,
        }


# ──────────────────────────────────────────────────────────────
# Review Model (Execution)
# ──────────────────────────────────────────────────────────────

@dataclass
class Review:
    """Review = Execution on a version.

    Contains:
    - Version ID it was run against
    - Prompt used
    - Output generated
    - Timestamp
    - Persona + backend info
    """

    review_id: str = ""
    version_id: str = ""
    project_id: str = ""
    phase_id: str = ""
    persona: str = ""
    ai_backend: str = "files_only"
    created_at: str = ""

    # Execution data
    prompt_used: str = ""
    custom_prompt: str = ""
    output: Dict[str, Any] = field(default_factory=dict)
    findings: Dict[str, List[str]] = field(default_factory=dict)
    questions: List[str] = field(default_factory=list)
    summary: str = ""

    # Context from version (denormalized for display)
    included_files: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)

    # AI metadata
    ai_metadata: Dict[str, Any] = field(default_factory=dict)

    # Deep dive results (if AI mode was on)
    deep_dive: Optional[Dict[str, Any]] = None

    # P9: Pre-sales feedback captured against this review
    # Schema: {accepted:[str], rejected:[str], concerns:[str], notes:str, captured_at:str}
    feedback: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["total_findings"] = sum(
            len(v) for v in self.findings.values() if isinstance(v, list)
        )
        return d

    def to_summary(self) -> Dict[str, Any]:
        """Lightweight summary for list views."""
        total_findings = sum(
            len(v) for v in self.findings.values() if isinstance(v, list)
        )
        return {
            "review_id": self.review_id,
            "version_id": self.version_id,
            "phase_id": self.phase_id,
            "persona": self.persona,
            "ai_backend": self.ai_backend,
            "created_at": self.created_at,
            "total_findings": total_findings,
            "summary": self.summary[:120] if self.summary else "",
            "included_files": self.included_files,
            "categories": self.categories,
        }


# ──────────────────────────────────────────────────────────────
# Hierarchy Store (File-based persistence)
# ──────────────────────────────────────────────────────────────

PROJECTS_DIR = Path("projects_data")


def _sqlite_enabled() -> bool:
    """Return True if SQLite write is enabled in admin config."""
    try:
        from admin.config import load_config  # noqa: PLC0415
        return getattr(load_config(), "sqlite_write_enabled", True)
    except Exception:
        return True


def _make_hierarchy_store(project_id: str) -> "HierarchyStore":
    """Factory: returns SQLite-backed store when enabled, else file-based."""
    if _sqlite_enabled():
        from db.hierarchy_store_sql import HierarchyStoreSQLite  # noqa: PLC0415
        return HierarchyStoreSQLite(project_id)  # type: ignore[return-value]
    return HierarchyStore(project_id)


class HierarchyStore:
    """Manages Project→Phase→Version→Review persistence.

    Storage layout:
        projects_data/{project_id}/hierarchy/
            phases.json          (phase list with state)
            versions/
                {version_id}.json
                index.json
            reviews/
                {review_id}.json
                index.json
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.base_dir = PROJECTS_DIR / project_id / "hierarchy"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "versions").mkdir(exist_ok=True)
        (self.base_dir / "reviews").mkdir(exist_ok=True)

    # ── Phase Operations ──

    def get_phases(self) -> List[Dict[str, Any]]:
        """Get all phases with activity counts."""
        phases_file = self.base_dir / "phases.json"
        if phases_file.exists():
            with open(phases_file) as f:
                return json.load(f)

        # Initialize with standard phases
        phases = []
        for sp in STANDARD_PHASES:
            phases.append({
                **sp,
                "entered_at": "",
                "exited_at": "",
                "is_current": sp["id"] == "pre-sales",
                "version_count": 0,
                "review_count": 0,
            })
        self._save_phases(phases)
        return phases

    def get_current_phase(self) -> str:
        """Get the current active phase ID."""
        phases = self.get_phases()
        for p in phases:
            if p.get("is_current"):
                return p["id"]
        return "pre-sales"

    def set_current_phase(self, phase_id: str, reason: str = "") -> Dict[str, Any]:
        """Transition to a new phase."""
        phases = self.get_phases()
        now = _now_iso()

        for p in phases:
            if p.get("is_current"):
                p["is_current"] = False
                p["exited_at"] = now
            if p["id"] == phase_id:
                p["is_current"] = True
                p["entered_at"] = now

        self._save_phases(phases)
        return {"phase_id": phase_id, "transitioned_at": now, "reason": reason}

    def _save_phases(self, phases: List[Dict[str, Any]]) -> None:
        phases_file = self.base_dir / "phases.json"
        with open(phases_file, "w") as f:
            json.dump(phases, f, indent=2)

    def _increment_phase_count(self, phase_id: str, field: str) -> None:
        """Increment version_count or review_count for a phase."""
        phases = self.get_phases()
        for p in phases:
            if p["id"] == phase_id:
                p[field] = p.get(field, 0) + 1
                break
        self._save_phases(phases)

    # ── Version Operations ──

    def create_version(
        self,
        included_artifacts: List[Dict[str, Any]],
        excluded_artifacts: Optional[List[Dict[str, Any]]] = None,
        persona: str = "",
        scope: str = "",
        ai_backend: str = "files_only",
        label: str = "",
        stats: Optional[Dict[str, int]] = None,
    ) -> Version:
        """Create a new version (snapshot)."""
        phase_id = self.get_current_phase()
        versions = self._load_version_index()
        version_num = len(versions) + 1
        version_id = f"v{version_num}"

        version = Version(
            version_id=version_id,
            project_id=self.project_id,
            phase_id=phase_id,
            label=label or f"Version {version_num}",
            created_at=_now_iso(),
            included_artifacts=included_artifacts or [],
            excluded_artifacts=excluded_artifacts or [],
            persona=persona,
            scope=scope[:2000] if scope else "",
            ai_backend=ai_backend,
            stats=stats or {},
            review_ids=[],
        )

        # Save version
        version_file = self.base_dir / "versions" / f"{version_id}.json"
        with open(version_file, "w") as f:
            json.dump(asdict(version), f, indent=2)

        # Update index
        versions.append(version.to_summary())
        self._save_version_index(versions)

        # Increment phase version count
        self._increment_phase_count(phase_id, "version_count")

        return version

    def get_version(self, version_id: str) -> Optional[Version]:
        """Get a specific version by ID."""
        version_file = self.base_dir / "versions" / f"{version_id}.json"
        if not version_file.exists():
            return None
        with open(version_file) as f:
            data = json.load(f)
        return Version(**{k: v for k, v in data.items() if k in Version.__dataclass_fields__})

    def list_versions(self, phase_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all versions, optionally filtered by phase. Newest first.

        Each version summary is enriched with LIVE review data so that
        review_count and active_review_id are always accurate, even if the
        stored index is stale (e.g. after manual data edits or merges).
        """
        index = self._load_version_index()
        if phase_id:
            index = [v for v in index if v.get("phase_id") == phase_id]
        grouped = self._reviews_by_version()
        enriched = [self._enrich_version_summary(v, grouped) for v in index]
        return sorted(enriched, key=lambda v: v.get("created_at", ""), reverse=True)

    # ── Live review enrichment (single source of truth) ──

    def _reviews_by_version(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group all review summaries by version_id (newest first per group)."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in self.list_reviews():  # already sorted newest-first
            grouped.setdefault(r.get("version_id", ""), []).append(r)
        return grouped

    def _enrich_version_summary(
        self, summary: Dict[str, Any], grouped: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Recompute review_count + active_review_id from live review data.

        - review_count = actual number of reviews linked to the version.
        - active_review_id is validated; if missing/invalid it defaults to the
          latest review for that version.
        - active_review = the resolved active review summary (or None).
        """
        vid = summary.get("version_id", "")
        v_reviews = grouped.get(vid, [])  # newest-first
        review_ids = [r.get("review_id") for r in v_reviews if r.get("review_id")]

        active_id = summary.get("active_review_id", "")
        if active_id not in review_ids:
            # Default to latest review (newest-first → index 0)
            active_id = review_ids[0] if review_ids else ""

        active_review = None
        if active_id:
            active_review = next(
                (r for r in v_reviews if r.get("review_id") == active_id), None
            )

        enriched = dict(summary)
        enriched["review_count"] = len(v_reviews)
        enriched["active_review_id"] = active_id
        enriched["active_review"] = active_review
        return enriched

    def _load_version_index(self) -> List[Dict[str, Any]]:
        index_file = self.base_dir / "versions" / "index.json"
        if not index_file.exists():
            return []
        with open(index_file) as f:
            return json.load(f)

    def _save_version_index(self, index: List[Dict[str, Any]]) -> None:
        index_file = self.base_dir / "versions" / "index.json"
        with open(index_file, "w") as f:
            json.dump(index, f, indent=2)

    # ── Review Operations ──

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
    ) -> Review:
        """Create a new review (execution on a version)."""
        phase_id = self.get_current_phase()
        reviews = self._load_review_index()
        review_num = len(reviews) + 1
        review_id = f"r{review_num}"

        review = Review(
            review_id=review_id,
            version_id=version_id,
            project_id=self.project_id,
            phase_id=phase_id,
            persona=persona,
            ai_backend=ai_backend,
            created_at=_now_iso(),
            prompt_used=prompt_used,
            custom_prompt=custom_prompt,
            output=output or {},
            findings=findings or {},
            questions=questions or [],
            summary=summary,
            included_files=included_files or [],
            categories=categories or [],
            ai_metadata=ai_metadata or {},
            deep_dive=deep_dive,
        )

        # Save review
        review_file = self.base_dir / "reviews" / f"{review_id}.json"
        with open(review_file, "w") as f:
            json.dump(asdict(review), f, indent=2)

        # Update review index
        reviews.append(review.to_summary())
        self._save_review_index(reviews)

        # Link review to version
        version = self.get_version(version_id)
        if version:
            version.review_ids.append(review_id)
            # Set as active review (latest by default)
            version.active_review_id = review_id
            version_file = self.base_dir / "versions" / f"{version_id}.json"
            with open(version_file, "w") as f:
                json.dump(asdict(version), f, indent=2)
            # Update version index summary
            v_index = self._load_version_index()
            for vi in v_index:
                if vi["version_id"] == version_id:
                    vi["review_count"] = len(version.review_ids)
                    vi["active_review_id"] = review_id
                    break
            self._save_version_index(v_index)

        # Increment phase review count
        self._increment_phase_count(phase_id, "review_count")

        return review

    def get_review(self, review_id: str) -> Optional[Review]:
        """Get a specific review by ID."""
        review_file = self.base_dir / "reviews" / f"{review_id}.json"
        if not review_file.exists():
            return None
        with open(review_file) as f:
            data = json.load(f)
        return Review(**{k: v for k, v in data.items() if k in Review.__dataclass_fields__})

    def list_reviews(
        self, version_id: Optional[str] = None, phase_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List reviews, optionally filtered. Newest first."""
        index = self._load_review_index()
        if version_id:
            index = [r for r in index if r.get("version_id") == version_id]
        if phase_id:
            index = [r for r in index if r.get("phase_id") == phase_id]
        return sorted(index, key=lambda r: r.get("created_at", ""), reverse=True)

    def _load_review_index(self) -> List[Dict[str, Any]]:
        index_file = self.base_dir / "reviews" / "index.json"
        if not index_file.exists():
            return []
        with open(index_file) as f:
            return json.load(f)

    def _save_review_index(self, index: List[Dict[str, Any]]) -> None:
        index_file = self.base_dir / "reviews" / "index.json"
        with open(index_file, "w") as f:
            json.dump(index, f, indent=2)

    def set_active_review(self, version_id: str, review_id: str) -> Dict[str, Any]:
        """Set the active review for a version.

        Args:
            version_id: The version to update.
            review_id: The review to mark as active.

        Returns:
            Updated version summary or error dict.
        """
        version = self.get_version(version_id)
        if version is None:
            return {"error": f"Version not found: {version_id}"}
        if review_id not in version.review_ids:
            return {"error": f"Review {review_id} not linked to version {version_id}"}

        version.active_review_id = review_id
        version_file = self.base_dir / "versions" / f"{version_id}.json"
        with open(version_file, "w") as f:
            json.dump(asdict(version), f, indent=2)

        # Update index
        v_index = self._load_version_index()
        for vi in v_index:
            if vi["version_id"] == version_id:
                vi["active_review_id"] = review_id
                break
        self._save_version_index(v_index)

        return {"version_id": version_id, "active_review_id": review_id, "status": "updated"}

    def delete_review(self, review_id: str) -> Dict[str, Any]:
        """Delete a review and unlink it from its parent version.

        Args:
            review_id: The review to delete.

        Returns:
            Confirmation dict or error.
        """
        review = self.get_review(review_id)
        if review is None:
            return {"error": f"Review not found: {review_id}"}

        version_id = review.version_id

        # Remove review file
        review_file = self.base_dir / "reviews" / f"{review_id}.json"
        if review_file.exists():
            review_file.unlink()

        # Remove from review index
        r_index = self._load_review_index()
        r_index = [r for r in r_index if r.get("review_id") != review_id]
        self._save_review_index(r_index)

        # Unlink from version
        version = self.get_version(version_id)
        if version and review_id in version.review_ids:
            version.review_ids.remove(review_id)
            # If deleted review was active, set active to latest remaining or empty
            if version.active_review_id == review_id:
                version.active_review_id = version.review_ids[-1] if version.review_ids else ""
            version_file = self.base_dir / "versions" / f"{version_id}.json"
            with open(version_file, "w") as f:
                json.dump(asdict(version), f, indent=2)
            # Update version index
            v_index = self._load_version_index()
            for vi in v_index:
                if vi["version_id"] == version_id:
                    vi["review_count"] = len(version.review_ids)
                    vi["active_review_id"] = version.active_review_id
                    break
            self._save_version_index(v_index)

        # Decrement phase review count
        self._decrement_phase_count(review.phase_id, "review_count")

        return {"review_id": review_id, "deleted": True, "version_id": version_id}

    def _decrement_phase_count(self, phase_id: str, field: str) -> None:
        """Decrement version_count or review_count for a phase."""
        phases = self.get_phases()
        for p in phases:
            if p["id"] == phase_id:
                p[field] = max(0, p.get(field, 0) - 1)
                break
        self._save_phases(phases)

    def get_active_review_for_version(self, version_id: str) -> Optional[Review]:
        """Get the active review for a version (validated, with fallback).

        Resolution order:
        1. The version's active_review_id (if it still points to a live review).
        2. The latest review for that version.
        3. None (no reviews exist).
        """
        version = self.get_version(version_id)
        if version is None:
            return None

        # Live list of reviews for this version (newest-first)
        v_reviews = self.list_reviews(version_id=version_id)
        if not v_reviews:
            return None
        review_ids = [r.get("review_id") for r in v_reviews]

        active_id = version.active_review_id
        if active_id not in review_ids:
            # Fallback: latest review
            active_id = v_reviews[0].get("review_id")

        return self.get_review(active_id) if active_id else None

    # ── Dashboard Metrics ──

    def get_metrics(
        self, version_id: Optional[str] = None, review_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get dashboard metrics, optionally scoped to a version/review.

        Default: latest version + its active review.
        Reviews are always scoped to the selected version.
        """
        versions = self.list_versions()
        phases = self.get_phases()

        # Select context
        target_version = None
        target_review = None

        if version_id:
            target_version = self.get_version(version_id)
        elif versions:
            target_version = self.get_version(versions[0]["version_id"])

        # Reviews scoped to selected version
        scoped_reviews = []
        if target_version:
            scoped_reviews = self.list_reviews(version_id=target_version.version_id)

        if review_id:
            target_review = self.get_review(review_id)
        elif target_version:
            # Use active review for this version
            target_review = self.get_active_review_for_version(target_version.version_id)

        all_reviews = self.list_reviews()

        # Build metrics
        metrics: Dict[str, Any] = {
            "total_versions": len(versions),
            "total_reviews": len(all_reviews),
            "version_reviews": len(scoped_reviews),
            "current_phase": self.get_current_phase(),
            "phases": phases,
        }

        # Version context
        if target_version:
            v_summary = target_version.to_summary()
            v_summary["review_count"] = len(scoped_reviews)
            metrics["selected_version"] = v_summary
            metrics["artifact_count"] = len(target_version.included_artifacts)
            
            # If a review is selected, use its findings counts; otherwise use version stats
            if target_review:
                # Count items from review findings
                findings = target_review.findings
                metrics["risks_identified"] = len(findings.get("risks", []))
                metrics["dependencies"] = len(findings.get("dependencies", []))
                metrics["constraints"] = len(findings.get("constraints", []))
                metrics["assumptions"] = len(findings.get("assumptions", []))
                metrics["action_items"] = len(findings.get("action_items", []))
                
                # Include ALL finding categories dynamically
                metrics["finding_categories"] = {}
                for key, val in findings.items():
                    if isinstance(val, list) and val:
                        metrics["finding_categories"][key] = len(val)
            else:
                # Use version stats (snapshot from intelligence build)
                metrics["risks_identified"] = target_version.stats.get("risks", 0)
                metrics["dependencies"] = target_version.stats.get("dependencies", 0)
                metrics["constraints"] = target_version.stats.get("constraints", 0)
                metrics["assumptions"] = target_version.stats.get("assumptions", 0)
                metrics["action_items"] = target_version.stats.get("action_items", 0)

        # Review context (scoped to version)
        if target_review:
            metrics["selected_review"] = target_review.to_summary()
            metrics["gaps_identified"] = len(target_review.findings.get("gaps", []))
            metrics["total_findings"] = sum(
                len(v) for v in target_review.findings.values() if isinstance(v, list)
            )
            metrics["review_persona"] = target_review.persona

        # Trend (last 5 versions)
        recent = versions[:5]
        metrics["trend"] = [
            {"version_id": v["version_id"], "stats": v.get("stats", {}), "created_at": v.get("created_at", "")}
            for v in recent
        ]

        # Data source context (for display)
        metrics["data_source"] = {
            "version": target_version.version_id if target_version else None,
            "review": target_review.review_id if target_review else None,
            "phase": self.get_current_phase(),
            "version_label": target_version.label if target_version else None,
            "review_persona": target_review.persona if target_review else None,
        }

        # Available reviews for selected version (for dropdown population)
        metrics["available_reviews"] = scoped_reviews

        return metrics

    # ── Full Hierarchy View ──

    def get_hierarchy(self) -> Dict[str, Any]:
        """Get the full Phase→Version→Review tree for navigation."""
        phases = self.get_phases()
        versions = self.list_versions()
        reviews = self.list_reviews()

        # Build tree
        tree: List[Dict[str, Any]] = []
        for phase in sorted(phases, key=lambda p: p.get("order", 0)):
            phase_versions = [v for v in versions if v.get("phase_id") == phase["id"]]
            phase_node: Dict[str, Any] = {
                **phase,
                "versions": [],
            }
            for ver in phase_versions:
                ver_reviews = [r for r in reviews if r.get("version_id") == ver["version_id"]]
                phase_node["versions"].append({
                    **ver,
                    "reviews": ver_reviews,
                })
            tree.append(phase_node)

        return {
            "project_id": self.project_id,
            "current_phase": self.get_current_phase(),
            "tree": tree,
            "total_versions": len(versions),
            "total_reviews": len(reviews),
        }
