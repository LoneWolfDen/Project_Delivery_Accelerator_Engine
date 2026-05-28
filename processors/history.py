"""Iteration & History module.

Tracks versioned context builds and review runs, enabling:
- Compare intelligence across build versions (what changed)
- Compare reviews across runs (risks increased/decreased)
- Track evolution of risks, assumptions, dependencies over time
- Audit trail of all analysis iterations
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


def save_context_version(
    project_dir: Path, context: Dict[str, Any], version_label: Optional[str] = None
) -> Dict[str, Any]:
    """Save a context build as a versioned snapshot.

    Args:
        project_dir: Path to the project's data directory.
        context: Built intelligence dict.
        version_label: Optional label (e.g. 'post-discovery', 'v2-proposal').

    Returns:
        Version metadata dict with version_id, timestamp, label, stats.
    """
    versions_dir = project_dir / "versions"
    versions_dir.mkdir(exist_ok=True)

    # Determine version number
    existing = _list_version_files(versions_dir)
    version_num = len(existing) + 1
    timestamp = datetime.now(timezone.utc).isoformat()

    version_meta = {
        "version_id": f"v{version_num}",
        "version_number": version_num,
        "timestamp": timestamp,
        "label": version_label or f"Build #{version_num}",
        "stats": {
            "risks": len(context.get("risks", [])),
            "assumptions": len(context.get("assumptions", [])),
            "dependencies": len(context.get("dependencies", [])),
            "constraints": len(context.get("constraints", [])),
            "action_items": len(context.get("action_items", [])),
            "document_count": context.get("_build_metadata", {}).get("document_count", 0),
        },
    }

    # Save the full context snapshot
    version_file = versions_dir / f"v{version_num}.json"
    snapshot = {
        "_version_meta": version_meta,
        **context,
    }
    with open(version_file, "w") as f:
        json.dump(snapshot, f, indent=2)

    # Update version index
    _update_version_index(versions_dir, version_meta)

    return version_meta


def list_context_versions(project_dir: Path) -> List[Dict[str, Any]]:
    """List all context versions for a project (summary view).

    Args:
        project_dir: Path to the project's data directory.

    Returns:
        List of version metadata dicts, newest first.
    """
    versions_dir = project_dir / "versions"
    index_path = versions_dir / "index.json"

    if not index_path.exists():
        return []

    with open(index_path) as f:
        index = json.load(f)

    return sorted(index, key=lambda v: v["version_number"], reverse=True)


def get_context_version(project_dir: Path, version_id: str) -> Optional[Dict[str, Any]]:
    """Load a specific context version snapshot.

    Args:
        project_dir: Path to the project's data directory.
        version_id: e.g. 'v1', 'v2', 'v3'.

    Returns:
        Full context snapshot dict, or None if not found.
    """
    versions_dir = project_dir / "versions"
    version_file = versions_dir / f"{version_id}.json"

    if not version_file.exists():
        return None

    with open(version_file) as f:
        return json.load(f)


def compare_context_versions(
    project_dir: Path, version_a: str, version_b: str
) -> Dict[str, Any]:
    """Compare two context versions and show what changed.

    Args:
        project_dir: Path to the project's data directory.
        version_a: Earlier version (e.g. 'v1').
        version_b: Later version (e.g. 'v2').

    Returns:
        Comparison dict with added/removed/unchanged per category.
    """
    ctx_a = get_context_version(project_dir, version_a)
    ctx_b = get_context_version(project_dir, version_b)

    if not ctx_a:
        raise ValueError(f"Version not found: {version_a}")
    if not ctx_b:
        raise ValueError(f"Version not found: {version_b}")

    comparison = {
        "version_a": version_a,
        "version_b": version_b,
        "timestamp_a": ctx_a.get("_version_meta", {}).get("timestamp", ""),
        "timestamp_b": ctx_b.get("_version_meta", {}).get("timestamp", ""),
        "categories": {},
    }

    # Compare each category
    for category in ["risks", "assumptions", "dependencies", "constraints", "action_items"]:
        items_a = set(_normalise_items(ctx_a.get(category, [])))
        items_b = set(_normalise_items(ctx_b.get(category, [])))

        added = items_b - items_a
        removed = items_a - items_b
        unchanged = items_a & items_b

        comparison["categories"][category] = {
            "count_before": len(items_a),
            "count_after": len(items_b),
            "added": sorted(added),
            "removed": sorted(removed),
            "unchanged_count": len(unchanged),
            "net_change": len(items_b) - len(items_a),
        }

    # Overall summary
    total_added = sum(len(c["added"]) for c in comparison["categories"].values())
    total_removed = sum(len(c["removed"]) for c in comparison["categories"].values())
    comparison["summary"] = {
        "total_added": total_added,
        "total_removed": total_removed,
        "net_change": total_added - total_removed,
        "trend": _determine_trend(comparison["categories"]),
    }

    return comparison


def compare_reviews(
    review_a: Dict[str, Any], review_b: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare two review outputs from the same persona.

    Args:
        review_a: Earlier review result dict.
        review_b: Later review result dict.

    Returns:
        Comparison dict showing evolution of findings.
    """
    persona_a = review_a.get("persona", "")
    persona_b = review_b.get("persona", "")

    comparison = {
        "persona": persona_b or persona_a,
        "timestamp_a": review_a.get("timestamp", ""),
        "timestamp_b": review_b.get("timestamp", ""),
        "backend_a": review_a.get("ai_backend", ""),
        "backend_b": review_b.get("ai_backend", ""),
        "sections": {},
    }

    findings_a = review_a.get("findings", {})
    findings_b = review_b.get("findings", {})

    # Compare each findings section
    all_sections = set(list(findings_a.keys()) + list(findings_b.keys()))
    for section in sorted(all_sections):
        items_a = set(_normalise_items(findings_a.get(section, [])))
        items_b = set(_normalise_items(findings_b.get(section, [])))

        comparison["sections"][section] = {
            "count_before": len(items_a),
            "count_after": len(items_b),
            "new_findings": sorted(items_b - items_a),
            "resolved": sorted(items_a - items_b),
            "persistent": len(items_a & items_b),
        }

    # Summary
    total_new = sum(len(s["new_findings"]) for s in comparison["sections"].values())
    total_resolved = sum(len(s["resolved"]) for s in comparison["sections"].values())
    comparison["summary"] = {
        "new_findings": total_new,
        "resolved_findings": total_resolved,
        "net_change": total_new - total_resolved,
        "direction": "improving" if total_resolved > total_new else (
            "stable" if total_new == total_resolved else "degrading"
        ),
    }

    return comparison


def get_evolution_timeline(
    project_dir: Path, category: str = "risks"
) -> List[Dict[str, Any]]:
    """Get the evolution of a specific category across all versions.

    Useful for tracking how risks/dependencies grow or shrink over time.

    Args:
        project_dir: Path to the project's data directory.
        category: One of 'risks', 'assumptions', 'dependencies', 'constraints', 'action_items'.

    Returns:
        Timeline: list of {version_id, timestamp, count, items} per version.
    """
    versions = list_context_versions(project_dir)
    timeline = []

    for version_meta in sorted(versions, key=lambda v: v["version_number"]):
        version_id = version_meta["version_id"]
        ctx = get_context_version(project_dir, version_id)
        if ctx:
            items = ctx.get(category, [])
            timeline.append({
                "version_id": version_id,
                "label": version_meta.get("label", ""),
                "timestamp": version_meta.get("timestamp", ""),
                "count": len(items) if isinstance(items, list) else 0,
                "items": items if isinstance(items, list) else [],
            })

    return timeline


def get_review_history(
    project_dir: Path, persona_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get chronological review history, optionally filtered by persona.

    Args:
        project_dir: Path to the project's data directory.
        persona_id: Optional filter (e.g. 'solution_architect').

    Returns:
        List of review summaries, newest first.
    """
    reviews_dir = project_dir / "reviews"
    if not reviews_dir.exists():
        return []

    reviews = []
    for json_file in sorted(reviews_dir.glob("*.json"), reverse=True):
        with open(json_file) as f:
            review = json.load(f)

        # Filter by persona if specified
        if persona_id and review.get("persona_id") != persona_id:
            continue

        # Build summary (don't load full findings into response)
        findings = review.get("findings", {})
        total_findings = sum(len(v) for v in findings.values() if isinstance(v, list))

        reviews.append({
            "persona": review.get("persona", ""),
            "persona_id": review.get("persona_id", ""),
            "timestamp": review.get("timestamp", ""),
            "ai_backend": review.get("ai_backend", ""),
            "total_findings": total_findings,
            "summary": review.get("summary", ""),
            "file": json_file.name,
        })

    return reviews


# ──────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────


def _list_version_files(versions_dir: Path) -> List[Path]:
    """List existing version files sorted by number."""
    return sorted(versions_dir.glob("v*.json"))


def _update_version_index(versions_dir: Path, version_meta: Dict[str, Any]) -> None:
    """Update the version index file."""
    index_path = versions_dir / "index.json"
    index: List[Dict[str, Any]] = []

    if index_path.exists():
        with open(index_path) as f:
            index = json.load(f)

    index.append(version_meta)

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)


def _normalise_items(items: List[Any]) -> List[str]:
    """Normalise a list of items to comparable strings."""
    normalised = []
    for item in items:
        if isinstance(item, str):
            normalised.append(item.strip().lower())
        elif isinstance(item, dict):
            normalised.append(json.dumps(item, sort_keys=True).lower())
    return normalised


def _determine_trend(categories: Dict[str, Any]) -> str:
    """Determine overall trend from category comparisons."""
    risk_change = categories.get("risks", {}).get("net_change", 0)
    dep_change = categories.get("dependencies", {}).get("net_change", 0)

    if risk_change < 0 and dep_change <= 0:
        return "improving"
    elif risk_change > 0:
        return "risks_increasing"
    elif dep_change > 0:
        return "complexity_increasing"
    else:
        return "stable"
