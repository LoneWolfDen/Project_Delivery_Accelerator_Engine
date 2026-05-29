# Step-by-Step Flow Validation

## Flow Overview

```
Ingest → Build Intelligence → Create Version → Reviews → Active Review → Proposal → Feedback → Inject → Next Proposal → Finalise
```

---

## STEP 1: Ingest → Build Intelligence → Create Version

### Expected Behaviour

| Aspect | Detail |
|--------|--------|
| Trigger | User uploads/inputs a deliverable (document, spec, artifact) |
| Ingest | System parses and stores raw content. Creates an artifact/document record |
| Build Intelligence | System analyses content (AI backend processes, extracts structure, identifies sections) |
| Create Version | Version record created linking to project + processed content |

### Data Created/Updated

| Entity | Fields | State |
|--------|--------|-------|
| `artifact` / `document` | `{ id, raw_content, file_type, ingested_at }` | Persisted |
| `intelligence` (if modelled) | `{ id, artifact_id, analysis_result, processed_at }` | Derived from ingest |
| `version` | `{ id, project_id, version_number: N, status: "draft", content: processed_content, source_version_id: null, created_at, updated_at }` | New record |
| `project` | `{ updated_at }` | Timestamp bumped |

### UI Should Show

- Upload/ingest progress indicator
- Intelligence processing status (e.g., "Analysing document...")
- On completion: Version card appears in project view with status badge `DRAFT`
- Version number displayed (auto-incremented)
- Content preview available
- Empty states: "No reviews yet" in the review panel

### What Should Fail

| Failure Case | Expected Error |
|--------------|----------------|
| Ingest with empty/corrupt file | 400: "Unable to process file. Check format and try again." |
| Ingest with unsupported file type | 400: "File type not supported" |
| Intelligence processing timeout | 500 with retry: "Processing failed. Retry?" (offline-first: queue for retry) |
| Create version on non-existent project | 404: "Project not found" |
| Create version on archived/closed project | 409: "Project is not active" |
| Duplicate ingest of identical content | Define: allow (new version) or warn "Identical to version N"? |

### Dependencies

| Dependency | Required State |
|------------|---------------|
| Project must exist | `project.status: active` |
| Ingest must succeed | Artifact stored before intelligence runs |
| Intelligence must complete | Processed content available before version creation |
| Version numbering | `max(version_number) + 1` for this project |

### Validation Rules

- `version.content` must NOT be null/empty after intelligence processing
- `version.version_number` must be unique within project scope
- `version.status` must start at `draft` (no other initial state allowed)
- If this version was created from backward transition: `source_version_id` must reference a valid, finalised version

---

## STEP 2: Run Multiple Reviews Under One Version

### Expected Behaviour

| Aspect | Detail |
|--------|--------|
| Trigger | User (or system/persona) initiates a review on the version |
| First review | Created AND automatically set as active review |
| Subsequent reviews | Created but do NOT change active review |
| Each review | Independent content, criteria, and feedback space |
| Reviews run concurrently | No ordering dependency between reviews |

### Data Created/Updated

| Entity | Fields | State |
|--------|--------|-------|
| `review` (first) | `{ id, version_id, status: "pending", content, criteria, injected_feedback: [...], created_at }` | New + auto-active |
| `version` | `{ active_review_id: review_1.id, updated_at }` | Updated (first review only) |
| `review` (2nd, 3rd...) | `{ id, version_id, status: "pending", content, criteria, injected_feedback: [...], created_at }` | New, NOT active |

### UI Should Show

- Review panel on version detail page shows list of all reviews
- First review: highlighted with "Active" badge
- Subsequent reviews: shown without active badge
- Each review card shows: title/criteria, status badge, feedback count
- "Add Review" button visible (disabled if version is finalised)
- Active review indicator prominent at top of version detail

### What Should Fail

| Failure Case | Expected Error |
|--------------|----------------|
| Create review on non-existent version | 404: "Version not found" |
| Create review on finalised version | 409: "Cannot add reviews to finalised version" |
| Create review with empty content/criteria | 400: "Review content is required" |
| Create review with version_id from different project (if cross-project ref attempted) | 403: "Scope violation" |

### Dependencies

| Dependency | Required State |
|------------|---------------|
| Version must exist | `version.status != finalised` |
| Version must belong to active project | `project.status: active` |
| For injection: active review must exist OR be null | If active exists, its feedback is injected into new review |

### Validation Rules

- Review count per version: unlimited (but paginated in UI)
- Each review has unique ID within system
- `review.version_id` must match an existing, non-finalised version
- `review.injected_feedback` is populated at creation time and NEVER updated after
- First review on a version with `active_review_id: null` MUST auto-set active

---

## STEP 3: Set Active Review

### Expected Behaviour

| Aspect | Detail |
|--------|--------|
| Trigger | User explicitly selects a different review as active |
| Effect | `version.active_review_id` changes to selected review |
| Previous active | No status change (remains in whatever status it was) |
| Idempotent | Setting already-active review as active = no-op, 200 OK |
| Impact on existing proposals | NONE — proposals snapshot their review reference at creation |

### Data Created/Updated

| Entity | Fields | State |
|--------|--------|-------|
| `version` | `{ active_review_id: new_review.id, updated_at }` | Updated |

No new entities created. No other entities modified.

### UI Should Show

- Previous active review loses highlight/"Active" badge
- Newly selected review gains "Active" badge
- Optimistic update (instant, no page reload)
- If switching while a draft proposal exists: confirmation dialog "Changing active review will not affect existing proposals. Continue?"
- Version detail header updates to show new active review name/title

### What Should Fail

| Failure Case | Expected Error |
|--------------|----------------|
| Set active to review from DIFFERENT version | 400: "Review does not belong to this version" |
| Set active to non-existent review ID | 404: "Review not found" |
| Set active on finalised version | 409: "Cannot modify finalised version" |
| Set active to null explicitly | 400: "active_review_id must reference a valid review" |
| Set active to deleted review | 404: "Review not found" |

### Dependencies

| Dependency | Required State |
|------------|---------------|
| Target review must exist | `review.id` valid |
| Target review must belong to same version | `review.version_id == version.id` |
| Version must not be finalised | `version.status != finalised` |

### Validation Rules

- Only ONE active review per version at any time (enforced at DB level)
- Active review switch is atomic (no intermediate state where two are active)
- Switch does NOT invalidate or alter any existing proposals
- Switch does NOT retroactively change injected feedback in any existing review

---

## STEP 4: Generate Proposal from Version + Active Review

### Expected Behaviour

| Aspect | Detail |
|--------|--------|
| Trigger | User requests proposal generation |
| Precondition | Version has an active review (`active_review_id != null`) |
| Creation | System generates proposal content using version content + active review analysis |
| Snapshot | Proposal locks references to `version_id` + `review_id` at creation time |
| Feedback injection | Active review's feedback is snapshot into `proposal.injected_feedback` |
| Auto-supersede | If a `draft` proposal already exists on this version, it becomes `superseded` |

### Data Created/Updated

| Entity | Fields | State |
|--------|--------|-------|
| `proposal` (new) | `{ id, version_id, review_id: active_review.id, proposal_version: N, status: "draft", content: generated, injected_feedback: [...], created_at }` | New |
| `proposal` (existing draft, if any) | `{ status: "superseded", superseded_at: now, updated_at }` | Updated |

### UI Should Show

- "Generate Proposal" button enabled (only when active review exists)
- Generation progress indicator (AI processing)
- On completion: new proposal card appears with `DRAFT` badge and `v{N}` label
- Shows "Based on: [Active Review Name]" attribution
- If previous draft was superseded: that card now shows "Superseded" badge (grey)
- Proposal content displayed in editor (editable while draft)

### What Should Fail

| Failure Case | Expected Error |
|--------------|----------------|
| Generate proposal with no active review | 400: "No active review set. Create and activate a review first." |
| Generate proposal with zero reviews on version | 400: "No reviews exist on this version" |
| Generate proposal on finalised version | 409: "Cannot create proposals on finalised version" |
| Generate proposal referencing different project's version | 403: "Cross-project reference not allowed" |
| Manually set `proposal_version` | 400: "proposal_version is auto-generated" |

### Dependencies

| Dependency | Required State |
|------------|---------------|
| `version.active_review_id` | Must be non-null |
| Active review must have been processed | Review content/criteria available |
| Version must not be finalised | `version.status != finalised` |
| Proposal versioning | `max(proposal_version for version_id) + 1` |
| Auto-supersede check | Query for existing `status: draft` proposals on this version |

### Validation Rules

- `proposal.review_id` MUST match `version.active_review_id` at time of creation (snapshot)
- `proposal.version_id` MUST match a non-finalised version
- `proposal.proposal_version` is system-generated, monotonically increasing, never recycled
- At most ONE `draft` proposal per version after creation (enforced by auto-supersede)
- `proposal.injected_feedback` is immutable after creation

---

## STEP 5: Capture Feedback

### Expected Behaviour

| Aspect | Detail |
|--------|--------|
| Trigger | User adds feedback to a review OR proposal |
| Target | Exactly ONE parent: either `review_id` or `proposal_id` |
| Closed reviews | Feedback still accepted (append-only audit log) |
| Storage | Feedback persisted with content, author, timestamp, optional category |
| Resolution tracking | Feedback has `resolved: boolean` field for finalisation checks |

### Data Created/Updated

| Entity | Fields | State |
|--------|--------|-------|
| `feedback` | `{ id, review_id OR proposal_id, content, author, resolved: false, added_after_close: bool, category: optional, created_at }` | New |
| `review` or `proposal` (parent) | `{ updated_at }` | Timestamp bumped |

### UI Should Show

- Feedback input form on review/proposal detail page
- Author auto-populated from session
- Submit button creates feedback immediately (optimistic update)
- Feedback list: chronological order, shows content, author, timestamp
- Each feedback item has "Resolve" toggle
- On closed review: input still present, labelled "Add follow-up note (audit log)"
- Unresolved count badge visible on review/version cards

### What Should Fail

| Failure Case | Expected Error |
|--------------|----------------|
| Empty feedback content | 400: "Feedback content is required" |
| Feedback to non-existent review | 404: "Review not found" |
| Feedback to non-existent proposal | 404: "Proposal not found" |
| Feedback referencing BOTH review_id AND proposal_id | 400: "Feedback must reference exactly one parent" |
| Feedback with no parent reference | 400: "Either review_id or proposal_id is required" |
| Feedback to deleted (hard-deleted) review | 404: "Review not found" |

### Dependencies

| Dependency | Required State |
|------------|---------------|
| Parent entity must exist | Review or Proposal with valid ID |
| No status restriction on parent | Feedback allowed on any status (including closed) |
| Author context | Session/user must be identifiable |

### Validation Rules

- Feedback content must be non-empty string
- Feedback must reference exactly ONE parent (XOR constraint)
- `added_after_close` is system-derived: `true` if `review.status == closed` at feedback creation time
- `resolved` defaults to `false`
- Feedback is append-only: can be resolved/unresolved but content is immutable after creation

---

## STEP 6: Inject Feedback into Next Review

### Expected Behaviour

| Aspect | Detail |
|--------|--------|
| Trigger | Automatic — occurs when a NEW review is created on a version that has an active review |
| Source | ALL feedback from the CURRENT `active_review` at the moment of new review creation |
| Mechanism | System queries `feedback WHERE review_id = version.active_review_id`, snapshots into `review.injected_feedback` |
| Immutability | Injected feedback is frozen at creation time. Never updated retroactively. |
| Scope | Active review ONLY. Non-active reviews' feedback is excluded. |

### Data Created/Updated

| Entity | Fields | State |
|--------|--------|-------|
| `review` (new) | `{ injected_feedback: [snapshot of active review's feedback] }` | Set at creation |

No existing entities are modified by this step. This is a read-from-active + write-to-new operation.

### UI Should Show

- On new review detail page: "Feedback from previous review" section at top
- Visually distinct: grey/muted background, italic text, or collapsible panel
- Read-only (no edit/delete controls on injected items)
- Each injected item shows: original content, original author, original timestamp, source review name
- If active review had zero feedback: section hidden or shows "No prior feedback"
- Clear separation between injected (historical) and native (new) feedback

### What Should Fail

| Failure Case | Expected Error |
|--------------|----------------|
| Attempt to edit injected feedback | UI: controls not rendered. API: 403 "Injected feedback is read-only" |
| Attempt to delete injected feedback | UI: no delete button. API: 403 "Injected feedback cannot be deleted" |
| Manual override of injected_feedback field via API | 400: "injected_feedback is system-managed" |
| Injection from non-active review | Architecturally prevented: system only reads from `version.active_review_id` |
| Injection from review on different version | Architecturally prevented: active_review_id is scoped to version |

### Dependencies

| Dependency | Required State |
|------------|---------------|
| `version.active_review_id` | Can be null (injection produces empty array) or valid review ID |
| Active review's feedback | Queried at point-in-time of new review creation |
| New review creation | This step is PART OF review creation (Step 2), not a separate action |

### Validation Rules

- `injected_feedback` array is written ONCE at review creation. Never appended to.
- Feedback added to source review AFTER injection does NOT appear in target review
- Deleting feedback from source review does NOT remove from injected copy
- If `active_review_id` is null at time of new review creation: `injected_feedback = []`
- Injection cannot cross version boundaries
- No circular injection possible (review cannot inject from itself)

---

## STEP 7: Create Next Proposal Version

### Expected Behaviour

| Aspect | Detail |
|--------|--------|
| Trigger | User requests new proposal after previous was rejected/superseded, or after new review + feedback cycle |
| Version number | Auto-incremented: `max(proposal_version for this version_id) + 1` |
| Active review snapshot | New proposal captures CURRENT active review (may differ from previous proposal's review) |
| Auto-supersede | Any existing `draft` proposal on this version → `superseded` |
| Traceability | New proposal records which review it was built from |

### Data Created/Updated

| Entity | Fields | State |
|--------|--------|-------|
| `proposal` (new) | `{ id, version_id, review_id: current_active, proposal_version: N+1, status: "draft", content, injected_feedback: [...], created_at }` | New |
| `proposal` (prev draft, if any) | `{ status: "superseded", superseded_at: now, updated_at }` | Updated |

### UI Should Show

- Proposal history list shows all versions: v1 (rejected/superseded), v2 (superseded), v3 (draft)
- Status badges: Rejected (red), Superseded (grey), Draft (blue), Submitted (yellow), Accepted (green)
- Latest/active proposal at top or highlighted
- "Based on: [Review Name]" for each proposal — allows tracking which review informed which proposal
- Proposal content diff view (optional): compare v2 to v1

### What Should Fail

| Failure Case | Expected Error |
|--------------|----------------|
| Create proposal when active_review_id is null | 400: "No active review set" |
| Create proposal on finalised version | 409: "Cannot create proposals on finalised version" |
| Manually set proposal_version | 400: "proposal_version is auto-generated" |
| Create proposal_version 3 when v1 and v2 don't exist (gap) | Impossible — system auto-increments. If attempted via API manipulation: 400 |
| Create proposal on version from different project | 403: "Cross-project reference not allowed" |

### Dependencies

| Dependency | Required State |
|------------|---------------|
| Previous proposal cycle | Not strictly required (v1 doesn't need v0) but typical flow is: reject → feedback → new review → new proposal |
| Active review exists | `version.active_review_id != null` |
| Version not finalised | `version.status != finalised` |
| Auto-supersede query | System checks for `proposals WHERE version_id = X AND status = 'draft'` |

### Validation Rules

- Proposal version numbers never recycle (deleted v2 → next is still v3)
- At most ONE `draft` proposal per version at any time
- `submitted` and `rejected` proposals are NOT auto-superseded (only `draft`)
- Each proposal is independently immutable once status leaves `draft`
- `proposal.review_id` is a point-in-time snapshot — changing active review later doesn't affect existing proposals

---

## STEP 8: Finalise and Move Phase

### Expected Behaviour

| Aspect | Detail |
|--------|--------|
| Trigger | User clicks "Finalise" on a version with an accepted proposal |
| Preconditions | (1) At least one `proposal.status: accepted` exists (2) No active in-progress reviews (3) Soft warning if unresolved feedback |
| Phase transition | `version.status: proposed → finalised` (or from current valid state via linear progression) |
| Side effects | All reviews on this version → `status: closed`. Version becomes immutable. |
| Backward option | After finalisation, user can trigger backward transition → spawns new version at `draft` |

### Data Created/Updated

| Entity | Fields | State |
|--------|--------|-------|
| `version` | `{ status: "finalised", finalised_at: now, finalised_by: user, updated_at }` | Updated |
| All `reviews` on version | `{ status: "closed", updated_at }` | Updated (batch) |
| `project` (optional) | `{ current_phase: updated, updated_at }` | If project tracks phase |

On backward transition (separate action AFTER finalisation):

| Entity | Fields | State |
|--------|--------|-------|
| `version` (new) | `{ id, project_id, version_number: N+1, status: "draft", content: cloned, source_version_id: finalised_version.id, created_at }` | New |
| Original version | UNCHANGED | Immutable |

### UI Should Show

**Finalisation flow:**
- "Finalise" button enabled only when: accepted proposal exists AND no in-progress reviews
- If unresolved feedback: modal warning "N feedback items remain unresolved. Finalise anyway?" with [Cancel] / [Confirm Finalise]
- If no unresolved feedback: simple confirmation "Finalise this version? This cannot be undone." with [Cancel] / [Finalise]
- After finalisation: page transitions to read-only view. All edit controls removed. Lock icon. Success banner.
- Phase stepper updates to show `FINALISED` as current

**Post-finalisation:**
- "Create Revision" button appears (backward transition)
- All review cards show "Closed" badge
- Feedback input on closed reviews still visible (audit log)
- No "Add Review", "Generate Proposal", or "Edit" buttons

**Backward transition:**
- Confirmation: "This will create a new version (v{N+1}) at Draft. The current version will remain finalised and unchanged."
- On confirm: navigates to new version detail page (status: Draft, empty reviews)

### What Should Fail

| Failure Case | Expected Error |
|--------------|----------------|
| Finalise without accepted proposal | 400: "No accepted proposal exists for this version" |
| Finalise with in-progress active review | 400: "Active review has not been completed" |
| Finalise with unresolved feedback, no `confirm` flag | 200: `{ blocked: true, warning: "N items unresolved", action_required: "confirm" }` |
| Skip phases: `draft` → `finalised` directly | 400: "Invalid transition. Required path: draft → in_review → proposed → finalised" |
| Any mutation after finalisation | 409: "Version is finalised. Use backward transition to create new version." |
| Un-finalise (revert without new version) | 400: "Cannot revert finalisation. Use 'Create Revision' instead." |
| Finalise same version twice | Idempotent: 200 OK, no state change |
| Concurrent finalisation (race) | First succeeds, second returns 200 (idempotent) or 409 |

### Dependencies

| Dependency | Required State |
|------------|---------------|
| Accepted proposal | At least one `proposal.status: accepted` on this version |
| Reviews completed | No review in `pending` or `active` state (all must be `closed` or system auto-closes) |
| Linear phase progression | Version must be at `proposed` phase (or system must validate it can reach `finalised` from current) |
| Soft warning check | Query `feedback WHERE review_id IN (version's reviews) AND resolved = false` |

### Validation Rules

- Finalisation is ONE-WAY. No undo without creating new version.
- `finalised_at` timestamp is set exactly once
- All reviews batch-closed atomically with version finalisation
- Feedback added to closed reviews post-finalisation: allowed (audit log)
- New proposals on finalised version: blocked
- New reviews on finalised version: blocked
- Content edits on finalised version: blocked
- Backward transition creates clean slate: no reviews, no proposals, no feedback carried over (only content cloned)

---

## Cross-Step Dependency Map

```
Step 1 ──────────────────────────────────────────────────────────────────────
  │ Creates: version (draft)
  │ Requires: project (active)
  ▼
Step 2 ──────────────────────────────────────────────────────────────────────
  │ Creates: reviews (pending), sets first as active
  │ Requires: version (non-finalised)
  │ Triggers: Step 6 (injection) automatically on review creation
  ▼
Step 3 ──────────────────────────────────────────────────────────────────────
  │ Updates: version.active_review_id
  │ Requires: reviews exist on version, version non-finalised
  ▼
Step 4 ──────────────────────────────────────────────────────────────────────
  │ Creates: proposal (draft)
  │ Requires: active_review_id != null, version non-finalised
  │ May trigger: auto-supersede of existing draft proposal
  ▼
Step 5 ──────────────────────────────────────────────────────────────────────
  │ Creates: feedback on review or proposal
  │ Requires: parent entity exists (no status restriction)
  ▼
Step 6 ──────────────────────────────────────────────────────────────────────
  │ Modifies: new review's injected_feedback field (at creation time)
  │ Requires: Step 2 triggered (new review creation)
  │ Reads from: active review's feedback (Step 5 data)
  ▼
Step 7 ──────────────────────────────────────────────────────────────────────
  │ Creates: new proposal version
  │ Requires: active_review_id != null, version non-finalised
  │ Typical flow: after Step 5 + Step 6 cycle
  ▼
Step 8 ──────────────────────────────────────────────────────────────────────
  │ Updates: version (finalised), reviews (closed)
  │ Requires: accepted proposal, no in-progress reviews
  │ Optionally creates: new version (backward transition)
```

---

## Critical Invariants (Must NEVER Be Violated)

| # | Invariant | Enforcement |
|---|-----------|-------------|
| 1 | Finalised version is immutable | All write endpoints check `version.status != finalised` |
| 2 | Only one active review per version | DB constraint or application-level atomic swap |
| 3 | Only one draft proposal per version | Auto-supersede on creation |
| 4 | Injected feedback is immutable after review creation | No update endpoint for `injected_feedback` field |
| 5 | Proposal version numbers never recycle | `MAX() + 1`, tombstone deleted versions |
| 6 | Phase transitions are linear forward | State machine validation on every transition |
| 7 | Backward transition always creates new version | No in-place phase regression |
| 8 | Feedback is always appendable (audit log) | No status check on parent for feedback creation |
| 9 | Proposals snapshot their review reference | `proposal.review_id` set once at creation, never updated |
| 10 | Version numbers are unique within project | DB unique constraint on `(project_id, version_number)` |
