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
