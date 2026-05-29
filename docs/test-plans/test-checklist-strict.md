# Strict End-to-End Test Checklist

This checklist covers individual feature validation before the full E2E test plan is executed.
Use this for focused testing of each subsystem in isolation.

---

## 1. Version Creation

### Expected Behaviour

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 1.1 | Create version with valid payload (title, content, parent project ref) | Version created with auto-generated ID, `status: draft`, `created_at` timestamp, `version_number: 1` |
| 1.2 | Create second version for same project | `version_number` increments to 2, both versions retrievable |
| 1.3 | Retrieve version by ID | Returns full version object including empty reviews array |
| 1.4 | List versions for a project | Returns ordered list (newest first or by version_number) |

### Edge Cases

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 1.5 | Create version with empty/missing title | Validation error, no version persisted |
| 1.6 | Create version referencing non-existent project | Foreign key / reference error |
| 1.7 | Create version with duplicate version_number (manual override if allowed) | Conflict error OR auto-increment ignores manual input |
| 1.8 | Create version when project is in `finalised` phase | Should FAIL — no new versions allowed post-finalisation |

### Should Fail

- Creating a version with no content body
- Creating a version on a locked/archived project
- Negative or zero version numbers (if user-supplied)

---

## 2. Multiple Reviews Per Version

### Expected Behaviour

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 2.1 | Create first review on a version | Review created, linked to version, `status: pending`, auto-becomes active review |
| 2.2 | Create second review on same version | Second review created, first remains active (no auto-switch) |
| 2.3 | Create N reviews (e.g., 5) on same version | All 5 retrievable, only one marked active |
| 2.4 | List reviews for a version | Returns all reviews in creation order with status indicators |
| 2.5 | Each review has independent content/criteria | Reviews are isolated — editing one doesn't affect others |

### Edge Cases

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 2.6 | Create review on non-existent version | Reference error |
| 2.7 | Create review with empty body/criteria | Validation error |
| 2.8 | Delete a review that is NOT active | Review removed, active review unchanged |
| 2.9 | Delete the ACTIVE review (last one) | Active review cleared to null. Message: "No reviews available. Create a review to continue." |
| 2.10 | Create review on a finalised version | Should FAIL |

### Should Fail

- Review creation without version reference
- Review with invalid/unknown reviewer reference (if applicable)
- Duplicate review submission within same millisecond (idempotency check)

---

## 3. Active Review Selection

### Expected Behaviour

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 3.1 | First review created becomes active automatically | `version.active_review_id` = first review's ID |
| 3.2 | Explicitly set review #3 as active | `active_review_id` updates, previous active has no special status change |
| 3.3 | Query version returns active review inline or by reference | Active review data accessible without separate lookup |
| 3.4 | Switch active review multiple times | Each switch is clean, only latest assignment persists |

### Edge Cases

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 3.5 | Set active review to a review belonging to DIFFERENT version | Should FAIL — cross-version reference rejected |
| 3.6 | Set active review to non-existent review ID | Not found error |
| 3.7 | Set active review on version with zero reviews | Should FAIL or no-op with error |
| 3.8 | Set active review to already-active review (idempotent) | No error, no state change, 200 OK |
| 3.9 | Set active review while a proposal is in-progress using current active | Allowed — confirmation dialog in UI but no backend block |

### Should Fail

- Setting active review after version is finalised
- Setting active review to a deleted/archived review
- Null/empty review ID in set-active request

---

## 4. Proposal Creation from Version + Active Review

### Expected Behaviour

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 4.1 | Create proposal with valid version (has active review) | Proposal created, references `version_id` AND `review_id` (snapshot of active at creation time) |
| 4.2 | Proposal captures version content + review content at point-in-time | Changing review after proposal creation does NOT alter proposal |
| 4.3 | Proposal has own lifecycle status (`draft` → `submitted` → `accepted`/`rejected`) | Status transitions work correctly |
| 4.4 | Multiple proposals can exist for same version | Each independently tracked |
| 4.5 | Proposal includes `proposal_version: 1` | First proposal for a version starts at 1 |

### Edge Cases

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 4.6 | Create proposal on version with NO active review | Should FAIL — active review is required input |
| 4.7 | Create proposal on version with no reviews at all | Should FAIL |
| 4.8 | Create proposal referencing version from different project | Should FAIL — scope violation |
| 4.9 | Active review is switched AFTER proposal creation | Proposal retains original review reference (immutable snapshot) |
| 4.10 | Create proposal on finalised version | Should FAIL |

### Should Fail

- Proposal with no version reference
- Proposal when active review is in `rejected` state (if reviews have states)
- Proposal creation by unauthorized user (if auth exists)

---

## 5. Feedback Capture

### Expected Behaviour

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 5.1 | Add feedback to a review | Feedback stored with `review_id`, `content`, `author`, `created_at` |
| 5.2 | Add feedback to a proposal | Feedback stored with `proposal_id`, content, metadata |
| 5.3 | Multiple feedback items on same review | All retrievable, ordered by creation time |
| 5.4 | Feedback supports categories/tags (if modelled) | Category persisted and filterable |
| 5.5 | Retrieve all feedback for a version (aggregated across reviews) | Returns unified list with source attribution |

### Edge Cases

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 5.6 | Add feedback to non-existent review/proposal | Reference error |
| 5.7 | Add empty feedback (no content) | Validation error |
| 5.8 | Add feedback after review is finalised/closed | ALLOWED (append-only audit log) |
| 5.9 | Very long feedback content (>10KB) | Either accepted or truncated with warning — define limit |
| 5.10 | Feedback with special characters / markdown / HTML | Stored and retrieved without corruption (sanitised if needed) |

### Should Fail

- Feedback with no parent reference (orphaned)
- Feedback on a deleted review
- Feedback referencing both a review AND a proposal simultaneously (pick one parent)

---

## 6. Feedback Injection into Next Review

### Expected Behaviour

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 6.1 | Create new review on version that has previous active review with feedback | New review's context/input includes prior active review's feedback |
| 6.2 | Feedback injection is automatic (not manual copy) | System populates `injected_feedback` field |
| 6.3 | Only feedback from the ACTIVE review is injected | Non-active reviews' feedback is excluded |
| 6.4 | Injected feedback is read-only in the new review | Cannot edit the injected portion |
| 6.5 | Chain of 3+ reviews shows selective injection (active only, not cumulative) | Review 3 contains feedback from whichever review was active at Review 3's creation time |

### Edge Cases

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 6.6 | Create review when active review has ZERO feedback | Injection field is empty/null, no error |
| 6.7 | Feedback added to Review 1 AFTER Review 2 was created | Review 2's injected context is NOT retroactively updated (point-in-time snapshot) |
| 6.8 | Delete feedback from prior review after injection | Injected copy in next review persists (immutable) |
| 6.9 | Very large volume of prior feedback (100+ items) | All injected (define pagination/truncation if needed) |
| 6.10 | Circular injection (review references itself) | Architecturally impossible — validate |

### Should Fail

- Manual override of injected feedback content
- Injection from reviews belonging to different versions
- Injection skipping a review in the chain (only active matters, not chain position)

---

## 7. Proposal Versioning

### Expected Behaviour

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 7.1 | First proposal for a version = `proposal_version: 1` | Numbering starts at 1 |
| 7.2 | Reject proposal, create new one = `proposal_version: 2` | Auto-increments based on version scope |
| 7.3 | Each proposal version is independently retrievable | Full history accessible |
| 7.4 | Previous draft proposals become `superseded` on new proposal creation | Status auto-updates |
| 7.5 | Proposal version references which review it was built from | Traceability: Proposal v2 → Review #3, Proposal v1 → Review #1 |

### Edge Cases

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 7.6 | Create proposal v2 while proposal v1 is still `draft` | v1 auto-superseded, v2 created as draft |
| 7.7 | Proposal version numbering after deletion of middle version | Numbers don't recycle — if v2 deleted, next is still v3 |
| 7.8 | Maximum proposal versions (if capped) | Define limit or allow unlimited with pagination |
| 7.9 | Retrieve "latest" proposal for a version | Shortcut query returns highest version number |
| 7.10 | Compare two proposal versions (diff) | If supported: returns delta of content changes |

### Should Fail

- Manually setting proposal_version to arbitrary number
- Creating proposal version 2 without version 1 existing (gap)
- Proposal versioning across different parent versions (scope leak)

---

## 8. Finalisation and Phase Transition

### Expected Behaviour

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 8.1 | Finalise a version with accepted proposal | Version status → `finalised`, proposal status → `accepted`, all reviews → `closed` |
| 8.2 | Phase transition triggers (e.g., `draft` → `in_review` → `proposed` → `finalised`) | Each transition validates preconditions |
| 8.3 | Finalised version is immutable | No edits to content, reviews, or proposals allowed |
| 8.4 | Finalisation records timestamp and actor | Audit trail persisted |
| 8.5 | Backward transition creates new version at draft | New version spawned with `source_version_id`, content cloned |

### Edge Cases

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 8.6 | Finalise version with NO accepted proposal | Should FAIL — precondition not met |
| 8.7 | Finalise version with active review still `in_progress` | Should FAIL — open work exists |
| 8.8 | Finalise version with pending/unresolved feedback | Soft warning — requires `confirm: true` to proceed |
| 8.9 | Attempt to un-finalise (revert) | Should FAIL — use backward transition instead (creates new version) |
| 8.10 | Finalise same version twice (idempotent) | No error, no state change, 200 OK |
| 8.11 | Phase transition skipping steps (`draft` → `finalised`) | Should FAIL — invalid state machine transition |
| 8.12 | Concurrent finalisation attempts (race condition) | Only one succeeds, second gets conflict error or is idempotent |

### Should Fail

- Finalisation without accepted proposal
- Finalisation of already-finalised version (unless idempotent)
- Any mutation (create review, add feedback to non-closed review, edit content) after finalisation
- Phase transition backwards without triggering new version creation
- Skipping phases in forward direction
