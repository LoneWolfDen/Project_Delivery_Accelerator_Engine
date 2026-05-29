# End-to-End Test Plan: Version → Review → Proposal → Feedback Lifecycle

## Design Decisions In Effect

| Decision | Resolution |
|----------|-----------|
| Active review on last deletion | `active_review_id` = null, user prompted to create review |
| Feedback on closed reviews | Append-only audit log, always writable |
| Injection scope | Active review only |
| Proposal v2 while v1 is draft | Auto-supersede |
| Finalisation with unresolved feedback | Soft warning, requires explicit confirm |
| Phase transition backward | Single backward always creates new version at `draft` |
| Offline conflict resolution | Last-write-wins by timestamp |

---

## 1. POSITIVE FLOW (Happy Path)

### HP-01: Full Lifecycle — Single Version, Single Review, Single Proposal

| Step | Action | Expected Outcome | Data Created/Updated |
|------|--------|-------------------|----------------------|
| 1 | Create Project | Project created with `status: active` | `project { id, title, status: active, created_at }` |
| 2 | Create Version 1 | Version created under project | `version { id, project_id, version_number: 1, status: draft, content, created_at }` |
| 3 | Create Review on Version 1 | Review created and auto-assigned as active | `review { id, version_id, status: pending }` + `version.active_review_id = review.id` |
| 4 | Add Feedback to Review | Feedback stored against review | `feedback { id, review_id, content, author, created_at }` |
| 5 | Create Proposal from Version 1 | Proposal created referencing version + active review | `proposal { id, version_id, review_id, proposal_version: 1, status: draft, injected_feedback: [...] }` |
| 6 | Submit Proposal | Status transitions | `proposal.status: draft → submitted` |
| 7 | Accept Proposal | Status transitions | `proposal.status: submitted → accepted` |
| 8 | Finalise Version | Version locked, phase transitions | `version.status: draft → finalised`, all reviews → `closed` |

---

### HP-02: Multiple Reviews with Active Switch

| Step | Action | Expected Outcome | Data Created/Updated |
|------|--------|-------------------|----------------------|
| 1 | Create Version 1 (status: draft) | Version exists | `version { version_number: 1, status: draft }` |
| 2 | Create Review A | Auto-active | `review_a { status: pending }`, `version.active_review_id = review_a.id` |
| 3 | Add 2 feedback items to Review A | Both stored | `feedback_1, feedback_2 { review_id: review_a.id }` |
| 4 | Create Review B | Not active by default | `review_b { status: pending }`, `version.active_review_id` unchanged (still A) |
| 5 | Switch active review to B | Active updates | `version.active_review_id = review_b.id` |
| 6 | Create Review C | Not active | `review_c { status: pending }` |
| 7 | Add feedback to Review B | Stored on B | `feedback_3 { review_id: review_b.id }` |
| 8 | Create Proposal | Injects feedback from B only (active) | `proposal { review_id: review_b.id, injected_feedback: [feedback_3] }` — feedback_1, feedback_2 NOT injected |

---

### HP-03: Feedback Injection Chain

| Step | Action | Expected Outcome | Data Created/Updated |
|------|--------|-------------------|----------------------|
| 1 | Create Version, Create Review 1 (auto-active) | Baseline | `review_1, version.active_review_id = review_1.id` |
| 2 | Add feedback F1, F2 to Review 1 | Stored | `feedback { F1, F2 on review_1 }` |
| 3 | Create Review 2 | Injection occurs from active (Review 1) | `review_2.injected_feedback = [F1, F2]` |
| 4 | Switch active to Review 2 | Active changes | `version.active_review_id = review_2.id` |
| 5 | Add feedback F3 to Review 2 | Stored on Review 2 | `feedback { F3 on review_2 }` |
| 6 | Create Review 3 | Injection from active (Review 2) only | `review_3.injected_feedback = [F3]` — F1, F2 NOT re-injected |

---

### HP-04: Proposal Versioning via Rejection Cycle

| Step | Action | Expected Outcome | Data Created/Updated |
|------|--------|-------------------|----------------------|
| 1 | Create Proposal v1 (from active review) | First proposal | `proposal { proposal_version: 1, status: draft }` |
| 2 | Submit Proposal v1 | Status change | `proposal.status: submitted` |
| 3 | Reject Proposal v1 | Status change | `proposal.status: rejected` |
| 4 | Create Proposal v2 (new active review feedback injected) | New version | `proposal { proposal_version: 2, status: draft }` — v1 remains `rejected` |
| 5 | Submit + Accept Proposal v2 | Clean acceptance | `proposal_v2.status: accepted` |
| 6 | Finalise Version | Success | `version.status: finalised` |

---

### HP-05: Auto-Supersede Draft Proposal

| Step | Action | Expected Outcome | Data Created/Updated |
|------|--------|-------------------|----------------------|
| 1 | Create Proposal v1 (remains draft, not submitted) | Draft exists | `proposal_v1 { status: draft }` |
| 2 | Create Proposal v2 | v1 auto-superseded | `proposal_v1.status: superseded`, `proposal_v2 { proposal_version: 2, status: draft }` |
| 3 | Query superseded proposal | Still retrievable | Returns `proposal_v1` with full data, `status: superseded`, immutable |

---

### HP-06: Backward Phase Transition (New Version at Draft)

| Step | Action | Expected Outcome | Data Created/Updated |
|------|--------|-------------------|----------------------|
| 1 | Version 1 reaches `finalised` | Locked | `version_1 { status: finalised }` |
| 2 | Trigger backward transition on Version 1 | New version spawned | `version_2 { version_number: 2, status: draft, source_version_id: version_1.id, content: cloned }` |
| 3 | Query Version 1 | Still immutable, finalised | No changes to version_1, its reviews, proposals, or feedback |
| 4 | Version 2 progresses independently | Full lifecycle available | Reviews, proposals, feedback all start fresh on version_2 |

---

### HP-07: Finalisation with Soft Warning

| Step | Action | Expected Outcome | Data Created/Updated |
|------|--------|-------------------|----------------------|
| 1 | Version has accepted proposal + 2 unresolved feedback items | Precondition | `feedback_1 { resolved: false }, feedback_2 { resolved: false }` |
| 2 | Attempt finalise WITHOUT confirm flag | Blocked with warning | Response: `{ warning: "2 feedback items unresolved", requires_confirm: true }` — no state change |
| 3 | Attempt finalise WITH `confirm: true` | Succeeds | `version.status: finalised`, feedback remains unresolved (persisted as-is) |

---

### HP-08: Feedback on Closed Review (Audit Log)

| Step | Action | Expected Outcome | Data Created/Updated |
|------|--------|-------------------|----------------------|
| 1 | Finalise version (all reviews → closed) | Reviews closed | `review.status: closed` |
| 2 | Add feedback to closed review | Succeeds (append-only) | `feedback { review_id, content, added_after_close: true, created_at }` |
| 3 | Retrieve review feedback | Includes post-close feedback with metadata | Returns all feedback with `added_after_close` flag where applicable |

---

## 2. NEGATIVE SCENARIOS (Validation Failures)

### NEG-01: Version Creation Failures

| # | Action | Expected Failure | HTTP Status / Error |
|---|--------|------------------|---------------------|
| 1 | Create version with empty title | Validation error | 400: "Title is required" |
| 2 | Create version with null content | Validation error | 400: "Content is required" |
| 3 | Create version referencing non-existent project_id | Reference error | 404: "Project not found" |
| 4 | Create version on finalised project (if project has terminal state) | Business logic error | 409: "Project is archived/closed" |

---

### NEG-02: Review Creation Failures

| # | Action | Expected Failure | HTTP Status / Error |
|---|--------|------------------|---------------------|
| 1 | Create review with no version_id | Validation error | 400: "version_id is required" |
| 2 | Create review referencing non-existent version | Reference error | 404: "Version not found" |
| 3 | Create review on finalised version | Business logic error | 409: "Cannot add reviews to finalised version" |
| 4 | Create review with empty body/criteria | Validation error | 400: "Review content is required" |

---

### NEG-03: Active Review Failures

| # | Action | Expected Failure | HTTP Status / Error |
|---|--------|------------------|---------------------|
| 1 | Set active review to ID from different version | Scope violation | 400: "Review does not belong to this version" |
| 2 | Set active review to non-existent ID | Not found | 404: "Review not found" |
| 3 | Set active review on finalised version | Immutability violation | 409: "Cannot modify finalised version" |
| 4 | Set active review to null explicitly (without deletion) | Validation error | 400: "active_review_id must reference a valid review" |
| 5 | Delete last review → attempt create proposal | Missing precondition | 400: "No active review. Create a review to continue." |

---

### NEG-04: Proposal Creation Failures

| # | Action | Expected Failure | HTTP Status / Error |
|---|--------|------------------|---------------------|
| 1 | Create proposal on version with null active_review | Precondition failure | 400: "No active review set. Create and activate a review first." |
| 2 | Create proposal on version with zero reviews | Precondition failure | 400: "No reviews exist on this version" |
| 3 | Create proposal referencing version from different project | Scope violation | 403: "Cross-project reference not allowed" |
| 4 | Create proposal on finalised version | Immutability violation | 409: "Cannot create proposals on finalised version" |
| 5 | Manually set proposal_version to arbitrary number | Validation error | 400: "proposal_version is auto-generated" |

---

### NEG-05: Feedback Failures

| # | Action | Expected Failure | HTTP Status / Error |
|---|--------|------------------|---------------------|
| 1 | Add feedback with empty content | Validation error | 400: "Feedback content is required" |
| 2 | Add feedback to non-existent review_id | Reference error | 404: "Review not found" |
| 3 | Add feedback referencing both review_id AND proposal_id | Ambiguous parent | 400: "Feedback must reference exactly one parent (review or proposal)" |
| 4 | Add feedback to deleted review | Reference error | 404: "Review not found" (hard delete) or 410: "Review deleted" (soft delete) |

---

### NEG-06: Phase Transition Failures

| # | Action | Expected Failure | HTTP Status / Error |
|---|--------|------------------|---------------------|
| 1 | Transition `draft` → `finalised` (skipping steps) | Invalid transition | 400: "Invalid transition. Required path: draft → in_review → proposed → finalised" |
| 2 | Transition `draft` → `proposed` (skipping in_review) | Invalid transition | 400: "Cannot skip in_review phase" |
| 3 | Finalise version without accepted proposal | Precondition failure | 400: "No accepted proposal exists for this version" |
| 4 | Finalise version with active review still in-progress | Precondition failure | 400: "Active review has not been closed/completed" |
| 5 | Finalise with unresolved feedback, no confirm flag | Soft block | 200 with `{ blocked: true, warning: "N items unresolved", action_required: "confirm" }` |
| 6 | Any mutation after finalisation (edit content, add review, create proposal) | Immutability | 409: "Version is finalised. Trigger backward transition to create new version." |

---

### NEG-07: Offline / Conflict Failures

| # | Action | Expected Failure | HTTP Status / Error |
|---|--------|------------------|---------------------|
| 1 | Sync with device clock significantly in the future | Last-write-wins applies but: | Log warning about clock skew; accept write |
| 2 | Sync delete + sync edit on same entity (delete is later) | Entity deleted | Delete wins, edit discarded |
| 3 | Two offline creates of same logical entity (no ID collision) | Both persist | Both get unique IDs, both are valid |

---

## 3. DATA CONSISTENCY CHECKS

### DC-01: Referential Integrity

| # | Check | Expected State |
|---|-------|----------------|
| 1 | Every `review.version_id` points to existing version | No orphaned reviews |
| 2 | `version.active_review_id` is either null or points to a review with matching `version_id` | No cross-version active references |
| 3 | Every `proposal.version_id` + `proposal.review_id` belong to same version | Proposal never references review from different version |
| 4 | Every `feedback.review_id` OR `feedback.proposal_id` points to existing entity | No orphaned feedback |
| 5 | `version.source_version_id` (on backward-created versions) points to existing finalised version | Provenance chain intact |

---

### DC-02: State Machine Integrity

| # | Check | Expected State |
|---|-------|----------------|
| 1 | No version has `status: finalised` without at least one `proposal.status: accepted` | Finalisation precondition always met |
| 2 | No version has `status: finalised` with any review in `pending` or `active` (not `closed`) | All reviews closed on finalisation |
| 3 | Only ONE `active_review_id` per version at any time | No dual-active state |
| 4 | `proposal_version` numbers are sequential per version with no gaps (except deleted) | 1, 2, 3... never 1, 3 |
| 5 | All proposals with `status: superseded` have a later proposal_version in `draft`/`submitted`/`accepted` | Supersede always has successor |
| 6 | Finalised versions have zero mutations after `finalised_at` timestamp | Immutability verified by audit log |

---

### DC-03: Injection Snapshot Integrity

| # | Check | Expected State |
|---|-------|----------------|
| 1 | `review.injected_feedback` content matches feedback state AT TIME of review creation | Point-in-time snapshot, not live reference |
| 2 | Adding feedback to Review A after Review B was created (with A's injection) does NOT alter B's `injected_feedback` | Immutable snapshot confirmed |
| 3 | Deleting feedback from source review does NOT remove it from injected copy | Injected data is independent |
| 4 | `proposal.injected_feedback` matches active review's feedback at proposal creation time | Same snapshot rule applies to proposals |

---

### DC-04: Version Numbering Integrity

| # | Check | Expected State |
|---|-------|----------------|
| 1 | No two versions in same project have same `version_number` | Unique within project |
| 2 | Version numbers are monotonically increasing | Never decreasing |
| 3 | Backward-transition-created versions get next sequential number | version_number = max(existing) + 1 |
| 4 | Deleted version numbers are never recycled | If v2 deleted, next is v3 not v2 |

---

### DC-05: Timestamp Consistency

| # | Check | Expected State |
|---|-------|----------------|
| 1 | `created_at` never changes after entity creation | Immutable |
| 2 | `updated_at` >= `created_at` always | Logical ordering |
| 3 | `finalised_at` is set only when status = `finalised` | Not prematurely set |
| 4 | Child entities have `created_at` >= parent `created_at` | Review created after version, feedback after review |
| 5 | Proposal's `created_at` >= its referenced review's `created_at` | Temporal ordering respected |

---

### DC-06: Auto-Supersede Consistency

| # | Check | Expected State |
|---|-------|----------------|
| 1 | At most ONE proposal with `status: draft` per version at any time | Auto-supersede enforces this |
| 2 | All superseded proposals have `superseded_at` timestamp | Audit trail |
| 3 | Superseded proposals are fully immutable | No field changes after supersession |
| 4 | `submitted` proposals are NOT superseded by new draft creation | Only drafts are auto-superseded |

---

## 4. UI BEHAVIOUR VALIDATION

### UI-01: Version Management Screen

| # | Scenario | Expected UI Behaviour |
|---|----------|----------------------|
| 1 | Version list for project | Displays versions ordered by `version_number` descending. Shows status badge (draft/in_review/proposed/finalised) |
| 2 | Finalised version row | Greyed out or marked with lock icon. No "Edit" or "Add Review" buttons visible |
| 3 | Version with `source_version_id` set | Shows "Created from Version N" lineage indicator |
| 4 | Empty project (no versions) | Shows empty state: "No versions yet. Create your first version to get started." |
| 5 | "Go Back" / backward transition button | Only visible on non-draft versions. Labelled: "Revise (creates new version)" with confirmation dialog |

---

### UI-02: Review Management

| # | Scenario | Expected UI Behaviour |
|---|----------|----------------------|
| 1 | Review list on version | Shows all reviews. Active review highlighted/badged. Others are visually subordinate |
| 2 | "Set as Active" button | Visible on non-active reviews. Disabled/hidden on already-active review |
| 3 | Delete active review (last one) | Confirmation dialog: "This is the only review. Deleting it will clear the active review." After deletion: message "No reviews available. Create a review to continue." |
| 4 | Injected feedback section on review | Read-only block at top of review, visually distinct (e.g., grey background, italic). Labelled "Feedback from previous review" |
| 5 | Closed review | All fields read-only EXCEPT feedback input (append-only). Visual indicator: "Closed — feedback still accepted" |
| 6 | Create review on finalised version | "Add Review" button not rendered or disabled with tooltip: "Version is finalised" |

---

### UI-03: Active Review Indicator

| # | Scenario | Expected UI Behaviour |
|---|----------|----------------------|
| 1 | Version has active review | Active review name/title shown prominently on version detail page |
| 2 | Version has null active review | Warning banner: "No active review. Create or select a review to continue." |
| 3 | Switching active review | Instant UI update. Previous active loses highlight, new one gains it. No page reload needed (optimistic update) |
| 4 | Active switch while proposal exists (draft) | Confirmation dialog: "Changing active review will not affect existing proposals. Continue?" |

---

### UI-04: Proposal Management

| # | Scenario | Expected UI Behaviour |
|---|----------|----------------------|
| 1 | Create proposal button | Disabled if `active_review_id` is null. Tooltip: "Set an active review first" |
| 2 | Proposal shows source review | Displays: "Based on: [Review Name]" with link to that review |
| 3 | Draft proposal exists, user creates another | No prompt needed (auto-supersede is silent). Old proposal shows "Superseded" badge in list |
| 4 | Proposal version history | Expandable list showing v1, v2, v3... with status badges and creation dates |
| 5 | Accepted proposal | Highlighted in green. "Finalise Version" button becomes enabled |
| 6 | Rejected proposal | Shown with red badge. "Create New Proposal" button appears prominently |

---

### UI-05: Feedback Interface

| # | Scenario | Expected UI Behaviour |
|---|----------|----------------------|
| 1 | Add feedback form | Text input + submit. Author auto-populated from session. Category/tag selector if applicable |
| 2 | Feedback list on review | Chronological order. Each item shows content, author, timestamp |
| 3 | Feedback on closed review | Input field still present. Label: "Add follow-up note (audit log)" |
| 4 | Unresolved feedback indicator | Count badge on version/review showing unresolved items |
| 5 | Feedback exceeding length limit (if defined) | Character counter. Blocks submit at limit with: "Exceeds maximum length" |
| 6 | Injected feedback (read-only) | Visually separated from native feedback. Cannot be edited or deleted. Source attribution shown |

---

### UI-06: Finalisation Flow

| # | Scenario | Expected UI Behaviour |
|---|----------|----------------------|
| 1 | "Finalise" button availability | Only enabled when: version has accepted proposal AND no active in-progress reviews |
| 2 | Click finalise with unresolved feedback | Modal: "Warning: 3 feedback items remain unresolved. Finalise anyway?" with [Cancel] [Confirm Finalise] buttons |
| 3 | Click finalise with no unresolved feedback | Direct confirmation: "Finalise this version? This action cannot be undone." with [Cancel] [Finalise] |
| 4 | After finalisation | Page transitions to read-only view. All edit controls hidden. Success banner: "Version finalised successfully" |
| 5 | "Revise" button on finalised version | Prominent button: "Create Revision" → confirmation dialog explaining new version will be created at draft |

---

### UI-07: Phase Transition Indicators

| # | Scenario | Expected UI Behaviour |
|---|----------|----------------------|
| 1 | Phase progress bar/stepper | Visual stepper: `draft` → `in_review` → `proposed` → `finalised`. Current phase highlighted |
| 2 | Forward transition available | "Next Phase" or contextual button (e.g., "Start Review" for draft→in_review) |
| 3 | Forward transition blocked (missing precondition) | Button disabled. Tooltip explains why: "Add a review to proceed" or "Accept a proposal to finalise" |
| 4 | Backward transition | Separate button/link: "Go back to draft (new version)". Clearly communicates consequence |
| 5 | Linear progression enforcement | No ability to click/jump to non-adjacent phases in the stepper |

---

### UI-08: Offline Behaviour

| # | Scenario | Expected UI Behaviour |
|---|----------|----------------------|
| 1 | User goes offline | Subtle indicator: "Offline — changes will sync when reconnected" (banner or icon) |
| 2 | User makes edits offline | All CRUD operations work locally. Queue indicator: "3 changes pending sync" |
| 3 | User comes back online | Auto-sync begins. Progress indicator. Success: "All changes synced" |
| 4 | Conflict resolved (last-write-wins) | No user prompt. Silently resolved. Optional: "1 conflict auto-resolved" in activity log |
| 5 | Failed sync (server error) | Retry with backoff. User message: "Sync failed. Retrying..." with manual retry button |

---

## Summary Matrix

| Category | Total Scenarios | Must Pass | Must Fail | Data Checks |
|----------|---------------:|:---------:|:---------:|:-----------:|
| Positive Flow (HP) | 8 flows, ~50 steps | All | — | All create/update assertions |
| Negative (NEG) | 27 cases | — | All | No data mutation on failure |
| Data Consistency (DC) | 24 checks | All | — | Query-based verification |
| UI Behaviour (UI) | 42 scenarios | All | — | Visual state assertions |

---

## Test Dependencies and Execution Order

```
Phase 1: Foundation
  └─ HP-01 (full happy path) — validates core wiring end-to-end

Phase 2: Branching Paths
  ├─ HP-02 (multiple reviews)
  ├─ HP-03 (injection chain)
  └─ HP-04 (proposal versioning)

Phase 3: Edge Mechanics
  ├─ HP-05 (auto-supersede)
  ├─ HP-06 (backward transition)
  ├─ HP-07 (soft warning finalisation)
  └─ HP-08 (post-close feedback)

Phase 4: Failure Boundaries
  ├─ NEG-01 through NEG-07 (all negative cases)
  └─ Run AFTER positive paths confirm baseline works

Phase 5: Consistency Audit
  ├─ DC-01 through DC-06
  └─ Run against database state AFTER Phase 1-3 data exists

Phase 6: UI Validation
  ├─ UI-01 through UI-08
  └─ Can run in parallel with Phase 4-5 (separate concern)
```

---

## State Machines Reference

### Version Status
```
draft → in_review → proposed → finalised
                                    ↓
                    (backward = new version created at draft)
```

### Proposal Status
```
draft → submitted → accepted
  ↓                    ↓
superseded          (triggers finalisation eligibility)

draft → submitted → rejected
                       ↓
                    (user creates new proposal → new draft, old stays rejected)
```

### Review Status
```
pending → active → closed
                     ↓
            (feedback still appendable as audit log)
```
