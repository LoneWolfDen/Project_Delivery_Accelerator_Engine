# Application Flow

**Project Delivery Accelerator Engine — V2 End-to-End Application Flow**

> This document maps the complete runtime flow from server startup through user interactions. Each node references a real file and function.

---

## Linked Components

| Step | File | Function |
|------|------|----------|
| Server startup | `server.py` | `main()`, `_parse_args()` |
| UI version resolution | `server.py` | `_resolve_ui_version()` |
| HTML load | `static/v2/dashboard_v2.html` | — |
| App bootstrap | `static/v2/js/dashboard.js` | `Dashboard.init()` |
| Project fetch | `static/v2/js/api.js` | `API.fetchProjects()` |
| Hierarchy fetch | `static/v2/js/api.js` | `API.fetchHierarchy()` |
| Metrics fetch | `static/v2/js/api.js` | `API.fetchMetrics()` |
| State update | `static/v2/js/state.js` | `AppState.setData()` |
| Full render | `static/v2/js/dashboard.js` | `Dashboard.renderAll()` |
| Accordion render | `static/v2/js/accordion.js` | `VersionAccordion.render()` |
| Card render | `ui/v2/components/Cards.js` | `Cards.render()` |
| Review drawer render | `static/v2/js/review_detail.js` | `ReviewDetail.renderReview()` *(Sprint 1)* |
| Weakness note persist | `static/v2/js/api.js` | `API.updateWeaknessNote()` *(Sprint 1)* |
| Weakness status persist | `static/v2/js/api.js` | `API.updateWeaknessStatus()` *(Sprint 1)* |
| Review iteration toggle | `static/v2/js/review_detail.js` | `ReviewDetail.onToggleIterationForm()` *(Sprint 2)* |
| Review iteration submit | `static/v2/js/review_detail.js` | `ReviewDetail.onCreateIteration()` *(Sprint 2)* |
| Review iteration API call | `static/v2/js/api.js` | `API.createReviewIteration()` *(Sprint 2)* |

---

## Startup and Bootstrap Flow

```mermaid
flowchart TD
    A([python server.py]) --> B["_parse_args()<br/>--ui v1|v2"]
    B --> C["UI_VERSION = 'v1' or 'v2'<br/>(module-level constant)"]
    C --> D["HTTPServer starts<br/>HOST:PORT"]
    D --> E["Browser GET /"]
    E --> F{"_resolve_ui_version()<br/>?ui= param OR flag"}
    F -->|v2| G["_serve_static('v2/dashboard_v2.html')"]
    F -->|v1| H["_serve_static('index.html')"]
    G --> I["Browser parses HTML<br/>loads CSS + JS in order"]
    I --> J["DOMContentLoaded fires<br/>Dashboard.init()"]
    J --> K["API.fetchProjects()"]
    K --> L{"Projects returned?"}
    L -->|yes| M["AppState.selectProject(projects[0])"]
    L -->|no (error)| N["Show empty state"]
    M --> O["Dashboard.loadAll()"]
    O --> P["Promise.all: fetchHierarchy + fetchMetrics"]
    P --> Q["AppState.setData(hierarchy, metrics, versions)"]
    Q --> R["State subscribers fire"]
    R --> S["Dashboard.renderAll()"]
    S --> T["_renderSnapshotCards()"]
    S --> U["VersionAccordion.render()"]
    S --> V["_renderSidebar()"]
    S --> W["_populateVersionDropdown()"]
    S --> X["_populateReviewDropdown()"]
```

---

## User Interaction Flows

### Project Selection Loop

```mermaid
flowchart LR
    P1["User selects project<br/>(header dropdown)"] --> P2["Dashboard.onProjectChange()"]
    P2 --> P3["AppState.selectProject(proj)<br/>resets version + review"]
    P3 --> P4["Dashboard.loadAll()"]
    P4 --> P5["API.fetchHierarchy + fetchMetrics"]
    P5 --> P6["AppState.setData()"]
    P6 --> P7["renderAll() fires<br/>via subscriber"]
```

### Version Selection Loop

```mermaid
flowchart LR
    V1["User selects version<br/>(header dropdown OR<br/>accordion header click OR<br/>sidebar item click)"] --> V2["Dashboard.onVersionChange()<br/>OR VersionAccordion.onVersionHeaderClick()<br/>OR Dashboard.onSidebarVersionClick()"]
    V2 --> V3["AppState.selectVersion(version)"]
    V3 --> V4["API.fetchMetrics(pid, vid, null)"]
    V4 --> V5["AppState.setData(metrics)"]
    V5 --> V6["_renderSnapshotCards()<br/>_renderContextBanner()<br/>review dropdown updates"]
```

### Review Selection + Drawer Open Loop

```mermaid
flowchart LR
    R1["User clicks review row<br/>(accordion OR sidebar)"] --> R2["VersionAccordion.onReviewClick()<br/>OR Dashboard.onSidebarReviewClick()"]
    R2 --> R3["AppState.selectReview(review)"]
    R3 --> R4["AppState.openDrawer('review', data)"]
    R4 --> R5["State subscriber fires:<br/>'drawerOpen' changed"]
    R5 --> R6["Dashboard._syncDrawer()"]
    R6 --> R7["CSS: #v2-drawer.open<br/>#v2-main.drawer-open"]
    R6 --> R8["ReviewDetail.renderReview(summary)<br/>(Sprint 1 — full details panel)"]
    R8 --> R9["_loadDrawerDetail() async"]
    R9 --> R10["API.fetchReviewDetail(pid, rid)"]
    R10 --> R11["ReviewDetail.renderReview(full)<br/>updates drawer with:<br/>• Version ID + Persona + Prompt<br/>• Top 3 Risks (always visible)<br/>• Artifact provenance chips<br/>• Weaknesses + status + note<br/>• Decision Points<br/>• Lineage banner (Sprint 2)<br/>• Create New Review form (Sprint 2)"]
```

> **Sprint 1:** `ReviewDetail` (`static/v2/js/review_detail.js`) is the primary drawer renderer for reviews. It is aliased as `window.DetailPanel` for backward compatibility. Compare remains a secondary explicit button action — it does **not** open on review click.

### Review Iteration Flow (Sprint 2)

```mermaid
flowchart LR
    I1["User opens Review<br/>Full Details drawer"] --> I2["ReviewDetail.renderReview(r)<br/>renders lineage banner if<br/>previous_review_id present"]
    I2 --> I3["User clicks<br/>'New Iteration' button"]
    I3 --> I4["onToggleIterationForm(rid)<br/>reveals iteration form<br/>(explicit user action only)"]
    I4 --> I5["User selects persona<br/>(same or different)<br/>+ optional custom prompt"]
    I5 --> I6["User clicks<br/>'Create New Review'"]
    I6 --> I7["onCreateIteration(btn)<br/>collects persona + prompt"]
    I7 --> I8["API.createReviewIteration(pid, rid,<br/>newPersona, customPrompt)"]
    I8 --> I9["POST /hierarchy/reviews/{rid}/iterate"]
    I9 --> I10["handle_create_review_iteration()<br/>handlers/review.py"]
    I10 --> I11["create_review_iteration()<br/>services/review.py"]
    I11 --> I12["store.create_review()<br/>previous_review_id = rid<br/>persona = new or base<br/>artifact_refs = base refs"]
    I12 --> I13["Returns new review summary<br/>review_id, persona_used,<br/>previous_review_id, persona_changed"]
    I13 --> I14["_renderIterationResult(result)<br/>confirmation card in drawer<br/>shows new ID + lineage"]
```

> **Sprint 2 rules:**
> - The original review is **never modified**. A new review is always created.
> - Persona selection is **optional** — defaults to base review persona when omitted.
> - Base review becomes **context input** for the new review execution.
> - Open decision points from the base review are **carried forward** into the new review.

### Refresh Loop (no page reload)

```mermaid
flowchart LR
    RF1["User clicks ↺ Refresh"] --> RF2["Dashboard.onRefresh()"]
    RF2 --> RF3["_toast('Refreshing…')"]
    RF3 --> RF4["Dashboard.loadAll(silent=false)"]
    RF4 --> RF5["AppState.set('loading', true)"]
    RF5 --> RF6["Promise.all: fetchHierarchy + fetchMetrics"]
    RF6 --> RF7["AppState.setData(new data)"]
    RF7 --> RF8["AppState.set('loading', false)"]
    RF8 --> RF9["All subscribers re-render<br/>with fresh data"]
    RF9 --> RF10["_renderLastUpdated(timestamp)"]
```

---

## Full Application State Machine

```mermaid
stateDiagram-v2
    [*] --> Loading: Dashboard.init()
    Loading --> NoProject: projects = []
    Loading --> ProjectSelected: selectProject(p)

    NoProject --> ProjectSelected: user creates project (v1 tab)

    ProjectSelected --> DataLoaded: loadAll() resolves
    DataLoaded --> VersionSelected: selectVersion(v)
    DataLoaded --> DataLoaded: onRefresh()

    VersionSelected --> ReviewSelected: selectReview(r)
    VersionSelected --> VersionSelected: onVersionChange()

    ReviewSelected --> DrawerOpen: openDrawer('review', r)
    ReviewSelected --> ReviewSelected: onReviewChange() → metrics refresh

    DrawerOpen --> ReviewSelected: closeDrawer()
    DrawerOpen --> DrawerOpen: fetchReviewDetail() resolves → update content
    DrawerOpen --> IterationFormOpen: user clicks 'New Iteration' button *(Sprint 2)*
    IterationFormOpen --> DrawerOpen: user cancels form
    IterationFormOpen --> IterationCreated: onCreateIteration() → POST /iterate
    IterationCreated --> DrawerOpen: result card shown; user refreshes list
```
