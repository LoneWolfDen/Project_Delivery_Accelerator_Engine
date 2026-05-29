# Edge Cases and Validation Failures: End-to-End Flow

> Format: Step → Failure Scenario → Expected Validation Error → Expected System Behaviour

---

## 1. Version Without Reviews

| # | Failure Scenario | Expected Validation Error | Expected System Behaviour |
|---|------------------|---------------------------|---------------------------|
| 1.1 | User navigates to version detail with zero reviews | None (valid state) | UI shows empty state: "No reviews yet. Create a review to get started." No active review indicator. |
| 1.2 | Attempt to set active review on version with no reviews | 400: "No reviews exist on this version" | Request rejected. `active_review_id` remains null. No data mutation. |
| 1.3 | Attempt to generate proposal on version with zero reviews | 400: "No reviews exist on this version" | Request rejected. No proposal created. "Generate Proposal" button disabled in UI. |
| 1.4 | Attempt to finalise version with no reviews | 400: "No accepted proposal exists for this version" | Request rejected. Version stays at current phase. |
| 1.5 | Attempt phase transition `draft` → `in_review` with no reviews | 400: "At least one review is required to enter review phase" | Transition blocked. UI shows tooltip on disabled "Next Phase" button. |
| 1.6 | Delete all reviews on a version that previously had reviews | None (valid operation) | `active_review_id` → null. UI reverts to empty state. Existing proposals remain (they snapshot their review). |

---

## 2. Multiple Reviews Without Active Review

| # | Failure Scenario | Expected Validation Error | Expected System Behaviour |
|---|------------------|---------------------------|---------------------------|
| 2.1 | Active review deleted, other reviews still exist, user tries to generate proposal | 400: "No active review set. Create or select a review to continue." | Proposal not created. UI shows warning banner on version detail. |
| 2.2 | Active review deleted, user creates new review | None (auto-assigns) | New review becomes active automatically. `version.active_review_id` = new review. Normal flow resumes. |
| 2.3 | DB corruption: `active_review_id` points to non-existent review | 500 / data integrity error on version fetch | System logs error. UI shows: "Active review reference is invalid. Please select a review." Admin alert triggered. |
| 2.4 | Race condition: two users delete active review simultaneously | First delete succeeds, second returns 404: "Review not found" | `active_review_id` = null after first delete. Second delete is no-op (already gone). |
| 2.5 | `active_review_id` = null, user clicks "Set as Active" on one of the existing reviews | None (valid operation) | `active_review_id` updates to selected review. UI updates immediately. |
| 2.6 | Version has 3 reviews, none active, user tries feedback injection (creates review 4) | None (injection produces empty array) | Review 4 created with `injected_feedback: []`. No crash. No injection since active is null. |

---

## 3. Proposal Creation Without Active Review

| # | Failure Scenario | Expected Validation Error | Expected System Behaviour |
|---|------------------|---------------------------|---------------------------|
| 3.1 | `active_review_id` is null, user clicks "Generate Proposal" | 400: "No active review set. Create and activate a review first." | Button disabled in UI (tooltip explains why). API rejects if called directly. No proposal created. |
| 3.2 | Active review deleted between page load and proposal submit (stale UI) | 400: "No active review set" | Optimistic UI fails. Error toast displayed. User must refresh and select new active review. |
| 3.3 | API call manually crafted with `review_id` but version's `active_review_id` is null | 400: "Active review must be set on the version" | System validates against version state, not just provided `review_id`. Prevents bypass. |
| 3.4 | API call with `review_id` that differs from `version.active_review_id` | 400: "Provided review_id does not match version's active review" | System enforces snapshot from active, not arbitrary review. |
| 3.5 | Active review exists but has `status: closed` | Define: allow or block? Recommend: block with 400: "Active review is closed. Create or activate an open review." | No proposal generated from closed review. User must activate an open review. |

---

## 4. Feedback Linked to Wrong Proposal or Review

| # | Failure Scenario | Expected Validation Error | Expected System Behaviour |
|---|------------------|---------------------------|---------------------------|
| 4.1 | Feedback submitted with `review_id` from different version | 400: "Review does not belong to the current context" OR silently stored (review exists) | Recommend: validate scope. If review belongs to different version, reject. Feedback must be scoped. |
| 4.2 | Feedback submitted with both `review_id` AND `proposal_id` | 400: "Feedback must reference exactly one parent (review or proposal)" | Request rejected. No feedback stored. |
| 4.3 | Feedback submitted with neither `review_id` nor `proposal_id` | 400: "Either review_id or proposal_id is required" | Request rejected. Orphan feedback never created. |
| 4.4 | Feedback submitted with `proposal_id` from different version | 400: "Proposal does not belong to this version" | Scope validation prevents cross-version feedback attachment. |
| 4.5 | Feedback submitted with `review_id` of a review that was soft-deleted | 404: "Review not found" (soft delete) or 410: "Review has been deleted" | No feedback stored. UI should not show deleted reviews in selection. |
| 4.6 | UI shows wrong review's feedback in detail panel (display bug) | N/A (UI rendering issue) | Feedback list must filter by `review_id == currently_displayed_review.id`. Query must include WHERE clause. |
| 4.7 | Feedback submitted to superseded proposal | None (valid — audit log) | Feedback stored successfully. Superseded proposals can receive feedback for audit purposes. |

---

## 5. Old Feedback Incorrectly Injected into New Review

| # | Failure Scenario | Expected Validation Error | Expected System Behaviour |
|---|------------------|---------------------------|---------------------------|
| 5.1 | Injection pulls feedback from NON-active review | Bug — should never happen | System must ONLY query `WHERE review_id = version.active_review_id`. If wrong review injected, it's a critical bug. |
| 5.2 | Feedback added to Review A AFTER Review B was created with A's injection | None (valid timing) | Review B's `injected_feedback` is UNCHANGED. Snapshot is immutable. New feedback only visible on Review A directly. |
| 5.3 | Deleted feedback still appears in injected copy on target review | None (correct behaviour) | Injected data is a snapshot. Source deletion does NOT affect injected copies. This is expected, not a bug. |
| 5.4 | Injection includes feedback from ALL reviews (not just active) | Bug — scope violation | System must filter to active review only. If all reviews' feedback appears, injection query is wrong. |
| 5.5 | Injection includes feedback added after close (`added_after_close: true`) from active review | None (correct — audit log feedback is still feedback) | All feedback on the active review at time of creation is injected, regardless of `added_after_close` flag. |
| 5.6 | `active_review_id` changed between "create review" request and injection execution (race) | Potential inconsistency | Injection must read `active_review_id` atomically within the same transaction as review creation. No TOCTOU gap. |
| 5.7 | Injected feedback array manually modified via API | 400: "injected_feedback is system-managed" | Field is write-once at creation. No update endpoint exists for this field. |
| 5.8 | Large feedback set (500+ items) injected — performance concern | None (valid but slow) | System handles gracefully. Consider: pagination in UI display, but full injection in data layer. |

---

## 6. Wrong Version or Review Shown in Dashboard / Intelligence Tab

| # | Failure Scenario | Expected Validation Error | Expected System Behaviour |
|---|------------------|---------------------------|---------------------------|
| 6.1 | Dashboard shows version from different project | N/A (UI/query bug) | All queries MUST include `WHERE project_id = current_project.id`. Cross-project leakage is a security bug. |
| 6.2 | Intelligence tab shows analysis from previous version (stale cache) | N/A (caching bug) | Intelligence data must be keyed by `version_id`. Cache invalidation on new version creation. |
| 6.3 | Active review indicator shows wrong review after switch (stale UI) | N/A (UI state bug) | UI must re-fetch or optimistically update `active_review_id` after switch. WebSocket/polling if multi-user. |
| 6.4 | Version list shows deleted version | N/A (soft-delete query bug) | Queries must filter `WHERE deleted_at IS NULL` (if soft-delete) or row must not exist (hard-delete). |
| 6.5 | Proposal shows wrong `review_id` attribution ("Based on: [wrong review]") | N/A (display bug) | Proposal stores `review_id` at creation. UI renders review name from this stored ID. If wrong, data layer bug at creation. |
| 6.6 | Dashboard shows `version_number: 0` or negative | N/A (numbering bug) | Version numbers start at 1, auto-increment. DB constraint: `version_number > 0`, unique per project. |
| 6.7 | Intelligence tab shows results for version N but user is viewing version N+1 | N/A (routing/state bug) | Intelligence queries must filter by currently viewed `version_id`. URL params or state must stay in sync. |
| 6.8 | Backward-created version shows original version's reviews in its review panel | N/A (query scope bug) | New version starts with zero reviews. Query: `WHERE version_id = new_version.id` returns empty. Original version's reviews stay on original. |
| 6.9 | Finalised version's content appears editable in UI | N/A (UI guard missing) | UI must check `version.status == 'finalised'` and hide/disable all edit controls. Server rejects mutations regardless. |

---

## 7. Finalise Attempted Before Stop Conditions Are Met

| # | Failure Scenario | Expected Validation Error | Expected System Behaviour |
|---|------------------|---------------------------|---------------------------|
| 7.1 | No proposals exist on version | 400: "No accepted proposal exists for this version" | Finalisation blocked. UI: "Finalise" button disabled, tooltip: "Accept a proposal first". |
| 7.2 | Proposals exist but all are `draft` | 400: "No accepted proposal exists for this version" | Finalisation blocked. Must submit + accept at least one. |
| 7.3 | Proposals exist but all are `rejected` | 400: "No accepted proposal exists for this version" | Finalisation blocked. User must create and accept a new proposal. |
| 7.4 | Proposals exist but all are `superseded` | 400: "No accepted proposal exists for this version" | Finalisation blocked. Only `accepted` status qualifies. |
| 7.5 | One proposal is `submitted` (not yet accepted) | 400: "No accepted proposal exists for this version" | Finalisation blocked. Proposal must be explicitly accepted. |
| 7.6 | Accepted proposal exists but active review is still `pending`/`active` (not closed) | 400: "Active review has not been completed" | Finalisation blocked. All reviews must be closed first. |
| 7.7 | Reviews exist in `pending` state (never started) | 400: "Pending reviews must be completed or removed before finalisation" | User must either complete or delete pending reviews. |
| 7.8 | Unresolved feedback exists, no `confirm` flag | 200 (not error): `{ blocked: true, warning: "N feedback items unresolved", action_required: "confirm" }` | Soft block. UI shows modal. No state change until user confirms. |
| 7.9 | Unresolved feedback exists, `confirm: true` provided | None (proceeds) | Finalisation succeeds. Feedback remains unresolved (persisted for audit). |
| 7.10 | Version is at `draft` phase, user attempts finalise directly | 400: "Invalid transition. Required path: draft → in_review → proposed → finalised" | Phase skipping blocked. Must progress linearly. |
| 7.11 | Version is at `in_review`, user attempts finalise | 400: "Invalid transition. Must reach 'proposed' phase before finalisation" | Phase skipping blocked. |
| 7.12 | Concurrent finalisation: two requests arrive simultaneously | First: succeeds. Second: 200 (idempotent, no state change) | Atomic operation. No double-finalisation. `finalised_at` set once. |
| 7.13 | Finalise after version already finalised | 200: idempotent, no state change | Not an error. Returns current state. No duplicate side effects. |
| 7.14 | Network drops during finalisation (offline scenario) | Operation queued locally | On reconnect: syncs. If server already finalised (by another device): last-write-wins (idempotent, same result). |

---

## Summary Matrix

| Category | Total Cases | Must Fail | Must Succeed | Bug Detection |
|----------|:-----------:|:---------:|:------------:|:-------------:|
| Version without reviews | 6 | 4 | 2 | 0 |
| Multiple reviews without active | 6 | 1 | 4 | 1 |
| Proposal without active review | 5 | 5 | 0 | 0 |
| Feedback linked wrong | 7 | 4 | 2 | 1 |
| Old feedback wrongly injected | 8 | 1 | 3 | 4 |
| Wrong version/review in UI | 9 | 0 | 0 | 9 |
| Finalise before stop conditions | 14 | 8 | 3 | 3 |
| **TOTAL** | **55** | **23** | **14** | **18** |

---

## Key Takeaways

### Critical Validation Gates (MUST block)
1. No proposal without active review
2. No finalisation without accepted proposal
3. No phase skipping
4. No feedback without exactly one parent
5. No injection from non-active reviews

### Silent Bugs to Test For (no error thrown, but wrong behaviour)
1. Injection pulling from wrong review (scope leak)
2. Dashboard showing cross-project data
3. Stale active review indicator after switch
4. Backward-created version inheriting original's reviews in UI
5. Injected feedback retroactively updating after source changes

### Race Conditions to Guard Against
1. Active review deleted between page load and proposal submit
2. Active review switched during injection transaction
3. Concurrent finalisation attempts
4. Two users deleting same active review simultaneously
