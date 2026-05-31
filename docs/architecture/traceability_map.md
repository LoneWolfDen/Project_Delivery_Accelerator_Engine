# Traceability Map

**Project Delivery Accelerator Engine — V2 Full Traceability**

> Maps every UI action to its logic path, API endpoint, data entity, and diagram reference. No orphan components. Naming is consistent across all layers.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| `→` | Data/control flows to |
| `[file]` | Source file reference |
| `{entity}` | Data entity from data model |
| `GET/POST` | HTTP method |

---

## 1. UI → Logic → API → Data → Diagram Map

### 1.1 Page Load

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | `dashboard_v2.html` | `static/v2/dashboard_v2.html` | Entry point, served by server.py |
| **Logic** | `Dashboard.init()` | `static/v2/js/dashboard.js` | Bootstraps all components |
| **Logic** | `AppState.selectProject()` | `static/v2/js/state.js` | Sets initial project |
| **API** | `GET /api/projects` | `server.py → services/project.py` | Returns `{projects:[]}` |
| **Data** | `{Project}` | `models/project.py` | id, name, phase |
| **Diagram** | Application Flow §1 | `docs/architecture/application_flow.md` | Startup sequence |

---

### 1.2 Version Selection

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | Version dropdown | `static/v2/dashboard_v2.html` `#v2-version-select` | Header control |
| **UI** | Accordion header click | `static/v2/js/accordion.js` `onVersionHeaderClick()` | Expand/collapse |
| **UI** | Sidebar version click | `static/v2/js/dashboard.js` `onSidebarVersionClick()` | Left panel |
| **Logic** | `AppState.selectVersion()` | `static/v2/js/state.js` | Resets review + reviews[] |
| **Logic** | `Dashboard.onVersionChange()` | `static/v2/js/dashboard.js` | Calls fetchMetrics |
| **API** | `GET /hierarchy/metrics?version_id=` | `server.py → services/hierarchy.py` | Scoped metrics |
| **Data** | `{Version}` | `models/hierarchy.py → Version` | version_id, label, review_ids |
| **Data** | `{MetricsPayload}` | `models/hierarchy.py → get_metrics()` | risks, gaps, etc. |
| **Diagram** | Application Flow §Version Selection | `docs/architecture/application_flow.md` | Selection loop |
| **Diagram** | Sequence 2 | `docs/architecture/sequence_flows.md` | Full message sequence |

---

### 1.3 Review Selection → Drawer

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | Review row click | `static/v2/js/accordion.js` `onReviewClick()` | Inside accordion |
| **UI** | Sidebar review click | `static/v2/js/dashboard.js` `onSidebarReviewClick()` | Left panel |
| **Logic** | `AppState.selectReview()` | `static/v2/js/state.js` | Updates selectedReview |
| **Logic** | `AppState.openDrawer('review', data)` | `static/v2/js/state.js` | Sets drawerOpen=true |
| **Logic** | `Dashboard._syncDrawer()` | `static/v2/js/dashboard.js` | CSS class mutations |
| **Logic** | `DetailPanel.renderReview(summary)` | `ui/v2/components/DetailPanel.js` | Immediate render |
| **Logic** | `Dashboard._loadDrawerDetail()` | `static/v2/js/dashboard.js` | Async full fetch |
| **API** | `GET /hierarchy/reviews/{rid}` | `server.py → services/hierarchy.py` | Full review object |
| **Data** | `{Review}` | `models/hierarchy.py → Review` | findings, weaknesses, questions |
| **Diagram** | Sequence 3 | `docs/architecture/sequence_flows.md` | Drawer open sequence |
| **Diagram** | Logic Flow §6 | `docs/architecture/logic_flow.md` | Drawer loading logic |

---

### 1.4 Refresh (No Reload)

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | ↺ Refresh button | `static/v2/dashboard_v2.html` `#v2-refresh-btn` | Header control |
| **Logic** | `Dashboard.onRefresh()` | `static/v2/js/dashboard.js` | Calls loadAll |
| **Logic** | `AppState.set('loading', true)` | `static/v2/js/state.js` | Disables button |
| **API** | `GET /hierarchy` | `server.py → services/hierarchy.py` | Fresh tree |
| **API** | `GET /hierarchy/metrics` | `server.py → services/hierarchy.py` | Fresh metrics |
| **Logic** | `AppState.setData()` | `static/v2/js/state.js` | Sets lastUpdated |
| **Logic** | `Dashboard.renderAll()` | `static/v2/js/dashboard.js` | Re-renders all regions |
| **Diagram** | Application Flow §Refresh Loop | `docs/architecture/application_flow.md` | Refresh flow |
| **Diagram** | Sequence 4 | `docs/architecture/sequence_flows.md` | Full refresh sequence |

---

### 1.5 Expand / Collapse All

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | "Expand All" button | `static/v2/dashboard_v2.html` `#v2-expand-all-btn` | Section B header |
| **Logic** | `Dashboard.onExpandAll()` | `static/v2/js/dashboard.js` | Delegates to Accordion |
| **Logic** | `VersionAccordion.toggleExpandAll()` | `static/v2/js/accordion.js` | CSS class toggle |
| **Data** | No API call | — | Pure DOM state |
| **Diagram** | Sequence 6 | `docs/architecture/sequence_flows.md` | Toggle sequence |

---

### 1.6 Drawer Close

| Layer | Component | File | Notes |
|-------|-----------|------|-------|
| **UI** | × button | `static/v2/dashboard_v2.html` `#v2-drawer-close` | Drawer header |
| **UI** | Esc key | `ui/v2/layout/MainLayout.js` `_handleKeydown()` | Keyboard shortcut |
| **Logic** | `AppState.closeDrawer()` | `static/v2/js/state.js` | drawerOpen=false |
| **Logic** | `Dashboard._syncDrawer(false)` | `static/v2/js/dashboard.js` | Removes CSS classes |
| **Data** | No API call | — | Pure state change |
| **Diagram** | Sequence 5 | `docs/architecture/sequence_flows.md` | Close sequence |

---

## 2. Component Mapping

| V2 Component | File | Renders | Data Source | State Keys Read |
|--------------|------|---------|-------------|-----------------|
| Header | `ui/v2/components/Header.js` | Dropdowns, context label | AppState | projects, versions, selectedVersion, selectedReview |
| Sidebar | `ui/v2/components/Sidebar.js` | Version + review list | AppState | versions, selectedVersion, selectedReview |
| VersionAccordion | `static/v2/js/accordion.js` | Accordion items + review rows | versions[] | versions (via render param) |
| Cards | `ui/v2/components/Cards.js` | Snapshot metric tiles | MetricsPayload | metrics |
| DetailPanel | `ui/v2/components/DetailPanel.js` | Version or review detail | API response | drawerEntity |
| MainLayout | `ui/v2/layout/MainLayout.js` | CSS class mutations only | AppState events | drawerOpen, loading |
| Dashboard | `static/v2/js/dashboard.js` | Orchestrates all above | AppState + API | all |

---

## 3. API Endpoint → Component Mapping

| Endpoint | HTTP | Called By | Returns | Renders In |
|----------|------|-----------|---------|------------|
| `/api/projects` | GET | `API.fetchProjects()` | `Project[]` | Header project dropdown |
| `/api/projects/{pid}/hierarchy` | GET | `API.fetchHierarchy()` | `HierarchyPayload` | Sidebar, Accordion |
| `/api/projects/{pid}/hierarchy/metrics` | GET | `API.fetchMetrics()` | `MetricsPayload` | Snapshot Cards, Context Banner |
| `/api/projects/{pid}/hierarchy/versions` | GET | `API.fetchVersions()` | `Version[]` | Header version dropdown |
| `/api/projects/{pid}/hierarchy/reviews` | GET | `API.fetchReviews()` | `Review[]` | Header review dropdown |
| `/api/projects/{pid}/hierarchy/reviews/{rid}` | GET | `API.fetchReviewDetail()` | `Review (full)` | Detail Drawer (review) |
| `/api/projects/{pid}/hierarchy/versions/{vid}` | GET | `API.fetchVersionDetail()` | `Version (full)` | Detail Drawer (version) |

---

## 4. Data Entity → UI Mapping

| Entity | Attribute | Displayed In | Component |
|--------|-----------|--------------|-----------|
| `{Project}` | `name` | Header dropdown | `#v2-project-select` |
| `{Version}` | `version_id`, `label` | Header dropdown, Sidebar, Accordion header | Version controls |
| `{Version}` | `review_count` | Accordion header badge, Sidebar badge | VersionAccordion |
| `{Version}` | `active_review_id` | Accordion review "Active" badge | VersionAccordion |
| `{Review}` | `review_id`, `persona` | Accordion review row, Header review dropdown | Review rows |
| `{Review}` | `quality_status` | Status dot, badge | Review rows + DetailPanel |
| `{Review}` | `total_findings` | Amber badge on review row | VersionAccordion |
| `{MetricsPayload}` | `total_versions` | Snapshot card | Cards.js |
| `{MetricsPayload}` | `total_reviews` | Snapshot card | Cards.js |
| `{MetricsPayload}` | `risks_identified` | Snapshot card (red) | Cards.js |
| `{MetricsPayload}` | `gaps_identified` | Snapshot card (amber) | Cards.js |
| `{MetricsPayload}` | `data_source` | Context banner | ContextBanner |
| `{Review}` | `findings{}` | Findings blocks | DetailPanel.js |
| `{Review}` | `weaknesses[]` | Open weaknesses section | DetailPanel.js |
| `{Review}` | `questions[]` | Open questions section | DetailPanel.js |

---

## 5. Impact Analysis

> What breaks if a file changes?

| File Changed | Immediate Impact | Downstream Impact |
|--------------|-----------------|-------------------|
| `state.js` — change notify logic | All subscriber components stop updating | Full UI freezes on state changes |
| `api.js` — change endpoint path | Data fetch fails silently | Snapshot cards show stale/mock data |
| `accordion.js` — change `.expanded` class name | Accordion CSS transitions break | Layout broken (CSS targets that class) |
| `dashboard.js` — remove renderAll() | Components not re-rendered after state changes | Stale UI after project/version change |
| `server.py` — remove `_resolve_ui_version()` | `?ui=v2` param ignored | v2 unreachable via URL override |
| `services/hierarchy.py` — change `get_metrics()` response shape | MetricsPayload shape mismatch | Cards.js renders 0 for all values |
| `models/hierarchy.py` — rename `review_ids` | HierarchyStore breaks version→review links | Reviews not linked, active_review_id invalid |
| `theme.css` — remove `--primary` token | All primary-coloured elements lose colour | Accordion chevrons, badges, snapshot values |

---

## 6. Naming Consistency Audit

| Concept | Python (server/models) | JS (state/api) | HTML (template) | CSS (components) |
|---------|----------------------|----------------|-----------------|-----------------|
| Version identifier | `version_id` | `version_id` | `data-version-id` | `.accordion-version-id` |
| Review identifier | `review_id` | `review_id` | `data-review-id` | `.review-item-id` |
| Project identifier | `id` (Project) | `id` (projects[]) | `v2-project-select` value | — |
| Active review | `active_review_id` | `active_review_id` | `data-active` badge | `.active-review` |
| Quality status | `quality_status` | `quality_status` | `data-quality` | `.badge-green/amber/default` |
| Drawer open | `drawerOpen` (state) | `drawerOpen` | `#v2-drawer.open` | `.open` class |
| Loading | `loading` (state) | `loading` | `#v2-refresh-btn[disabled]` | `.spin` class |
| Version label | `label` | `label` | option text | `.accordion-version-label` |
