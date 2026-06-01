"""Reconciliation Service — Sprint 3.

Public surface:
  save_reconciliation_selection(project_id, version_id, anchor_review_id,
                                selected_review_ids, selected_by) → dict
  get_reconciliation_selection(project_id, version_id) → dict | None
  run_reconciliation(project_id, version_id, anchor_review_id,
                     selected_review_ids) → ReconciliationOutput
  get_reconciliation(project_id, version_id) → ReconciliationOutput | None

Design rules:
- Explicit selection only — no auto-selection of latest-N reviews.
- anchor_review_id is always required and always recorded.
- selected_review_ids must include anchor_review_id.
- Reconciliation is deterministic: structural + text-similarity, no LLM.
- Provenance (source review + artifact refs) is carried on every item.
- Missing fields on old reviews degrade safely (empty lists / strings).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from models.reconciliation import (
    RECONCILABLE_CATEGORIES,
    NormalisedReviewInput,
    ProvenanceRef,
    ReconciledItem,
    ReconciliationOutput,
    ReconciliationSelection,
    _now_iso,
)
from models.hierarchy import _make_hierarchy_store

logger = logging.getLogger(__name__)

# ── Similarity threshold ──────────────────────────────────────────────────────
# Two text items are treated as "the same" when their normalised overlap ratio
# meets or exceeds this value.  Kept conservative (0.70) to avoid false merges.
_SIMILARITY_THRESHOLD = 0.70


# ──────────────────────────────────────────────────────────────────────────────
# Selection persistence  (thin wrapper around the store layer added in task 6)
# ──────────────────────────────────────────────────────────────────────────────

def save_reconciliation_selection(
    project_id: str,
    version_id: str,
    anchor_review_id: str,
    selected_review_ids: List[str],
    selected_by: str = "",
) -> Dict[str, Any]:
    """Persist the user's explicit review selection.

    Validates:
    - anchor_review_id must not be empty.
    - selected_review_ids must include anchor_review_id.
    - All IDs must exist as reviews on this project.

    Returns the saved selection dict or an error dict.
    """
    if not anchor_review_id:
        return {"error": "anchor_review_id is required"}
    if not selected_review_ids:
        return {"error": "selected_review_ids must contain at least the anchor review"}

    # Ensure anchor is in the selected list
    ids = list(dict.fromkeys(selected_review_ids))  # deduplicate, preserve order
    if anchor_review_id not in ids:
        ids = [anchor_review_id] + ids

    store = _make_hierarchy_store(project_id)

    # Validate all reviews exist
    for rid in ids:
        if store.get_review(rid) is None:
            return {"error": f"Review not found: {rid}"}

    selection = ReconciliationSelection(
        version_id=version_id,
        project_id=project_id,
        anchor_review_id=anchor_review_id,
        selected_review_ids=ids,
        selected_at=_now_iso(),
        selected_by=selected_by,
    )

    # Persist via store (added in task 6)
    store.save_reconciliation_selection(selection)

    return selection.to_dict()


def get_reconciliation_selection(
    project_id: str, version_id: str
) -> Optional[Dict[str, Any]]:
    """Return the stored selection for a version, or None."""
    store = _make_hierarchy_store(project_id)
    sel = store.get_reconciliation_selection(version_id)
    return sel.to_dict() if sel else None


# ──────────────────────────────────────────────────────────────────────────────
# Core reconciliation engine
# ──────────────────────────────────────────────────────────────────────────────

def run_reconciliation(
    project_id: str,
    version_id: str,
    anchor_review_id: str,
    selected_review_ids: List[str],
) -> ReconciliationOutput:
    """Run reconciliation across selected reviews and return the output.

    Steps:
    1. Validate inputs.
    2. Load and normalise each review.
    3. Build consensus, divergent, decisions, weaknesses, merged findings.
    4. Attach provenance to every output item.
    5. Persist the output.
    6. Return ReconciliationOutput.

    Raises ValueError on invalid inputs.
    """
    if not anchor_review_id:
        raise ValueError("anchor_review_id is required")
    if not selected_review_ids:
        raise ValueError("selected_review_ids must not be empty")

    ids = list(dict.fromkeys(selected_review_ids))
    if anchor_review_id not in ids:
        ids = [anchor_review_id] + ids

    store = _make_hierarchy_store(project_id)

    # ── 1. Load reviews ───────────────────────────────────────────────────────
    normalised: List[NormalisedReviewInput] = []
    for rid in ids:
        review = store.get_review(rid)
        if review is None:
            raise ValueError(f"Review not found: {rid}")
        normalised.append(NormalisedReviewInput(
            review_id=rid,
            version_id=review.version_id,
            persona=review.persona,
            is_anchor=(rid == anchor_review_id),
            findings=review.findings or {},
            weaknesses=list(review.weaknesses or []),
            decision_points=list(review.decision_points or []),
            artifact_refs=list(review.artifact_refs or []),
            previous_review_id=review.previous_review_id or "",
            created_at=review.created_at or "",
        ))

    anchor_input = next(n for n in normalised if n.is_anchor)
    supplemental = [n for n in normalised if not n.is_anchor]
    anchor_only = len(supplemental) == 0

    # ── 2. Reconcile findings (risks / assumptions / dependencies / etc.) ────
    consensus_points  = _reconcile_findings_consensus(anchor_input, supplemental)
    divergent_points  = _reconcile_findings_divergent(anchor_input, supplemental)
    merged_findings   = _merge_all_findings(normalised)

    # ── 3. Reconcile decisions ────────────────────────────────────────────────
    confirmed_decisions, open_decisions = _reconcile_decisions(normalised)

    # ── 4. Reconcile weaknesses ───────────────────────────────────────────────
    unresolved_weaknesses = _reconcile_weaknesses(normalised)

    # ── 5. Build provenance summary ───────────────────────────────────────────
    provenance_summary = _build_provenance_summary(normalised)

    # ── 6. Assemble output ────────────────────────────────────────────────────
    output = ReconciliationOutput(
        reconciliation_id=f"rec_{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        version_id=version_id,
        anchor_review_id=anchor_review_id,
        selected_review_ids=ids,
        created_at=_now_iso(),
        consensus_points=consensus_points,
        divergent_points=divergent_points,
        confirmed_decisions=confirmed_decisions,
        open_decisions=open_decisions,
        unresolved_weaknesses=unresolved_weaknesses,
        merged_findings=merged_findings,
        provenance_summary=provenance_summary,
        anchor_only=anchor_only,
        total_consensus=len(consensus_points),
        total_divergent=len(divergent_points),
        total_open_decisions=len(open_decisions),
        total_unresolved_weaknesses=len(unresolved_weaknesses),
    )

    # ── 7. Persist ────────────────────────────────────────────────────────────
    store.save_reconciliation_output(output)

    return output


def get_reconciliation(
    project_id: str, version_id: str
) -> Optional[ReconciliationOutput]:
    """Return the stored ReconciliationOutput for a version, or None."""
    store = _make_hierarchy_store(project_id)
    return store.get_reconciliation_output(version_id)


# ──────────────────────────────────────────────────────────────────────────────
# Internal: text normalisation + similarity
# ──────────────────────────────────────────────────────────────────────────────

def _normalise_text(text: Any) -> str:
    """Extract a clean, lowercased string from a finding item."""
    if text is None:
        return ""
    if isinstance(text, dict):
        raw = text.get("description") or text.get("text") or ""
    else:
        raw = str(text)
    return raw.strip().lower()


def _canonical_text(text: Any) -> str:
    """Return display-ready (original case) string from a finding item."""
    if text is None:
        return ""
    if isinstance(text, dict):
        return str(text.get("description") or text.get("text") or "").strip()
    return str(text).strip()


def _token_overlap(a: str, b: str) -> float:
    """Jaccard-like token overlap ratio between two normalised strings.

    Returns a float in [0, 1].  Empty strings return 0.0.
    """
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _is_similar(a: str, b: str, threshold: float = _SIMILARITY_THRESHOLD) -> bool:
    return _token_overlap(a, b) >= threshold


# ──────────────────────────────────────────────────────────────────────────────
# Internal: findings reconciliation
# ──────────────────────────────────────────────────────────────────────────────

def _iter_findings(review: NormalisedReviewInput):
    """Yield (category, canonical_text, normalised_text) for every finding."""
    for cat, items in (review.findings or {}).items():
        if not isinstance(items, list):
            continue
        for item in items:
            canon = _canonical_text(item)
            norm  = _normalise_text(item)
            if norm:
                yield cat, canon, norm


def _make_provenance(review: NormalisedReviewInput) -> Dict[str, Any]:
    """Build a lightweight provenance dict for a review."""
    return ProvenanceRef(
        review_id=review.review_id,
        review_persona=review.persona,
        is_anchor=review.is_anchor,
    ).to_dict()


def _make_provenance_with_artifact(
    review: NormalisedReviewInput, artifact: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    ref = ProvenanceRef(
        review_id=review.review_id,
        review_persona=review.persona,
        is_anchor=review.is_anchor,
        artifact_id=artifact.get("artifact_id", "") if artifact else "",
        artifact_name=artifact.get("artifact_name", "") if artifact else "",
        section_reference=artifact.get("section_reference", "") if artifact else "",
    )
    return ref.to_dict()


def _reconcile_findings_consensus(
    anchor: NormalisedReviewInput,
    supplemental: List[NormalisedReviewInput],
) -> List[Dict[str, Any]]:
    """Return items that appear in the anchor AND all supplemental reviews.

    If there are no supplemental reviews, all anchor findings are consensus
    (anchor-only mode).

    Each returned item is a ReconciledItem dict.
    """
    if not supplemental:
        # Anchor-only: every anchor finding is a "consensus" point
        results: List[Dict[str, Any]] = []
        for i, (cat, canon, norm) in enumerate(_iter_findings(anchor), start=1):
            item = ReconciledItem(
                id=f"cons_{i}",
                text=canon,
                category=cat,
                status="",
                source_reviews=[_make_provenance(anchor)],
                anchor_text=canon,
                supplemental_texts=[],
            )
            results.append(item.to_dict())
        return results

    # Multi-review mode: find anchor items matched by ALL supplemental reviews
    results = []
    item_counter = 0
    for cat, canon, norm in _iter_findings(anchor):
        matched_by_all = True
        supplemental_texts: List[str] = []
        source_provs = [_make_provenance(anchor)]

        for supp in supplemental:
            matched = False
            for s_cat, s_canon, s_norm in _iter_findings(supp):
                if s_cat == cat and _is_similar(norm, s_norm):
                    matched = True
                    supplemental_texts.append(s_canon)
                    source_provs.append(_make_provenance(supp))
                    break
            if not matched:
                matched_by_all = False
                break

        if matched_by_all:
            item_counter += 1
            item = ReconciledItem(
                id=f"cons_{item_counter}",
                text=canon,
                category=cat,
                status="",
                source_reviews=source_provs,
                anchor_text=canon,
                supplemental_texts=supplemental_texts,
            )
            results.append(item.to_dict())

    return results


def _reconcile_findings_divergent(
    anchor: NormalisedReviewInput,
    supplemental: List[NormalisedReviewInput],
) -> List[Dict[str, Any]]:
    """Return items where reviews differ.

    Divergence = anchor item NOT matched in at least one supplemental, OR
                 supplemental item NOT in anchor.

    Returns items with nuance: which review raised it and who did not.
    Does NOT return anything when there are no supplemental reviews.
    """
    if not supplemental:
        return []

    results: List[Dict[str, Any]] = []
    item_counter = 0

    # Items in anchor not matched by all supplementals
    for cat, canon, norm in _iter_findings(anchor):
        missing_from: List[str] = []
        present_in: List[str] = [anchor.review_id]

        for supp in supplemental:
            matched = any(
                s_cat == cat and _is_similar(norm, s_norm)
                for s_cat, _, s_norm in _iter_findings(supp)
            )
            if matched:
                present_in.append(supp.review_id)
            else:
                missing_from.append(supp.review_id)

        if missing_from:
            item_counter += 1
            source_provs = [_make_provenance(r) for r in [anchor] + supplemental
                            if r.review_id in present_in]
            item = ReconciledItem(
                id=f"div_{item_counter}",
                text=canon,
                category=cat,
                status="",
                source_reviews=source_provs,
                anchor_text=canon,
                supplemental_texts=[],
            )
            d = item.to_dict()
            d["present_in_reviews"]  = present_in
            d["absent_from_reviews"] = missing_from
            results.append(d)

    # Items in supplementals NOT in anchor — unique supplemental findings
    anchor_norms = {(cat, norm) for cat, _, norm in _iter_findings(anchor)}
    seen: set = set()
    for supp in supplemental:
        for cat, canon, norm in _iter_findings(supp):
            key = (cat, norm)
            if key not in anchor_norms and key not in seen:
                seen.add(key)
                item_counter += 1
                item = ReconciledItem(
                    id=f"div_{item_counter}",
                    text=canon,
                    category=cat,
                    status="",
                    source_reviews=[_make_provenance(supp)],
                    anchor_text="",
                    supplemental_texts=[canon],
                )
                d = item.to_dict()
                d["present_in_reviews"]  = [supp.review_id]
                d["absent_from_reviews"] = [anchor.review_id]
                results.append(d)

    return results


def _merge_all_findings(
    normalised: List[NormalisedReviewInput],
) -> List[Dict[str, Any]]:
    """Produce a de-duplicated flat list of all findings across selected reviews.

    Uses the anchor's text as canonical when duplicates exist.
    Each item carries source_reviews provenance.
    """
    # Collect all items keyed by (category, normalised_text)
    # First pass: record all with their provenance
    seen: Dict[tuple, Dict[str, Any]] = {}  # (cat, norm) → ReconciledItem dict
    item_counter = 0

    # Process anchor first so its text is canonical
    for review in normalised:
        for cat, canon, norm in _iter_findings(review):
            key = (cat, norm)
            if key not in seen:
                # New item
                item_counter += 1
                item = ReconciledItem(
                    id=f"mf_{item_counter}",
                    text=canon,
                    category=cat,
                    source_reviews=[_make_provenance(review)],
                    anchor_text=canon if review.is_anchor else "",
                    supplemental_texts=[] if review.is_anchor else [canon],
                )
                seen[key] = item.to_dict()
            else:
                # Already seen — merge provenance
                existing = seen[key]
                prov = _make_provenance(review)
                # Avoid duplicate provenance entries for same review
                if not any(p.get("review_id") == review.review_id
                           for p in existing["source_reviews"]):
                    existing["source_reviews"].append(prov)
                if not review.is_anchor and canon not in existing["supplemental_texts"]:
                    existing["supplemental_texts"].append(canon)

    return list(seen.values())


# ──────────────────────────────────────────────────────────────────────────────
# Internal: decision points reconciliation
# ──────────────────────────────────────────────────────────────────────────────

def _reconcile_decisions(
    normalised: List[NormalisedReviewInput],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split decision_points into confirmed and open.

    A decision is "confirmed" when its status != 'open' in the anchor review.
    A decision is "open" when its status == 'open' in any selected review.

    Returns (confirmed_decisions, open_decisions) — each a list of ReconciledItem dicts.
    """
    # Collect all decision texts across all reviews
    # Keyed by normalised text → dict with status + source_reviews
    collected: Dict[str, Dict[str, Any]] = {}
    dp_counter = 0

    for review in normalised:
        for dp in (review.decision_points or []):
            if not isinstance(dp, dict):
                continue
            text  = _canonical_text(dp)
            norm  = _normalise_text(dp)
            if not norm:
                continue
            status = dp.get("status", "open")

            # Find existing or create
            matched_key = next(
                (k for k in collected if _is_similar(norm, k)), None
            )
            if matched_key is None:
                dp_counter += 1
                prov = _make_provenance(review)
                collected[norm] = {
                    "id": f"dp_{dp_counter}",
                    "text": text,
                    "category": dp.get("category", ""),
                    "status": status,
                    "source_reviews": [prov],
                    "anchor_text": text if review.is_anchor else "",
                    "supplemental_texts": [] if review.is_anchor else [text],
                }
            else:
                existing = collected[matched_key]
                prov = _make_provenance(review)
                if not any(p.get("review_id") == review.review_id
                           for p in existing["source_reviews"]):
                    existing["source_reviews"].append(prov)
                # Prefer anchor's status
                if review.is_anchor:
                    existing["status"] = status
                    existing["anchor_text"] = text
                else:
                    if text not in existing["supplemental_texts"]:
                        existing["supplemental_texts"].append(text)
                    # If anchor has no status yet, escalate to open if any says open
                    if existing.get("status") != "open" and status == "open":
                        existing["status"] = status

    confirmed: List[Dict[str, Any]] = []
    open_: List[Dict[str, Any]] = []

    for item in collected.values():
        rc_item = {
            "id": item["id"],
            "text": item["text"],
            "category": item["category"],
            "status": item["status"],
            "source_reviews": item["source_reviews"],
            "anchor_text": item["anchor_text"],
            "supplemental_texts": item["supplemental_texts"],
        }
        if item.get("status", "open") == "open":
            open_.append(rc_item)
        else:
            confirmed.append(rc_item)

    return confirmed, open_


# ──────────────────────────────────────────────────────────────────────────────
# Internal: weakness reconciliation
# ──────────────────────────────────────────────────────────────────────────────

def _reconcile_weaknesses(
    normalised: List[NormalisedReviewInput],
) -> List[Dict[str, Any]]:
    """Return weaknesses that remain 'open' in at least one selected review.

    De-duplicates by text similarity.  Provenance records which review(s)
    still have it open.  User notes are preserved from whichever review has one.
    """
    collected: Dict[str, Dict[str, Any]] = {}
    w_counter = 0

    for review in normalised:
        for w in (review.weaknesses or []):
            if not isinstance(w, dict):
                continue
            text   = _canonical_text(w)
            norm   = _normalise_text(w)
            status = w.get("status", "open")
            if not norm:
                continue

            matched_key = next(
                (k for k in collected if _is_similar(norm, k)), None
            )
            if matched_key is None:
                w_counter += 1
                prov = _make_provenance(review)
                collected[norm] = {
                    "id": f"uw_{w_counter}",
                    "text": text,
                    "category": w.get("category", ""),
                    "status": status,
                    "user_note": w.get("user_note", ""),
                    "source_reviews": [prov],
                    "anchor_text": text if review.is_anchor else "",
                    "supplemental_texts": [] if review.is_anchor else [text],
                }
            else:
                existing = collected[matched_key]
                prov = _make_provenance(review)
                if not any(p.get("review_id") == review.review_id
                           for p in existing["source_reviews"]):
                    existing["source_reviews"].append(prov)
                # Preserve anchor status
                if review.is_anchor:
                    existing["status"] = status
                    existing["anchor_text"] = text
                # Carry forward any user note (non-empty wins)
                if not existing.get("user_note") and w.get("user_note"):
                    existing["user_note"] = w.get("user_note", "")

    # Return only open weaknesses
    return [
        {
            "id": v["id"],
            "text": v["text"],
            "category": v["category"],
            "status": v["status"],
            "user_note": v.get("user_note", ""),
            "source_reviews": v["source_reviews"],
            "anchor_text": v["anchor_text"],
            "supplemental_texts": v["supplemental_texts"],
        }
        for v in collected.values()
        if v.get("status", "open") == "open"
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Internal: provenance summary
# ──────────────────────────────────────────────────────────────────────────────

def _build_provenance_summary(
    normalised: List[NormalisedReviewInput],
) -> List[Dict[str, Any]]:
    """Build a per-review summary for the provenance_summary field."""
    summary = []
    for review in normalised:
        total_items = sum(
            len(v) for v in (review.findings or {}).values() if isinstance(v, list)
        )
        total_items += len(review.decision_points or [])
        total_items += len(review.weaknesses or [])
        summary.append({
            "review_id":     review.review_id,
            "persona":       review.persona,
            "is_anchor":     review.is_anchor,
            "created_at":    review.created_at,
            "item_count":    total_items,
            "artifact_refs": [
                {
                    "artifact_id":   ref.get("artifact_id", ""),
                    "artifact_name": ref.get("artifact_name", ""),
                    "artifact_type": ref.get("artifact_type", ""),
                    "section_reference": ref.get("section_reference", ""),
                }
                for ref in (review.artifact_refs or [])
            ],
        })
    return summary
