"""Context Builder module.

Orchestrates intelligence extraction across all ingested documents
and produces a unified ProjectContext pack.

Workflow:
1. Accept list of ingested documents (dicts from to_dict())
2. Run intelligence extraction on each document
3. Aggregate and deduplicate across all documents
4. Produce a ProjectContext with scope, risks, assumptions, dependencies,
   constraints, resources, and a summary

Supports:
- Full rebuild (from scratch)
- Incremental merge (add new documents to existing context)
- Version tracking (each build is timestamped)
"""

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from models.project import ProjectContext
from processors.extractors.intelligence_extractor import extract_intelligence


def build_context(
    ingested_documents: List[Dict[str, Any]],
    ai_backend: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a structured context pack from ingested documents.

    This is the main entry point. Takes all documents for a project
    and produces a unified context pack.

    When ``ai_backend`` is supplied (and is not ``"files_only"``), a second
    AI-powered extraction pass runs after the regex baseline and its findings
    are merged in additively.  Regex extraction always runs first; the AI
    pass degrades gracefully to a no-op on any error.

    Args:
        ingested_documents: List of IngestedDocument dicts (from to_dict()).
        ai_backend: Optional AI backend name (e.g. ``"groq"``, ``"gemini"``).
            Pass ``None`` or ``"files_only"`` to skip AI enrichment.

    Returns:
        Dict representing a ProjectContext with all extracted intelligence,
        plus metadata about the build.
    """
    if not ingested_documents:
        return _empty_context()

    # ── Phase 1: regex baseline (always runs) ────────────────────────────────
    extractions: List[Dict[str, Any]] = []
    for doc in ingested_documents:
        if doc.get("is_valid", False):
            extraction = extract_intelligence(doc)
            extractions.append(extraction)

    # Aggregate across all documents
    aggregated = _aggregate_extractions(extractions)

    # ── Phase 2: AI enrichment pass (runs only when a real backend given) ────
    # Build intermediate context dict so the AI extractor has the regex
    # baseline to merge into.
    if ai_backend and ai_backend != "files_only":
        _baseline_for_ai = {
            "risks": aggregated.get("risks", []),
            "assumptions": aggregated.get("assumptions", []),
            "dependencies": aggregated.get("dependencies", []),
            "constraints": aggregated.get("constraints", []),
            "action_items": aggregated.get("action_items", []),
            "scope": _build_scope_summary(aggregated.get("scope_fragments", [])),
            "_build_metadata": {},
        }
        try:
            from processors.extractors.ai_extractor import extract_with_ai  # noqa: PLC0415
            enriched = extract_with_ai(ingested_documents, ai_backend, _baseline_for_ai)
            # Write AI-enriched lists back into aggregated
            for cat in ("risks", "assumptions", "dependencies", "constraints", "action_items"):
                aggregated[cat] = enriched.get(cat, aggregated.get(cat, []))
            # Preserve AI scope override if set
            if enriched.get("scope") and not aggregated.get("scope_fragments"):
                aggregated["_ai_scope"] = enriched["scope"]
            aggregated["_ai_extraction_meta"] = enriched.get("_ai_extraction_meta", {})
        except Exception:
            pass  # Degrade silently – regex results are untouched

    # Build scope summary from scope fragments
    scope = _build_scope_summary(aggregated.get("scope_fragments", []))
    # Use AI-generated scope if regex found none
    if not scope:
        scope = aggregated.get("_ai_scope", "")

    # Build project context
    context = ProjectContext(
        scope=scope,
        risks=aggregated.get("risks", []),
        assumptions=aggregated.get("assumptions", []),
        dependencies=aggregated.get("dependencies", []),
        resources=_build_resource_list(aggregated.get("resources", [])),
        constraints=aggregated.get("constraints", []),
        summary=_build_summary(aggregated, ingested_documents),
        raw_extractions=extractions,
    )

    # Convert to dict and add build metadata
    result = asdict(context)
    result["_build_metadata"] = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(ingested_documents),
        "valid_documents": len(extractions),
        "total_risks": len(context.risks),
        "total_assumptions": len(context.assumptions),
        "total_dependencies": len(context.dependencies),
        "total_constraints": len(context.constraints),
        "total_action_items": len(aggregated.get("action_items", [])),
        "ai_backend": ai_backend or "files_only",
        "ai_enriched": bool(aggregated.get("_ai_extraction_meta")),
    }
    result["action_items"] = aggregated.get("action_items", [])
    if aggregated.get("_ai_extraction_meta"):
        result["_ai_extraction_meta"] = aggregated["_ai_extraction_meta"]

    return result


def merge_contexts(
    existing: Dict[str, Any], new: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge new context into existing project context (additive).

    Deduplicates items, preserves source attribution,
    and marks potential conflicts.

    Args:
        existing: Current project context dict.
        new: New context to merge in.

    Returns:
        Merged context dict with combined intelligence.
    """
    if not existing:
        return new
    if not new:
        return existing

    merged = {
        "scope": _merge_scope(existing.get("scope", ""), new.get("scope", "")),
        "risks": _merge_list(existing.get("risks", []), new.get("risks", [])),
        "assumptions": _merge_list(
            existing.get("assumptions", []), new.get("assumptions", [])
        ),
        "dependencies": _merge_list(
            existing.get("dependencies", []), new.get("dependencies", [])
        ),
        "constraints": _merge_list(
            existing.get("constraints", []), new.get("constraints", [])
        ),
        "resources": _merge_resources(
            existing.get("resources", []), new.get("resources", [])
        ),
        "action_items": _merge_list(
            existing.get("action_items", []), new.get("action_items", [])
        ),
        "summary": new.get("summary", existing.get("summary", "")),
        "raw_extractions": (
            existing.get("raw_extractions", []) + new.get("raw_extractions", [])
        ),
        "_build_metadata": new.get("_build_metadata", existing.get("_build_metadata", {})),
    }

    # Update metadata
    merged["_build_metadata"]["merged_at"] = datetime.now(timezone.utc).isoformat()
    merged["_build_metadata"]["total_risks"] = len(merged["risks"])
    merged["_build_metadata"]["total_assumptions"] = len(merged["assumptions"])
    merged["_build_metadata"]["total_dependencies"] = len(merged["dependencies"])
    merged["_build_metadata"]["total_constraints"] = len(merged["constraints"])

    return merged


def build_context_summary(context: Dict[str, Any]) -> str:
    """Generate a concise text summary of a context pack.

    Useful for token-efficient prompts: gives persona engine a quick overview
    without loading full raw extractions.

    Args:
        context: A built context dict.

    Returns:
        Multi-line text summary suitable for prompt injection.
    """
    lines = []
    lines.append("## Project Context Summary")
    lines.append("")

    scope = context.get("scope", "")
    if scope:
        lines.append(f"**Scope:** {_truncate(scope, 300)}")
        lines.append("")

    risks = context.get("risks", [])
    if risks:
        lines.append(f"**Risks ({len(risks)}):**")
        for r in risks[:10]:
            lines.append(f"  - {r}")
        if len(risks) > 10:
            lines.append(f"  ... and {len(risks) - 10} more")
        lines.append("")

    assumptions = context.get("assumptions", [])
    if assumptions:
        lines.append(f"**Assumptions ({len(assumptions)}):**")
        for a in assumptions[:10]:
            lines.append(f"  - {a}")
        lines.append("")

    dependencies = context.get("dependencies", [])
    if dependencies:
        lines.append(f"**Dependencies ({len(dependencies)}):**")
        for d in dependencies[:10]:
            lines.append(f"  - {d}")
        lines.append("")

    constraints = context.get("constraints", [])
    if constraints:
        lines.append(f"**Constraints ({len(constraints)}):**")
        for c in constraints[:10]:
            lines.append(f"  - {c}")
        lines.append("")

    action_items = context.get("action_items", [])
    if action_items:
        lines.append(f"**Action Items ({len(action_items)}):**")
        for ai in action_items[:10]:
            lines.append(f"  - {ai}")
        lines.append("")

    meta = context.get("_build_metadata", {})
    if meta:
        lines.append(f"*Built from {meta.get('document_count', '?')} documents, "
                     f"{meta.get('valid_documents', '?')} valid.*")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────


def _empty_context() -> Dict[str, Any]:
    """Return an empty context pack."""
    return asdict(ProjectContext())


def _aggregate_extractions(extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate intelligence from multiple document extractions."""
    aggregated: Dict[str, Any] = {
        "risks": [],
        "assumptions": [],
        "dependencies": [],
        "constraints": [],
        "resources": [],
        "scope_fragments": [],
        "action_items": [],
    }

    for extraction in extractions:
        for key in aggregated:
            aggregated[key].extend(extraction.get(key, []))

    # Deduplicate string lists
    for key in ["risks", "assumptions", "dependencies", "constraints", "action_items"]:
        aggregated[key] = _deduplicate_strings(aggregated[key])

    return aggregated


def _deduplicate_strings(items: List[str]) -> List[str]:
    """Deduplicate strings case-insensitively."""
    seen: set = set()
    unique: List[str] = []
    for item in items:
        if isinstance(item, str):
            normalised = item.lower().strip()
            if normalised not in seen and len(normalised) > 3:
                seen.add(normalised)
                unique.append(item)
    return unique


def _build_scope_summary(scope_fragments: List[Dict[str, Any]]) -> str:
    """Combine scope fragments into a unified scope statement."""
    if not scope_fragments:
        return ""

    parts = []
    for fragment in scope_fragments:
        heading = fragment.get("heading", "")
        content = fragment.get("content", "")
        source = fragment.get("source", "")
        if content:
            parts.append(f"[{source}] {heading}: {_truncate(content, 300)}")

    return "\n\n".join(parts)


def _build_resource_list(raw_resources: List[Any]) -> List[Dict[str, Any]]:
    """Convert raw resource strings to structured resource dicts."""
    resources: List[Dict[str, Any]] = []
    for item in raw_resources:
        if isinstance(item, dict):
            resources.append(item)
        elif isinstance(item, str):
            resources.append({"description": item, "source": "extracted"})
    return resources


def _build_summary(aggregated: Dict[str, Any], documents: List[Dict[str, Any]]) -> str:
    """Build a one-paragraph summary of the project context."""
    doc_count = len(documents)
    risk_count = len(aggregated.get("risks", []))
    dep_count = len(aggregated.get("dependencies", []))
    constraint_count = len(aggregated.get("constraints", []))
    action_count = len(aggregated.get("action_items", []))

    source_types = set()
    for doc in documents:
        st = doc.get("metadata", {}).get("source_type", "")
        if st:
            source_types.add(st)

    summary_parts = [
        f"Context built from {doc_count} document(s)",
        f"({', '.join(sorted(source_types))})" if source_types else "",
        f"containing {risk_count} risks,",
        f"{dep_count} dependencies,",
        f"{constraint_count} constraints,",
        f"and {action_count} action items.",
    ]
    return " ".join(p for p in summary_parts if p)


def _merge_scope(existing: str, new: str) -> str:
    """Merge scope text: append new if different."""
    if not existing:
        return new
    if not new:
        return existing
    if new.strip() == existing.strip():
        return existing
    return f"{existing}\n\n---\n\n{new}"


def _merge_list(existing: List[str], new: List[str]) -> List[str]:
    """Merge two string lists with deduplication."""
    combined = existing + new
    return _deduplicate_strings(combined)


def _merge_resources(
    existing: List[Dict[str, Any]], new: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Merge resource lists, dedup by description."""
    seen = {r.get("description", "").lower() for r in existing}
    merged = list(existing)
    for r in new:
        desc = r.get("description", "").lower()
        if desc and desc not in seen:
            seen.add(desc)
            merged.append(r)
    return merged


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."
