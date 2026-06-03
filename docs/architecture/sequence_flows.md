# Sequence Flows

**Project Delivery Accelerator Engine — V2 Interaction Sequence Diagrams**

> Each diagram shows the full message sequence between actors for a specific user interaction. Participants map directly to files in this repository.

---

## Linked Components

| Participant | File |
|-------------|------|
| User | — (browser) |
| Browser | `static/v2/dashboard_v2.html` |
| Dashboard | `static/v2/js/dashboard.js` |
| AppState | `static/v2/js/state.js` |
| API | `static/v2/js/api.js` |
| Accordion | `static/v2/js/accordion.js` |
| DetailPanel | `ui/v2/components/DetailPanel.js` |
| Server | `server.py` |
| HierarchyService | `services/hierarchy.py` |
| HierarchyStore | `models/hierarchy.py` |

---

## Sequence 1: Page Load and Initial Render

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Dashboard
    participant AppState
    participant API
    participant Server
    participant HierarchyService

    User->>Browser: Navigate to /?ui=v2
    Browser->>Server: GET /?ui=v2
    Server->>Server: _resolve_ui_version() → 'v2'
    Server->>Browser: 200 dashboard_v2.html + CSS
    Browser->>Browser: Load state.js, api.js, accordion.js, dashboard.js

    Note over Browser,Dashboard: DOMContentLoaded fires
    Browser->>Dashboard: Dashboard.init()
    Dashboard->>AppState: set('loading', true)
    Dashboard->>API: fetchProjects()
    API->>Server: GET /api/projects
    Server->>HierarchyService: list_projects()
    HierarchyService->>Server: [{id, name, phase}]
    Server->>API: 200 {projects:[...]}
    API->>Dashboard: projects[]
    Dashboard->>AppState: set('projects', projects)
    Dashboard->>AppState: selectProject(projects[0])
    Note over AppState: Resets version, review, metrics

    Dashboard->>API: fetchHierarchy(pid)
    Dashboard->>API: fetchMetrics(pid)
    Note over API: Parallel Promise.all

    API->>Server: GET /api/projects/{pid}/hierarchy
    Server->>HierarchyService: get_hierarchy(pid)
    HierarchyService->>Server: {tree, total_versions, total_reviews}
    Server->>API: 200 hierarchy

    API->>Server: GET /api/projects/{pid}/hierarchy/metrics
    Server->>HierarchyService: get_metrics(pid)
    HierarchyService->>Server: {total_versions, risks, ...}
    Server->>API: 200 metrics

    API->>Dashboard: [hierarchy, metrics]
    Dashboard->>AppState: setData({hierarchy, metrics, versions})
    AppState->>Dashboard: notify subscribers
    Dashboard->>Dashboard: renderAll()
    Dashboard->>Browser: Render snapshot cards, accordion, sidebar
    Browser->>User: Dashboard visible
```

---

## Sequence 2: Version Selection (Header Dropdown)

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Dashboard
    participant AppState
    participant API
    participant Server

    User->>Browser: Select version from dropdown
    Browser->>Dashboard: onVersionChange(selectEl)
    Dashboard->>Dashboard: Find version in state.versions[]
    Dashboard->>AppState: selectVersion(version)
    Note over AppState: Clears selectedReview + reviews[]
    AppState->>Dashboard: notify 'selectedVersion'
    Dashboard->>Dashboard: _populateReviewDropdown(version.reviews)
    Dashboard->>API: fetchMetrics(pid, vid, null)
    API->>Server: GET /hierarchy/metrics?version_id=v3
    Server->>API: 200 {metrics scoped to v3}
    API->>Dashboard: metrics
    Dashboard->>AppState: setData({metrics})
    AppState->>Dashboard: notify 'metrics'
    Dashboard->>Browser: _renderSnapshotCards(new metrics)
    Dashboard->>Browser: _renderContextBanner() → "v3 → Active Review"
    Browser->>User: Cards update, context banner updates
```

---

## Sequence 3: Review Click → Detail Drawer Opens

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Accordion
    participant AppState
    participant Dashboard
    participant DetailPanel
    participant API
    participant Server

    User->>Browser: Click review row in accordion
    Browser->>Accordion: onReviewClick(el)
    Accordion->>Accordion: Read data-review-id, data-version-id
    Accordion->>AppState: selectReview(review)
    Accordion->>AppState: openDrawer('review', reviewSummary)
    Note over AppState: set drawerOpen=true, drawerEntity={type,data}

    AppState->>Dashboard: notify 'drawerOpen'
    Dashboard->>Dashboard: _syncDrawer(true, entity)
    Dashboard->>Browser: Add CSS: drawer.open, main.drawer-open
    Note over Browser: Drawer slides in (300ms CSS transition)

    Dashboard->>DetailPanel: renderReview(summary data)
    DetailPanel->>Browser: Inject summary HTML into #v2-drawer-content
    Browser->>User: Drawer visible with summary

    Note over Dashboard: Async: load full detail
    Dashboard->>API: fetchReviewDetail(pid, rid)
    API->>Server: GET /hierarchy/reviews/{rid}
    Server->>API: 200 full review {findings, questions, weaknesses}
    API->>Dashboard: full review data
    Dashboard->>DetailPanel: renderReview(full data)
    DetailPanel->>Browser: Replace drawer content with full detail
    Browser->>User: Drawer updates with findings, questions
```

---

## Sequence 4: Refresh Loop (No Page Reload)

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Dashboard
    participant AppState
    participant API
    participant Server

    User->>Browser: Click ↺ Refresh button
    Browser->>Dashboard: onRefresh()
    Dashboard->>Dashboard: _toast('Refreshing…')
    Dashboard->>Dashboard: loadAll(silent=false)
    Dashboard->>AppState: set('loading', true)
    Note over Browser: Refresh button disabled + spin

    Dashboard->>API: fetchHierarchy(pid)
    Dashboard->>API: fetchMetrics(pid, selectedVid, selectedRid)
    Note over API: Parallel

    API->>Server: GET /hierarchy (fresh data)
    Server->>API: 200 updated hierarchy

    API->>Server: GET /hierarchy/metrics (scoped)
    Server->>API: 200 updated metrics

    API->>Dashboard: [hierarchy, metrics]
    Dashboard->>AppState: setData({hierarchy, metrics, versions, lastUpdated: now})
    Note over AppState: loading=false set in setData()

    AppState->>Dashboard: notify subscribers
    Dashboard->>Browser: renderAll() — all regions update
    Dashboard->>Browser: _renderLastUpdated("Updated 14:32")
    Note over Browser: Refresh button re-enabled
    Browser->>User: Fresh data displayed
```

---

## Sequence 5: Drawer Close (Esc Key or × Button)

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant MainLayout
    participant AppState
    participant Dashboard

    alt User presses Esc key
        User->>Browser: keydown: Escape
        Browser->>MainLayout: _handleKeydown(event)
        MainLayout->>AppState: check drawerOpen
        AppState->>MainLayout: true
        MainLayout->>AppState: closeDrawer()
    else User clicks × button
        User->>Browser: click #v2-drawer-close
        Browser->>Dashboard: onCloseDrawer()
        Dashboard->>AppState: closeDrawer()
    end

    Note over AppState: set drawerOpen=false, drawerEntity=null

    AppState->>Dashboard: notify 'drawerOpen'
    Dashboard->>Dashboard: _syncDrawer(false, null)
    Dashboard->>Browser: Remove CSS: drawer.open, main.drawer-open
    Note over Browser: Drawer slides out (300ms transition)
    Browser->>User: Drawer closed, main content full-width
```

---

## Sequence 6: Accordion Expand / Collapse All

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Dashboard
    participant Accordion

    User->>Browser: Click "Expand All" button
    Browser->>Dashboard: onExpandAll()
    Dashboard->>Accordion: toggleExpandAll(container, btn)
    Accordion->>Accordion: Check: any .accordion-item.expanded?
    alt Any expanded
        Accordion->>Browser: Remove .expanded from all items
        Accordion->>Browser: Set aria-expanded="false" on all headers
        Accordion->>Browser: btn.textContent = "Expand All"
        Note over Browser: All accordions collapse (CSS transition)
    else None expanded
        Accordion->>Browser: Add .expanded to all items
        Accordion->>Browser: Set aria-expanded="true" on all headers
        Accordion->>Browser: btn.textContent = "Collapse All"
        Note over Browser: All accordions expand (CSS transition)
    end
    Browser->>User: Accordion state toggled
```


---

## Sequence 7: Weakness User Note Update (S9-03)

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Server
    participant ReviewHandler
    participant ReviewService
    participant HierarchyStore

    Note over Browser: Review detail view is open.<br/>User edits the note textarea under a weakness item.

    User->>Browser: Tab / click away from textarea (blur event)
    Browser->>Browser: onblur fires → updateWeaknessStatus(reviewId, weaknessId, null, this.value)
    Note over Browser: status=null (no change), note=textarea.value
    Browser->>Browser: Read current status from sibling <select>
    Browser->>Server: POST /api/projects/{pid}/hierarchy/reviews/{rid}/weakness/{wid}/status<br/>body: { status: "open", user_note: "Confirmed by client" }

    Server->>ReviewHandler: handle_weakness_status(pid, rid, wid, body)
    ReviewHandler->>ReviewHandler: status = body["status"]<br/>user_note = body["user_note"]
    ReviewHandler->>ReviewService: update_weakness_status(pid, rid, wid, status, user_note=note)

    ReviewService->>HierarchyStore: get_review(rid)
    HierarchyStore->>ReviewService: Review dataclass

    ReviewService->>ReviewService: Find weakness by id<br/>target["status"] = status<br/>target["user_note"] = user_note

    ReviewService->>HierarchyStore: update_review_weaknesses(rid, weaknesses)
    HierarchyStore->>HierarchyStore: UPDATE reviews SET weaknesses=? WHERE review_id=?<br/>+ file dual-write

    ReviewService->>ReviewHandler: { review_id, weakness_id, status, user_note, updated: true }
    ReviewHandler->>Server: respond(result, 200)
    Server->>Browser: 200 { updated: true, user_note: "Confirmed by client" }

    Note over Browser: No re-render needed — textarea already shows the value.
    Browser->>User: (silent success)

    alt Status-only update (user changes <select>)
        User->>Browser: Change status dropdown
        Browser->>Server: POST … body: { status: "addressed", user_note: null }
        Note over Server: user_note=None → service skips target["user_note"] assignment<br/>Existing note is preserved.
    end
```

### Key rules enforced (S9-03)
| Rule | Where |
|------|-------|
| `user_note` defaults to `""` on every new weakness | `processors/review_quality.py → extract_weaknesses()` |
| Status-only call (no `user_note` key) leaves note unchanged | `services/review.py → update_weakness_status()` |
| Note-only blur sends current status from sibling `<select>` | `static/index.html → updateWeaknessStatus()` |
| Existing reviews without `user_note` render empty textarea (no error) | `static/index.html` — `w.user_note\|\|''` |


---

## Sequence 8: Review Compare via Hierarchy Store (Compare bug fix)

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant CompareJS as compare.js (Compare module)
    participant Server
    participant Handler as handlers/hierarchy.py
    participant Service as services/hierarchy.py
    participant HierarchyStore

    Note over Browser: User opens Compare modal, switches to Reviews mode,<br/>selects two reviews (r1, r2) and clicks Compare.

    User->>Browser: Click ⇄ Compare (Reviews mode)
    Browser->>CompareJS: Compare.run()
    CompareJS->>Server: POST /api/projects/{pid}/compare-reviews<br/>body: { review_a: "r1", review_b: "r2" }

    Server->>Handler: handle_compare_reviews(pid, body)
    Handler->>Handler: review_a = body["review_a"]  → "r1"<br/>review_b = body["review_b"]  → "r2"
    Handler->>Service: compare_project_reviews(pid, "r1", "r2")

    Note over Service: FIX: was opening flat file projects_data/{pid}/reviews/r1<br/>which does not exist. Now uses hierarchy store.

    Service->>HierarchyStore: _make_hierarchy_store(pid).get_review("r1")
    HierarchyStore->>Service: Review dataclass (r1)
    Service->>HierarchyStore: _make_hierarchy_store(pid).get_review("r2")
    HierarchyStore->>Service: Review dataclass (r2)

    Service->>Service: compare_reviews(r1.to_dict(), r2.to_dict())
    Note over Service: processors/history.compare_reviews() compares<br/>findings dicts: new_findings, resolved, persistent per category.

    Service->>Handler: comparison result dict
    Handler->>Server: respond(result, 200)
    Server->>CompareJS: { sections: {...}, summary: {...} }
    CompareJS->>Browser: Render review progression tiles + per-category diff
    Browser->>User: Shows Resolved / New / Persistent counts
```

### Root cause of the bug
`compare_project_reviews()` was looking for a file at:
`projects_data/{pid}/reviews/<review_id>` — the legacy flat-file store path.
The hierarchy store (SQLite-backed) stores reviews in `projects_data/{pid}/hierarchy/reviews/`
and uses IDs like `r1`, not filenames. The flat-file path never exists for hierarchy reviews,
so the function always raised `ValueError("Review not found: r1")`.

### Fix
`services/hierarchy.py → compare_project_reviews()` now calls
`_make_hierarchy_store(pid).get_review(review_id)` for both reviews,
then passes `review.to_dict()` to `processors/history.compare_reviews()`.

---

## Sequence 9: v2 Reviews Tab — Full Action Set

The v2 Reviews tab (`static/v2/dashboard_v2.html`) previously rendered
each review with only a Compare button. All the following actions are now
available in both the Reviews tab and the Versions tab review-item-body:

| Action | Function | API call |
|--------|----------|----------|
| Full Details | `v2ViewReviewDetail(rid)` | Sets `state._v2ReviewDetail`, re-renders |
| Set Active | `v2SetActiveReview(vid, rid)` | `POST /hierarchy/versions/{vid}/active-review` |
| Mark as Draft | `v2OpenMarkComplete(rid,'interim')` | `POST /hierarchy/reviews/{rid}/complete` |
| Mark as Final | `v2OpenMarkComplete(rid,'complete')` | `POST /hierarchy/reviews/{rid}/complete` |
| Delete | `v2DeleteReview(rid)` | `POST /hierarchy/reviews/{rid}/delete` |
| Run Review | `v2RunReview()` | `POST /api/review` |
| Ask SME | `v2RunDeepDive()` | `POST /api/projects/{pid}/deep-dive` |
| Add to Prompt | `v2AddSelectedToPrompt()` | Client-side state update only |

All functions use the `v2` prefix to avoid collision with the v1 global namespace.
Role checkboxes use class `v2-role-check` (vs v1's `role-check`).


---

## Sequence 10: Phase 1 — V2 Connects to Live Backend

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant API
    participant Server

    Note over Browser: dashboard_v2.html sets window.V2_USE_MOCK = false<br/>before any scripts execute.

    User->>Browser: Navigate to /?ui=v2
    Browser->>Browser: Parse inline script block:<br/>window.V2_USE_MOCK = false
    Browser->>Browser: Load compare.js, state.js, api.js, dashboard.js

    Note over API: api.js _useMock() reads window.V2_USE_MOCK !== false<br/>→ returns false → live path taken for every call.

    Browser->>API: fetchProjects()
    API->>API: _useMock() → false
    API->>Server: GET /api/projects
    Server->>API: 200 {projects:[...]}
    API->>Browser: real project list

    Browser->>API: fetchHierarchy(pid)
    API->>API: _useMock() → false
    API->>Server: GET /api/projects/{pid}/hierarchy
    Server->>API: 200 hierarchy
    API->>Browser: real hierarchy tree

    Note over Browser: All subsequent calls (metrics, versions,<br/>reviews, detail) follow the same live path.
    Browser->>User: Dashboard populated with real data
```

### What changed (Phase 1)
| File | Change |
|------|--------|
| `static/v2/dashboard_v2.html` | Added `<script>window.V2_USE_MOCK = false;</script>` before `compare.js` |

### Contract preserved
- Mock data in `api.js` is retained for local offline development.
- To re-enable mock mode, set `window.V2_USE_MOCK = true` in the HTML.
- `_useMock()` guard still wraps every mock return path — no unconditional mock returns.

---

## Sequence 11: Phase 2 — V2 Weakness Status Update from Drawer

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant DetailPanel
    participant API
    participant Server
    participant ReviewHandler
    participant ReviewService
    participant HierarchyStore

    Note over Browser: Review detail drawer is open.<br/>renderReview() has rendered weakness rows<br/>with status <select> and note <textarea>.

    alt User changes status dropdown
        User->>Browser: Change status <select> → "addressed"
        Browser->>DetailPanel: _onWeaknessStatusChange(selectEl)
        DetailPanel->>DetailPanel: Read data-pid, data-rid, data-wid from selectEl.dataset
        DetailPanel->>API: updateWeaknessStatus(pid, rid, wid, "addressed", null)
        Note over API: userNote=null → body only contains {status}.<br/>Existing note is preserved server-side.
        API->>Server: POST /api/projects/{pid}/hierarchy/reviews/{rid}/weakness/{wid}/status<br/>body: { status: "addressed" }
        Server->>ReviewHandler: handle_weakness_status(pid, rid, wid, body)
        ReviewHandler->>ReviewService: update_weakness_status(pid, rid, wid, "addressed", user_note=None)
        ReviewService->>HierarchyStore: get_review(rid)
        HierarchyStore->>ReviewService: Review dataclass
        ReviewService->>ReviewService: target["status"] = "addressed"<br/>(user_note untouched — None passed)
        ReviewService->>HierarchyStore: update_review_weaknesses(rid, weaknesses)
        HierarchyStore->>ReviewService: persisted
        ReviewService->>ReviewHandler: { updated: true, status: "addressed" }
        ReviewHandler->>Server: respond(result, 200)
        Server->>API: 200 { updated: true }
        API->>DetailPanel: result
        Note over Browser: No re-render — select already shows new value.
        Browser->>User: (silent success)
    end

    alt User types a note and tabs away
        User->>Browser: Type note text → blur textarea
        Browser->>DetailPanel: _onWeaknessNoteBlur(textarea)
        DetailPanel->>DetailPanel: Read data-pid, data-rid, data-wid from textarea.dataset
        DetailPanel->>DetailPanel: Find sibling <select> in .weakness-row → read .value
        DetailPanel->>API: updateWeaknessStatus(pid, rid, wid, currentStatus, textarea.value)
        Note over API: Both status and user_note are sent.
        API->>Server: POST … body: { status: "addressed", user_note: "Confirmed by client" }
        Server->>ReviewHandler: handle_weakness_status(pid, rid, wid, body)
        ReviewHandler->>ReviewService: update_weakness_status(…, "addressed", user_note="Confirmed by client")
        ReviewService->>ReviewService: target["status"] = "addressed"<br/>target["user_note"] = "Confirmed by client"
        ReviewService->>HierarchyStore: update_review_weaknesses(rid, weaknesses)
        HierarchyStore->>ReviewService: persisted
        ReviewService->>ReviewHandler: { updated: true, user_note: "Confirmed by client" }
        ReviewHandler->>Server: respond(result, 200)
        Server->>API: 200 { updated: true, user_note: "Confirmed by client" }
        Note over Browser: No re-render — textarea already shows the value.
        Browser->>User: (silent success)
    end
```

---

## Sequence 12: Phase 2 — V2 Decision Point Status Update from Drawer

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant DetailPanel
    participant API
    participant Server
    participant ReviewHandler
    participant ReviewService
    participant HierarchyStore

    Note over Browser: Review detail drawer is open.<br/>renderReview() has rendered decision point rows<br/>each with a status <select>.

    User->>Browser: Change decision status <select> → "validated"
    Browser->>DetailPanel: _onDecisionStatusChange(selectEl)
    DetailPanel->>DetailPanel: Read data-pid, data-rid, data-did from selectEl.dataset
    DetailPanel->>API: updateDecisionStatus(pid, rid, did, "validated")
    API->>Server: POST /api/projects/{pid}/hierarchy/reviews/{rid}/decision/{did}/status<br/>body: { status: "validated" }

    Server->>ReviewHandler: handle_decision_status(pid, rid, did, body)
    ReviewHandler->>ReviewService: update_decision_status(pid, rid, did, "validated")
    ReviewService->>HierarchyStore: get_review(rid)
    HierarchyStore->>ReviewService: Review dataclass
    ReviewService->>ReviewService: Find dp by id<br/>target["status"] = "validated"
    ReviewService->>HierarchyStore: update_review_decision_points(rid, dps)
    HierarchyStore->>ReviewService: persisted
    ReviewService->>ReviewHandler: { updated: true, decision_id: did, status: "validated" }
    ReviewHandler->>Server: respond(result, 200)
    Server->>API: 200 { updated: true }
    API->>DetailPanel: result

    Note over Browser: No re-render — select already shows new value.
    Browser->>User: (silent success)
```

---

## Sequence 13: Phase 2 — V2 Provenance Line Render

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Accordion
    participant Dashboard
    participant DetailPanel
    participant API
    participant Server

    User->>Browser: Click review row in accordion
    Browser->>Accordion: onReviewClick(el)
    Accordion->>Dashboard: AppState.openDrawer('review', summary)
    Dashboard->>DetailPanel: renderReview(summary)
    DetailPanel->>Browser: Inject skeleton HTML (summary only)

    Dashboard->>API: fetchReviewDetail(pid, rid)
    API->>Server: GET /api/projects/{pid}/hierarchy/reviews/{rid}
    Server->>API: 200 full review {findings, questions, weaknesses,<br/>decision_points, included_files, categories, persona}
    API->>Dashboard: full review

    Dashboard->>DetailPanel: renderReview(full)
    DetailPanel->>DetailPanel: _renderProvenanceLine(r)<br/>→ reads r.persona, r.included_files.length, r.categories
    Note over DetailPanel: No extra API call — provenance data<br/>is already in the review detail response.
    DetailPanel->>Browser: Inject full HTML:<br/>• Provenance line (persona · N artefacts · [category chips])<br/>• Findings by category<br/>• Weaknesses (interactive)<br/>• Decision points (interactive)
    Browser->>User: Drawer shows full detail with provenance
```

### Provenance line data sources (Phase 2.3)
| Field shown | Source in Review object |
|-------------|------------------------|
| Persona label | `review.persona` |
| Artefact count | `review.included_files.length` |
| Category chips | `review.categories[]` (up to 4, +N overflow) |

### Key rules enforced (Phase 2)
| Rule | Where enforced |
|------|----------------|
| `userNote=null` → `user_note` key absent from POST body | `api.js → updateWeaknessStatus()` |
| `user_note=None` on service → existing note preserved | `services/review.py → update_weakness_status()` |
| Status-only change does not re-render the drawer | `DetailPanel.js → _onWeaknessStatusChange()` |
| Note blur reads current status from sibling `<select>` | `DetailPanel.js → _onWeaknessNoteBlur()` |
| All weaknesses rendered (not just open) so any can be updated | `DetailPanel.js → renderReview()` |
| Provenance line rendered above findings, no extra API call | `DetailPanel.js → _renderProvenanceLine()` |
| `projectId` resolved from `AppState.get('selectedProject')` at render time | `DetailPanel.js → renderReview()` |

### Linked components — Phase 2 additions
| Participant | File |
|-------------|------|
| DetailPanel | `ui/v2/components/DetailPanel.js` |
| API | `static/v2/js/api.js` |
| ReviewHandler | `handlers/review.py` |
| ReviewService | `services/review.py` |
| HierarchyStore | `models/hierarchy.py` |


---

## Sequence 14: Phase 3 — Review Iteration (Drawer → New Linked Review)

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant DetailPanel
    participant API
    participant Server
    participant ReviewHandler
    participant ReviewService
    participant HierarchyStore

    Note over Browser: Review detail drawer is open.<br/>User expands "↩ Iterate from this review" panel.

    User->>Browser: Click "↩ Iterate from this review" summary
    Browser->>DetailPanel: _onIterateSummaryClick(summaryEl)
    DetailPanel->>DetailPanel: Derive rid from details#id
    DetailPanel->>Browser: Check data-loaded attribute on persona <select>
    alt First open — personas not yet loaded
        DetailPanel->>Server: GET /api/personas
        Server->>DetailPanel: 200 { personas: [{id, name, ...}] }
        DetailPanel->>Browser: Populate persona <select> options
        DetailPanel->>Browser: Set data-loaded="1"
    end
    Browser->>User: Persona dropdown + prompt textarea visible

    User->>Browser: Select persona, optionally add context, click "▶ Run Iteration"
    Browser->>DetailPanel: _onIterateSubmit(btn)
    DetailPanel->>DetailPanel: Read data-review-id from btn
    DetailPanel->>DetailPanel: Read persona from #v2-iterate-persona-{rid}
    DetailPanel->>DetailPanel: Read custom_prompt from #v2-iterate-prompt-{rid}
    DetailPanel->>Browser: btn.disabled=true, show "Running…"
    DetailPanel->>API: iterateReview(pid, rid, persona, 'files_only', customPrompt)
    API->>Server: POST /api/projects/{pid}/hierarchy/reviews/{rid}/iterate<br/>body: { roles:[persona], ai_backend, custom_prompt? }

    Server->>ReviewHandler: handle_iterate_review(pid, rid, body)
    ReviewHandler->>ReviewHandler: Validate roles present<br/>Validate previous_review_id (rid) non-empty
    ReviewHandler->>ReviewHandler: Build ReviewRequest(previous_review_id=rid)
    ReviewHandler->>ReviewService: ServiceReviewAgent().run(request)
    ReviewService->>ReviewService: run_persona_review(project_id, roles,<br/>   previous_review_id=rid, ...)
    Note over ReviewService: Open decision points from predecessor<br/>are inherited into the new review.
    ReviewService->>HierarchyStore: create_review(version_id, ..., previous_review_id=rid)
    HierarchyStore->>ReviewService: Review dataclass (new review_id)
    ReviewService->>ReviewHandler: ReviewResult.raw (dict with review_id)
    ReviewHandler->>Server: respond(result, 200)
    Server->>API: 200 { review_id: "r8", previous_review_id: "r7", ... }
    API->>DetailPanel: result

    DetailPanel->>Browser: Show "✓ Iteration created: r8"
    DetailPanel->>Browser: Close <details> panel
    DetailPanel->>AppState: closeDrawer()
    DetailPanel->>Dashboard: Dashboard.loadAll(silent=true)
    Note over Dashboard: Hierarchy re-fetched silently.<br/>New review r8 appears in accordion.
    Browser->>User: Drawer closed, accordion updated with new review
```

### Key rules enforced (Phase 3)
| Rule | Where |
|------|-------|
| `previous_review_id` set from URL `{rid}`, not body | `handlers/review.py → handle_iterate_review()` |
| Open decision points from predecessor inherited | `services/review.py → run_persona_review()` |
| Persona lazily loaded from `/api/personas` on first panel open | `ui/v2/components/DetailPanel.js → _onIterateSummaryClick()` |
| Hierarchy silently refreshed after success | `ui/v2/components/DetailPanel.js → _onIterateSubmit()` |
| `DashboardRefresh` global available as alternative refresh trigger | `static/v2/js/dashboard.js` |

---

## Sequence 15: Phase 4 — Reconciliation (Version ⇄ Button → Panel → Result)

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Accordion
    participant Dashboard
    participant AppState
    participant ReconciliationPanel
    participant API
    participant Server
    participant HierarchyHandler
    participant HierarchyService
    participant Synthesizer

    User->>Browser: Click ⇄ button on version header in accordion
    Browser->>Accordion: onclick — Dashboard.openReconcileDrawer(vid)
    Accordion->>Dashboard: openReconcileDrawer(vid)
    Dashboard->>AppState: selectVersion(version)
    Dashboard->>AppState: openDrawer('reconcile', { version, projectId })
    AppState->>Dashboard: notify 'drawerOpen'
    Dashboard->>Dashboard: _renderDrawerContent(entity)
    Dashboard->>Browser: Inject drawer HTML with #v2-reconcile-panel-container
    Dashboard->>ReconciliationPanel: ReconciliationPanel.render(container, pid, vid, reviews, null)
    ReconciliationPanel->>Browser: Render anchor <select> + supplemental checkboxes + backend <select>
    Browser->>User: Reconciliation panel visible in drawer

    User->>Browser: Optionally check supplemental review(s), click "⇄ Reconcile Reviews"
    Browser->>ReconciliationPanel: onRunReconcile(btnEl)
    ReconciliationPanel->>ReconciliationPanel: Read anchorId from #rec-anchor-{vid}
    ReconciliationPanel->>ReconciliationPanel: Collect checked .rec-supp-check-{vid}
    ReconciliationPanel->>Browser: btn.disabled=true, show "Reconciling…"
    ReconciliationPanel->>API: reconcileReviews(pid, anchorId, supplementalIds, aiBackend)
    API->>Server: POST /api/projects/{pid}/hierarchy/reconcile<br/>body: { anchor_review_id, supplemental_review_ids[], ai_backend }

    Server->>HierarchyHandler: handle_reconcile_reviews(pid, body)
    HierarchyHandler->>HierarchyHandler: Validate anchor_review_id present
    HierarchyHandler->>HierarchyService: reconcile_reviews(pid, anchorId, suppIds, aiBackend)

    HierarchyService->>HierarchyService: store.get_review(anchorId) → anchor
    loop Each supplemental_review_id
        HierarchyService->>HierarchyService: store.get_review(rid) → supplemental
    end
    HierarchyService->>HierarchyService: store.get_version(anchor.version_id) → version_scope
    HierarchyService->>Synthesizer: synthesize_reviews(anchor, supplementals, version_scope, ai_backend)
    Note over Synthesizer: normalize → deduplicate → LLM or deterministic
    Synthesizer->>HierarchyService: ReconciliationResult
    HierarchyService->>HierarchyHandler: result.to_dict()
    HierarchyHandler->>Server: respond(result, 200)
    Server->>API: 200 ReconciliationResult

    API->>ReconciliationPanel: result
    ReconciliationPanel->>Browser: Show "✓ Reconciliation complete."
    ReconciliationPanel->>ReconciliationPanel: renderResult(result)
    ReconciliationPanel->>Browser: Render findings by category + conflicts + notes
    Browser->>User: Reconciled output visible in drawer
```

---

## Sequence 16: Phase 4 — Anchor Change Rebuilds Supplemental List

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant ReconciliationPanel

    Note over Browser: Reconciliation panel is rendered.<br/>User changes the anchor review selection.

    User->>Browser: Change anchor <select> to different review
    Browser->>ReconciliationPanel: onAnchorChange(selectEl)
    ReconciliationPanel->>ReconciliationPanel: Derive vid from selectEl.id
    ReconciliationPanel->>ReconciliationPanel: Read newAnchorId = selectEl.value
    ReconciliationPanel->>ReconciliationPanel: Parse container.dataset.recReviews → reviews[]
    ReconciliationPanel->>ReconciliationPanel: _renderSupplementalCheckboxes(reviews, newAnchorId, vid)
    Note over ReconciliationPanel: New anchor is excluded from supplemental list.<br/>Previous checkboxes are replaced.
    ReconciliationPanel->>Browser: Update #rec-supp-area-{vid} innerHTML
    Browser->>User: Supplemental checkboxes rebuilt (old anchor now selectable as supplemental)
```

### Key rules enforced (Phase 4)
| Rule | Where |
|------|-------|
| `anchor_review_id` required; returns 400 when absent | `handlers/hierarchy.py → handle_reconcile_reviews()` |
| All reviews must share the same `version_id` | `processors/review_synthesizer.py → synthesize_reviews()` |
| `files_only` path is always deterministic (no LLM) | `processors/review_synthesizer.py → _deterministic_reconcile()` |
| Anchor excluded from supplemental checkbox list | `ui/v2/components/ReconciliationPanel.js → _renderSupplementalCheckboxes()` |
| onComplete callback fired on success (Phase 6 hook) | `ui/v2/components/ReconciliationPanel.js → onRunReconcile()` |
| Served static copy (`reconciliation_panel.js`) must stay in sync | `static/v2/js/reconciliation_panel.js` |

### Linked components — Phase 3 + 4 additions
| Participant | File |
|-------------|------|
| ReconciliationPanel | `ui/v2/components/ReconciliationPanel.js` (source) |
| ReconciliationPanel (served) | `static/v2/js/reconciliation_panel.js` |
| ReviewHandler | `handlers/review.py` — `handle_iterate_review()` |
| HierarchyHandler | `handlers/hierarchy.py` — `handle_reconcile_reviews()` |
| HierarchyService | `services/hierarchy.py` — `reconcile_reviews()` |
| Synthesizer | `processors/review_synthesizer.py` — `synthesize_reviews()` |
| API | `static/v2/js/api.js` — `iterateReview()`, `reconcileReviews()` |
| Dashboard | `static/v2/js/dashboard.js` — `openReconcileDrawer()` |
| Accordion | `static/v2/js/accordion.js` — ⇄ button |
