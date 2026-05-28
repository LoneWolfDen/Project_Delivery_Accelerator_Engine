"""Intelligence Extractor – extracts structured facts from ingested documents.

Operates in files-only mode (no AI). Uses pattern matching + section heuristics
to extract risks, assumptions, dependencies, constraints, resources, and scope.
"""

from typing import Dict, List, Any

from processors.extractors.patterns import (
    ACTION_HEADING_KEYWORDS,
    ACTION_INLINE_PATTERNS,
    ASSUMPTION_HEADING_KEYWORDS,
    ASSUMPTION_INLINE_PATTERNS,
    CONSTRAINT_HEADING_KEYWORDS,
    CONSTRAINT_INLINE_PATTERNS,
    DEPENDENCY_HEADING_KEYWORDS,
    DEPENDENCY_INLINE_PATTERNS,
    RESOURCE_HEADING_KEYWORDS,
    RESOURCE_INLINE_PATTERNS,
    RISK_HEADING_KEYWORDS,
    RISK_INLINE_PATTERNS,
    SCOPE_HEADING_KEYWORDS,
    extract_bullet_items,
    extract_by_patterns,
    extract_numbered_items,
    matches_heading,
)


def extract_intelligence(document: Dict[str, Any]) -> Dict[str, Any]:
    """Extract structured intelligence from a single ingested document.

    Args:
        document: Dict representation of an IngestedDocument (from to_dict()).

    Returns:
        Dict with keys: risks, assumptions, dependencies, constraints,
        resources, scope_fragments, action_items, source.
    """
    sections = document.get("sections", [])
    metadata = document.get("metadata", {})

    extraction: Dict[str, Any] = {
        "source": document.get("filename", "unknown"),
        "source_type": metadata.get("source_type", "unknown"),
        "risks": [],
        "assumptions": [],
        "dependencies": [],
        "constraints": [],
        "resources": [],
        "scope_fragments": [],
        "action_items": [],
    }

    for section in sections:
        heading = section.get("heading", "")
        content = section.get("content", "")
        section_type = section.get("section_type", "body")

        # ── Risks ──
        if matches_heading(heading, RISK_HEADING_KEYWORDS):
            items = _extract_section_items(content)
            extraction["risks"].extend(items)
        else:
            extraction["risks"].extend(
                extract_by_patterns(content, RISK_INLINE_PATTERNS)
            )

        # ── Assumptions ──
        if matches_heading(heading, ASSUMPTION_HEADING_KEYWORDS):
            items = _extract_section_items(content)
            extraction["assumptions"].extend(items)
        else:
            extraction["assumptions"].extend(
                extract_by_patterns(content, ASSUMPTION_INLINE_PATTERNS)
            )

        # ── Dependencies ──
        if matches_heading(heading, DEPENDENCY_HEADING_KEYWORDS):
            items = _extract_section_items(content)
            extraction["dependencies"].extend(items)
        else:
            extraction["dependencies"].extend(
                extract_by_patterns(content, DEPENDENCY_INLINE_PATTERNS)
            )

        # ── Constraints ──
        if matches_heading(heading, CONSTRAINT_HEADING_KEYWORDS):
            items = _extract_section_items(content)
            extraction["constraints"].extend(items)
        else:
            extraction["constraints"].extend(
                extract_by_patterns(content, CONSTRAINT_INLINE_PATTERNS)
            )

        # ── Resources ──
        if matches_heading(heading, RESOURCE_HEADING_KEYWORDS):
            items = _extract_section_items(content)
            extraction["resources"].extend(items)
        else:
            extraction["resources"].extend(
                extract_by_patterns(content, RESOURCE_INLINE_PATTERNS)
            )

        # ── Scope ──
        if matches_heading(heading, SCOPE_HEADING_KEYWORDS):
            extraction["scope_fragments"].append({
                "heading": heading,
                "content": _truncate(content, 500),
                "source": document.get("filename", ""),
            })

        # ── Action Items ──
        if section_type == "action_item":
            items = _extract_section_items(content)
            extraction["action_items"].extend(items)
        elif matches_heading(heading, ACTION_HEADING_KEYWORDS):
            items = _extract_section_items(content)
            extraction["action_items"].extend(items)

    # Deduplicate
    for key in ["risks", "assumptions", "dependencies", "constraints", "resources", "action_items"]:
        extraction[key] = _deduplicate(extraction[key])

    return extraction


def _extract_section_items(content: str) -> List[str]:
    """Extract items from a section – tries bullets, then numbered, then lines."""
    items = extract_bullet_items(content)
    if items:
        return items
    items = extract_numbered_items(content)
    if items:
        return items
    # Fall back to non-empty lines
    lines = [l.strip() for l in content.splitlines() if l.strip() and len(l.strip()) > 10]
    return lines[:20]  # Cap to avoid noise


def _deduplicate(items: List[str]) -> List[str]:
    """Remove duplicate items (case-insensitive)."""
    seen: set = set()
    unique: List[str] = []
    for item in items:
        normalised = item.lower().strip()
        if normalised not in seen:
            seen.add(normalised)
            unique.append(item)
    return unique


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, adding ellipsis if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."
