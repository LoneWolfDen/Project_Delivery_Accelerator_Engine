# Logic Flow

**Project Delivery Accelerator Engine — V2 Internal Logic Flow**

> This document maps the decision logic, branching conditions, and data transformation steps within each layer. Covers mock/live switching, state notification, cascade resets, and drawer loading.

---

## Linked Components

| Logic Area | File | Key Functions |
|------------|------|---------------|
| UI version resolution | `server.py` | `_resolve_ui_version()` |
| Mock/live API switch | `static/v2/js/api.js` | `_useMock()`, all fetch functions |
| State notification | `static/v2/js/state.js` | `_notify()`, `set()`, `subscribe()` |
| Cascade resets | `static/v2/js/state.js` | `selectProject()`, `selectVersion()` |
| Data load decision | `static/v2/js/dashboard.js` | `loadAll()`, `onVersionChange()` |
| Drawer load | `static/v2/js/dashboard.js` | `_loadDrawerDetail()` |
| Accordion expand | `static/v2/js/accordion.js` | `onVersionHeaderClick()` |
| Metrics scope | `services/hierarchy.py` | `get_metrics()` |
| Weakness persistence | `services/review.py` | `update_weakness_note()`, `update_weakness_status()` *(Sprint 1)* |
| Reconciliation selection | `services/reconciliation.py` | `save_reconciliation_selection()` *(Sprint 3)* |
| Reconciliation engine | `services/reconciliation.py` | `run_reconciliation()` *(Sprint 3)* |
| Drawer load | `static/v2/js/dashboard.js` | `_loadDrawerDetail()` |
| Accordion expand | `static/v2/js/accordion.js` | `onVersionHeaderClick()` |
| Metrics scope | `services/hierarchy.py` | `get_metrics()` |

---

## 1. UI Version Resolution Logic

```mermaid
flowchart TD
    A["HTTP GET / arrives"] --> B["_parse_path() → query dict"]
    B --> C{"query.get('ui')"}
    C -->|"'v1' or 'v2'"| D["Return query param value<br/>(overrides startup flag)"]
    C -->|"absent or invalid"| E["Return UI_VERSION module constant<br/>(set by --ui flag at startup)"]
    D --> F{"resolved == 'v2'?"}
    E --> F
    F -->|yes| G["_serve_static('v2/dashboard_v2.html')"]
    F -->|no| H["_serve_static('index.html')"]
```

**Decision point:** Query param always wins. This allows `?ui=v2` to load v2 even when server started with `--ui v1`.

---

## 2. API Mock / Live Switch Logic

```mermaid
flowchart TD
    A["API.fetchXxx() called"] --> B{"window.V2_USE_MOCK !== false?"}
    B -->|true (default)| C["Return MOCK_DATA constant<br/>No HTTP call made<br/>Instant, deterministic"]
    B -->|false (Step 2)| D["_request(method, path, body)"]
    D --> E["fetch(path, opts)"]
    E --> F{"res.ok?"}
    F -->|yes| G["Return res.json()"]
    F -->|no| H["Return { error: 'HTTP 4xx/5xx' }"]
    E -->|"Network error"| I["Return { error: err.message }"]
    G --> J["Caller receives data"]
    H --> J
    I --> J
```

**Step 2 migration:** Set `window.V2_USE_MOCK = false` in `dashboard_v2.html` script block. No other changes needed — API shapes are identical between mock and live.

---

## 3. State Notification Logic

```mermaid
flowchart TD
    A["AppState.set(keyOrObject, value)"] --> B{"Value changed?<br/>(strict equality)"}
    B -->|no| C["No-op — skip notification"]
    B -->|yes| D["_state[key] = value<br/>push to changed[]"]
    D --> E["_notify(changed[])"]
    E --> F["For each changed key:<br/>get subscribers Set"]
    F --> G["Call each fn once<br/>(dedup via called Set)"]
    E --> H["Get wildcard '*' subscribers"]
    H --> I["Call each fn once with<br/>all changed keys + full state"]
```

**Key behaviour:** A subscriber registered for `'selectedVersion'` only fires when `selectedVersion` changes — not on every state mutation. Wildcard `'*'` subscribers receive all changes in one batched call.

---

## 4. Cascade Reset Logic

```mermaid
flowchart TD
    A["selectProject(proj)"] --> B["set({<br/>  selectedProject: proj,<br/>  selectedVersion: null,<br/>  selectedReview: null,<br/>  versions: [],<br/>  reviews: [],<br/>  metrics: null<br/>})"]
    B --> C["6 keys changed → 6 notifications<br/>(batched in one _notify call)"]

    D["selectVersion(version)"] --> E["set({<br/>  selectedVersion: version,<br/>  selectedReview: null,<br/>  reviews: []<br/>})"]
    E --> F["3 keys changed → components that<br/>watch selectedVersion update<br/>(review dropdown cleared)"]

    G["selectReview(review)"] --> H["set('selectedReview', review)"]
    H --> I["1 key changed → only review-watching<br/>components update"]
```

**Purpose:** Cascading ensures dropdowns never show stale data from a previous selection. Changing project clears version; changing version clears review.

---

## 5. Data Load Decision Logic

```mermaid
flowchart TD
    A["loadAll(silent)"] --> B{"selectedProject set?"}
    B -->|no| C["Early return — nothing to load"]
    B -->|yes| D{"silent == false?"}
    D -->|yes| E["AppState.set('loading', true)<br/>setLoading indicator in header"]
    D -->|no| F["Skip loading indicator"]
    E --> G["Promise.all([fetchHierarchy, fetchMetrics])"]
    F --> G
    G --> H["Extract versions from tree<br/>sort newest-first"]
    H --> I["AppState.setData({<br/>  hierarchy, metrics, versions,<br/>  lastUpdated: now<br/>})"]
    I --> J{"selectedVersion already set?"}
    J -->|yes| K["Skip default selection"]
    J -->|no| L["selectVersion(versions[0])<br/>(latest version)"]
    L --> M["Find active review for latest version"]
    M --> N["selectReview(activeReview || reviews[0])"]
```

---

## 6. Drawer Loading Logic

```mermaid
flowchart TD
    A["AppState.openDrawer(type, data)"] --> B["_syncDrawer() fires<br/>(subscriber)"]
    B --> C["CSS: drawer.open, main.drawer-open"]
    C --> D{"entity.type?"}
    D -->|'review'| E["ReviewDetail.renderReview(summary data)<br/>(Sprint 1 — fast, shows immediately)"]
    D -->|'version'| F["DetailPanel.renderVersion(summary data)<br/>(fast — shows immediately)"]
    E --> G["_loadDrawerDetail(entity) async"]
    F --> G
    G --> H{"entity.type?"}
    H -->|'review'| I["API.fetchReviewDetail(pid, rid)"]
    H -->|'version'| J["API.fetchVersionDetail(pid, vid)"]
    I --> K{"full data returned?"}
    J --> K
    K -->|yes| L["ReviewDetail.renderReview(full)<br/>replaces drawer — shows provenance,<br/>weakness notes, all findings"]
    K -->|error/404| M["Drawer keeps summary view<br/>(non-blocking — no error shown)"]
```

**UX pattern:** Drawer always shows immediately with summary data. Full detail loads async and replaces content silently. Never blocks the user.

---

## 7. Backend Metrics Scope Logic (server-side)

```mermaid
flowchart TD
    A["GET /hierarchy/metrics?version_id=&review_id="] --> B{"version_id provided?"}
    B -->|yes| C["Load specific version"]
    B -->|no| D["Load latest version (versions[0])"]
    C --> E["Scope reviews to this version"]
    D --> E
    E --> F{"review_id provided?"}
    F -->|yes| G["Load specific review"]
    F -->|no| H["Load active_review for version<br/>(validated, falls back to latest)"]
    G --> I["Count findings from review.findings"]
    H --> I
    I --> J["Build MetricsPayload:<br/>total_versions, total_reviews,<br/>risks, gaps, constraints,<br/>dependencies, assumptions,<br/>data_source, trend, available_reviews"]
    J --> K["Return JSON"]
```

**Location:** `services/hierarchy.py → get_metrics()` and `models/hierarchy.py → HierarchyStore.get_metrics()`

---

## 8. Weakness Note + Status Persistence Logic (Sprint 1)

```mermaid
flowchart TD
    A["User changes weakness status dropdown<br/>ReviewDetail.onWeaknessStatus(el)"] --> B["Optimistic UI: update CSS class<br/>(immediate — no wait)"]
    B --> C["API.updateWeaknessStatus(pid, rid, wid, status)"]
    C --> D["POST /hierarchy/reviews/{rid}/weakness/{wid}/status"]
    D --> E["handlers/review.handle_weakness_status()"]
    E --> F["services/review.update_weakness_status()"]
    F --> G{"status in DECISION_STATUSES?"}
    G -->|no| H["Return {error: 'Invalid status'}"]
    G -->|yes| I["store.get_review(rid)"]
    I --> J["Find weakness by id"]
    J --> K["weakness['status'] = status<br/>(preserves user_note)"]
    K --> L["store.update_review_weaknesses(rid, weaknesses)"]
    L --> M["SQLite UPDATE + file dual-write"]

    N["User blurs weakness note textarea<br/>ReviewDetail.onWeaknessNote(el)"] --> O["API.updateWeaknessNote(pid, rid, wid, note)"]
    O --> P["POST /hierarchy/reviews/{rid}/weakness/{wid}/note"]
    P --> Q["handlers/review.handle_weakness_note()"]
    Q --> R["services/review.update_weakness_note()"]
    R --> S["store.get_review(rid)"]
    S --> T["Find weakness by id"]
    T --> U["weakness['user_note'] = note<br/>(preserves status)"]
    U --> V["store.update_review_weaknesses(rid, weaknesses)"]
    V --> W["SQLite UPDATE + file dual-write"]
    W --> X["Return {updated: true, user_note: note}"]
    X --> Y["Show '✓ Saved' next to textarea<br/>(2 s then clear)"]
```

**Rules:**
- Status and note updates are independent — each preserves the other field.
- Note is optional — empty string clears it; field is never required.
- Persisted within the weakness dict alongside `status`.
- No separate table required — stored as JSON within the `weaknesses` column.



---

## 9. Reconciliation Selection + Engine Logic (Sprint 3)

```mermaid
flowchart TD
    A["POST /reconciliation/select\nbody: anchor_review_id, selected_review_ids"] --> B{"anchor_review_id empty?"}
    B -->|yes| C["Return {error: 'anchor_review_id is required'}"]
    B -->|no| D{"selected_review_ids empty?"}
    D -->|yes| E["Return {error: 'must contain anchor'}"]
    D -->|no| F["Deduplicate IDs\nPrepend anchor if missing"]
    F --> G["Validate all review IDs exist in store"]
    G -->|any missing| H["Return {error: 'Review not found: {rid}'}"]
    G -->|all present| I["store.save_reconciliation_selection()\nSQLite UPSERT"]
    I --> J["Return ReconciliationSelection dict"]

    K["POST /reconciliation/run\nbody: anchor_review_id (opt), selected_review_ids (opt)"] --> L{"body has anchor + selected?"}
    L -->|no| M["Load stored selection\nfor this version"]
    M --> N{"stored selection found?"}
    N -->|no| O["Return {error: 'No selection found. POST /select first.'}"]
    N -->|yes| P["Use stored anchor + selected_review_ids"]
    L -->|yes| P
    P --> Q["Load + normalise each review\nNormalisedReviewInput per review"]
    Q --> R["_reconcile_findings_consensus()\nJaccard overlap ≥ 0.70 across ALL selected"]
    Q --> S["_reconcile_findings_divergent()\nItems missing from any review"]
    Q --> T["_merge_all_findings()\nDe-duplicated flat list"]
    Q --> U["_reconcile_decisions()\nSplit open vs confirmed by status"]
    Q --> V["_reconcile_weaknesses()\nOpen weaknesses only"]
    Q --> W["_build_provenance_summary()\nPer-review metadata + artifact_refs"]
    R & S & T & U & V & W --> X["Assemble ReconciliationOutput\nreconciliation_id = rec_{uuid12}\ncreated_at = now"]
    X --> Y["store.save_reconciliation_output()\nSQLite UPSERT reconciliation_outputs"]
    Y --> Z["Return ReconciliationOutput dict"]
```

**Key invariants:**
- `anchor_only = True` when `len(selected_review_ids) == 1` — all anchor findings become consensus; divergent is empty.
- Similarity threshold: Jaccard token overlap ≥ 0.70 (`_SIMILARITY_THRESHOLD`).
- Original reviews are **never modified** by reconciliation.
- Every output item has `source_reviews: [ProvenanceRef, ...]` — never empty.
- Re-running overwrites the stored output for the version (latest wins).
