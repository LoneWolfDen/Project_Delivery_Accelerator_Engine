"""AI-powered intelligence extractor.

Sends the aggregated project text to an LLM and merges the structured
response back into the regex-baseline extraction.

Design principles
─────────────────
- One LLM call per intelligence build (not per document) – keeps latency
  and token cost predictable regardless of how many files are ingested.
- Additive only – AI findings are merged *into* regex results, never
  replacing them.  Files-only extraction always runs first.
- Graceful degradation – any failure returns the regex baseline unchanged.
- Deterministic output shape – the returned dict has exactly the same keys
  as the regex extractor so nothing downstream changes.

Output format the LLM is asked to return
─────────────────────────────────────────
```json
{
  "risks": ["...", "..."],
  "assumptions": ["...", "..."],
  "dependencies": ["...", "..."],
  "constraints": ["...", "..."],
  "action_items": ["...", "..."],
  "scope": "one-paragraph scope summary"
}
```
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Categories the LLM is asked to populate
_CATEGORIES = ["risks", "assumptions", "dependencies", "constraints", "action_items"]

# Maximum characters of raw project text fed to the LLM.
# Keeps the prompt within a safe token budget for all backends.
_MAX_CONTEXT_CHARS = 6_000

_SYSTEM_PROMPT = """\
You are a senior delivery consultant performing pre-sales intelligence extraction.
Extract structured project intelligence from the documents provided.
Return ONLY a valid JSON object — no markdown fences, no commentary.
"""

_USER_PROMPT_TEMPLATE = """\
Analyse the following project documents and extract intelligence into these categories:

- risks: specific delivery, technical, or commercial risks (max 15 items)
- assumptions: things assumed to be true that haven't been confirmed (max 15 items)
- dependencies: external teams, systems, or decisions this project depends on (max 15 items)
- constraints: hard limits on time, budget, technology, compliance, or operations (max 15 items)
- action_items: open actions or next steps mentioned (max 10 items)
- scope: a single concise paragraph summarising what is in scope

Rules:
- Each item must be a complete, self-contained sentence (min 15 characters).
- Do not repeat items across categories.
- If a category has no relevant content, return an empty list [].
- Return ONLY a JSON object with keys: risks, assumptions, dependencies,
  constraints, action_items, scope.

PROJECT DOCUMENTS
─────────────────
{context}
"""


# ── Public API ────────────────────────────────────────────────────────────────


def extract_with_ai(
    documents: List[Dict[str, Any]],
    ai_backend: str,
    baseline: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run AI-powered extraction and merge with the regex baseline.

    Args:
        documents: List of IngestedDocument dicts (from to_dict()).
        ai_backend: Backend name, e.g. ``"groq"``, ``"gemini"``, ``"ollama"``.
        baseline: Regex extraction result from ``build_context()``.  When
            provided the AI findings are merged in additively.

    Returns:
        Merged extraction dict with the same keys as the regex extractor.
        Returns ``baseline`` unchanged on any failure.
    """
    if ai_backend in ("files_only", "", None):
        return baseline or {}

    try:
        from ai_backends import get_backend  # noqa: PLC0415
        backend = get_backend(ai_backend)
        if not backend.is_available():
            logger.warning("AI extraction: backend '%s' unavailable, skipping.", ai_backend)
            return baseline or {}
    except Exception as exc:
        logger.warning("AI extraction: could not load backend '%s': %s", ai_backend, exc)
        return baseline or {}

    context_text = _build_context_text(documents)
    if not context_text.strip():
        return baseline or {}

    prompt = _USER_PROMPT_TEMPLATE.format(context=context_text)

    try:
        response = backend.generate(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            temperature=0.1,   # low temperature → more deterministic extraction
            max_tokens=2_000,
        )
    except Exception as exc:
        logger.warning("AI extraction: generate() failed: %s", exc)
        return baseline or {}

    if not response.success or not response.text:
        logger.warning(
            "AI extraction: backend returned error: %s",
            response.error or "empty response",
        )
        return baseline or {}

    ai_result = _parse_response(response.text)
    if not ai_result:
        logger.warning("AI extraction: could not parse JSON from response.")
        return baseline or {}

    return _merge(baseline or {}, ai_result, ai_backend, response)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_context_text(documents: List[Dict[str, Any]]) -> str:
    """Concatenate document text up to _MAX_CONTEXT_CHARS.

    Uses raw_text when available; falls back to joining section content.
    Each document is prefixed with its filename so the LLM has source context.
    """
    parts: List[str] = []
    total = 0

    for doc in documents:
        if not doc.get("is_valid", False):
            continue

        filename = doc.get("filename", "unknown")
        raw = doc.get("raw_text", "")
        if not raw:
            raw = "\n".join(
                s.get("content", "") for s in doc.get("sections", [])
            )

        snippet = raw.strip()
        if not snippet:
            continue

        available = _MAX_CONTEXT_CHARS - total
        if available <= 0:
            break

        if len(snippet) > available:
            snippet = snippet[:available].rsplit(" ", 1)[0] + "\n[...truncated]"

        parts.append(f"### {filename}\n{snippet}")
        total += len(snippet)

    return "\n\n".join(parts)


def _parse_response(text: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from the LLM response text.

    Handles responses wrapped in markdown code fences or with leading prose.
    """
    # Strip markdown fences if present
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fenced:
        text = fenced.group(1)

    # Try direct parse
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Find the first {...} block
    brace_match = re.search(r"\{[\s\S]+\}", text)
    if brace_match:
        try:
            data = json.loads(brace_match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


def _merge(
    baseline: Dict[str, Any],
    ai_result: Dict[str, Any],
    backend_name: str,
    response: Any,
) -> Dict[str, Any]:
    """Merge AI findings into the baseline extraction.

    - List categories: deduplicated union (baseline items first).
    - scope: AI scope replaces blank baseline scope; otherwise appended.
    - _ai_extraction_meta: attached for traceability.
    """
    merged = dict(baseline)

    for cat in _CATEGORIES:
        ai_items = _clean_list(ai_result.get(cat, []))
        base_items = list(baseline.get(cat, []))
        merged[cat] = _dedup_merge(base_items, ai_items)

    # Scope: prefer AI summary when baseline is empty
    ai_scope = (ai_result.get("scope") or "").strip()
    base_scope = (baseline.get("scope") or "").strip()
    if ai_scope:
        if not base_scope:
            merged["scope"] = ai_scope
        elif ai_scope.lower() not in base_scope.lower():
            merged["scope"] = base_scope + "\n\n[AI summary] " + ai_scope

    # Traceability metadata
    merged["_ai_extraction_meta"] = {
        "backend": backend_name,
        "model": getattr(response, "model", ""),
        "tokens_used": getattr(response, "tokens_used", None),
        "latency_ms": getattr(response, "latency_ms", None),
        "ai_risks": len(_clean_list(ai_result.get("risks", []))),
        "ai_assumptions": len(_clean_list(ai_result.get("assumptions", []))),
        "ai_dependencies": len(_clean_list(ai_result.get("dependencies", []))),
        "ai_constraints": len(_clean_list(ai_result.get("constraints", []))),
        "ai_action_items": len(_clean_list(ai_result.get("action_items", []))),
    }

    # Update build metadata counts
    meta = merged.get("_build_metadata", {})
    for cat in _CATEGORIES:
        key = f"total_{cat}" if cat != "action_items" else "total_action_items"
        # Normalise key names to match existing metadata keys
        key_map = {
            "total_risks": "total_risks",
            "total_assumptions": "total_assumptions",
            "total_dependencies": "total_dependencies",
            "total_constraints": "total_constraints",
            "total_action_items": "total_action_items",
        }
        mapped = key_map.get(f"total_{cat}", f"total_{cat}")
        meta[mapped] = len(merged.get(cat, []))
    meta["ai_backend_used"] = backend_name
    merged["_build_metadata"] = meta

    return merged


def _clean_list(items: Any) -> List[str]:
    """Ensure items is a list of non-empty strings meeting minimum length."""
    from processors.extractors.patterns import MIN_EXTRACTION_LENGTH  # noqa: PLC0415
    if not isinstance(items, list):
        return []
    cleaned = []
    for item in items:
        if isinstance(item, str):
            s = item.strip()
            if len(s) >= MIN_EXTRACTION_LENGTH:
                cleaned.append(s)
    return cleaned


def _dedup_merge(base: List[str], ai: List[str]) -> List[str]:
    """Merge two lists, keeping baseline order and adding novel AI items."""
    seen = {item.lower().strip() for item in base}
    result = list(base)
    for item in ai:
        normalised = item.lower().strip()
        # Skip if exact match or near-duplicate (substring of existing item)
        if normalised in seen:
            continue
        if any(normalised in existing or existing in normalised for existing in seen):
            continue
        seen.add(normalised)
        result.append(item)
    return result
