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
