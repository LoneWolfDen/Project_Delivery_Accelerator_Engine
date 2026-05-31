# System Overview

**Project Delivery Accelerator Engine — V2 Architecture**

> This document describes the full system architecture: runtime layers, component boundaries, and data flow direction. Every node links to a real file in this repository.

---

## Linked Components

| Layer | File |
|-------|------|
| Entry point (v2) | `static/v2/dashboard_v2.html` |
| Server | `server.py` |
| State store | `static/v2/js/state.js` |
| API module | `static/v2/js/api.js` |
| Accordion | `static/v2/js/accordion.js` |
| Orchestrator | `static/v2/js/dashboard.js` |
| Detail drawer | `ui/v2/components/DetailPanel.js` |
| Cards | `ui/v2/components/Cards.js` |
| Header | `ui/v2/components/Header.js` |
| Sidebar | `ui/v2/components/Sidebar.js` |
| Layout coordinator | `ui/v2/layout/MainLayout.js` |
| Hierarchy service | `services/hierarchy.py` |
| Hierarchy store | `models/hierarchy.py` |
| Data persistence | `db/hierarchy_store_sql.py` |

---

## System Architecture Diagram

```mermaid
graph TB
    subgraph Browser["Browser — Vanilla JS SPA"]
        direction TB
        HTML["dashboard_v2.html<br/>(entry point)"]
        STATE["AppState<br/>state.js<br/>(observable store)"]
        API_MOD["API module<br/>api.js<br/>(fetch wrappers)"]

        subgraph Components["UI Components"]
            HEADER["Header.js<br/>dropdowns + refresh"]
            SIDEBAR["Sidebar.js<br/>version list"]
            ACCORDION["VersionAccordion<br/>accordion.js"]
            CARDS["Cards.js<br/>snapshot metrics"]
            DETAIL["DetailPanel.js<br/>drawer renderer"]
        end

        DASH["Dashboard.js<br/>(orchestrator)"]
        LAYOUT["MainLayout.js<br/>(layout coordinator)"]
    end

    subgraph Server["Python Server (http.server)"]
        SRV["server.py<br/>AcceleratorHandler"]
        subgraph Handlers["handlers/"]
            H_HIER["hierarchy.py"]
            H_PROJ["project.py"]
            H_REV["review.py"]
        end
        subgraph Services["services/"]
            S_HIER["hierarchy.py"]
            S_PROJ["project.py"]
        end
    end

    subgraph Persistence["Persistence Layer"]
        STORE["HierarchyStore<br/>models/hierarchy.py"]
        SQL["HierarchyStoreSQLite<br/>db/hierarchy_store_sql.py"]
        FILES["JSON files<br/>projects_data/"]
        DB[("SQLite DB<br/>accelerator.db")]
    end

    HTML -->|"loads"| STATE
    HTML -->|"loads"| API_MOD
    HTML -->|"boots"| DASH
    DASH -->|"orchestrates"| Components
    DASH -->|"reads/writes"| STATE
    DASH -->|"calls"| API_MOD
    STATE -->|"notifies"| Components
    STATE -->|"notifies"| LAYOUT
    API_MOD -->|"HTTP fetch"| SRV
    SRV -->|"routes"| Handlers
    Handlers -->|"calls"| Services
    Services -->|"uses"| STORE
    STORE -->|"dual-write"| SQL
    STORE -->|"dual-write"| FILES
    SQL -->|"persists"| DB
```

---

## Layer Descriptions

### Browser Layer
- **dashboard_v2.html** — Static HTML shell. No server-side templating. Served as a flat file by `server.py`.
- **AppState** — Singleton observable store. Holds `projects`, `selectedProject`, `selectedVersion`, `selectedReview`, `metrics`, `hierarchy`, `drawerOpen`. Components subscribe to specific keys; changes notify only relevant subscribers.
- **API module** — All `fetch` calls isolated here. Supports mock data fallback (`window.V2_USE_MOCK = true`) for Step 1 development without a running backend.
- **Dashboard.js** — Orchestrator. Calls `API`, writes to `AppState`, renders all regions. Auto-boots on `DOMContentLoaded`.
- **Components** — Pure renderers. Receive data, return HTML strings or mutate specific DOM nodes. No direct API calls.
- **MainLayout.js** — Handles CSS class mutations for drawer, loading state, keyboard events. No business logic.

### Server Layer
- **server.py** — `http.server.HTTPServer` with `AcceleratorHandler`. Zero business logic. Routes `GET /` to `static/index.html` (v1) or `static/v2/dashboard_v2.html` (v2) based on `--ui` flag or `?ui=` query param.
- **handlers/** — Thin request parsers. Extract path params, call services, return JSON.
- **services/** — All business logic. Hierarchy, projects, reviews, intelligence, proposals.

### Persistence Layer
- **HierarchyStore** — File-based JSON persistence (`projects_data/{pid}/hierarchy/`).
- **HierarchyStoreSQLite** — SQLite-backed alternative. Selected via admin config (`sqlite_write_enabled`).
- Dual-write mode is the default: both stores receive every write.

---

## UI Version Selection Flow

```mermaid
flowchart LR
    START([HTTP GET /]) --> PARSE{Parse ?ui= param}
    PARSE -->|"?ui=v2"| V2["Serve v2/dashboard_v2.html"]
    PARSE -->|"?ui=v1 or absent"| FLAG{Check --ui flag}
    FLAG -->|"--ui v2"| V2
    FLAG -->|"--ui v1 (default)"| V1["Serve index.html (v1)"]
    V1 -->|"unchanged"| V1_APP["V1 dark-theme SPA"]
    V2 -->|"isolated"| V2_APP["V2 pastel SPA"]
```

**Key constraint:** v1 and v2 are fully isolated. No shared JS or CSS. v1 (`static/index.html`) is never modified.
