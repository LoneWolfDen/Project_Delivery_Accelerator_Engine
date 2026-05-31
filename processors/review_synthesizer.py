"""Review Synthesizer — PDAE-MS-01 Sprint 1.

Standalone synthesis engine.  No imports from proposal_generator,
handlers, services, or DB.  Safe to import at any point without
triggering side-effects.

Public API (Sprint 1)
─────────────────────
  normalize_review_findings(review)          -> List[NormalizedItem]
  deduplicate_normalized(items, score_map)   -> List[NormalizedItem]
  build_reconciliation_prompt(deduped, scope)-> str
  parse_reconciliation_response(raw, ...)    -> ReconciliationResult
  synthesize_reviews(anchor, supplementals,
                     version_scope,
                     ai_backend)             -> ReconciliationResult
  extract_scope_themes(scope, findings)      -> List[str]
  merge_decision_points(reviews)             -> List[Dict]

Internal helpers (prefixed _) are not part of the public contract.

Caching
───────
  Normalisation and deduplication results are cached in module-level
  dicts keyed by review_id / frozenset(review_ids).
  Cache is in-memory only — cleared on process restart.
  LLM reconciliation is NEVER cached.
"""

from __future__ import annotations

import logging
import re
import string
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from models.proposal import (
    ConflictEntry,
    NormalizedItem,
    ReconciliationResult,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

FINDING_CATEGORIES = [
    "risks",
    "assumptions",
    "dependencies",
    "constraints",
    "action_items",
]

_DEDUP_THRESHOLD = 0.75  # Jaccard similarity above which items are duplicates

# Scope-theme extraction: known platform / tech keywords kept as single tokens
_PLATFORM_KEYWORDS = {
    "azure", "aws", "gcp", "google cloud", "salesforce", "servicenow",
    "kubernetes", "docker", "terraform", "jenkins", "gitlab", "github",
    "oracle", "sap", "dynamics", "sharepoint", "confluence", "jira",
    "postgresql", "mysql", "mongodb", "redis", "kafka", "rabbitmq",
    "datadog", "splunk", "grafana", "prometheus",
}

# ── Module-level caches ──────────────────────────────────────────────────────

_normalise_cache: Dict[str, List[NormalizedItem]] = {}
_dedup_cache: Dict[FrozenSet[str], List[NormalizedItem]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ────────────────────────────────────────────────────────────────────────────
# S1-01  Normalise review findings
# ────────────────────────────────────────────────────────────────────────────

def normalize_review_findings(review: Any) -> List[NormalizedItem]:
    """Flatten a single review's findings into typed, provenance-tagged items.

    Args:
        review: A Review dataclass instance (or duck-typed object with
                .review_id, .persona, .findings attributes).

    Returns:
        List[NormalizedItem] — one item per non-empty finding string.
        Empty list when findings is absent or empty.
    """
    review_id: str = getattr(review, "review_id", "") or ""
    persona: str = getattr(review, "persona", "") or ""
    findings: Dict[str, Any] = getattr(review, "findings", None) or {}

    # Cache check
    if review_id and review_id in _normalise_cache:
        return _normalise_cache[review_id]

    items: List[NormalizedItem] = []

    for category in FINDING_CATEGORIES:
        raw_list = findings.get(category, [])
        if not isinstance(raw_list, list):
            continue
        for raw in raw_list:
            text = raw if isinstance(raw, str) else str(raw)
            text = text.strip()
            if not text:
                continue
            dedup_key = _make_dedup_key(text)
            if not dedup_key:
                continue
            items.append(NormalizedItem(
                text=text,
                category=category,
                review_id=review_id,
                persona=persona,
                dedup_key=dedup_key,
            ))

    if review_id:
        _normalise_cache[review_id] = items

    return items


def _make_dedup_key(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace.

    AC3: 'Risk: Database access  may fail.' -> 'risk database access may fail'
    """
    lowered = text.lower()
    # Remove punctuation except spaces
    no_punct = lowered.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
    collapsed = " ".join(no_punct.split())
    return collapsed


# ────────────────────────────────────────────────────────────────────────────
# S1-02  Deterministic deduplication
# ────────────────────────────────────────────────────────────────────────────

def deduplicate_normalized(
    items: List[NormalizedItem],
    review_completeness_map: Optional[Dict[str, int]] = None,
) -> List[NormalizedItem]:
    """Collapse near-identical findings using Jaccard similarity.

    Args:
        items:                    Normalised items spanning one or more reviews.
        review_completeness_map:  {review_id: completeness_score}.  Used to
                                  prefer items from higher-quality reviews on
                                  dedup collision.  Defaults to equal priority.

    Returns:
        Deduplicated list.  Items from different categories are never merged.
        Order within each category is preserved (first survivor wins unless a
        later item comes from a higher-quality review).
    """
    score_map = review_completeness_map or {}

    # Build cache key from the sorted unique review IDs present in items
    review_ids_in = frozenset(i.review_id for i in items)
    cache_key: FrozenSet[str] = frozenset(
        f"{i.review_id}:{i.category}:{i.dedup_key}" for i in items
    )
    if cache_key in _dedup_cache:
        return _dedup_cache[cache_key]

    # Process per category to avoid cross-category merges (AC4)
    result: List[NormalizedItem] = []
    by_category: Dict[str, List[NormalizedItem]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)

    for category in FINDING_CATEGORIES:
        cat_items = by_category.get(category, [])
        survivors = _dedup_category(cat_items, score_map)
        result.extend(survivors)

    _dedup_cache[cache_key] = result
    return result


def _dedup_category(
    items: List[NormalizedItem],
    score_map: Dict[str, int],
) -> List[NormalizedItem]:
    """Dedup within one category."""
    survivors: List[NormalizedItem] = []

    for candidate in items:
        replaced = False
        for idx, existing in enumerate(survivors):
            sim = _jaccard_similarity(candidate.dedup_key, existing.dedup_key)
            if sim >= _DEDUP_THRESHOLD:
                # Keep the item from the higher-quality review
                cand_score = score_map.get(candidate.review_id, 0)
                exist_score = score_map.get(existing.review_id, 0)
                if cand_score > exist_score:
                    survivors[idx] = candidate
                # Equal score: keep existing (first/older wins — stable)
                replaced = True
                break
        if not replaced:
            survivors.append(candidate)

    return survivors


def _jaccard_similarity(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two dedup_key strings."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    set_a = set(a.split())
    set_b = set(b.split())
    intersection = set_a & set_b
    union = set_a | set_b
    if not union:
        return 0.0
    return len(intersection) / len(union)


# ────────────────────────────────────────────────────────────────────────────
# S1-03  Build and parse reconciliation prompt
# ────────────────────────────────────────────────────────────────────────────

def build_reconciliation_prompt(
    deduped: List[NormalizedItem],
    version_scope: str,
) -> str:
    """Build the structured reconciliation prompt for the LLM.

    Args:
        deduped:        Deduplicated NormalizedItems (all categories).
        version_scope:  Version scope text — truncated to 800 chars.

    Returns:
        Formatted prompt string ready to send to the LLM.
    """
    scope_trunc = (version_scope or "")[:800]

    # Group by category for prompt formatting
    by_cat: Dict[str, List[NormalizedItem]] = {}
    for item in deduped:
        by_cat.setdefault(item.category, []).append(item)

    def _format_cat(cat: str) -> str:
        cat_items = by_cat.get(cat, [])
        if not cat_items:
            return "(none)"
        lines = []
        for it in cat_items[:15]:  # token-budget guard: max 15 per category
            lines.append(f"  [{it.review_id} / {it.persona}] {it.text}")
        return "\n".join(lines)

    review_ids = sorted({i.review_id for i in deduped})
    n = len(review_ids)

    prompt = f"""You are a senior delivery consultant reconciling findings from {n} review(s) of the same intelligence version into a single coherent proposal-ready set.

Source reviews: {', '.join(review_ids)}

DEDUPLICATED FINDINGS (with review provenance):

RISKS:
{_format_cat('risks')}

ASSUMPTIONS:
{_format_cat('assumptions')}

DEPENDENCIES:
{_format_cat('dependencies')}

CONSTRAINTS:
{_format_cat('constraints')}

ACTION ITEMS:
{_format_cat('action_items')}

VERSION SCOPE (max 800 chars):
{scope_trunc}

Tasks:
1. For each category produce one merged list. Where items overlap in substance, keep the most specific and complete version. Do not invent new items.
2. Flag genuine contradictions as CONFLICT entries with a plain-English description.
3. Provide brief reconciliation notes explaining key merge decisions.

Output (use EXACTLY these headers, no markdown):
---RECONCILED_RISKS---
---RECONCILED_ASSUMPTIONS---
---RECONCILED_DEPENDENCIES---
---RECONCILED_CONSTRAINTS---
---RECONCILED_ACTION_ITEMS---
---CONFLICTS---
---RECONCILIATION_NOTES---"""

    return prompt


def parse_reconciliation_response(
    raw: str,
    source_ids: List[str],
    anchor_id: str,
    backend: str,
) -> ReconciliationResult:
    """Parse the LLM reconciliation response into a ReconciliationResult.

    Missing sections → empty list (not an error).
    Empty raw response → ReconciliationResult with all empty fields.
    """
    raw = raw or ""

    category_map = {
        "risks":        "RECONCILED_RISKS",
        "assumptions":  "RECONCILED_ASSUMPTIONS",
        "dependencies": "RECONCILED_DEPENDENCIES",
        "constraints":  "RECONCILED_CONSTRAINTS",
        "action_items": "RECONCILED_ACTION_ITEMS",
    }

    reconciled: Dict[str, List[str]] = {}
    for cat, header in category_map.items():
        reconciled[cat] = _extract_section_lines(raw, header)

    # Parse conflicts
    conflict_lines = _extract_section_lines(raw, "CONFLICTS")
    contradictions: List[ConflictEntry] = []
    for line in conflict_lines:
        line = line.strip()
        if not line:
            continue
        # Each non-empty line is one conflict description
        contradictions.append(ConflictEntry(
            category="general",
            description=line,
            review_ids=list(source_ids),
        ))

    # Overlaps resolved = lines that appeared in multiple reviews but were merged
    # (we surface reconciliation_notes for this; overlaps_resolved is a bonus field)
    notes_lines = _extract_section_lines(raw, "RECONCILIATION_NOTES")
    reconciliation_notes = "\n".join(notes_lines).strip()

    return ReconciliationResult(
        reconciled_findings=reconciled,
        overlaps_resolved=[],      # populated by LLM notes — not separately parsed
        contradictions=contradictions,
        reconciliation_notes=reconciliation_notes,
        source_review_ids=list(source_ids),
        anchor_review_id=anchor_id,
        generated_by=backend,
        generated_at=_now_iso(),
    )


def _extract_section_lines(raw: str, header: str) -> List[str]:
    """Extract non-empty lines between ---HEADER--- and the next ---*--- marker."""
    pattern = rf"---{re.escape(header)}---\s*(.*?)(?=---[A-Z_]+---|$)"
    match = re.search(pattern, raw, re.DOTALL)
    if not match:
        return []
    block = match.group(1).strip()
    lines = [ln.strip().lstrip("- ").strip() for ln in block.splitlines()]
    return [ln for ln in lines if ln]


# ────────────────────────────────────────────────────────────────────────────
# S1-04  synthesize_reviews() orchestrator
# ────────────────────────────────────────────────────────────────────────────

def synthesize_reviews(
    anchor_review: Any,
    supplemental_reviews: List[Any],
    version_scope: str,
    ai_backend: str = "files_only",
) -> ReconciliationResult:
    """Orchestrate: normalise → dedupe → LLM reconcile (or deterministic fallback).

    Args:
        anchor_review:        The active Review (mandatory anchor).
        supplemental_reviews: Additional Review objects from the same version.
                              quality_status is NOT checked — user is trusted.
        version_scope:        scope text from the hierarchy Version.
        ai_backend:           Backend name.  'files_only' → deterministic only.

    Returns:
        ReconciliationResult

    Raises:
        ValueError: if any supplemental review has a different version_id
                    than the anchor.
    """
    anchor_version_id: str = getattr(anchor_review, "version_id", "") or ""
    anchor_id: str = getattr(anchor_review, "review_id", "") or ""

    # Validate version_id consistency
    for sup in supplemental_reviews:
        sup_version_id = getattr(sup, "version_id", "") or ""
        sup_review_id = getattr(sup, "review_id", "") or ""
        if anchor_version_id and sup_version_id and sup_version_id != anchor_version_id:
            raise ValueError(
                f"Supplemental review '{sup_review_id}' belongs to version "
                f"'{sup_version_id}', but anchor review '{anchor_id}' belongs to "
                f"version '{anchor_version_id}'. All reviews must be from the same version."
            )

    all_reviews = [anchor_review] + list(supplemental_reviews)
    source_ids = [getattr(r, "review_id", "") for r in all_reviews]

    # Build completeness score map for dedup tie-breaking
    score_map: Dict[str, int] = {
        getattr(r, "review_id", ""): getattr(r, "completeness_score", 0)
        for r in all_reviews
    }

    # Step 3: Normalise each review
    all_items: List[NormalizedItem] = []
    for review in all_reviews:
        all_items.extend(normalize_review_findings(review))

    # Step 4: Deterministic dedup
    deduped = deduplicate_normalized(all_items, score_map)

    # Steps 5a (files_only): deterministic union — skip LLM
    if ai_backend == "files_only":
        return _deterministic_reconcile(deduped, source_ids, anchor_id)

    # Step 5b (AI): call LLM
    try:
        return _llm_reconcile(deduped, version_scope, source_ids, anchor_id, ai_backend)
    except Exception as exc:
        logger.warning(
            "LLM reconciliation failed (%s) — falling back to deterministic. Error: %s",
            ai_backend, exc,
        )
        result = _deterministic_reconcile(deduped, source_ids, anchor_id)
        result.generated_by = f"{ai_backend}_fallback"
        return result


def _deterministic_reconcile(
    deduped: List[NormalizedItem],
    source_ids: List[str],
    anchor_id: str,
) -> ReconciliationResult:
    """Deterministic reconciliation: union of deduped items per category."""
    reconciled: Dict[str, List[str]] = {cat: [] for cat in FINDING_CATEGORIES}
    for item in deduped:
        reconciled[item.category].append(item.text)

    return ReconciliationResult(
        reconciled_findings=reconciled,
        overlaps_resolved=[],
        contradictions=[],
        reconciliation_notes="",
        source_review_ids=list(source_ids),
        anchor_review_id=anchor_id,
        generated_by="deterministic",
        generated_at=_now_iso(),
    )


def _llm_reconcile(
    deduped: List[NormalizedItem],
    version_scope: str,
    source_ids: List[str],
    anchor_id: str,
    ai_backend: str,
) -> ReconciliationResult:
    """Call the LLM and parse its response."""
    from ai_backends import get_backend  # deferred import — no side-effects at module load

    prompt = build_reconciliation_prompt(deduped, version_scope)
    backend = get_backend(ai_backend)

    system_prompt = (
        "You are a senior delivery consultant. "
        "Reconcile the provided review findings into a clean, proposal-ready set. "
        "Be concise. Do not invent items not present in the source findings."
    )

    response = backend.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=2500,
    )

    if not response.success:
        raise RuntimeError(f"LLM call failed: {response.error}")

    return parse_reconciliation_response(response.text, source_ids, anchor_id, ai_backend)


# ────────────────────────────────────────────────────────────────────────────
# S1-05  Scope theme extraction
# ────────────────────────────────────────────────────────────────────────────

def extract_scope_themes(
    version_scope: str,
    findings: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Extract named deliverables, systems, and workstreams.

    Sources:
      1. version_scope text (capitalised noun phrases ≥ 2 words, platform names,
         quoted strings)
      2. action_items from findings

    Returns:
        Lowercase, deduplicated list of themes.  Empty list on empty input.
    """
    scope = version_scope or ""
    findings = findings or {}
    action_items: List[str] = [
        it if isinstance(it, str) else str(it)
        for it in findings.get("action_items", [])
    ]

    raw_themes: List[str] = []

    # 1. Quoted strings in scope
    raw_themes.extend(re.findall(r'"([^"]{4,})"', scope))
    raw_themes.extend(re.findall(r"'([^']{4,})'", scope))

    # 2. Known platform keywords in scope (case-insensitive)
    scope_lower = scope.lower()
    for kw in _PLATFORM_KEYWORDS:
        if kw in scope_lower:
            raw_themes.append(kw)

    # 3. Capitalised noun phrases ≥ 2 consecutive Title-Case words in scope
    cap_phrases = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', scope)
    raw_themes.extend(cap_phrases)

    # 4. Known platform keywords in action_items
    for ai_text in action_items:
        ai_lower = ai_text.lower()
        for kw in _PLATFORM_KEYWORDS:
            if kw in ai_lower:
                raw_themes.append(kw)
        # Capitalised phrases in action items
        cap_in_action = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', ai_text)
        raw_themes.extend(cap_in_action)

    # Normalise and deduplicate
    seen: set = set()
    result: List[str] = []
    for theme in raw_themes:
        norm = theme.strip().lower()
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)

    return result


# ────────────────────────────────────────────────────────────────────────────
# S1-06  Merge decision points
# ────────────────────────────────────────────────────────────────────────────

def merge_decision_points(selected_reviews: List[Any]) -> List[Dict[str, Any]]:
    """Collect and deduplicate decision_points across selected reviews.

    Anchor review's version of a duplicate takes precedence on status.
    The first review in the list is treated as the anchor.

    Args:
        selected_reviews: List of Review objects (anchor first).

    Returns:
        List of dicts with keys: text, category, status, source_review_id.
    """
    if not selected_reviews:
        return []

    anchor_id: str = getattr(selected_reviews[0], "review_id", "") or ""
    merged: List[Dict[str, Any]] = []
    seen_keys: List[str] = []  # dedup_key for each survivor

    # Anchor first, then supplementals — so anchor wins on ties
    for review in selected_reviews:
        review_id = getattr(review, "review_id", "") or ""
        dps = getattr(review, "decision_points", None) or []

        for dp in dps:
            if not isinstance(dp, dict):
                continue
            text = dp.get("text", "") or ""
            if not text:
                continue
            key = _make_dedup_key(text)

            # Check for near-duplicate
            is_dup = False
            for idx, existing_key in enumerate(seen_keys):
                if _jaccard_similarity(key, existing_key) >= _DEDUP_THRESHOLD:
                    # Duplicate found — anchor wins on status
                    if review_id == anchor_id:
                        merged[idx]["status"] = dp.get("status", "open")
                        merged[idx]["source_review_id"] = anchor_id
                    is_dup = True
                    break

            if not is_dup:
                seen_keys.append(key)
                merged.append({
                    "text":             text,
                    "category":         dp.get("category", "general"),
                    "status":           dp.get("status", "open"),
                    "source_review_id": review_id,
                })

    return merged


# ────────────────────────────────────────────────────────────────────────────
# Prompt builders for later sprints (defined here for testability)
# ────────────────────────────────────────────────────────────────────────────

def build_decision_summary_prompt(
    merged_decisions: List[Dict[str, Any]],
    reconciliation_notes: str,
) -> str:
    """Build the decision summary classification prompt."""
    n = len(merged_decisions)
    lines = [
        f"  {d['text']} | {d.get('category','general')} | {d.get('source_review_id','')}"
        for d in merged_decisions
    ]
    items_block = "\n".join(lines) if lines else "  (none)"

    return f"""You are reviewing decision points extracted from {n} review(s).
Classify each as CONFIRMED, OPEN, or BLOCKER.

CONFIRMED: clearly resolved in the findings
OPEN: unresolved or deferred — needs a decision
BLOCKER: unresolved and directly risks sign-off or delivery

MERGED DECISION POINTS:
{items_block}

RECONCILIATION NOTES:
{reconciliation_notes or '(none)'}

Output (use EXACTLY these headers):
---CONFIRMED---
---OPEN---
---BLOCKERS---"""


def build_forward_guidance_prompt(
    review_pass_dict: Dict[str, Any],
    decision_summary_dict: Dict[str, Any],
    conflicts: List[ConflictEntry],
    version_scope: str,
) -> str:
    """Build the forward guidance prompt."""
    scope_trunc = (version_scope or "")[:600]

    # Collect still_weak across all domains
    still_weak: List[str] = []
    for domain in ["scope", "architecture", "delivery", "security_compliance",
                   "operations", "commercials"]:
        domain_data = review_pass_dict.get(domain, {})
        still_weak.extend(domain_data.get("still_weak", []))

    open_decisions = [d.get("text", "") for d in decision_summary_dict.get("open", [])]
    conflict_descs = [c.description for c in conflicts]

    # Coverage gaps: domains with status != Addressed
    coverage_gaps: List[str] = []
    # (populated in Sprint 3 when proposal_coverage is available)

    def _block(title: str, items: List[str]) -> str:
        if not items:
            return f"{title}:\n  (none)"
        return f"{title}:\n" + "\n".join(f"  - {it}" for it in items)

    return f"""You are a senior delivery advisor. Based only on the data provided, identify recommended focus areas to strengthen this proposal toward sign-off readiness.

Rules:
- Recommendations must be grounded in the data below
- Respect stated constraints: budget, timeline, client preferences, delivery model
- Do not invent new facts or unsupported scope
- Optional enhancements must be clearly viable given current context

{_block('UNRESOLVED WEAKNESSES', still_weak)}

{_block('OPEN DECISIONS', open_decisions)}

{_block('CONFLICTS', conflict_descs)}

VERSION SCOPE:
{scope_trunc}

For each recommendation include:
- issue
- why_it_matters
- suggested_action
- trade_off_or_constraint (empty string if none)

Output (use EXACTLY these headers):
---STRENGTHEN_WEAK_AREAS---
---RESOLVE_KEY_DECISIONS---
---IMPROVE_CREDIBILITY---
---ACCELERATE_CLIENT_ALIGNMENT---
---OPTIONAL_ENHANCEMENTS---"""


# ────────────────────────────────────────────────────────────────────────────
# Cache management (test helper)
# ────────────────────────────────────────────────────────────────────────────

def _clear_caches() -> None:
    """Clear all module-level caches.  Intended for test isolation only."""
    global _normalise_cache, _dedup_cache
    _normalise_cache = {}
    _dedup_cache = {}
