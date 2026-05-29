# Design Decisions: Resolved

These decisions were made during the test planning phase and govern the implementation
of the Version → Review → Proposal → Feedback lifecycle.

---

## Decision Summary

| # | Decision Point | Resolution |
|---|---------------|------------|
| 1 | **Active review on first-review-deletion** | If no reviews remain, `active_review_id` = null. System surfaces message: "No reviews available. Create a review to continue." No fallback selection. |
| 2 | **Feedback on closed reviews** | Append-only audit log. Feedback can always be added regardless of review status. Closed reviews are never write-locked for feedback. |
| 3 | **Injection scope** | Active review only. When creating a new review, only feedback from the current active review is injected. Feedback from non-active reviews is ignored in injection. |
| 4 | **Proposal v2 while v1 is still draft** | Auto-supersede. Creating a new proposal automatically transitions any existing `draft` proposal to `superseded` status. No user prompt required. |
| 5 | **Finalisation with unresolved feedback** | Soft warning. System allows finalisation but surfaces a warning: "N feedback items remain unresolved." User explicitly confirms to proceed. |
| 6 | **Phase transition model** | Linear progression with backward option. Going back always creates a new version at `draft` status (cannot mutate the finalised one). Original version remains immutable. |
| 7 | **Offline conflict resolution** | Last-write-wins. No merge UI. Most recent timestamp takes precedence on sync. Recommend: use server-received timestamp on sync, not device clock. |

---

## Detailed Implications

### 1. Active Review on Last Deletion

- `version.active_review_id` is set to `null`
- Any operation requiring an active review (proposal creation, feedback injection) returns informative error
- Creating a new review after deletion auto-assigns it as active (same as first-review behaviour)
- UI must show clear empty state with call-to-action

### 2. Feedback on Closed Reviews (Append-Only Audit Log)

- Feedback table has no write-lock check against review status
- Post-close feedback is tagged with metadata (`added_after_close: true` or equivalent timestamp comparison)
- This feedback IS injectable if the closed review happens to be active at time of next review creation
- Supports compliance/audit requirements where post-hoc notes are necessary

### 3. Injection Scope: Active Review Only

- On review creation: system queries `version.active_review_id`, fetches all feedback for that review, snapshots it into `review.injected_feedback`
- This is a POINT-IN-TIME snapshot — immutable after creation
- Feedback added to the source review AFTER injection does not retroactively update
- Non-active reviews' feedback is never automatically injected (accessible via direct query only)

### 4. Auto-Supersede Draft Proposals

- On proposal creation: system checks for existing proposals with `status: draft` on same version
- ALL found drafts transition to `status: superseded` with `superseded_at` timestamp
- Only `draft` status is auto-superseded. `submitted` and `rejected` proposals are untouched
- Superseded proposals are fully immutable and retrievable for audit purposes
- Enforces invariant: at most ONE draft proposal per version at any time

### 5. Finalisation with Soft Warning

- Finalisation endpoint checks for unresolved feedback count
- If count > 0 AND request does not include `confirm: true`: returns warning response (not an error)
- If count > 0 AND `confirm: true` is present: proceeds with finalisation
- If count == 0: proceeds without needing confirm flag
- Unresolved feedback persists as-is (not auto-resolved on finalisation)

### 6. Linear Phase Transition with Single-Step Backward

- Forward transitions: `draft` → `in_review` → `proposed` → `finalised` (strict order, no skipping)
- Backward transition: ANY non-draft version → triggers creation of NEW version at `draft`
- Single backward action regardless of source phase (finalised→draft, proposed→draft, in_review→draft)
- Original version is NEVER mutated — remains at its current phase, fully immutable
- New version has `source_version_id` pointing to the original for traceability
- New version content is cloned from original; reviews/proposals/feedback start fresh
- Version numbering continues: if original was v3, new version is v4

### 7. Last-Write-Wins Offline Resolution

- No user-facing merge conflict UI
- Timestamp comparison determines winner
- Recommendation: use server-received timestamp (not device clock) to avoid clock skew issues
- Deletes win over edits if delete timestamp is later
- Creates with unique IDs always persist (no content-based deduplication)
- Status transitions: last timestamp wins; if both are same transition, idempotent
