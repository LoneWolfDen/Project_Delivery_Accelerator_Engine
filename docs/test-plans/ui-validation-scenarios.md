# UI Validation Scenarios

> Format: UI Area → Action → Expected Result → What Should Fail

---

## 1. VERSION DROPDOWN

| # | Action | Expected Result | What Should Fail |
|---|--------|-----------------|------------------|
| 1.1 | Open version dropdown on any page | Shows ALL versions for current project, ordered by `version_number` descending | Versions from other projects must NOT appear |
| 1.2 | Version dropdown with finalised versions | Finalised versions shown with lock icon / "Finalised" badge | Finalised versions must NOT be hidden (they're read-only, not invisible) |
| 1.3 | Create new version, then open dropdown | New version appears immediately at top of list | Stale list without new version = caching bug |
| 1.4 | Backward transition creates Version N+1 | Dropdown shows new version at top with "(from Version N)" label | Missing lineage indicator = display bug |
| 1.5 | Select different version from dropdown | Entire page context switches: reviews, proposals, feedback all reload for selected version | Previous version's data still showing = state leak |
| 1.6 | Version dropdown on project with 1 version | Dropdown functional (not hidden). Single item selectable. | Dropdown hidden or disabled when only 1 version = UX bug |
| 1.7 | Version dropdown after version deletion (soft) | Deleted version NOT shown in dropdown | Deleted version still selectable = query missing filter |

---

## 2. REVIEW DROPDOWN (Filters by Version)

| # | Action | Expected Result | What Should Fail |
|---|--------|-----------------|------------------|
| 2.1 | Select Version 1 → open review dropdown | Shows ONLY reviews where `review.version_id == Version 1` | Reviews from Version 2 appearing = missing WHERE clause |
| 2.2 | Switch from Version 1 to Version 2 | Review dropdown clears and repopulates with Version 2's reviews | Version 1's reviews still in dropdown = stale state |
| 2.3 | Active review highlighted in dropdown | Active review has distinct indicator (star, bold, "Active" tag) | No visual distinction between active and non-active = UX failure |
| 2.4 | Version with zero reviews | Dropdown empty or shows placeholder: "No reviews. Create one to begin." | Dropdown shows reviews from previous version selection = state leak |
| 2.5 | Version with null `active_review_id` (all deleted) | No review pre-selected. Warning: "No active review set." | Random review auto-selected despite no active = incorrect default |
| 2.6 | Create review on current version | New review appears in dropdown immediately | Requires page refresh to see new review = missing reactive update |
| 2.7 | Delete active review | Dropdown updates: review removed, no item selected, warning shown | Deleted review still showing as selected = stale reference |
| 2.8 | Select non-active review from dropdown | Content panels update to show selected review's data | Dashboard/intelligence still showing active review's data = selection ignored |

---

## 3. DASHBOARD UPDATES ON VERSION/REVIEW CHANGE

| # | Action | Expected Result | What Should Fail |
|---|--------|-----------------|------------------|
| 3.1 | Switch version in dropdown | Dashboard metrics refresh: review count, feedback count, proposal status, phase indicator all reflect new version | Any metric showing old version's data = partial refresh bug |
| 3.2 | Switch active review | Dashboard "Active Review" card updates: title, status, feedback count | Stale active review card = subscription/binding failure |
| 3.3 | Add feedback to review | Dashboard feedback count increments in real-time (optimistic) | Count unchanged until page refresh = missing reactive binding |
| 3.4 | Finalise version | Dashboard transitions to read-only state: phase shows "Finalised", all action buttons removed/disabled | Action buttons still clickable after finalise = UI guard missing |
| 3.5 | Create new proposal (auto-supersedes draft) | Dashboard "Current Proposal" card updates to new version. Previous shows "Superseded". | Old draft still shown as current = auto-supersede not reflected |
| 3.6 | Accept proposal | Dashboard "Finalise" button becomes enabled. Proposal card shows green "Accepted" badge. | "Finalise" still disabled after acceptance = precondition check not updating |
| 3.7 | Backward transition (creates new version) | Dashboard navigates to new version context. All panels empty/fresh. | Dashboard still showing finalised version's data = navigation failure |
| 3.8 | Version selected has no proposals | Dashboard proposal section shows empty state: "No proposals yet." | Previous version's proposals bleeding through = query scope bug |
| 3.9 | Multiple users: User B adds review while User A views dashboard | User A's dashboard updates on next poll/websocket event | Requires full page refresh = no live update mechanism |

---

## 4. INTELLIGENCE TAB (Selected Version + Review Only)

| # | Action | Expected Result | What Should Fail |
|---|--------|-----------------|------------------|
| 4.1 | Open intelligence tab with Version 2 selected | Shows analysis/intelligence for Version 2 ONLY | Intelligence from Version 1 showing = wrong `version_id` in query |
| 4.2 | Switch version while on intelligence tab | Intelligence content reloads for newly selected version | Stale intelligence from previous version = no re-fetch on version change |
| 4.3 | Select specific review on intelligence tab | Intelligence scoped to that review's analysis (if review-level intelligence exists) | Showing all reviews' intelligence merged together = missing review filter |
| 4.4 | Version with no intelligence data (just created) | Empty state: "Intelligence processing... " or "No analysis available yet." | Showing another version's intelligence as fallback = dangerous |
| 4.5 | Finalised version's intelligence tab | Read-only display. No "Re-analyse" or "Refresh" buttons. | Ability to trigger re-analysis on finalised version = immutability violation |
| 4.6 | Backward-created version (cloned content) | Shows NEW intelligence for the new version (re-analysed), not copied from source | Displaying source version's intelligence = wrong `version_id` reference |
| 4.7 | Intelligence tab after review deletion | If intelligence was review-specific: removed or marked "Source review deleted" | Orphaned intelligence with no review context = confusing |
| 4.8 | Intelligence tab with active review vs non-active review selected | Both viewable. Active review's intelligence has no special priority in display. | Non-active review's intelligence hidden = over-filtering |

---

## 5. VERSIONS TAB (Full Hierarchy)

| # | Action | Expected Result | What Should Fail |
|---|--------|-----------------|------------------|
| 5.1 | Open versions tab | Shows all versions in hierarchical/list view: version number, status badge, creation date, source lineage | Missing versions = query not returning all |
| 5.2 | Finalised version in list | Lock icon + "Finalised" badge. No action buttons except "Create Revision". | Edit/delete buttons visible on finalised version = UI guard missing |
| 5.3 | Version created from backward transition | Shows "Created from Version N" with visual connector/lineage arrow | No provenance indicator = `source_version_id` not rendered |
| 5.4 | Expand version row | Shows: review count, proposal count (with latest status), active review name, phase | Counts showing wrong numbers = aggregate query bug |
| 5.5 | Click version row | Navigates to version detail OR selects in global dropdown (consistent behaviour) | Clicking does nothing or navigates to wrong version = routing bug |
| 5.6 | Sort versions | Sortable by: version number, creation date, status. Default: version number desc. | Sort by status puts finalised above draft when user expects chronological = bad default |
| 5.7 | Filter versions by status | Filter options: All, Draft, In Review, Proposed, Finalised | Filter shows versions with wrong status = status mismatch between filter and data |
| 5.8 | Empty project (no versions) | Full empty state: "No versions yet. Ingest a document to create your first version." | Blank page with no guidance = poor UX |
| 5.9 | Version with accepted proposal visible in hierarchy | Green checkmark or "Ready to finalise" indicator on that version row | No visual distinction between versions with/without accepted proposals = missed affordance |

---

## 6. COMPARE VERSIONS (Version + Review Context)

| # | Action | Expected Result | What Should Fail |
|---|--------|-----------------|------------------|
| 6.1 | Select two versions to compare | Side-by-side diff of version content. Each side labelled with version number + status. | Comparing version with itself = should be blocked or show "No differences" |
| 6.2 | Compare shows review context | Each side shows which review was active (or "No active review") at time of comparison context | Missing review attribution = traceability gap in comparison |
| 6.3 | Compare Version 1 (finalised) with Version 2 (draft, cloned from V1) | Shows content diff. V2 side labelled "Created from Version 1". Minimal or no diff if just cloned. | Large diff showing when content was cloned = content not actually cloned properly |
| 6.4 | Compare versions from different projects | BLOCKED: "Can only compare versions within the same project" | Cross-project comparison allowed = scope violation |
| 6.5 | Compare includes proposal context | Optional panel: shows which proposal was accepted on each version (if any) | Proposal from wrong version shown in comparison = query scope bug |
| 6.6 | Compare includes feedback summary | Shows feedback count per version, unresolved count | Feedback counts from wrong version = aggregate query wrong |
| 6.7 | Select review within comparison view | Can drill into specific review's content/feedback for each version side | Review selection affects wrong side of comparison = state binding bug |
| 6.8 | Compare with version that has no reviews | That side shows "No reviews" gracefully. No crash. | Error/crash when one side has no reviews = null handling failure |

---

## 7. REVIEWS TAB (Selection and Expansion)

| # | Action | Expected Result | What Should Fail |
|---|--------|-----------------|------------------|
| 7.1 | Open reviews tab for selected version | Lists all reviews for that version. Active review highlighted at top or with badge. | Reviews from other versions showing = missing version filter |
| 7.2 | Click review to expand | Expands to show: content/criteria, feedback list, injected feedback (collapsed), status | Expansion shows wrong review's data = data binding to wrong ID |
| 7.3 | Expand review → injected feedback section | Shows read-only injected feedback with source attribution: "From: [Review Name]" | Injected section editable = immutability guard missing in UI |
| 7.4 | Expand review → native feedback section | Shows editable feedback list. "Add feedback" input visible (unless version finalised). | Cannot add feedback on open review = input missing |
| 7.5 | Expand closed review → feedback section | Input present but labelled "Add follow-up note (audit log)". Existing feedback read-only (content). | Feedback input hidden on closed review = append-only audit log blocked in UI |
| 7.6 | Select review as active ("Set as Active" button) | Button visible on non-active reviews. Click updates active. Previous active loses badge. | Button visible on already-active review = redundant action. Button works on finalised version = should be hidden. |
| 7.7 | Delete review | Confirmation dialog. On confirm: review removed from list. If was active: active cleared. | No confirmation on delete = dangerous. Active not cleared = stale reference. |
| 7.8 | Delete last review | Extra warning: "This is the only review. Deleting it will clear the active review." After: empty state shown. | Generic delete confirmation without extra warning = user unaware of consequence |
| 7.9 | Review with zero feedback | Feedback section shows: "No feedback yet." | Section hidden entirely = user doesn't know where to add feedback |
| 7.10 | Review on finalised version | All fields read-only. No "Set as Active", "Delete", or "Edit" buttons. Feedback input still present (audit). | Any edit controls visible on finalised version's review = immutability violation in UI |

---

## 8. PROPOSAL AND FEEDBACK LINKS

| # | Action | Expected Result | What Should Fail |
|---|--------|-----------------|------------------|
| 8.1 | Proposal card shows "Based on: [Review Name]" | Clickable link navigating to that specific review | Link points to wrong review = `proposal.review_id` rendered incorrectly |
| 8.2 | Click review link from proposal | Navigates to review detail (expanded in reviews tab) with correct content | Navigation goes to review from different version = routing bug |
| 8.3 | Feedback item on review shows "View in context" link | Links to the proposal/review where this feedback was injected (if applicable) | Link points to wrong injection target = traceability broken |
| 8.4 | Proposal version history shows links to each version | Each entry clickable, shows that proposal version's content + source review | Link to deleted proposal version = 404 or graceful "This version was removed" |
| 8.5 | Injected feedback items show source attribution link | "Injected from: [Source Review Name]" with link | Link points to review on different version = cross-version leak |
| 8.6 | Superseded proposal shows link to successor | "Superseded by: Proposal v{N}" with clickable link | Link missing on superseded proposal = user can't find current draft |
| 8.7 | Rejected proposal shows "Create New Proposal" action | Button visible, creates next proposal version when clicked | Button creates proposal on wrong version = scoping bug |
| 8.8 | Feedback count badge on review card | Shows total feedback count. Clickable to expand feedback panel. | Count includes feedback from other reviews = aggregate wrong |
| 8.9 | Unresolved feedback badge on version card | Shows count of unresolved feedback across all reviews on this version | Count includes resolved items = filter bug. Count includes other versions = scope bug. |
| 8.10 | Proposal link from finalisation confirmation modal | Modal shows "Accepting proposal: [title/version]" with link to view it | Wrong proposal referenced in modal = critical UX error before irreversible action |
| 8.11 | Deep link to specific feedback item (URL addressable) | Direct URL like `/project/X/version/Y/review/Z/feedback/F` resolves correctly | Deep link shows wrong feedback or 404 = routing/ID resolution bug |
| 8.12 | Breadcrumb trail on any detail page | Shows: Project > Version N > Review Name > (Feedback/Proposal context) | Breadcrumb shows wrong hierarchy = navigation state desync |

---

## Summary Matrix

| UI Area | Scenarios | Must Pass | What Fails (Bug Type) |
|---------|:---------:|:---------:|----------------------|
| Version Dropdown | 7 | All | State leak, caching, scope violation |
| Review Dropdown | 8 | All | Missing filter, stale state, wrong default |
| Dashboard Updates | 9 | All | Partial refresh, binding failure, scope bug |
| Intelligence Tab | 8 | All | Wrong version_id, stale cache, immutability |
| Versions Tab | 9 | All | Missing data, routing, guard failure |
| Compare Versions | 8 | All | Scope violation, null handling, binding |
| Reviews Tab | 10 | All | Filter missing, immutability, UX gap |
| Proposal/Feedback Links | 12 | All | Routing, traceability, scope leak |
| **TOTAL** | **71** | **71** | — |

---

## Cross-Cutting UI Rules (Apply to ALL Areas)

| Rule | Enforces | Violation Symptom |
|------|----------|-------------------|
| All queries include `project_id` filter | Project isolation | Data from other projects visible |
| All queries include `version_id` filter when version-scoped | Version isolation | Data from other versions bleeding in |
| Finalised state hides all mutation controls | Immutability in UI | Edit/delete/create buttons on locked entities |
| Optimistic updates on user actions | Responsiveness | Requires page refresh to see own changes |
| Dropdown selections propagate to all panels | Consistent context | One panel shows V1 data while another shows V2 |
| Deep links resolve to correct entity | Addressability | Shared URLs show wrong content to recipients |
| Empty states provide guidance | Discoverability | Blank panels with no call-to-action |
| Active review always visually distinguished | Orientation | User cannot tell which review is active |
