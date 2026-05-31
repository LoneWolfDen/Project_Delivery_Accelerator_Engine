# Multi-Review Synthesis for Proposal Creation
# Spec: PDAE-MS-01
# Status: Ready for implementation
# Last updated: 2026-05-31


---

## 1. Product Intent

This feature evolves proposal creation from a single-review output into a
multi-review, decision-assistant capability.

The system should help users understand:
- what is missing from the proposal
- what is weak or underspecified
- what is unresolved and needs a decision
- what should be actioned next to reach SoW sign-off confidence

Proposal generation must be a **reconciled synthesis** of multiple selected
review perspectives — not a raw roll-up of one review's findings.

The output is a **Proposal Data Pack**: a format-agnostic, proposal-ready
intelligence pack that users can adapt into client templates.

---

## 2. Hard Constraints

| Constraint | Rule |
|---|---|
| Architecture | No new intermediate domain layer |
| Version compare | Untouched — `compare_proposal_versions` not modified |
| Draft / Final | Review maturity only — never used as proposal inclusion logic |
| Auto-use of reviews | Prohibited — user must explicitly select supplemental reviews |
| Active Review | Mandatory anchor — existing gate check unchanged |
| Single-review path | Must produce identical output to today when no supplementals selected |
| Deployment | Single-container Docker, offline-first, open-source backends only |



---

## 3. Processing Pipeline (multi-review path only)

```
User selects:  Version → Active Review (anchor) → [optional supplemental reviews]

Step 1   SNAPSHOT          Capture ProposalInputSnapshot before any processing
Step 2   VALIDATE          All reviews belong to same version_id; anchor is active_review
Step 3   NORMALISE         Flatten each review's findings to typed, provenance-tagged items
Step 4   DEDUPE            Deterministic: collapse near-identical text (pre-processing only)
                           Cache: normalise + dedupe results are cacheable per review set
Step 5   LLM RECONCILE     Resolve overlap, contradictions, nuance → ReconciliationResult
                           Never cached — always recomputed
Step 6   LLM GENERATE      Produce Proposal Data Pack using reconciled findings
                           Never cached — always recomputed
Step 7   LLM REVIEW PASS   Critique across 6 domains → ProposalReviewPass
Step 8   COVERAGE          Deterministic: map domains to version intelligence + scope themes
Step 9   LLM DECISION      Merge decision_points from selected reviews; LLM refines
                           confirmed / open / sign-off blockers → DecisionSummary
Step 10  FORWARD GUIDANCE  LLM generates Recommended Focus Areas & Proposed Actions
Step 11  PERSIST           All artifacts stored on ProposalDocument record
```

**LLM calls:** Steps 5, 6, 7, 9, 10 — each is a discrete call with its own prompt.
**files_only fallback:** Steps 5, 7, 9, 10 use deterministic fallback. Step 6 uses
existing template population. Blocker detection in files_only uses keyword matching
only: `must`, `required`, `block`, `cannot proceed`, `prevent`.



---

## 4. Proposal Data Pack — Output Sections

The generated output replaces the existing `ProposalDocument` sections
with a richer, format-agnostic pack. All sections are present whether
single-review or multi-review path is used; multi-review path populates
them with synthesised content.

| # | Section | Source |
|---|---|---|
| 1 | Executive Position | LLM / deterministic summary |
| 2 | Client Need / Problem Framing | Scope + action_items + assumptions |
| 3 | Recommended Solution Approach | Reconciled findings + dependencies |
| 4 | What This Proposal Covers | Scope themes + action_items |
| 5 | Key Assumptions | Merged assumptions from selected reviews |
| 6 | Confirmed Decisions | DecisionSummary.confirmed |
| 7 | Open Decisions / Clarifications Needed | DecisionSummary.open |
| 8 | Key Risks and Mitigations | Merged risks, categorised |
| 9 | Delivery Approach and Phasing | Delivery phases + Gantt |
| 10 | Operations / MSP Considerations | Ops-signal action items |
| 11 | Commercial Sensitivities | Commercial-signal risks + assumptions |
| 12 | Why This Proposal Is Credible | LLM credibility narrative |
| 13 | Next Best Actions | DecisionSummary.sign_off_blockers + forward guidance |
| 14 | Proposal Review Pass | ProposalReviewPass (6 domains) |
| 15 | Proposal Coverage | ProposalCoverage (6 domains) |
| 16 | Recommended Focus Areas & Proposed Actions | ForwardGuidance |

Lightweight origin references are permitted on any item, e.g.:
`Derived from: Architecture Review / Client Meeting / Review Weakness`
No formal traceability matrix in this phase.



---

## 5. New Dataclasses (all in `models/proposal.py`)

```python
@dataclass
class ProposalInputSnapshot:
    anchor_review_id: str
    selected_review_ids: List[str]   # includes anchor
    selected_version_id: str
    generation_mode: str             # "single" | "multi"
    captured_at: str

@dataclass
class NormalizedItem:
    text: str
    category: str        # risks|assumptions|dependencies|constraints|action_items
    review_id: str
    persona: str
    dedup_key: str       # lowercase, stripped, collapsed whitespace

@dataclass
class ConflictEntry:
    category: str
    description: str     # human-readable statement of the contradiction
    review_ids: List[str]

@dataclass
class ReconciliationResult:
    reconciled_findings: Dict[str, List[str]]  # category → merged list (LLM output)
    overlaps_resolved: List[str]
    contradictions: List[ConflictEntry]
    reconciliation_notes: str
    source_review_ids: List[str]
    anchor_review_id: str
    generated_by: str    # backend name or "deterministic"
    generated_at: str

@dataclass
class ReviewPassDomain:
    covered_well: List[str]
    still_weak: List[str]
    may_block_signoff: List[str]

@dataclass
class ProposalReviewPass:
    scope: ReviewPassDomain
    architecture: ReviewPassDomain
    delivery: ReviewPassDomain
    security_compliance: ReviewPassDomain
    operations: ReviewPassDomain
    commercials: ReviewPassDomain
    generated_by: str
    generated_at: str

@dataclass
class CoverageDomain:
    status: str              # "Addressed" | "Partial" | "Not Yet Addressed"
    matched_themes: List[str]
    gap_notes: str

@dataclass
class ProposalCoverage:
    scope: CoverageDomain
    architecture: CoverageDomain
    delivery: CoverageDomain
    security_compliance: CoverageDomain
    operations: CoverageDomain
    commercials: CoverageDomain
    source_theme_count: int
    computed_at: str

@dataclass
class DecisionItem:
    text: str
    category: str
    source_review_id: str

@dataclass
class DecisionSummary:
    confirmed: List[DecisionItem]
    open: List[DecisionItem]
    sign_off_blockers: List[DecisionItem]
    source_review_ids: List[str]
    generated_by: str
    generated_at: str

@dataclass
class ForwardGuidanceItem:
    issue: str
    why_it_matters: str
    suggested_action: str
    trade_off_or_constraint: str   # empty string if none

@dataclass
class ForwardGuidance:
    strengthen_weak_areas: List[ForwardGuidanceItem]
    resolve_key_decisions: List[ForwardGuidanceItem]
    improve_credibility: List[ForwardGuidanceItem]
    accelerate_client_alignment: List[ForwardGuidanceItem]
    optional_enhancements: List[ForwardGuidanceItem]
    generated_by: str
    generated_at: str
```



---

## 6. Additive Fields on `ProposalDocument`

Five new optional fields, all `None` by default. Existing documents unaffected.

```python
input_snapshot:        Optional[Dict] = None   # ProposalInputSnapshot.to_dict()
reconciliation_result: Optional[Dict] = None   # ReconciliationResult.to_dict()
review_pass:           Optional[Dict] = None   # ProposalReviewPass.to_dict()
proposal_coverage:     Optional[Dict] = None   # ProposalCoverage.to_dict()
decision_summary:      Optional[Dict] = None   # DecisionSummary.to_dict()
forward_guidance:      Optional[Dict] = None   # ForwardGuidance.to_dict()
```

---

## 7. DB Schema Additions (`proposal_documents` table)

Six additive nullable TEXT columns. No migration required on existing rows.

```sql
ALTER TABLE proposal_documents ADD COLUMN input_snapshot        TEXT;
ALTER TABLE proposal_documents ADD COLUMN reconciliation_result TEXT;
ALTER TABLE proposal_documents ADD COLUMN review_pass           TEXT;
ALTER TABLE proposal_documents ADD COLUMN proposal_coverage     TEXT;
ALTER TABLE proposal_documents ADD COLUMN decision_summary      TEXT;
ALTER TABLE proposal_documents ADD COLUMN forward_guidance      TEXT;
```

`db/decision_log.py` — `save_proposal_document()` and `_row_to_doc()` updated
to serialise and deserialise all six fields with `None` defaults.

---

## 8. New File

| File | Purpose |
|---|---|
| `processors/review_synthesizer.py` | All normalisation, dedup, reconciliation, coverage, decision merge, forward guidance logic |

No other files created. No files renamed or deleted.



---

## 9. Modified Existing Files (signatures only)

### `processors/proposal_generator.py`
```python
# Public API signature change — one new optional param, default None
def generate_proposal_document(
    project_id: str,
    proposal_ver_id: str,
    hierarchy_version_id: str,
    review_id: str,
    ai_backend: str = "files_only",
    force: bool = False,
    supplemental_review_ids: Optional[List[str]] = None,  # NEW
) -> Dict[str, Any]:
```

New private functions added to this file:
- `_run_proposal_review_pass(doc, conflicts, ai_backend) -> ProposalReviewPass`
- `_run_decision_summary(merged_decisions, reconciliation_notes, ai_backend) -> DecisionSummary`
- `_run_forward_guidance(review_pass, decision_summary, conflicts, version_scope, ai_backend) -> ForwardGuidance`

### `handlers/proposal.py`
```python
# handle_generate_proposal_doc — one new body field read
supplemental_review_ids = body.get("supplemental_review_ids") or []
```

### `services/proposal.py`
```python
# generate_proposal_doc — one new param passed through
def generate_proposal_doc(
    project_id, proposal_ver_id, hierarchy_version_id,
    review_id, ai_backend="files_only", force=False,
    supplemental_review_ids=None,   # NEW
) -> Dict[str, Any]:
```



---

## 10. LLM Prompt Contracts

### Step 5 — Reconciliation Prompt
```
You are a senior delivery consultant reconciling findings from {N} reviews of the
same intelligence version into a single coherent proposal-ready set.

Anchor review persona: {anchor.persona}
All source reviews: {review_id_list}

DEDUPLICATED FINDINGS (with review provenance):
[category-grouped items, each tagged with review_id and persona]

VERSION SCOPE (max 800 chars):
{version.scope[:800]}

Tasks:
1. For each category produce one merged list. Where items overlap in substance,
   keep the most specific and complete version. Do not invent new items.
2. Flag genuine contradictions as CONFLICT entries with a plain-English description.
3. Provide brief reconciliation notes explaining key merge decisions.

Output (use EXACTLY these headers, no markdown):
---RECONCILED_RISKS---
---RECONCILED_ASSUMPTIONS---
---RECONCILED_DEPENDENCIES---
---RECONCILED_CONSTRAINTS---
---RECONCILED_ACTION_ITEMS---
---CONFLICTS---
---RECONCILIATION_NOTES---
```

### Step 7 — Proposal Review Pass Prompt
```
You are a delivery assurance reviewer. Critique the proposal below across six
domains. For each domain identify what is covered well, what is still weak or
underspecified, and what may block sign-off.

Domains: Scope | Architecture | Delivery | Security/Compliance | Operations | Commercials

PROPOSAL CONTENT:
[exec_summary, scope, delivery_phases, risks, assumptions]

UNRESOLVED CONFLICTS FROM SYNTHESIS:
[ConflictEntry list — empty if none]

Output (use EXACTLY these headers per domain, replace DOMAIN):
---DOMAIN_COVERED_WELL---
---DOMAIN_STILL_WEAK---
---DOMAIN_BLOCKERS---
```

### Step 9 — Decision Summary Prompt
```
You are reviewing decision points extracted from {N} reviews.
Classify each as CONFIRMED, OPEN, or BLOCKER.

CONFIRMED: clearly resolved in the findings
OPEN: unresolved or deferred — needs a decision
BLOCKER: unresolved and directly risks sign-off or delivery

MERGED DECISION POINTS:
[text | category | source_review_id — one per line]

RECONCILIATION NOTES:
[from ReconciliationResult.reconciliation_notes]

Output (use EXACTLY these headers):
---CONFIRMED---
---OPEN---
---BLOCKERS---
```

### Step 10 — Forward Guidance Prompt
```
You are a senior delivery advisor. Based only on the data provided, identify
recommended focus areas to strengthen this proposal toward sign-off readiness.

Rules:
- Recommendations must be grounded in the data below
- Respect stated constraints: budget, timeline, client preferences, delivery model
- Do not invent new facts or unsupported scope
- Optional enhancements must be clearly viable given current context

Inputs:
UNRESOLVED WEAKNESSES: [still_weak items from ProposalReviewPass, all domains]
OPEN DECISIONS: [DecisionSummary.open]
CONFLICTS: [ReconciliationResult.contradictions]
COVERAGE GAPS: [domains where status != "Addressed" from ProposalCoverage]
VERSION SCOPE: {version.scope[:600]}

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
---OPTIONAL_ENHANCEMENTS---
```



---

## 11. Coverage Mapping Logic (deterministic — Step 8)

Source: `version.scope` + `reconciled_findings` + already-ingested structured context.
No new raw-artifact extraction step.

### Scope theme extraction (`extract_scope_themes`)
- Regex + keyword patterns on scope text and action_items
- Extracts named deliverables, systems, workstreams, platforms
- Returns `List[str]`; empty list on empty scope

### Domain signal mapping

| Domain | Signal sources |
|---|---|
| Scope | Themes matched in action_items + scope text |
| Architecture | Themes matched in dependencies + constraints (system/platform names) |
| Delivery | Themes matched in action_items + delivery_phases |
| Security/Compliance | Risk items containing: security, compliance, gdpr, auth, encryption, audit, access |
| Operations | Action items containing: monitor, sla, runbook, support, handover, alert, incident |
| Commercials | Risks or assumptions containing: budget, cost, commercial, pricing, contract, margin |

### Status rules
- **Addressed** — ≥2 matched items for domain AND no blocker in `review_pass` for this domain
- **Partial** — 1 matched item OR matched items exist but `still_weak` flags this domain
- **Not Yet Addressed** — 0 matched items



---

## 12. Caching Rules

| Step | Cacheable? | Rule |
|---|---|---|
| Normalisation | Yes | Cache per `review_id`; invalidate if review findings change |
| Deduplication | Yes | Cache per sorted `selected_review_ids` set |
| Conflict detection (deterministic pre-pass) | Yes | Same key as dedup |
| LLM Reconciliation (Step 5) | **Never** | Always recompute |
| LLM Proposal Generation (Step 6) | **Never** | Always recompute |
| LLM Review Pass (Step 7) | **Never** | Always recompute |
| Coverage (Step 8) | Derived | Recomputed from reconciliation output |
| LLM Decision Summary (Step 9) | **Never** | Always recompute |
| LLM Forward Guidance (Step 10) | **Never** | Always recompute |

Cache implementation: in-memory dict keyed by sorted tuple of review IDs.
Cleared on process restart. No persistent cache store required.



---

## 13. Sprint Backlog

---

### Sprint 1 — Synthesis Foundation
**Goal:** Build and validate the synthesis engine as a standalone, testable
module. No changes to proposal generation yet.

**Dependency:** None. Can start immediately.

**Architectural changes:**
- Create `processors/review_synthesizer.py`
- Add all new dataclasses to `models/proposal.py`
- No DB changes yet

---

#### Story S1-01: Normalise review findings

**As a** system component,
**I want to** flatten a single review's findings into typed, provenance-tagged items,
**so that** downstream processing has a consistent structure regardless of review source.

**Implementation notes:**
- Input: a `Review` dataclass instance
- Output: `List[NormalizedItem]`
- Five categories: `risks`, `assumptions`, `dependencies`, `constraints`, `action_items`
- Each item carries: `text`, `category`, `review_id`, `persona`, `dedup_key`
- `dedup_key` = lowercase text, strip punctuation, collapse whitespace
- Skip items where text is empty after normalisation

**Acceptance criteria:**
- AC1: Review with 3 risks, 2 assumptions → 5 NormalizedItems with correct categories
- AC2: Each item's `review_id` matches the source review
- AC3: `dedup_key` for "Risk: Database access  may fail." → "risk database access may fail"
- AC4: Empty findings dict → empty list returned, no error raised
- AC5: Non-string items in findings list are coerced to str, not dropped

---

#### Story S1-02: Deterministic deduplication

**As a** system component,
**I want to** collapse near-identical findings before LLM reasoning,
**so that** the LLM receives clean, non-repetitive input.

**Implementation notes:**
- Input: `List[NormalizedItem]` (may span multiple reviews)
- Output: `List[NormalizedItem]` (duplicates removed)
- Duplicate = `dedup_key` token overlap ≥ 75% (Jaccard similarity on word tokens)
- Keep item from review with highest `completeness_score`; tie-break on `created_at` (latest)
- Items from different categories are never deduplicated against each other
- Cache result in-memory keyed by `frozenset(review_ids)`

**Acceptance criteria:**
- AC1: Two items with identical text → one item retained from higher-quality review
- AC2: Two items with 80% token overlap → deduplicated
- AC3: Two items with 50% token overlap → both retained
- AC4: Same text in `risks` and `assumptions` → both retained (different categories)
- AC5: Three reviews, two with same risk text: retained item's `review_id` = higher-scoring review
- AC6: Cache hit on second call with same review set → normalisation not re-run



---

#### Story S1-03: Build and parse reconciliation prompt

**As a** system component,
**I want to** build a structured reconciliation prompt and reliably parse its response,
**so that** the LLM reconciliation step has consistent, predictable input/output contracts.

**Implementation notes:**
- `build_reconciliation_prompt(deduped, version_scope)` → `str`
- Scope truncated to 800 chars
- Each item in prompt includes: text, review_id, persona
- `parse_reconciliation_response(raw, source_ids, anchor_id, backend)` → `ReconciliationResult`
- Missing sections in LLM response → empty list for that category (not an error)
- `---CONFLICTS---` section: each line → one `ConflictEntry`; blank section → `contradictions = []`

**Acceptance criteria:**
- AC1: Prompt contains all five `---RECONCILED_*---` section headers
- AC2: Each item in prompt is tagged with its `review_id`
- AC3: Scope text > 800 chars is truncated to exactly 800 chars in prompt
- AC4: Response with two conflict lines → `ReconciliationResult.contradictions` has 2 items
- AC5: Response missing `---RECONCILED_DEPENDENCIES---` → `reconciled_findings["dependencies"] = []`
- AC6: Empty raw response → `ReconciliationResult` returned with all empty fields, no exception

---

#### Story S1-04: `synthesize_reviews()` orchestrator

**As a** system component,
**I want to** orchestrate the full normalise → dedupe → reconcile pipeline,
**so that** proposal generation has a single clean entry point for synthesis.

**Implementation notes:**
- Signature: `synthesize_reviews(anchor_review, supplemental_reviews, version_scope, ai_backend) -> ReconciliationResult`
- Validates all supplementals share same `version_id` as anchor; raises `ValueError` on mismatch
- Does NOT gate on `quality_status` of supplementals
- `files_only` backend → skips LLM call; returns `ReconciliationResult` with
  `generated_by="deterministic"`, `reconciliation_notes=""`, `contradictions=[]`,
  and merged findings = simple union of deduped items per category
- AI backend unavailable → falls back to deterministic result, logs warning

**Acceptance criteria:**
- AC1: Supplemental from different `version_id` → `ValueError` with descriptive message
- AC2: `files_only` backend → `ReconciliationResult.generated_by == "deterministic"`
- AC3: `files_only` backend → `reconciled_findings` contains union of deduped items per category
- AC4: AI backend → `ReconciliationResult.generated_by` == backend name
- AC5: Single supplemental review → reconciliation runs without error
- AC6: Zero supplementals (anchor only) → `ReconciliationResult` with anchor findings only
- AC7: `quality_status="pending"` on supplemental → accepted without error (no gate)



---

#### Story S1-05: Scope theme extraction

**As a** system component,
**I want to** extract named deliverables, systems, and workstreams from version scope text,
**so that** proposal coverage can be mapped to concrete client asks.

**Implementation notes:**
- `extract_scope_themes(version_scope, findings) -> List[str]`
- Deterministic: regex + keyword patterns
- Sources: `version.scope` + `reconciled_findings["action_items"]`
- Patterns: capitalised noun phrases ≥ 2 words, known platform names, quoted strings
- Deduplicates themes; returns lowercase normalised list
- Empty scope and empty findings → returns `[]`

**Acceptance criteria:**
- AC1: Scope mentioning "Azure Data Factory" and "legacy ERP migration" → both in output
- AC2: Empty scope + empty findings → `[]` returned, no error
- AC3: Same theme appearing twice in scope → appears once in output
- AC4: Themes from action_items included when not present in scope text

---

#### Story S1-06: Merge decision points

**As a** system component,
**I want to** collect and deduplicate decision points across selected reviews,
**so that** the decision summary LLM call receives clean, non-redundant input.

**Implementation notes:**
- `merge_decision_points(selected_reviews) -> List[Dict]`
- Reads `review.decision_points` from each selected review (may be empty list)
- Deduplicates using same 75% token overlap threshold as S1-02
- Each merged item retains: `text`, `category`, `status`, `source_review_id`
- `status` from anchor review takes precedence over supplementals on duplicate

**Acceptance criteria:**
- AC1: Two reviews with same open decision text → one item in output
- AC2: Two reviews with different open decisions → both retained
- AC3: `source_review_id` on merged item = anchor's review_id when anchor had the item
- AC4: Review with no `decision_points` field → treated as empty list, no error
- AC5: Mixed `open` and `addressed` statuses on duplicate → anchor status wins

---

### Sprint 1 — Done Definition
- All six stories pass their acceptance criteria
- `processors/review_synthesizer.py` exists and is importable
- All new dataclasses present in `models/proposal.py` with `to_dict()` / `from_dict()`
- No changes to `proposal_generator.py`, `handlers/`, `services/`, DB, or frontend
- Single-review proposal generation continues to work identically



---

### Sprint 2 — Proposal Review Pass
**Goal:** Integrate synthesis into the proposal generator, add the review pass,
and persist all new artifacts. Proposal Data Pack sections 1–13 are now populated.

**Dependency:** Sprint 1 complete.

**Architectural changes:**
- Extend `generate_proposal_document()` with `supplemental_review_ids` param
- Add `_run_proposal_review_pass()` to `proposal_generator.py`
- Add DB columns and update serialisation in `db/decision_log.py`
- Update `handlers/proposal.py` and `services/proposal.py` (signature pass-through only)

---

#### Story S2-01: `ProposalInputSnapshot` capture

**As a** system,
**I want to** record exactly which reviews and version were used before any processing begins,
**so that** every proposal document is fully auditable.

**Implementation notes:**
- Built as first step inside `generate_proposal_document()` when called
- Always built (single-review and multi-review paths)
- `generation_mode = "multi"` when `supplemental_review_ids` is non-empty, else `"single"`
- Stored on `ProposalDocument.input_snapshot`

**Acceptance criteria:**
- AC1: Single-review call → `input_snapshot.generation_mode == "single"`, `selected_review_ids` has 1 entry
- AC2: Multi-review call → `selected_review_ids` includes anchor + all supplementals
- AC3: `captured_at` is an ISO 8601 UTC timestamp
- AC4: `selected_version_id` matches the `hierarchy_version_id` passed in
- AC5: Snapshot is persisted in `proposal_documents.input_snapshot` column

---

#### Story S2-02: Wire synthesis into generate path

**As a** system,
**I want to** pass reconciled findings into proposal generation when supplementals are selected,
**so that** the generated document reflects a multi-review synthesis rather than one review.

**Implementation notes:**
- When `supplemental_review_ids` is non-empty:
  - Call `synthesize_reviews()` → `ReconciliationResult`
  - Pass `reconciliation.reconciled_findings` as `findings` input instead of `review.findings`
  - Store `ReconciliationResult.to_dict()` on `ProposalDocument.reconciliation_result`
- When `supplemental_review_ids` is empty or None:
  - Skip synthesis entirely — existing path runs unchanged
  - `reconciliation_result` remains `None`
- `generate_proposal_document()` signature adds `supplemental_review_ids: Optional[List[str]] = None`

**Acceptance criteria:**
- AC1: Single-review call → `reconciliation_result is None`; output matches current behaviour exactly
- AC2: Multi-review call → `reconciliation_result` populated with `source_review_ids`
- AC3: Multi-review + `files_only` → `reconciliation_result.generated_by == "deterministic"`
- AC4: Invalid supplemental `version_id` → function returns `{"error": "..."}`, no document saved
- AC5: All existing call sites with no `supplemental_review_ids` arg → unaffected (default None)



---

#### Story S2-03: Proposal Review Pass — six-domain critique

**As a** user,
**I want to** see a structured critique of the proposal across six domains,
**so that** I know exactly what is strong, what is weak, and what may block sign-off.

**Implementation notes:**
- `_run_proposal_review_pass(doc, conflicts, ai_backend) -> ProposalReviewPass`
- Private function in `proposal_generator.py`
- Domains: Scope, Architecture, Delivery, Security/Compliance, Operations, Commercials
- AI backend: single LLM call using Review Pass Prompt (Section 10 of spec)
- `files_only`: deterministic fallback — scan findings for weakness signals per domain;
  apply keyword-based blocker detection (`must`, `required`, `block`, `cannot proceed`, `prevent`);
  `covered_well` = categories with ≥2 items; `still_weak` = categories with 0–1 items
- Stored on `ProposalDocument.review_pass`
- Only runs after document sections are generated

**Acceptance criteria:**
- AC1: AI backend → all six domains populated with at least an empty list per sub-section
- AC2: `files_only` → `review_pass` populated (not `None`); blocker keywords trigger `may_block_signoff` items
- AC3: A conflict in `ReconciliationResult` appears in at least one domain's `may_block_signoff`
- AC4: Single-review path → review pass still runs (not conditional on multi-review)
- AC5: `generated_by` field = backend name used
- AC6: `generated_at` is an ISO 8601 UTC timestamp

---

#### Story S2-04: DB schema additions and serialisation

**As a** system,
**I want to** persist all new proposal artifacts to the database,
**so that** documents can be retrieved with full synthesis context intact.

**Implementation notes:**
- Add six nullable TEXT columns to `proposal_documents` table (see Section 7)
- Run as one-time idempotent migration on app startup (use `ADD COLUMN IF NOT EXISTS` pattern)
- Update `save_proposal_document()` to serialise all six new fields
- Update `_row_to_doc()` to deserialise all six fields with `None` defaults
- No change to any other DB table

**Acceptance criteria:**
- AC1: Existing rows read back without error — all new fields return `None`
- AC2: New multi-review document written with all six fields populated → read back intact
- AC3: `_row_to_doc()` on a row missing new columns → returns `None` for those fields, no exception
- AC4: Migration runs on a fresh DB with no existing tables → no error
- AC5: Migration runs on a DB with all columns already present → no error (idempotent)

---

#### Story S2-05: Handler and service pass-through

**As a** developer,
**I want to** pass `supplemental_review_ids` from the API request body through to the processor,
**so that** the frontend can drive multi-review generation.

**Implementation notes:**
- `handlers/proposal.py`: read `body.get("supplemental_review_ids") or []`; pass to service
- `services/proposal.py`: add `supplemental_review_ids=None` param; pass to processor
- Validation: if provided and not a list → return `{"error": "supplemental_review_ids must be a list"}`

**Acceptance criteria:**
- AC1: POST body with `supplemental_review_ids: ["r2", "r3"]` → processor receives `["r2", "r3"]`
- AC2: POST body with no `supplemental_review_ids` key → processor receives `None`
- AC3: POST body with `supplemental_review_ids: "r2"` (string not list) → `422` error returned
- AC4: Handler remains thin — no synthesis logic in handler or service

---

### Sprint 2 — Done Definition
- Multi-review call via API produces a `ProposalDocument` with `input_snapshot`, `reconciliation_result`, and `review_pass` populated
- Single-review call produces identical output to pre-sprint (regression safe)
- All six DB columns present and round-tripping correctly
- `review_pass` populated on both single and multi-review paths



---

### Sprint 3 — Proposal Coverage
**Goal:** Produce the six-domain coverage map and wire the Decision Summary.
Proposal Data Pack sections 6, 7, 15 are now fully populated.

**Dependency:** Sprint 2 complete (`ReconciliationResult` and `ProposalReviewPass` available).

**Architectural changes:**
- Add `compute_proposal_coverage()` and `_run_decision_summary()` to
  `processors/review_synthesizer.py` and `processors/proposal_generator.py` respectively

---

#### Story S3-01: Compute proposal coverage

**As a** user,
**I want to** see which proposal domains are addressed, partially covered, or missing,
**so that** I can identify gaps before submitting.

**Implementation notes:**
- `compute_proposal_coverage(reconciliation, review_pass, scope_themes) -> ProposalCoverage`
- Deterministic — no LLM call
- Domain signal mapping per Section 11 of this spec
- Status rules: Addressed / Partial / Not Yet Addressed per Section 11
- `source_theme_count` = `len(scope_themes)`
- Stored on `ProposalDocument.proposal_coverage`

**Acceptance criteria:**
- AC1: Zero security-signal risks → `security_compliance.status == "Not Yet Addressed"`
- AC2: Three security risks, no blocker in review_pass for that domain → `"Addressed"`
- AC3: One security risk, domain flagged in `still_weak` → `"Partial"`
- AC4: `matched_themes` lists the themes that triggered the domain match
- AC5: `gap_notes` is a non-empty string when status is `"Partial"` or `"Not Yet Addressed"`
- AC6: Same inputs always produce same output (deterministic)
- AC7: `computed_at` is an ISO 8601 UTC timestamp

---

#### Story S3-02: Decision Summary

**As a** user,
**I want to** see confirmed decisions, open decisions, and sign-off blockers in one place,
**so that** I know exactly what needs to be resolved before the proposal can progress.

**Implementation notes:**
- `_run_decision_summary(merged_decisions, reconciliation_notes, ai_backend) -> DecisionSummary`
- AI backend: single LLM call using Decision Summary Prompt (Section 10)
- `files_only` fallback:
  - `decision_points` with `status == "addressed"` → `confirmed`
  - `status == "open"` → `open`
  - Items containing blocker keywords → `sign_off_blockers` (subset of `open`)
  - Blocker keywords: `must`, `required`, `block`, `cannot proceed`, `prevent`
- Stored on `ProposalDocument.decision_summary`

**Acceptance criteria:**
- AC1: AI backend → items classified across all three buckets
- AC2: `files_only` → `confirmed` = addressed decision_points; `open` = open ones
- AC3: `files_only` item containing "must be resolved" → appears in `sign_off_blockers`
- AC4: `files_only` → `sign_off_blockers` is a subset of `open` (no item in both confirmed and blockers)
- AC5: No decision points in any selected review → all three lists empty, no error
- AC6: `source_review_ids` matches the full selected review set

---

### Sprint 3 — Done Definition
- `proposal_coverage` and `decision_summary` populated on all multi-review proposal documents
- Coverage is deterministic and consistent across re-runs with the same inputs
- Decision Summary populated on single-review path too (using anchor review's decision_points)
- All Sprint 2 regression behaviour preserved



---

### Sprint 4 — Forward Guidance & Recommendation Engine
**Goal:** Generate Recommended Focus Areas & Proposed Actions grounded in synthesis
output. Proposal Data Pack section 16 is now populated.

**Dependency:** Sprint 3 complete (`ProposalReviewPass`, `ProposalCoverage`, and
`DecisionSummary` all available as inputs).

**Architectural changes:**
- Add `_run_forward_guidance()` private function to `proposal_generator.py`
- Add `forward_guidance` field to `ProposalDocument` and DB column (already in schema plan)

---

#### Story S4-01: Forward guidance generation

**As a** user,
**I want to** receive practical, data-grounded recommendations for how to strengthen
my proposal,
**so that** I know what to do next rather than just what is missing.

**Implementation notes:**
- `_run_forward_guidance(review_pass, decision_summary, conflicts, version_scope, ai_backend) -> ForwardGuidance`
- AI backend: single LLM call using Forward Guidance Prompt (Section 10)
- Inputs to prompt: unresolved weaknesses from `review_pass`, open decisions,
  conflicts, coverage gaps, scope (max 600 chars)
- Five output sections: `strengthen_weak_areas`, `resolve_key_decisions`,
  `improve_credibility`, `accelerate_client_alignment`, `optional_enhancements`
- Each item: `issue`, `why_it_matters`, `suggested_action`, `trade_off_or_constraint`
- `files_only` fallback: generate one `ForwardGuidanceItem` per open decision
  and per domain with status `"Not Yet Addressed"` using template text
- Rules enforced in prompt: must be grounded in data; must not invent scope;
  optional_enhancements only if clearly viable

**Acceptance criteria:**
- AC1: AI backend → at least one item in `strengthen_weak_areas` when `still_weak` is non-empty
- AC2: AI backend → `optional_enhancements` empty when no viable enhancement is evident
- AC3: `files_only` → one item per open decision in `resolve_key_decisions`
- AC4: `files_only` → one item per `"Not Yet Addressed"` coverage domain
- AC5: Each `ForwardGuidanceItem` has non-empty `issue`, `why_it_matters`, `suggested_action`
- AC6: `trade_off_or_constraint` is empty string (not None) when no constraint applies
- AC7: `generated_by` and `generated_at` fields populated correctly
- AC8: Stored on `ProposalDocument.forward_guidance` and persisted to DB

---

#### Story S4-02: files_only deterministic guidance rules

**As a** user running without an LLM backend,
**I want to** still receive basic forward guidance from the system,
**so that** the tool remains useful in fully offline mode.

**Implementation notes:**
- Part of `files_only` branch of `_run_forward_guidance()`
- Template text rules (no free-form generation):
  - Open decision → `resolve_key_decisions` item: issue = decision text, why = "Unresolved before sign-off", action = "Schedule decision workshop or async resolution"
  - Not Yet Addressed domain → `strengthen_weak_areas` item: issue = "{domain} not covered", why = "Gap in proposal completeness", action = "Add {domain} section to proposal"
  - Sign-off blocker → `accelerate_client_alignment` item using blocker text
- `optional_enhancements` always empty in `files_only` mode

**Acceptance criteria:**
- AC1: 2 open decisions → 2 items in `resolve_key_decisions` with template text
- AC2: `"Security/Compliance": "Not Yet Addressed"` → 1 item in `strengthen_weak_areas`
- AC3: `optional_enhancements` is always empty list in `files_only` mode
- AC4: No open decisions, all domains Addressed → `ForwardGuidance` returned with all lists empty (no error)

---

### Sprint 4 — Done Definition
- `forward_guidance` populated on all proposal documents (single and multi-review paths)
- `files_only` guidance is practical and non-empty when inputs warrant it
- All Sprint 2 and 3 regression behaviour preserved
- Full Proposal Data Pack (sections 1–16) is now populated end-to-end



---

### Sprint 5 — Frontend: Selection, Display & Proposal Iteration Readiness
**Goal:** Expose multi-review selection in the UI, display all new Proposal Data Pack
sections, and add a proposal iteration readiness indicator.

**Dependency:** Sprint 4 complete (all backend artifacts available via API).

**Architectural changes:**
- `static/index.html` only — no backend changes
- Two new collapsible panel groups in the proposal document view
- Supplemental review selection added to `createProposalForm`

---

#### Story S5-01: Supplemental review selection in proposal creation form

**As a** user,
**I want to** select additional reviews from the same version when creating a proposal,
**so that** I can synthesise multiple perspectives into one stronger proposal.

**Implementation notes:**
- Section appears in `createProposalForm` after existing `propReviewSelect` row
- Only shown when selected version has > 1 review
- Anchor review shown as pinned, read-only row (always included)
- All other reviews for that version shown as checkboxes — no `quality_status` filter
- Each checkbox label: `{review_id} – {persona} · {quality_status} ({completeness_score}%)`
- `submitCreateProposal()` collects checked IDs → `supplemental_review_ids` array in generate body
- No supplementals checked → `supplemental_review_ids: []` in body

**Acceptance criteria:**
- AC1: Version with 1 review → supplemental section not rendered
- AC2: Version with 3 reviews → anchor pinned; 2 checkboxes shown for remaining reviews
- AC3: Pending review shown in checkbox list (no filter by quality_status)
- AC4: Zero checkboxes checked → POST body has `supplemental_review_ids: []`
- AC5: Two checkboxes checked → array contains exactly those 2 review_ids
- AC6: Anchor review ID never appears in `supplemental_review_ids` array

---

#### Story S5-02: Conflict warning banner

**As a** user,
**I want to** see a clear warning when conflicts were detected during synthesis,
**so that** I know to review the Decision Summary before finalising.

**Implementation notes:**
- Banner rendered above document sections when `reconciliation_result.contradictions` is non-empty
- Text: "⚠ {N} conflict(s) detected during review synthesis. See Decision Summary for details."
- Hidden when `reconciliation_result` is null or `contradictions` is empty

**Acceptance criteria:**
- AC1: 0 conflicts → banner not rendered
- AC2: 2 conflicts → banner shows "⚠ 2 conflict(s) detected..."
- AC3: Single-review document (`reconciliation_result == null`) → banner not rendered



---

#### Story S5-03: Proposal Review Pass display

**As a** user,
**I want to** see the six-domain proposal review pass in the document view,
**so that** I can quickly assess which areas need work before submission.

**Implementation notes:**
- Collapsible section "Proposal Review Pass" below existing document sections
- Six domain panels: Scope | Architecture | Delivery | Security/Compliance | Operations | Commercials
- Each panel contains three sub-lists:
  - ✓ Covered Well
  - ⚠ Still Weak
  - 🔴 May Block Sign-off
- Hidden when `review_pass` is null on the document
- Empty sub-list → renders with "(none)" placeholder, not blank

**Acceptance criteria:**
- AC1: `review_pass == null` → section not rendered
- AC2: All six domain panels present when `review_pass` is populated
- AC3: Empty `covered_well` list → shows "(none)" not a blank element
- AC4: `may_block_signoff` items styled in red to distinguish from weak items

---

#### Story S5-04: Proposal Coverage table display

**As a** user,
**I want to** see a coverage status table for the six proposal domains,
**so that** I can identify which client asks are and are not yet addressed.

**Implementation notes:**
- Six-row table: Domain | Status badge | Matched themes | Gap notes
- Status badge colours: Addressed = green, Partial = amber, Not Yet Addressed = red
- Hidden when `proposal_coverage` is null
- `matched_themes` rendered as comma-separated inline tags
- `gap_notes` shown as dimmed text below the status badge

**Acceptance criteria:**
- AC1: `proposal_coverage == null` → section not rendered
- AC2: `security_compliance.status == "Not Yet Addressed"` → red badge in Security/Compliance row
- AC3: All six rows present when coverage is populated
- AC4: `matched_themes: []` → themes cell shows "(none detected)"

---

#### Story S5-05: Decision Summary display

**As a** user,
**I want to** see confirmed decisions, open decisions, and sign-off blockers clearly,
**so that** I can track decision status without reading through the full proposal.

**Implementation notes:**
- Three collapsible sub-sections: "Confirmed Decisions ✓", "Open Decisions ⚠", "Sign-off Blockers 🔴"
- Hidden when `decision_summary` is null
- Empty list → renders with "None" placeholder
- Sign-off Blockers section highlighted with red border when non-empty

**Acceptance criteria:**
- AC1: `decision_summary == null` → section not rendered
- AC2: Empty `confirmed` list → "Confirmed Decisions" section shows "None"
- AC3: Non-empty `sign_off_blockers` → section has red visual treatment
- AC4: Each item shows `source_review_id` as a small tag for traceability

---

#### Story S5-06: Forward Guidance display

**As a** user,
**I want to** see practical recommended next actions in the document,
**so that** I know exactly what to do to improve the proposal.

**Implementation notes:**
- Five collapsible sub-sections matching the five guidance categories
- Each item renders: Issue → Why it matters → Suggested action → Trade-off (if present)
- Hidden when `forward_guidance` is null
- `optional_enhancements` section shown only when list is non-empty

**Acceptance criteria:**
- AC1: `forward_guidance == null` → section not rendered
- AC2: Empty `optional_enhancements` → that sub-section not rendered
- AC3: Each item's `trade_off_or_constraint` only shown when non-empty string
- AC4: `files_only`-generated guidance renders identically to LLM-generated guidance

---

#### Story S5-07: Proposal iteration readiness indicator

**As a** user,
**I want to** see a readiness signal for the current proposal version,
**so that** I can assess whether it is ready to submit or needs more work.

**Implementation notes:**
- Shown in the proposal version list and at the top of the document view
- Computed client-side from the retrieved document fields (no new API call)
- Logic:
  - 🔴 Not Ready — `sign_off_blockers` is non-empty OR any coverage domain is "Not Yet Addressed"
  - 🟡 Needs Work — `sign_off_blockers` empty but `open` decisions > 0 OR any domain is "Partial"
  - 🟢 Ready to Submit — all domains Addressed, no open decisions, no sign-off blockers
- Label: "Proposal Readiness: 🟢 Ready to Submit / 🟡 Needs Work / 🔴 Not Ready"
- Shown as `Not assessed` when `proposal_coverage` or `decision_summary` is null

**Acceptance criteria:**
- AC1: Sign-off blocker present → 🔴 Not Ready
- AC2: No blockers, one open decision → 🟡 Needs Work
- AC3: All domains Addressed, zero open decisions, zero blockers → 🟢 Ready to Submit
- AC4: `proposal_coverage == null` → shows "Not assessed" (no badge)
- AC5: Readiness computed from already-loaded document — no extra API call made

---

### Sprint 5 — Done Definition
- Supplemental review selection functional in proposal creation form
- All six new Proposal Data Pack display sections rendered correctly
- Proposal iteration readiness indicator shown on every proposal version
- Single-review documents (with `null` synthesis fields) display cleanly — no empty panels visible
- No backend changes in this sprint



---

## 14. Full Data Model Summary

### New dataclasses in `models/proposal.py`

| Dataclass | Sprint | Purpose |
|---|---|---|
| `ProposalInputSnapshot` | S2 | Immutable record of anchor + supplementals + version at generation time |
| `NormalizedItem` | S1 | One typed, provenance-tagged finding item |
| `ConflictEntry` | S1 | One detected contradiction between two reviews |
| `ReconciliationResult` | S1 | Full LLM reconcile output: merged findings, conflicts, notes |
| `ReviewPassDomain` | S2 | Per-domain critique: covered_well, still_weak, may_block_signoff |
| `ProposalReviewPass` | S2 | Six-domain proposal quality critique |
| `CoverageDomain` | S3 | Per-domain coverage: status, matched_themes, gap_notes |
| `ProposalCoverage` | S3 | Six-domain coverage map |
| `DecisionItem` | S3 | One classified decision: text, category, source_review_id |
| `DecisionSummary` | S3 | Confirmed / open / sign-off blockers |
| `ForwardGuidanceItem` | S4 | One recommendation: issue, why, action, trade-off |
| `ForwardGuidance` | S4 | Five-section recommendation set |

### Additive fields on `ProposalDocument`

| Field | Type | Default | Sprint |
|---|---|---|---|
| `input_snapshot` | `Optional[Dict]` | `None` | S2 |
| `reconciliation_result` | `Optional[Dict]` | `None` | S2 |
| `review_pass` | `Optional[Dict]` | `None` | S2 |
| `proposal_coverage` | `Optional[Dict]` | `None` | S3 |
| `decision_summary` | `Optional[Dict]` | `None` | S3 |
| `forward_guidance` | `Optional[Dict]` | `None` | S4 |

### DB columns added to `proposal_documents`

| Column | Type | Default | Sprint |
|---|---|---|---|
| `input_snapshot` | TEXT (JSON) | NULL | S2 |
| `reconciliation_result` | TEXT (JSON) | NULL | S2 |
| `review_pass` | TEXT (JSON) | NULL | S2 |
| `proposal_coverage` | TEXT (JSON) | NULL | S3 |
| `decision_summary` | TEXT (JSON) | NULL | S3 |
| `forward_guidance` | TEXT (JSON) | NULL | S4 |

### New file

| File | Sprint |
|---|---|
| `processors/review_synthesizer.py` | S1 |

**No files renamed. No files deleted. No new DB tables.**



---

## 15. Architectural Notes for Implementation

### A. `processors/review_synthesizer.py` structure
```
normalize_review_findings(review) -> List[NormalizedItem]
deduplicate_normalized(items, review_completeness_map) -> List[NormalizedItem]
_jaccard_similarity(a: str, b: str) -> float          # internal
_dedup_cache: Dict[frozenset, List[NormalizedItem]]    # module-level in-memory cache

build_reconciliation_prompt(deduped, version_scope) -> str
parse_reconciliation_response(raw, source_ids, anchor_id, backend) -> ReconciliationResult
synthesize_reviews(anchor, supplementals, version_scope, ai_backend) -> ReconciliationResult

extract_scope_themes(version_scope, findings) -> List[str]
compute_proposal_coverage(reconciliation, review_pass, scope_themes) -> ProposalCoverage

merge_decision_points(selected_reviews) -> List[Dict]
build_decision_summary_prompt(merged_decisions, reconciliation_notes) -> str

build_forward_guidance_prompt(review_pass, decision_summary, conflicts, version_scope) -> str
```

### B. `proposal_generator.py` additions (private functions)
```
_run_proposal_review_pass(doc, conflicts, ai_backend) -> ProposalReviewPass
_run_decision_summary(merged_decisions, reconciliation_notes, ai_backend) -> DecisionSummary
_run_forward_guidance(review_pass, decision_summary, conflicts, scope, ai_backend) -> ForwardGuidance
```

### C. LLM call pattern
All LLM calls use the existing `call_llm(backend_name, prompt, max_tokens)` helper
from `ai_backends`. No new backend abstraction needed.
Recommended `max_tokens` per call:
- Reconciliation: 2500
- Proposal generation: 3500
- Review pass: 2000
- Decision summary: 1000
- Forward guidance: 2000

### D. Token budget awareness
Five sequential LLM calls per multi-review generation run. For large reviews,
the reconciliation prompt may be long. Truncate deduped items to top 15 per
category if total prompt exceeds 6000 tokens (estimate: 4 tokens/word).
Truncation logged as a warning; not an error.

### E. Error isolation
Each LLM step (5, 7, 9, 10) is individually try/except wrapped.
If any step fails, the document is still saved with that artifact as `None`.
Failure logged. Generation does not abort.

### F. Single-review path regression guard
The `if supplemental_review_ids:` branch must be the only code path change.
`_generate_files_only()` and `_generate_ai()` signatures are unchanged.
The synthesis path passes `reconciled_findings` as a plain `dict` replacing
`review.findings` — both functions already accept `findings: Dict`.

---

## 16. Open Risks and Ambiguities

| # | Risk / Ambiguity | Severity | Recommendation |
|---|---|---|---|
| R1 | LLM reconciliation quality depends on model capability. Smaller local models (Ollama 7B) may produce poor merges. | Medium | Prompt includes explicit format constraints. Add validation: if reconciled category is empty but deduped input was non-empty, fall back to deduped union for that category. |
| R2 | Five LLM calls per generation may be slow on Ollama in Docker (potentially 60–120s total). | High | Show per-step progress in UI. Consider making steps 9 and 10 async / deferrable if latency is unacceptable. |
| R3 | `extract_scope_themes` regex approach may miss themes in poorly structured scope text. | Low | Acceptable for first implementation. Flag with "(limited themes extracted)" when < 3 themes found. |
| R4 | If anchor review's `decision_points` is empty (e.g., old review created before S5-01 was built), decision summary will have no input. | Low | Graceful: empty lists returned. No error. Forward guidance item added noting decisions were not extracted. |
| R5 | Dedup cache is in-memory only — cleared on Docker container restart. | Low | Acceptable. Cache is a performance optimisation only; correctness does not depend on it. |
| R6 | User may select supplemental reviews from different personas covering overlapping concerns. LLM reconciliation may lose nuance. | Medium | `reconciliation_notes` field surfaces LLM's merge rationale. Users can inspect and regenerate if needed. |

