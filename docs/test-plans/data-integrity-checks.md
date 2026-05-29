# Data Integrity Checks: Traceability Chain

> Chain: Version → Review → Proposal → Feedback → Next Review

---

## 1. VERSION

| # | Validation Rule | What Fails If Broken |
|---|----------------|----------------------|
| V1 | `version.project_id` must reference an existing, active project | Orphaned version. Queries by project return incomplete results. Version inaccessible in UI. |
| V2 | `version.version_number` must be unique within `project_id` scope | Duplicate version display. Ordering breaks. Proposal versioning loses meaning. |
| V3 | `version.version_number` must be > 0 and monotonically increasing per project | Sorting errors. "Latest version" query returns wrong result. |
| V4 | `version.status` must be one of: `draft`, `in_review`, `proposed`, `finalised` | State machine breaks. Phase transition validation cannot function. |
| V5 | `version.active_review_id` must be null OR reference a review WHERE `review.version_id == version.id` | Cross-version active review. Proposal created against wrong review. Injection pulls wrong feedback. |
| V6 | `version.source_version_id` (if set) must reference a finalised version in the same project | Broken provenance chain. "Created from Version N" shows wrong source. |
| V7 | `version.finalised_at` must be set if and only if `status == finalised` | Audit trail broken. Reports show finalisation without timestamp or timestamp without finalisation. |
| V8 | `version.content` must not be null or empty | Empty proposal generation. Intelligence tab shows blank. Review has no material to evaluate. |
| V9 | No version with `status: finalised` may have `active_review_id` pointing to a non-closed review | Inconsistent state. Finalised version appears to have active work. |
| V10 | After finalisation: no child entities (review, proposal) may have `created_at` > `version.finalised_at` | Immutability violated. Post-finalisation mutations occurred. |

---

## 2. REVIEW

| # | Validation Rule | What Fails If Broken |
|---|----------------|----------------------|
| R1 | `review.version_id` must reference an existing version | Orphaned review. Not visible in any version's review panel. |
| R2 | `review.version_id` must reference a version with `status != finalised` at time of creation | Review created on immutable version. Breaks finalisation contract. |
| R3 | `review.status` must be one of: `pending`, `active`, `closed` | State machine breaks. Closure check for finalisation cannot validate. |
| R4 | At most ONE review per version may be referenced by `version.active_review_id` | Dual active reviews. Injection ambiguous. Proposal references unpredictable. |
| R5 | `review.injected_feedback` must be immutable after creation (no updates to this field) | Retroactive injection. Historical traceability lost. Snapshot contract broken. |
| R6 | `review.injected_feedback` must contain ONLY feedback items that existed on the active review at `review.created_at` | Future feedback injected. Temporal consistency broken. Injection contains data that didn't exist yet. |
| R7 | `review.injected_feedback` must contain ONLY feedback from the review that was `version.active_review_id` at creation time | Wrong review's feedback injected. Scope violation. Traceability chain broken: cannot trace injected feedback to correct source. |
| R8 | If version has `active_review_id = null` at review creation time: `review.injected_feedback` must be `[]` | Null pointer on injection query. Crash or incorrect data pulled from previous active. |
| R9 | All reviews on a finalised version must have `status: closed` | Open reviews on locked version. UI shows actionable items on immutable entity. |
| R10 | `review.created_at` must be >= `version.created_at` of its parent version | Temporal paradox. Review appears to predate its own version. |

---

## 3. PROPOSAL VERSION

| # | Validation Rule | What Fails If Broken |
|---|----------------|----------------------|
| P1 | `proposal.version_id` must reference an existing version | Orphaned proposal. Not visible in any version's proposal list. |
| P2 | `proposal.review_id` must reference a review WHERE `review.version_id == proposal.version_id` | Cross-version proposal-review link. "Based on" shows review from wrong version. Traceability broken. |
| P3 | `proposal.review_id` must equal `version.active_review_id` at time of proposal creation | Proposal built from non-active review. Feedback injection from wrong source. User intent violated. |
| P4 | `proposal.proposal_version` must be unique within `version_id` scope | Duplicate version numbers. "Latest proposal" query returns arbitrary result. |
| P5 | `proposal.proposal_version` must be sequential (no gaps except for hard-deleted entries) | Confusing version history. User sees v1, v3 (missing v2) with no explanation. |
| P6 | `proposal.proposal_version` must equal `max(proposal_version for version_id) + 1` at creation | Version number collision. Race condition creating duplicate numbers. |
| P7 | `proposal.status` must be one of: `draft`, `submitted`, `accepted`, `rejected`, `superseded` | State machine breaks. Finalisation precondition check cannot validate. |
| P8 | At most ONE proposal per version may have `status: draft` at any time | Auto-supersede failed. Two drafts exist simultaneously. User confused about which is current. |
| P9 | All proposals with `status: superseded` must have `superseded_at` set | Audit trail incomplete. Cannot determine when supersession occurred. |
| P10 | A `superseded` proposal must have a later proposal (higher `proposal_version`) in non-superseded state | Superseded with no successor. Dead end in version chain. |
| P11 | `proposal.injected_feedback` must be immutable after creation | Same as review injection: snapshot contract broken. |
| P12 | `proposal.created_at` must be >= `review.created_at` of its referenced review | Temporal paradox. Proposal predates its own review source. |
| P13 | No proposal with `status: accepted` may exist on a version unless that version can reach `finalised` | Accepted proposal on a version stuck in invalid state. Finalisation permanently blocked. |
| P14 | `proposal.version_id` must reference a version with `status != finalised` at time of creation | Proposal created on immutable version. Breaks finalisation contract. |

---

## 4. FEEDBACK ITEM

| # | Validation Rule | What Fails If Broken |
|---|----------------|----------------------|
| F1 | Feedback must have exactly ONE of `review_id` or `proposal_id` set (XOR) | Orphaned feedback (neither set) or ambiguous parent (both set). Cannot determine where feedback belongs. |
| F2 | `feedback.review_id` (if set) must reference an existing review | Orphaned feedback. Not visible in any review's feedback panel. |
| F3 | `feedback.proposal_id` (if set) must reference an existing proposal | Orphaned feedback. Not visible in any proposal's feedback panel. |
| F4 | `feedback.content` must be non-empty string | Empty feedback pollutes lists. Injection carries empty items. |
| F5 | `feedback.resolved` must be boolean, default `false` | Finalisation soft-warning count incorrect. Unresolved count badge wrong. |
| F6 | `feedback.added_after_close` must be `true` if parent review `status == closed` at feedback creation time | Audit log metadata incorrect. Cannot distinguish pre-close from post-close feedback. |
| F7 | `feedback.created_at` must be >= parent entity's `created_at` | Temporal paradox. Feedback predates its own parent review/proposal. |
| F8 | Feedback on a review belonging to version V must NOT appear in `injected_feedback` of any review on a DIFFERENT version | Cross-version injection leak. Feedback from project A visible in project B's reviews. |
| F9 | Feedback with `review_id = R` must ONLY appear in `injected_feedback` of reviews created AFTER this feedback, AND only if R was active at that later review's creation time | Injection scope violation. Wrong feedback injected into wrong review. |
| F10 | `feedback.author` must be non-null | Anonymous feedback. Cannot trace who provided it. Audit compliance failure. |
| F11 | Feedback `content` must be immutable after creation (only `resolved` status can change) | Content tampering. Historical record altered. Injected copies become inconsistent with source. |
| F12 | Count of feedback WHERE `resolved = false` AND `review_id IN (version's reviews)` must match the finalisation warning count | Incorrect soft warning. User finalises thinking 0 unresolved exist when there are N, or is blocked incorrectly. |

---

## 5. FINALISE STEP

| # | Validation Rule | What Fails If Broken |
|---|----------------|----------------------|
| FN1 | Version must have at least one proposal with `status: accepted` | Finalisation without approval. Unreviewed content locked as final. |
| FN2 | All reviews on version must have `status: closed` at finalisation time | Open reviews on finalised version. Contradiction: work is "done" but reviews are "in progress". |
| FN3 | `version.status` must transition through valid path: `draft → in_review → proposed → finalised` | Phase skipping. Audit trail shows impossible transition. Compliance violation. |
| FN4 | `version.finalised_at` must be set atomically with status change to `finalised` | Timestamp missing or set at different time. Race condition window where version is finalised without timestamp. |
| FN5 | `version.finalised_by` must be set to the user who triggered finalisation | No actor attribution. Audit trail incomplete. Cannot trace who approved final version. |
| FN6 | After finalisation: `INSERT` into reviews table WHERE `version_id = this version` must fail | Post-finalisation review creation. Immutability violated. |
| FN7 | After finalisation: `INSERT` into proposals table WHERE `version_id = this version` must fail | Post-finalisation proposal creation. Immutability violated. |
| FN8 | After finalisation: `UPDATE` on `version.content` must fail | Content mutation after lock. Final deliverable altered without new version. |
| FN9 | After finalisation: `UPDATE` on `version.active_review_id` must fail | Active review changed on locked version. Meaningless state change. |
| FN10 | After finalisation: feedback `INSERT` on closed reviews must SUCCEED (audit log) | Audit log blocked. Post-delivery notes cannot be captured. Append-only contract broken. |
| FN11 | Backward transition must create new version with `source_version_id = finalised_version.id` | Provenance lost. New version has no traceability to its origin. |
| FN12 | Backward transition must NOT modify the finalised version in any way | Original version mutated. Immutability contract violated. Historical record altered. |
| FN13 | New version from backward transition must start with: zero reviews, zero proposals, zero feedback, `status: draft` | Inherited state from original. New version contaminated with old data. |
| FN14 | Concurrent finalisation of same version must be idempotent (not create duplicate side effects) | Double-close of reviews. Duplicate `finalised_at` entries. Event handlers fire twice. |

---

## Traceability Chain Validation

These checks verify the FULL chain is intact: Version → Review → Proposal → Feedback → Next Review

| # | Chain Link | Validation | Broken Trace If Violated |
|---|-----------|-----------|--------------------------|
| T1 | Version → Review | Every review's `version_id` exists in versions table | Review floats without version context |
| T2 | Version → Active Review | `version.active_review_id` → `review.id` where `review.version_id == version.id` | Active review belongs to different version |
| T3 | Active Review → Proposal | `proposal.review_id == version.active_review_id` at creation | Proposal built from wrong review |
| T4 | Review → Feedback | `feedback.review_id` exists in reviews table with matching `version_id` parent | Feedback attributed to wrong review |
| T5 | Feedback → Next Review (injection) | `next_review.injected_feedback` contains ONLY feedback from `version.active_review_id` at `next_review.created_at` | Wrong feedback injected; traceability broken |
| T6 | Proposal → Feedback | `feedback.proposal_id` exists in proposals table with matching `version_id` parent | Feedback on wrong proposal |
| T7 | Proposal Version → Previous Proposal | `proposal.proposal_version == prev.proposal_version + 1` within same version | Gap in proposal history; missing iteration |
| T8 | Finalised Version → Backward Version | `new_version.source_version_id` points to valid finalised version in same project | Origin untraceable; cloned content has no provenance |
| T9 | Injection Snapshot → Source Feedback | Every item in `review.injected_feedback` must correspond to a feedback record that existed at snapshot time | Phantom injection; injected data has no source record |
| T10 | Full Chain Audit | For any finalised version: can trace back from `finalised_at` → accepted proposal → review it was based on → feedback on that review → where that feedback was injected from | Full lifecycle audit trail broken; compliance failure |

---

## Enforcement Strategy

| Layer | What It Enforces | Examples |
|-------|-----------------|----------|
| **Database constraints** | Referential integrity, uniqueness, NOT NULL | Foreign keys, unique indexes on `(project_id, version_number)`, `(version_id, proposal_version)` |
| **Application validation** | Business rules, state machine, XOR constraints | Status transitions, auto-supersede, injection scope, finalisation preconditions |
| **Transaction boundaries** | Atomicity of multi-step operations | Finalisation (status + close reviews + set timestamp), injection (read active feedback + write to new review) |
| **Immutability guards** | Post-creation/post-finalisation write blocks | Check `version.status` on every write endpoint, `injected_feedback` field has no update path |
| **Scheduled integrity checks** | Detect drift/corruption over time | Cron job validating T1-T10 chain links, alerting on violations |

---

## Summary

| Entity | Rules | Critical (breaks chain) | Important (breaks audit) | Warning (UX issue) |
|--------|:-----:|:-----------------------:|:------------------------:|:------------------:|
| Version | 10 | V5, V10 | V7, V9 | V3, V6 |
| Review | 10 | R4, R6, R7 | R5, R9 | R2, R8 |
| Proposal | 14 | P2, P3, P8 | P9, P10, P11 | P5, P6 |
| Feedback | 12 | F1, F8, F9 | F6, F11, F12 | F4, F10 |
| Finalise | 14 | FN1, FN6, FN7, FN8, FN12 | FN3, FN4, FN5 | FN10, FN14 |
| Traceability | 10 | T2, T3, T5 | T9, T10 | T7, T8 |
| **TOTAL** | **70** | **16** | **15** | **12** |
