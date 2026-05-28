"""Intelligence Extractor – extracts structured facts from ingested documents.

Operates in files-only mode (no AI). Uses pattern matching + section heuristics
to extract risks, assumptions, dependencies, constraints, resources, and scope.

Enhanced extraction features:
- Markdown table parsing (risk tables → structured risk items)
- Noise filtering (table separators, pipe fragments, too-short items)
- Min/max length enforcement
- Context-aware extraction (uses heading + content together)
"""

from typing import Dict, List, Any

from processors.extractors.patterns import (
    ACTION_HEADING_KEYWORDS,
    ACTION_INLINE_PATTERNS,
    ASSUMPTION_HEADING_KEYWORDS,
    ASSUMPTION_INLINE_PATTERNS,
    CONSTRAINT_HEADING_EXCLUSIONS,
    CONSTRAINT_HEADING_KEYWORDS,
    CONSTRAINT_INLINE_PATTERNS,
    DEPENDENCY_HEADING_KEYWORDS,
    DEPENDENCY_INLINE_PATTERNS,
    MIN_EXTRACTION_LENGTH,
    RESOURCE_HEADING_KEYWORDS,
    RESOURCE_INLINE_PATTERNS,
    RISK_HEADING_KEYWORDS,
    RISK_INLINE_PATTERNS,
    SCOPE_HEADING_KEYWORDS,
    clean_extraction,
    extract_bullet_items,
    extract_by_patterns,
    extract_from_table,
    extract_numbered_items,
    extract_table_rows,
    is_noise_line,
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
            items = _extract_from_heading_section(content, "risk")
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
        if matches_heading(heading, CONSTRAINT_HEADING_KEYWORDS, CONSTRAINT_HEADING_EXCLUSIONS):
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

    # Deduplicate and final quality filter
    for key in ["risks", "assumptions", "dependencies", "constraints", "resources", "action_items"]:
        extraction[key] = _deduplicate(extraction[key])

    return extraction


def _extract_from_heading_section(content: str, category: str) -> List[str]:
    """Extract items from a section that matches a heading keyword.

    Enhanced: detects markdown tables and extracts structured data from them.
    Falls back to bullet/numbered/line extraction.
    """
    # Check if content contains a markdown table
    table_rows = extract_table_rows(content)
    if table_rows:
        return _extract_from_risk_table(content, table_rows, category)

    # Standard extraction
    return _extract_section_items(content)


def _extract_from_risk_table(
    content: str, table_rows: List[List[str]], category: str
) -> List[str]:
    """Extract structured items from a markdown risk/issue table.

    Detects column headers and builds meaningful items from rows.
    Example: "Data loss during DB migration (Impact: Critical, Likelihood: Low)"
    """
    # Try to find header row to understand columns
    lines = content.splitlines()
    header_cells: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and "---" not in stripped:
            header_cells = [c.strip().lower() for c in stripped.strip("|").split("|")]
            break

    # Build structured items from table data
    items: List[str] = []
    for row in table_rows:
        item = _build_table_row_item(row, header_cells, category)
        if item and len(item) >= MIN_EXTRACTION_LENGTH:
            items.append(item)

    return items


def _build_table_row_item(
    row: List[str], headers: List[str], category: str
) -> str:
    """Build a readable item string from a table row and its headers."""
    if not row:
        return ""

    # If we have headers, build a structured description
    if headers and len(headers) >= 2:
        # Find the main description column (first text-heavy column)
        main_value = row[0] if row else ""
        qualifiers: List[str] = []

        for i, cell in enumerate(row[1:], 1):
            if i < len(headers) and cell.strip():
                header = headers[i].strip()
                cell_val = cell.strip()
                # Skip mitigation/notes columns in risk tables
                if header in ("mitigation", "notes", "owner", "status"):
                    continue
                if cell_val and len(cell_val) < 50:
                    qualifiers.append(f"{header}: {cell_val}")

        if main_value:
            if qualifiers:
                return f"{main_value} ({', '.join(qualifiers[:3])})"
            return main_value
    else:
        # No headers, just use first meaningful cell
        for cell in row:
            if cell.strip() and len(cell.strip()) >= MIN_EXTRACTION_LENGTH:
                return cell.strip()

    return ""


def _extract_section_items(content: str) -> List[str]:
    """Extract items from a section – tries bullets, then numbered, then lines.

    Enhanced: filters noise, enforces minimum length.
    """
    items = extract_bullet_items(content)
    if items:
        return items
    items = extract_numbered_items(content)
    if items:
        return items
    # Fall back to non-empty, non-noise lines
    lines = []
    for line in content.splitlines():
        cleaned = clean_extraction(line)
        if cleaned and len(cleaned) >= MIN_EXTRACTION_LENGTH and not is_noise_line(cleaned):
            lines.append(cleaned)
    return lines[:15]  # Cap to avoid noise


def _deduplicate(items: List[str]) -> List[str]:
    """Remove duplicate items using fuzzy matching.

    Two items are considered duplicates if:
    - They are case-insensitively identical, OR
    - One is a substring of the other (>70% overlap)
    """
    seen: List[str] = []  # Keep originals for substring comparison
    unique: List[str] = []

    for item in items:
        normalised = item.lower().strip()
        if len(normalised) < MIN_EXTRACTION_LENGTH:
            continue

        is_dup = False
        for existing in seen:
            # Exact match
            if normalised == existing:
                is_dup = True
                break
            # Substring containment (shorter is contained in longer)
            shorter = min(normalised, existing, key=len)
            longer = max(normalised, existing, key=len)
            if shorter in longer:
                is_dup = True
                # Keep the longer (more context) — replace if new is longer
                if len(normalised) > len(existing):
                    idx = seen.index(existing)
                    seen[idx] = normalised
                    unique[idx] = item
                break
            # High overlap (>70% of words shared)
            words_a = set(normalised.split())
            words_b = set(existing.split())
            if words_a and words_b:
                overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
                if overlap > 0.7:
                    is_dup = True
                    # Keep longer version
                    if len(normalised) > len(existing):
                        idx = seen.index(existing)
                        seen[idx] = normalised
                        unique[idx] = item
                    break

        if not is_dup:
            seen.append(normalised)
            unique.append(item)

    return unique


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, adding ellipsis if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."
