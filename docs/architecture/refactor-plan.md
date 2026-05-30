# Refactor Plan — Production-Grade Hardening

**Date:** 2026-05-30  
**Roles:** Senior Developer · Technology Architect · Product Owner · Solution Architect  
**Scope:** Staged refactor of the Project Delivery Accelerator Engine toward production-grade
quality, maintainability, and agentic-ready module boundaries — without a rewrite.

---

## 1. Current State Assessment

### 1.1 What Is Already in Good Shape

| Area | Status | Notes |
|---|---|---|
| `models/` | ✅ Good | Clear dataclasses with type hints. `hierarchy.py`, `proposal.py`, `artifact.py` are well-structured. |
| `db/` layer | ✅ Good | Separated SQLite store from business logic. `__init__.py` exposes a clean public surface. Dual-write flag pattern works. |
| `admin/` module | ✅ Good | Cohesive module with clear `__init__.py`. Config, lifecycle, health each in their own file. |
| `ai_backends/` | ✅ Good | Clean provider abstraction. `base.py` defines the interface; concrete backends extend it. Registry pattern is solid. |
| `processors/extractors/` | ✅ Good | Sub-package separation for extraction logic is correct. |
| `processors/parsers/` | ✅ Good | One file per format. Easy to extend. |
| `pyproject.toml` | ✅ Good | `ruff` declared as a dev dependency. Target version set. Lint rules selected. |
| Test structure | ✅ Good | Sprint regression packs, E2E journey tests, conftest.py for shared fixtures. 350 tests. |
| `personas/engine.py` | ✅ Adequate | AI orchestration separated from project management. |
| Dual-write design | ✅ Good | SQLite-primary with JSON mirror is practical for offline-first operation. |

### 1.2 Primary Problem Areas

#### P1 — `project_manager.py` is a god module (2,036 lines, 79 functions)

Every domain action is in one file: project CRUD, ingest, context building, hierarchy
management, review orchestration, proposal lifecycle, presales finalisation, diagram
generation, decision log, admin, version control. This is the single biggest maintainability
risk. Functions use 18 deferred inline imports (`from db... import` inside function bodies)
to avoid circular imports — a symptom of missing domain boundaries.

**Risk:** High. Already hard to navigate; will worsen with every sprint.

#### P2 — `server.py` is a routing monolith (1,522 lines, 51 functions)

`do_GET` and `do_POST` are giant if/elif chains with 61 manual `clean_path.split("/")` calls
and inline business logic scattered throughout handler methods. Route matching is fragile
(order-dependent `startswith`/`endswith` checks). Handler methods contain logic that belongs
in `project_manager` or a dedicated service layer.

**Risk:** High for new route additions; medium for existing stability.

#### P3 — Broad exception swallowing is pervasive

`project_manager.py`: 26 bare `except Exception: pass` blocks.  
`server.py`: 16 similar blocks.  
`processors/`: 23 more.

Silent failures hide bugs in production. Some are intentional fallbacks but none are logged.

**Risk:** Medium. Bugs become invisible.

#### P4 — Deferred inline imports throughout `project_manager.py`

18 occurrences of `from db...`, `from processors...`, `from models...` inside function bodies.
These exist to avoid circular dependency — which indicates the module needs to be split, not
patched with deferred loading.

**Risk:** Medium. Makes dependency graph invisible and refactor harder.

#### P5 — No structured logging

`print()` statements exist in some paths. No `logging` module usage. No log levels, no
correlation IDs, no request tracing. In a production container, operational visibility is zero.

**Risk:** Medium for operations. Low for existing tests.

#### P6 — Dual `PROJECTS_DIR` definition

`project_manager.py` and `db/project_store_sql.py` and `db/hierarchy_store_sql.py` each
define their own `PROJECTS_DIR = Path("projects_data")`. Any path change requires three
edits; one is already overridden from `server.py` at startup by mutation
(`project_manager.PROJECTS_DIR = _Path(_data_dir)`).

**Risk:** Low-medium. Works today; breaks silently on refactor.

#### P7 — `APP_VERSION` hardcoded as a string literal in `server.py`

No single source of truth for version. `pyproject.toml` has `version = "3.0.0"`;
`server.py` has `APP_VERSION = "3.3.0"`. They are out of sync.

**Risk:** Low. Cosmetic but unprofessional.

#### P8 — `ruff` declared but not enforced

`pyproject.toml` declares `ruff` in `[project.optional-dependencies.dev]` with rules E/F/W/I,
but there is no CI step that runs it, no pre-commit hook, and no `ruff.toml` or `[tool.ruff]`
`format` section. Code is inconsistently formatted: mixed quote styles, inconsistent spacing
around operators, variable-length docstrings.

**Risk:** Low for current behaviour; medium for code-review velocity and contributor onboarding.

---

## 2. Staged Refactor Plan

### Phase 1 — Standards and Low-Risk Cleanup (zero behaviour change)

**Goal:** Make the codebase consistently readable and lintable. Close P3, P5, P7, P8.

| Task | File(s) | Action |
|---|---|---|
| 1.1 | `pyproject.toml` | Add `[tool.ruff.format]` section. Pin version. Add `black` or use `ruff format`. Add `isort` config under ruff I rules. |
| 1.2 | `pyproject.toml` | Read version from single source: add `__version__` to a `version.py` or use `importlib.metadata`. |
| 1.3 | `server.py` | Replace `APP_VERSION = "3.3.0"` with `from version import __version__`. |
| 1.4 | All `.py` files | Run `ruff check --fix` + `ruff format`. Commit as a single formatting commit. |
| 1.5 | `project_manager.py`, `server.py`, `processors/` | Replace `except Exception: pass` with explicit `except Exception as exc: logger.warning(...)`. Keep fallback logic; add the log. |
| 1.6 | All modules | Add `import logging; logger = logging.getLogger(__name__)` to each module. Replace `print()` calls. Configure root logger in `server.py` startup. |
| 1.7 | `project_manager.py` | Consolidate `PROJECTS_DIR` to a single canonical location (e.g. `core/paths.py`) and import everywhere. |

**Estimated effort:** 1–2 days. **Risk:** Near-zero (formatting + logging only).

---

### Phase 2 — Internal Modularization (split the god modules)

**Goal:** Break `project_manager.py` and `server.py` into cohesive domain modules with clear
responsibilities. Close P1, P2, P4, P6.

#### 2.1 Split `project_manager.py` into domain services

Each service is a module under a new `services/` package. `project_manager.py` becomes a
thin facade that re-exports the same public surface for backward compatibility.

| New module | Functions moved from `project_manager.py` |
|---|---|
| `services/project_service.py` | `create_project`, `get_project`, `list_projects`, `update_project`, `archive_project`, `restore_project`, `delete_project`, `get_admin_config`, `get_system_health_status`, `get_lifecycle_logs` |
| `services/ingest_service.py` | `ingest_document`, `build_intelligence`, `get_project_context`, `get_file_toggles`, `toggle_file`, `get_project_intelligence` |
| `services/review_service.py` | `run_persona_review`, `get_hierarchy`, `get_hierarchy_metrics`, `get_hierarchy_versions`, `get_hierarchy_reviews`, `get_hierarchy_review_detail`, `get_review_diff`, `update_weakness_status`, `update_decision_status`, `complete_review_gate`, `set_active_review_gated`, `get_version_readiness` |
| `services/proposal_service.py` | `create_proposal`, `add_proposal_version`, `get_proposal_info`, `generate_proposal_doc`, `get_proposal_doc` |
| `services/presales_service.py` | `get_presales_summary`, `get_presales_stop_condition`, `finalise_presales`, `save_presales_feedback`, `get_presales_feedback`, `create_share_token`, `submit_feedback` |
| `services/diagram_service.py` | `generate_diagram`, `get_diagram`, `list_diagrams` |
| `services/prompt_service.py` | `get_prompt_history` |

`project_manager.py` retains only re-exports:
```python
# project_manager.py — thin facade for backward compatibility
from services.project_service import *  # noqa: F401,F403
from services.ingest_service import *   # noqa: F401,F403
# ... etc
```

This means **zero breaking changes to `server.py`** during Phase 2.

#### 2.2 Introduce a route registry in `server.py`

Replace the 1,500-line `if/elif` chain with a declarative route table:

```python
# routing.py
from dataclasses import dataclass
from typing import Callable, Literal

@dataclass
class Route:
    method: Literal["GET", "POST"]
    pattern: str          # e.g. "/api/projects/{id}/hierarchy/reviews/{rid}/diff"
    handler: Callable
    match_type: Literal["exact", "startswith", "endswith", "contains"] = "exact"
```

Handler methods move to thin handler files per domain:
- `handlers/project_handlers.py`
- `handlers/hierarchy_handlers.py`
- `handlers/review_handlers.py`
- `handlers/proposal_handlers.py`
- `handlers/presales_handlers.py`
- `handlers/admin_handlers.py`

`server.py` shrinks to: startup, routing dispatch, shared response helpers, static file serving.

**Estimated effort:** 3–5 days. **Risk:** Medium — requires careful route-by-route migration
with existing tests validating each batch.

#### 2.3 Eliminate deferred inline imports

With services split, circular dependencies resolve naturally. All imports move to module-level.

---

### Phase 3 — Agentic-Ready Seams (future-proof boundaries)

**Goal:** Define internal interfaces so future agentic orchestration layers can route work to
domain services without coupling to `http.server`. No new runtime; just cleaner contracts.

| Task | What |
|---|---|
| 3.1 | Define `ServiceBus` interface: a simple dict-based message envelope `{action, payload, context}` that services can accept. No queue needed yet — just the contract. |
| 3.2 | Add `services/__init__.py` that exposes a `dispatch(action, payload)` function. Initially just calls the right service function. Future: can be replaced with async queue. |
| 3.3 | Move `personas/engine.py` invocation behind a `ReviewAgent` protocol class so it can be replaced by an agentic runtime later. |
| 3.4 | Add `contracts/` package with dataclasses defining input/output contracts for each service boundary (no runtime validation yet; documents intent). |
| 3.5 | Ensure `ai_backends/` is consumed only through `ai_backends.__init__.call_llm()` — no direct backend imports elsewhere. Audit and fix. |

**Estimated effort:** 3–5 days. **Risk:** Low (additive only, no behaviour changes).

---

## 3. Recommended Tooling and Standards

### Linting and Formatting

```toml
# pyproject.toml additions
[tool.ruff]
line-length = 100
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.ruff.lint.isort]
known-first-party = ["models", "processors", "personas", "db", "admin", "ai_backends", "services"]
```

Add to CI (`.github/workflows/ci.yml`):
```yaml
- name: Lint
  run: ruff check .
- name: Format check
  run: ruff format --check .
```

### Type Checking

- All new functions require type hints (already present in most modules — enforce going forward)
- Consider adding `mypy --strict` to CI for `models/` and `services/` only (lower risk zones)
- Do NOT run mypy over `server.py` or `project_manager.py` yet — too many existing `Any` returns

### Logging Standard

```python
# Every module
import logging
logger = logging.getLogger(__name__)

# server.py startup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
```

Replace:
- `except Exception: pass` → `except Exception as exc: logger.warning("context: %s", exc)`
- `except Exception: return {}` → log before returning
- `print(...)` → `logger.info(...)` or `logger.debug(...)`

### Testing

- Keep existing sprint regression packs unchanged (they are the regression safety net)
- Add `pytest-cov` report to CI: `pytest --cov=services --cov-report=term-missing`
- New services in Phase 2 must ship with unit tests before merge
- Target: ≥80% coverage for new `services/` package

---

## 4. Specific Duplication and Coupling Risks

| Issue | Location | Resolution |
|---|---|---|
| `PROJECTS_DIR = Path("projects_data")` defined in 3 files | `project_manager.py`, `db/project_store_sql.py`, `db/hierarchy_store_sql.py` | Single `core/paths.py`: `PROJECTS_DIR`, `DB_PATH`, `PROJECTS_FILE` |
| `_now()` / `_now_iso()` defined independently in `db/project_store_sql.py`, `db/hierarchy_store_sql.py`, `db/decision_log.py`, `processors/prompt_logger.py` | 4 files | Move to `db/utils.py` or `core/time_utils.py` |
| `_make_hierarchy_store(project_id)` imported inline 18 times | `project_manager.py` | Import once at module level in the relevant service |
| Route pattern matching (`startswith`/`endswith` chains) | `server.py` lines 60–800 | Route registry (Phase 2.2) |
| Dual-write flags (`_flags()`) duplicated in `project_store_sql.py` and `hierarchy_store_sql.py` | 2 files | Single `db/flags.py: get_write_flags()` |
| `APP_VERSION` out of sync between `pyproject.toml` (3.0.0) and `server.py` (3.3.0) | 2 files | Single `version.py` |
| `from admin.config import load_config` called defensively inside dozens of functions | Everywhere | Import at module top in the service that owns that domain |

---

## 5. Target Module Structure (Post Phase 2)

```
project_delivery_accelerator/
├── server.py                   # Startup + routing dispatch only (~150 lines)
├── version.py                  # Single source of truth for __version__
├── project_manager.py          # Thin re-export facade (backward compat)
│
├── core/
│   ├── __init__.py
│   ├── paths.py                # PROJECTS_DIR, DB_PATH, PROJECTS_FILE
│   └── logging_config.py       # Root logger setup
│
├── services/                   # Domain services (Phase 2)
│   ├── __init__.py             # dispatch() entry point
│   ├── project_service.py
│   ├── ingest_service.py
│   ├── review_service.py
│   ├── proposal_service.py
│   ├── presales_service.py
│   ├── diagram_service.py
│   └── prompt_service.py
│
├── handlers/                   # HTTP handler delegates (Phase 2)
│   ├── __init__.py
│   ├── project_handlers.py
│   ├── hierarchy_handlers.py
│   ├── review_handlers.py
│   ├── proposal_handlers.py
│   ├── presales_handlers.py
│   └── admin_handlers.py
│
├── contracts/                  # Input/output dataclasses per boundary (Phase 3)
│   ├── __init__.py
│   ├── review_contracts.py
│   ├── proposal_contracts.py
│   └── ingest_contracts.py
│
├── models/                     # Unchanged — already well-structured
├── processors/                 # Unchanged — already well-structured
├── personas/                   # Minor: hide behind ReviewAgent protocol (Phase 3)
├── ai_backends/                # Unchanged — already well-structured
├── db/                         # Minor: add flags.py, utils.py
├── admin/                      # Unchanged — already well-structured
└── tests/                      # Unchanged — regression packs remain as-is
```

---

## 6. Areas Where Refactor Should Be Deferred

| Area | Why Defer |
|---|---|
| `static/index.html` (SPA) | 4,000+ lines of vanilla JS. Not Python. No build toolchain. Refactoring would require a framework decision (React, Vue, etc.) — out of scope and not low-risk. |
| `personas/engine.py` deep refactor | Complex multi-role AI orchestration. Works correctly. Abstraction boundary (Phase 3) is sufficient for now. |
| `processors/pipeline.py` | Artifact processing pipeline is stable. Do not restructure until pipeline is a growth area. |
| DB schema changes | Schema is stable post-S7. No new tables needed for Phase 1–2. Do not touch `_SCHEMA_SQL` or `_apply_migrations()`. |
| `tests/test_sprint*_regression.py` | These are the regression safety net. Do not reorganise them during refactor. Run them after every Phase 1/2 commit. |
| Async server migration | `http.server` is simple and correct for single-container offline-first operation. Async migration (ASGI, FastAPI) is a separate architectural decision with significant risk and no current need. |
| `_archive/` directory | Legacy code. Leave as-is. |

---

## 7. Implementation Order

```
Phase 1
  Week 1, Day 1–2:
    [1.2] version.py
    [1.3] server.py version import
    [1.7] core/paths.py + update 3 files
    [1.6] Add logging to all modules
    [1.5] Replace except Exception: pass (project_manager first, then server, then processors)
    [1.4] ruff format + ruff check --fix — single formatting commit
    [1.1] pyproject.toml ruff format + CI additions
  → Run full test suite. Must be 350/350.

Phase 2
  Week 1–2, per domain:
    [2.1a] services/project_service.py  → validate with existing tests
    [2.1b] services/ingest_service.py   → validate
    [2.1c] services/review_service.py   → validate (highest value)
    [2.1d] services/proposal_service.py → validate
    [2.1e] services/presales_service.py → validate
    [2.1f] services/diagram_service.py  → validate
    [2.1g] project_manager.py facade    → validate full suite
    [2.2]  handlers/ + route registry   → validate after each handler file
    [2.3]  Eliminate inline imports     → validate
  → Each step: 350/350 tests must pass.

Phase 3
  Week 3 (if Phase 2 complete):
    [3.1–3.2] ServiceBus contract + dispatch()
    [3.3]     ReviewAgent protocol
    [3.4]     contracts/ package
    [3.5]     ai_backends audit
  → Each step: 350/350 tests must pass.
```

---

## 8. Definition of Done (per phase)

**Phase 1 complete when:**
- `ruff check .` passes with zero errors
- `ruff format --check .` passes
- No `except Exception: pass` without a log
- `APP_VERSION` reads from `version.py`
- All `PROJECTS_DIR` usages import from `core/paths.py`
- Logging configured; key transitions (project create, review run, proposal create) produce INFO logs
- 350/350 tests still passing

**Phase 2 complete when:**
- `project_manager.py` contains only re-exports (≤ 50 lines)
- `server.py` contains only startup, dispatch, static serving (≤ 200 lines)
- All handler logic lives in `handlers/`
- All domain logic lives in `services/`
- No inline deferred imports remain
- 350/350 tests still passing

**Phase 3 complete when:**
- `services/__init__.py` exposes `dispatch(action, payload)`
- `contracts/` package documents all service boundaries
- `ai_backends/` has zero direct imports outside `ai_backends.__init__`
- Architecture note updated in `docs/architecture/`
- 350/350 tests still passing
