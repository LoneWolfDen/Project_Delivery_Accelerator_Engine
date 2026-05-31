# Sequence Flows

## Purpose
Actor-level message choreography for the five most critical system operations.
Shows request/response pairs, async patterns, event bus publications, and
state changes returned to the UI.

---

## Sequence 1 — Application Boot

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as UI (index.html)
    participant Server as server.py<br/>AcceleratorHandler
    participant SvcProject as services/project.py
    participant SvcAdmin as services/admin.py
    participant DB as Data Layer<br/>(SQLite / JSON)

    User->>Browser: Navigate to http://localhost:8080
    Browser->>Server: GET /
    Server-->>Browser: 200 static/index.html (bytes)

    Note over Browser: DOMContentLoaded fires<br/>init() executes

    Browser->>Server: GET /api/health
    Server-->>Browser: 200 {status:"ok", version:"x.y.z", app:"Contexta"}

    Browser->>Server: GET /api/backends
    Server-->>Browser: 200 {backends:[{id,name,available},...]}

    Browser->>Server: GET /api/projects
    Server->>SvcProject: list_projects()
    SvcProject->>DB: SELECT * FROM projects WHERE status='active'
    DB-->>SvcProject: [{id, name, phase, ...}]
    SvcProject-->>Server: projects[]
    Server-->>Browser: 200 {projects:[...]}

    Note over Browser: state.projects = [...]\nstate.current = projects[0]\nstate.tab = 'dashboard'

    Browser->>Server: GET /api/projects/{pid}/hierarchy/metrics
    Server->>DB: SELECT versions, reviews, phases WHERE project_id=?
    DB-->>Server: metrics dict
    Server-->>Browser: 200 {total_versions, total_reviews, phases[], stat_counts, ...}

    Note over Browser: render() → viewDashboard()\nstat-grid + phase bar injected into #main
```

---

## Sequence 2 — Artifact Ingest & Processing

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as UI (index.html)
    participant Server as server.py
    participant H_Artifact as handlers/artifact.py
    participant P_Pipeline as processors/pipeline.py
    participant ArtStore as db/artifact_store_sql.py
    participant DB as Data Layer

    User->>Browser: Upload file on Ingest tab<br/>or paste text

    alt File upload (multipart/form-data)
        Browser->>Server: POST /api/v1/projects/{pid}/artifacts/upload<br/>Content-Type: multipart/form-data
        Server->>H_Artifact: handle_artifact_upload(pid, {}, R, raw_multipart, content_type)
    else Text paste
        Browser->>Server: POST /api/v1/projects/{pid}/artifacts/text<br/>{title, content, category, metadata{}}
        Server->>H_Artifact: handle_artifact_text(pid, body, R)
    end

    H_Artifact->>ArtStore: create_artifact(pid, type, file_name, title, category, metadata)
    ArtStore->>DB: INSERT INTO artifacts (artifact_id=a_xxx, project_id, type,<br/>file_name, title, category, include=1, status='ingested', created_at)
    DB-->>ArtStore: OK
    ArtStore-->>H_Artifact: Artifact{artifactId, status:'ingested'}
    H_Artifact-->>Server: {artifactId, status:'ingested', ...}
    Server-->>Browser: 201 {artifact: {...}}

    Note over Browser: Artifact row added to list\nstatus badge: 'ingested'

    User->>Browser: Click "Process All" (or Process single)
    Browser->>Server: POST /api/v1/projects/{pid}/artifacts/process
    Server->>H_Artifact: handle_process_all_artifacts(pid, body, R)
    H_Artifact->>P_Pipeline: process_all_artifacts(pid, only_included=True, force=True)

    loop For each included artifact
        P_Pipeline->>ArtStore: update_artifact_status(pid, artifact_id, 'processing')
        ArtStore->>DB: UPDATE artifacts SET status='processing'
        P_Pipeline->>P_Pipeline: get_artifact_text_content(pid, artifact_id)<br/>→ read raw file OR text_content field<br/>→ parse PDF/DOCX/XLSX via extractors
        P_Pipeline->>P_Pipeline: _detect_content_type(artifact, content)<br/>→ text/plain | text/markdown | application/json
        P_Pipeline->>P_Pipeline: _extract_tags(content, category)<br/>→ keyword scan → List[str] max 10
        P_Pipeline->>DB: WRITE projects_data/{pid}/processed/{artifact_id}.json<br/>{artifactId, content, contentType, tags, metadata}
        P_Pipeline->>ArtStore: update_artifact_status(pid, artifact_id, 'processed')
        ArtStore->>DB: UPDATE artifacts SET status='processed'
    end

    P_Pipeline-->>H_Artifact: [artifact_id, ...]
    H_Artifact-->>Server: {processed: [ids]}
    Server-->>Browser: 200 {processed: [...]}

    Note over Browser: Artifact status badges update to 'processed'<br/>Ready for Build Intelligence
```

---

## Sequence 3 — Build Intelligence & Create Version

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as UI (index.html)
    participant Server as server.py
    participant H_Intel as handlers/intelligence.py
    participant S_Intel as services/intelligence.py
    participant P_Context as processors/context_builder.py
    participant H_Store as db/hierarchy_store_sql.py
    participant Bus as contracts/bus.py
    participant DB as Data Layer

    User->>Browser: Click "Build Intelligence"\n(Ingest tab — selects ai_backend, persona, scope)
    Browser->>Server: POST /api/projects/{pid}/build-context<br/>{ai_backend, persona, scope, file_toggles{}}
    Server->>H_Intel: handle_build_context(pid, body, R)
    H_Intel->>S_Intel: build_project_intelligence(pid, backend)

    S_Intel->>DB: Load processed docs from projects_data/{pid}/processed/*.json
    S_Intel->>DB: Load legacy docs from projects_data/{pid}/context/*.json
    S_Intel->>P_Context: build_context(documents[])
    P_Context->>P_Context: For each doc: extract scope/risks/assumptions/<br/>dependencies/constraints from content
    P_Context-->>S_Intel: ProjectContext{scope, risks[], assumptions[], ...}

    S_Intel->>S_Intel: compute stats{risks:N, deps:N, constraints:N, assumptions:N}
    S_Intel->>DB: WRITE projects_data/{pid}/intelligence/current.json

    S_Intel->>H_Store: create_version(included_artifacts[], excluded_artifacts[],<br/>persona, scope, ai_backend, label, stats)
    H_Store->>DB: INSERT INTO versions (version_id='vN', project_id, phase_id,<br/>label, included_artifacts JSON, stats JSON, created_at)
    H_Store->>DB: UPDATE phases SET version_count=version_count+1
    H_Store->>DB: WRITE projects_data/{pid}/hierarchy/versions/vN.json (dual-write)
    H_Store->>DB: WRITE projects_data/{pid}/hierarchy/versions/index.json

    H_Store-->>S_Intel: Version{version_id:'vN', ...}
    S_Intel->>Bus: publish(Event topic='intelligence.built',<br/>payload={project_id, version_id:'vN'})
    Bus-->>S_Intel: (async in-process — no await)

    S_Intel-->>H_Intel: {version_id:'vN', artifact_count, stats}
    H_Intel-->>Server: response dict
    Server-->>Browser: 201 {version_id:'vN', label, stats}

    Note over Browser: toast('Intelligence built ✓')\nstate._dashVersion = 'vN'\nRe-render Versions tab
```

---

## Sequence 4 — Run Persona Review

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as UI (index.html)
    participant Server as server.py
    participant H_Review as handlers/review.py<br/>ServiceReviewAgent
    participant S_Review as services/review.py
    participant P_Engine as personas/engine.py
    participant AIB as ai_backends/<br/>(files_only|ollama|bedrock|gemini)
    participant P_Quality as processors/review_quality.py
    participant H_Store as db/hierarchy_store_sql.py
    participant P_Logger as processors/prompt_logger.py
    participant Bus as contracts/bus.py
    participant DB as Data Layer

    User->>Browser: Select persona + backend\n(optionally add injected questions / notes)\nClick "Run Review"
    Browser->>Server: POST /api/review<br/>{project_id, roles:['Solution Architect'],<br/>ai_backend:'ollama', custom_prompt?,<br/>previous_review_id?, prompt_builder_state{}}
    Server->>H_Review: handle_review(body, R)
    H_Review->>H_Review: Validate project_id + roles present\nBuild ReviewRequest dataclass
    H_Review->>S_Review: ServiceReviewAgent.run(ReviewRequest)
    S_Review->>Bus: publish(review.started, {project_id, roles, ai_backend})

    S_Review->>DB: get_project(project_id) → projects.json
    S_Review->>DB: get_project_intelligence(project_id) → intelligence/current.json
    S_Review->>H_Store: list_versions() → SELECT versions ORDER BY created_at DESC

    S_Review->>P_Engine: run_review(roles, context=intelligence,<br/>ai_backend, custom_prompt)

    alt ai_backend == 'files_only'
        P_Engine->>AIB: FilesOnlyBackend.generate(prompt)<br/>→ deterministic pattern analysis of context dict<br/>→ no network call
        AIB-->>P_Engine: {findings{risks,gaps,recommendations,<br/>questions,action_items,...}, summary}
    else ai_backend == 'ollama'
        P_Engine->>AIB: OllamaBackend.generate(prompt)<br/>→ POST http://localhost:11434/api/generate
        AIB-->>P_Engine: parsed LLM JSON response
    else ai_backend == 'bedrock' or 'gemini'
        P_Engine->>AIB: CloudBackend.generate(prompt)<br/>→ external API call (network required)
        AIB-->>P_Engine: parsed LLM JSON response
    end

    P_Engine-->>S_Review: review dict {findings{}, questions[], summary, prompt_used}

    opt ai_backend != files_only
        S_Review->>P_Engine: run_deep_dive(persona_name, scope,<br/>intelligence, active_files[], custom_prompt, ai_backend)
        P_Engine->>AIB: generate deep-dive prompt
        AIB-->>P_Engine: structured SME analysis
        P_Engine-->>S_Review: deep_dive dict
        S_Review->>S_Review: review['deep_dive'] = deep_dive
    end

    S_Review->>P_Quality: extract_weaknesses(findings)<br/>→ scan finding texts for weak signals<br/>→ return [{id,text,category,severity,status:'open'}]
    S_Review->>P_Quality: compute_missing_categories(findings)<br/>→ compare found categories vs VALID_CATEGORIES<br/>→ return [missing_category_names]
    S_Review->>P_Quality: extract_decision_points(findings)<br/>→ identify open decisions in findings<br/>→ return [{id,text,category,status:'open'}]

    opt previous_review_id provided
        S_Review->>H_Store: get_review(previous_review_id)
        H_Store->>DB: SELECT * FROM reviews WHERE review_id=?
        DB-->>H_Store: Review row
        H_Store-->>S_Review: Review{decision_points:[...]}
        S_Review->>S_Review: Inherit open decision_points from predecessor<br/>(deduplicated by text)
    end

    S_Review->>H_Store: create_review(version_id='vN', persona,<br/>findings, weaknesses, decision_points,<br/>prompt_builder_state, ...)
    H_Store->>DB: INSERT INTO reviews (review_id='rN', project_id,<br/>version_id='vN', findings JSON, weaknesses JSON,<br/>decision_points JSON, created_at)
    H_Store->>DB: UPDATE versions SET review_ids=['rN'], active_review_id='rN'
    H_Store->>DB: UPDATE phases SET review_count=review_count+1
    H_Store->>DB: WRITE projects_data/.../reviews/rN.json (dual-write)

    S_Review->>P_Logger: log_prompt(project_id, review_id='rN',<br/>prompt_builder_state, final_prompt, persona_name)
    P_Logger->>DB: INSERT INTO prompt_log

    S_Review->>Bus: publish(review.completed,<br/>{project_id, review_id:'rN', persona,<br/>weakness_count, decision_point_count})
    Bus-->>S_Review: (in-process, no await)

    S_Review-->>H_Review: ReviewResult{review_id:'rN', findings, weaknesses, ...}
    H_Review-->>Server: result.raw dict
    Server-->>Browser: 200 {review_id:'rN', persona,<br/>findings{}, weaknesses[], decision_points[],<br/>summary, questions[], missing_categories[]}

    Note over Browser: toast('Review complete ✓')\nstate._dashReview = 'rN'\nRe-render review list — rN appears at top\nIteration badge: R1|R2|R3...
```

---

## Sequence 5 — Review Quality Gate & Set Active Review

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as UI (index.html)
    participant Server as server.py
    participant H_Review as handlers/review.py
    participant S_Review as services/review.py
    participant P_Quality as processors/review_quality.py
    participant H_Store as db/hierarchy_store_sql.py
    participant DB as Data Layer

    User->>Browser: Click "Complete Review" on review detail panel
    Browser->>Server: POST /api/projects/{pid}/hierarchy/reviews/{rid}/complete<br/>{completed_by:'Alice', quality_status:'complete'}
    Server->>H_Review: handle_complete_review(pid, rid, body, R)
    H_Review->>S_Review: complete_review_gate(pid, rid, completed_by, quality_status)
    S_Review->>P_Quality: complete_review(pid, rid, completed_by, quality_status)
    P_Quality->>H_Store: get_review(rid)
    H_Store->>DB: SELECT * FROM reviews WHERE review_id=?
    DB-->>H_Store: Review row
    H_Store-->>P_Quality: Review{quality_status:'pending', ...}

    P_Quality->>P_Quality: Validate quality_status in [pending, interim, complete]
    P_Quality->>H_Store: UPDATE review: quality_status, completed_by, completed_at=now
    H_Store->>DB: UPDATE reviews SET quality_status='complete',<br/>completed_by='Alice', completed_at=?
    P_Quality->>DB: INSERT INTO decision_log<br/>(entity_type='review', entity_id=rid,<br/>action='completed', actor='Alice', created_at)

    P_Quality-->>S_Review: {review_id, quality_status:'complete', completed_by}
    S_Review-->>H_Review: result
    H_Review-->>Server: result
    Server-->>Browser: 200 {review_id:'rN', quality_status:'complete', completed_by:'Alice'}

    Note over Browser: Quality badge updates to ✓ complete\nNo full re-render

    User->>Browser: Click "Set as Active Review" on version row
    Browser->>Server: POST /api/projects/{pid}/hierarchy/versions/{vid}/set-active-review-gated<br/>{review_id:'rN', decided_by:'Alice', force:false}
    Server->>H_Review: handle_set_active_review_gated(pid, vid, body, R)
    H_Review->>S_Review: set_active_review_gated(pid, vid, 'rN', 'Alice', force=false)
    S_Review->>P_Quality: set_active_review_with_gate(pid, vid, 'rN', 'Alice', force)
    P_Quality->>H_Store: get_review('rN')
    H_Store->>DB: SELECT quality_status FROM reviews WHERE review_id='rN'

    alt quality_status != 'complete' AND force == false
        P_Quality-->>S_Review: {error:'Review must be complete before setting active', gate_failed:true}
        Server-->>Browser: 422 {error:'...', gate_failed:true}
        Note over Browser: toast(error, 'err')
    else quality_status == 'complete' OR force == true
        P_Quality->>H_Store: set_active_review(vid, 'rN')
        H_Store->>DB: UPDATE versions SET active_review_id='rN' WHERE version_id=?
        P_Quality->>DB: INSERT INTO decision_log<br/>(action='set_active', entity_id='rN', actor='Alice')
        P_Quality-->>S_Review: {version_id, active_review_id:'rN', status:'updated'}
        Server-->>Browser: 200 {version_id, active_review_id:'rN'}
        Note over Browser: Active review badge updates on version row\nNo full re-render
    end
```

---

## Inputs and Outputs

| Sequence | Input Actors | Key Inputs | Key Outputs |
|---|---|---|---|
| Boot | User + Browser | URL `http://localhost:8080` | Populated SPA with project dashboard |
| Artifact Ingest | User + Browser | File bytes or text + category | `artifact_id` stored; status `'ingested'` → `'processed'` |
| Build Version | User + Browser | `project_id`, artifact selection, persona | Version `vN` in DB; `intelligence/current.json` written |
| Run Review | User + Browser | `roles[]`, `ai_backend` | Review `rN` in DB; findings/weaknesses/decisions returned |
| Quality Gate | User + Browser | `review_id`, `completed_by` | `quality_status` = `complete`; decision log entry |

---

## Async / Fire-and-Forget Patterns

| Call | Pattern | Notes |
|---|---|---|
| `bus.publish(review.started)` | In-process sync publish; subscribers receive synchronously | No network I/O; no await needed |
| `bus.publish(review.completed)` | Same | Decouples post-review hooks from the critical path |
| `setTimeout(_renderInjectedQuestions, 0)` | Browser microtask after paint | DOM must exist before chip rendering |
| `setTimeout(_populateReadinessBadges, 0)` | Browser microtask after paint | Per-version readiness fetch after list paint |

---

## Linked Components

| Component | File |
|---|---|
| `handle_review()` | `handlers/review.py` |
| `run_persona_review()` | `services/review.py` |
| `run_review()` | `personas/engine.py` |
| `extract_weaknesses()` / `extract_decision_points()` | `processors/review_quality.py` |
| `create_review()` | `db/hierarchy_store_sql.py` |
| `log_prompt()` | `processors/prompt_logger.py` |
| `ServiceBus.publish()` | `contracts/bus.py` |
| `complete_review()` / `set_active_review_with_gate()` | `processors/review_quality.py` |
