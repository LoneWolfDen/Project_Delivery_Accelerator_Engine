"""Feedback Classifier — DS-06.

Converts raw pasted text (email, transcript, meeting notes) into
structured FeedbackItem lists.

Two code paths:
  AI mode    — LLM classifies each paragraph into category + mapped_to
  files_only — heuristic keyword pre-fill (hybrid tagger: user confirms)

Public API
──────────
  split_into_paragraphs(text)           → List[str]
  classify_items_heuristic(segments)    → List[FeedbackItem dict]
  classify_items_ai(segments, pid, bk)  → List[FeedbackItem dict]
  classify_feedback(raw, pid, bk)       → classification result dict
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_item(
    text: str,
    category: str = "concerns",
    mapped_to: Optional[str] = None,
    confidence: str = "low",
    is_critical: bool = False,
) -> Dict[str, Any]:
    """Build a FeedbackItem dict with auto-critical flagging."""
    item = {
        "item_id":              f"fi_{uuid.uuid4().hex[:8]}",
        "text":                 text.strip(),
        "category":             category,
        "mapped_to":            mapped_to,
        "confidence":           confidence,
        "status":               "new",
        "is_critical":          is_critical,
        "addressed_in_version": None,
        "created_at":           _now(),
    }
    # Auto-flag: change_requested + scope_change/risk → critical
    if category == "change_requested" and mapped_to in ("scope_change", "risk"):
        item["is_critical"] = True
    # Auto-flag: rejected + scope_change/constraint → critical
    if category == "rejected" and mapped_to in ("scope_change", "constraint"):
        item["is_critical"] = True
    return item


# ──────────────────────────────────────────────────────────────
# 1. Text splitting
# ──────────────────────────────────────────────────────────────

def split_into_paragraphs(text: str) -> List[str]:
    """Split raw pasted text into paragraph-level segments.

    Splits on blank lines first. Falls back to sentence splitting
    if a paragraph is very long (>300 chars) so the tagger stays manageable.
    """
    if not text or not text.strip():
        return []

    raw_paras = re.split(r"\n\s*\n", text.strip())
    segments: List[str] = []

    for para in raw_paras:
        para = para.strip()
        if not para:
            continue
        if len(para) <= 300:
            segments.append(para)
        else:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            buf = ""
            for sent in sentences:
                if len(buf) + len(sent) <= 300:
                    buf = (buf + " " + sent).strip()
                else:
                    if buf:
                        segments.append(buf)
                    buf = sent
            if buf:
                segments.append(buf)

    return [s for s in segments if len(s) > 10]


# ──────────────────────────────────────────────────────────────
# 2. Heuristic classifier (files_only / hybrid tagger pre-fill)
# ──────────────────────────────────────────────────────────────

# Each entry: ([keywords], category, mapped_to, confidence)
_CATEGORY_SIGNALS: List[tuple] = [
    # Accepted
    (["happy with", "agree with", "accepted", "approve", "confirmed",
      "good with", "fine with", "supports", "aligned on", "no issue with"],
     "accepted", None, "medium"),
    # Rejected
    (["not acceptable", "reject", "won't agree", "cannot accept", "disagree",
      "remove this", "take this out", "not proceeding"],
     "rejected", None, "medium"),
    # Change requested — scope
    (["scope change", "out of scope", "add to scope", "reduce scope",
      "scope needs", "not in scope", "include in scope"],
     "change_requested", "scope_change", "high"),
    # Change requested — risk
    (["too risky", "risk is too", "unacceptable risk", "risk level", "risk needs"],
     "change_requested", "risk", "high"),
    # Change requested — constraint (timeline)
    (["timeline", "deadline", "too long", "too short", "compress",
      "extend", "delay", "push back", "earlier date"],
     "change_requested", "constraint", "high"),
    # Change requested — gap
    (["missing", "not covered", "gap in", "no mention of",
      "haven't addressed", "left out"],
     "change_requested", "gap", "medium"),
    # Concerns — assumption
    (["assume", "assuming", "assumption", "based on",
      "depends on", "if this"],
     "concerns", "assumption", "medium"),
    # Concerns — general
    (["concern", "worried", "not sure", "unclear", "need clarification",
      "question", "what about", "how will", "who is responsible"],
     "concerns", None, "low"),
]


def classify_items_heuristic(segments: List[str]) -> List[Dict[str, Any]]:
    """Classify text segments using keyword heuristics.

    Returns pre-filled FeedbackItem dicts for the hybrid tagger.
    User reviews and corrects each classification in the UI.
    """
    items: List[Dict[str, Any]] = []
    for seg in segments:
        lower = seg.lower()
        matched = False
        for keywords, category, mapped_to, confidence in _CATEGORY_SIGNALS:
            if any(kw in lower for kw in keywords):
                items.append(_make_item(seg, category, mapped_to, confidence))
                matched = True
                break
        if not matched:
            items.append(_make_item(seg, "concerns", None, "low"))
    return items


# ──────────────────────────────────────────────────────────────
# 3. AI classifier
# ──────────────────────────────────────────────────────────────

def classify_items_ai(
    segments: List[str],
    project_id: str,
    ai_backend: str,
) -> List[Dict[str, Any]]:
    """Use LLM to classify feedback segments into structured FeedbackItems.

    Falls back to heuristic on any error.
    """
    if not segments:
        return []

    try:
        from ai_backends import call_llm
        import json as _json

        numbered = "\n".join(f"{i+1}. {s}" for i, s in enumerate(segments))
        prompt = f"""You are classifying client feedback items for a delivery proposal.

For each numbered item below, return a JSON object on its own line with:
  "idx": item number (int)
  "category": one of: accepted | rejected | change_requested | concerns
  "mapped_to": one of: risk | gap | scope_change | constraint | assumption | null
  "confidence": one of: high | medium | low
  "is_critical": true if change_requested+scope_change/risk OR rejected+scope_change/constraint

Return ONLY valid JSON lines, one per item. No other text.

Items:
{numbered}"""

        raw = call_llm(ai_backend, prompt, max_tokens=800)
        lines = [l.strip() for l in raw.strip().splitlines() if l.strip().startswith("{")]

        classified: Dict[int, Dict] = {}
        for line in lines:
            try:
                obj = _json.loads(line)
                classified[int(obj.get("idx", 0))] = obj
            except Exception:
                pass

        result = []
        for i, seg in enumerate(segments):
            obj = classified.get(i + 1, {})
            result.append(_make_item(
                seg,
                category=obj.get("category", "concerns"),
                mapped_to=obj.get("mapped_to") or None,
                confidence=obj.get("confidence", "medium"),
                is_critical=bool(obj.get("is_critical", False)),
            ))
        return result

    except Exception:
        return classify_items_heuristic(segments)


# ──────────────────────────────────────────────────────────────
# 4. Public entry point
# ──────────────────────────────────────────────────────────────

def classify_feedback(
    raw_text: str,
    project_id: str = "",
    ai_backend: str = "files_only",
) -> Dict[str, Any]:
    """Split raw feedback text into paragraphs and classify each.

    Args:
        raw_text:   Pasted email / transcript / meeting notes
        project_id: Used only in AI mode (for context)
        ai_backend: 'files_only' → heuristic pre-fill; else → LLM classification

    Returns:
        {
            segments:   [str],         # paragraph-level splits
            items:      [FeedbackItem dict],
            source:     "ai" | "heuristic",
            ai_backend: str,
        }
    """
    segments = split_into_paragraphs(raw_text)

    if ai_backend != "files_only" and project_id:
        items = classify_items_ai(segments, project_id, ai_backend)
        source = "ai"
    else:
        items = classify_items_heuristic(segments)
        source = "heuristic"

    return {
        "segments":   segments,
        "items":      items,
        "source":     source,
        "ai_backend": ai_backend,
    }
