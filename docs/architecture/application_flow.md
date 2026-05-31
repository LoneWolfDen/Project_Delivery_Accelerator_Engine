# Application Flow (End-to-End)

## Purpose
End-to-end user journey from loading the dashboard through project selection,
version/review navigation, running a review, and manual data refresh.
Shows decision points, selection loops, and refresh loops.

---

## Diagram

```mermaid
flowchart TD
    START([User opens http://localhost:8080])

    subgraph BOOT["Boot Sequence"]
        L1["GET /api/health\n→ {status, version, app}"]
        L2["GET /api/projects\n→ {projects:[...]}"]
        L3{"projects.length > 0?"}
        L4["Populate <select> project dropdown\nstate.projects = [...]\nstate.current = projects[0]"]
        L5["Show 'No projects' message\nstate.current = null"]
        L6["GET /api/backends\n→ {backends:[...]}"]
        L7["render() → renderHeader() + viewDashboard()"]
    end

    subgraph PROJECT_SELECT["Project Selection Loop"]
        PS1["User selects project from <select>\nonchange → selectProject(projectId)"]
        PS2["state.current = selectedProject"]
        PS3["state.tab = 'dashboard'\nstate._lastRenderedProject = projectId"]
        PS4["render() — full re-render\nrenderHeader() + active tab view"]
    end

    subgraph DASHBOARD["Dashboard Load  (viewDashboard)"]
        D1["GET /api/projects/{pid}/hierarchy/metrics\n?version_id=&review_id=\n→ {total_versions, total_reviews, phases, selected_version, selected_review, stat counts}"]
        D2["Render stat grid:\ntotal_versions · total_reviews ·\nrisks · gaps · action_items"]
        D3["Render phase progress bar\nphases[].is_current highlights current phase"]
        D4["Render trend chart (last 5 versions)"]
    end

    subgraph VERSION_LOOP["Version Selection Loop  (Versions tab)"]
        V1["User clicks 'Versions' tab\nswitchTab('versions')"]
        V2["GET /api/projects/{pid}/hierarchy/versions\n→ {versions:[{version_id, label, created_at,\nreview_count, active_review_id, active_review}]}"]
        V3["state._dashVersion = versions[0].version_id\nRender accordion list"]
        V4{"User expands\nversion accordion?"}
        V5["GET /api/projects/{pid}/hierarchy/versions/{vid}\n→ {version_id, included_artifacts[], persona,\nscope, stats, review_ids[], active_review_id}"]
        V6["Render version detail panel:\nartifacts used · persona · scope · reviews linked"]
        V7{"User clicks\n'Set Active Review'?"}
        V8["POST /api/projects/{pid}/hierarchy/versions/{vid}/set-active-review\nbody: {review_id}\n→ {version_id, active_review_id, status}"]
        V9["state updated → re-render accordion item"]
        V10{"User clicks\n'Decision Readiness'?"]
        V11["GET /api/projects/{pid}/hierarchy/versions/{vid}/readiness\n→ {level, open_decisions, open_weaknesses}"]
        V12["Render readiness badge inline"]
    end

    subgraph REVIEW_LOOP["Review Selection Loop  (Reviews tab)"]
        R1["User clicks 'Reviews' tab\nswitchTab('reviews')"]
        R2["GET /api/projects/{pid}/hierarchy/reviews\n?version_id={vid}\n→ {reviews:[{review_id, persona, created_at,\ntotal_findings, quality_status, iteration_number}]}"]
        R3["state._dashReview = reviews[0].review_id\nRender review list (newest first)"]
        R4{"User clicks\nreview row?"}
        R5["GET /api/projects/{pid}/hierarchy/reviews/{rid}\n→ {review_id, findings{}, weaknesses[], decision_points[],\nquestions[], summary, deep_dive, version_context}"]
        R6["Render right-side detail panel:\nsummary · findings · weaknesses · decision points · Q&A"]
        R7{"User toggles\nweakness/decision status?"}
        R8["POST /api/projects/{pid}/hierarchy/reviews/{rid}/weakness/{wid}/status\nbody: {status: open|resolved|deferred}\n→ {weakness_id, status, updated}"]
        R9["Inline DOM update — no full re-render"]
        R10{"User clicks\n'View Diff'?"}
        R11["GET /api/projects/{pid}/hierarchy/reviews/{rid}/diff\n→ {findings:{new[], resolved[], unchanged},\nweaknesses:{new[], resolved[]},\ndecision_points:{new[], resolved[]}}"]
        R12["Render diff panel with +/− indicators"]
    end

    subgraph RUN_REVIEW["Run Review Flow  (Reviews tab — Run panel)"]
        RR1["User selects persona + AI backend\nOptionally adds injected questions / notes\nstate._reviewSort, prompt_builder_state"]
        RR2["User clicks 'Run Review' button"]
        RR3["POST /api/review\nbody: {project_id, roles[], ai_backend,\ncustom_prompt, previous_review_id,\nprompt_builder_state}\n→ {review_id, persona, findings{}, weaknesses[],\ndecision_points[], summary, questions[]}"]
        RR4{"HTTP 200?"}
        RR5["toast('Review complete ✓')\nUpdate state._dashReview = new review_id"]
        RR6["Re-render review list — new review appears at top\nIteration number incremented (R1 → R2 → …)"]
        RR7["toast error message\nNo state change"]
    end

    subgraph REFRESH["Manual Refresh Loop"]
        RF1["User clicks 'Refresh' button\nor switchTab() to same tab"]
        RF2{"same tab AND\nsame project?"]
        RF3["Skip full re-render\nscrollTo(top)"]
        RF4["render() — re-fetch all tab data\nclear innerHTML → loading bar → re-inject"]
    end

    %% ── Connections ────────────────────────────────────────────
    START --> L1 --> L2 --> L3
    L3 -- "yes" --> L4 --> L6 --> L7
    L3 -- "no" --> L5 --> L6 --> L7

    L7 --> D1 --> D2 --> D3 --> D4

    D4 --> PS1
    PS1 --> PS2 --> PS3 --> PS4 --> D1

    D4 --> V1
    V1 --> V2 --> V3 --> V4
    V4 -- "yes" --> V5 --> V6
    V6 --> V7
    V7 -- "yes" --> V8 --> V9 --> V4
    V7 -- "no" --> V10
    V10 -- "yes" --> V11 --> V12 --> V4
    V10 -- "no" --> V4

    D4 --> R1
    R1 --> R2 --> R3 --> R4
    R4 -- "yes" --> R5 --> R6
    R6 --> R7
    R7 -- "yes" --> R8 --> R9 --> R4
    R7 -- "no" --> R10
    R10 -- "yes" --> R11 --> R12 --> R4
    R10 -- "no" --> R4

    R4 -- "run review" --> RR1 --> RR2 --> RR3 --> RR4
    RR4 -- "success" --> RR5 --> RR6 --> R2
    RR4 -- "error" --> RR7 --> R4

    V4 -- "refresh" --> RF1
    R4 -- "refresh" --> RF1
    RF1 --> RF2
    RF2 -- "yes" --> RF3
    RF2 -- "no" --> RF4 --> D1
```

---

## Inputs and Outputs

| Flow Step | Input | Output |
|---|---|---|
| Boot | Browser `DOMContentLoaded` | `state.projects[]`, `state.current`, initial render |
| Project Selection | `<select>` `onchange` event → `projectId` | `state.current` updated; full tab re-render |
| Dashboard Load | `project_id`, optional `version_id`, `review_id` | Stat grid, phase bar, trend chart |
| Version Loop | `project_id` | Accordion of versions; detail panel on expand |
| Review Loop | `project_id`, `version_id` filter | Review list; right-side detail panel on click |
| Run Review | `roles[]`, `ai_backend`, `custom_prompt`, `prompt_builder_state` | New review persisted; list prepended |
| Refresh | User action or tab switch | Refetched and re-rendered tab HTML |

---

## State Variables Involved

| Variable | Set by | Used by |
|---|---|---|
| `state.projects` | Boot fetch `/api/projects` | Header dropdown |
| `state.current` | `selectProject()` | All API calls (`pid`) |
| `state.tab` | `switchTab()` | `render()` view dispatcher |
| `state._dashVersion` | Version tab init | Dashboard metrics API query param |
| `state._dashReview` | Review tab init / after run | Dashboard metrics API query param |
| `state._versionSort` | Sort bar click | Version list sort order |
| `state._reviewSort` | Sort bar click | Review list sort order |
| `state._lastRenderedProject` | After `render()` | Refresh-skip guard |

---

## Edge Cases

| Condition | Behaviour |
|---|---|
| No projects exist | Header shows "No projects", dashboard shows empty state card |
| Project has no versions | `GET /hierarchy/metrics` returns `total_versions: 0`; stat shows `0` |
| Project has no reviews | Review list renders empty state with guidance message |
| API returns error | `toast(error.message, 'err')` shown; prior DOM unchanged |
| Same tab / same project clicked | Scroll-to-top only — no redundant API fetch |

---

## Linked Components

| Component | File |
|---|---|
| SPA entry & `state` object | `static/index.html` |
| `renderHeader()` | `static/index.html` |
| `render()` dispatcher | `static/index.html` |
| `viewDashboard()` | `static/index.html` |
| `viewVersions()` | `static/index.html` |
| `viewReviews()` | `static/index.html` |
| Dashboard metrics API | `GET /api/projects/{pid}/hierarchy/metrics` → `services/hierarchy.py` |
| Review run API | `POST /api/review` → `handlers/review.py` → `services/review.py` |
