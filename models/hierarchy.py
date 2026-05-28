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
        }


# ──────────────────────────────────────────────────────────────
# Hierarchy Store (File-based persistence)
# ──────────────────────────────────────────────────────────────

PROJECTS_DIR = Path("projects_data")


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
        """List all versions, optionally filtered by phase. Newest first."""
        index = self._load_version_index()
        if phase_id:
            index = [v for v in index if v.get("phase_id") == phase_id]
        return sorted(index, key=lambda v: v.get("created_at", ""), reverse=True)

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
            version_file = self.base_dir / "versions" / f"{version_id}.json"
            with open(version_file, "w") as f:
                json.dump(asdict(version), f, indent=2)
            # Update version index summary
            v_index = self._load_version_index()
            for vi in v_index:
                if vi["version_id"] == version_id:
                    vi["review_count"] = len(version.review_ids)
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

    # ── Dashboard Metrics ──

    def get_metrics(
        self, version_id: Optional[str] = None, review_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get dashboard metrics, optionally scoped to a version/review.

        Default: latest version + latest review.
        """
        versions = self.list_versions()
        reviews = self.list_reviews()
        phases = self.get_phases()

        # Select context
        target_version = None
        target_review = None

        if version_id:
            target_version = self.get_version(version_id)
        elif versions:
            target_version = self.get_version(versions[0]["version_id"])

        if review_id:
            target_review = self.get_review(review_id)
        elif reviews:
            target_review = self.get_review(reviews[0]["review_id"])

        # Build metrics
        metrics: Dict[str, Any] = {
            "total_versions": len(versions),
            "total_reviews": len(reviews),
            "current_phase": self.get_current_phase(),
            "phases": phases,
        }

        # Version context
        if target_version:
            metrics["selected_version"] = target_version.to_summary()
            metrics["risks_identified"] = target_version.stats.get("risks", 0)
            metrics["dependencies"] = target_version.stats.get("dependencies", 0)
            metrics["constraints"] = target_version.stats.get("constraints", 0)
            metrics["assumptions"] = target_version.stats.get("assumptions", 0)
            metrics["action_items"] = target_version.stats.get("action_items", 0)
            metrics["artifact_count"] = len(target_version.included_artifacts)

        # Review context
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

        # Data source context
        metrics["data_source"] = {
            "version": target_version.version_id if target_version else None,
            "review": target_review.review_id if target_review else None,
            "phase": self.get_current_phase(),
        }

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
