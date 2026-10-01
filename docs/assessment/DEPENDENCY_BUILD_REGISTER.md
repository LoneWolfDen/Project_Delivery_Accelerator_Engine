# Dependency and Build Register

| Field | Value |
|---|---|
| Assessment date | 2026-10-01 |
| Commit | `1ca4319` |
| Method | Read-only inspection of manifests, imports, Dockerfile, compose and CI. No packages were installed or resolved. Vulnerability advisories were **not** queried (no lockfile; no network audit performed). |

---

## 1. Build models present

| Layer | Model | Class | Evidence |
|---|---|---|---|
| Python back end | setuptools package (`pyproject.toml`), run as `python server.py` | PARTIAL | `pyproject.toml`; packaging omits required packages (§4) |
| Browser front end | No build (de facto charter model A): static HTML with inline scripts | WORKING | No `package.json`, bundler or transpiler |
| Front-end "modular" V2 | Separate ES5-style IIFE files under `static/v2/js`, `ui/v2` | UNUSED | Not loaded by any served page |
| Container | `Dockerfile`, `docker-compose.yml` | BROKEN | Missing source directories (§4) |
| CI | GitHub Actions `ci.yml` (ruff lint + format check; pytest on 3.9/3.11/3.12; coverage ≥ 80 %) | BROKEN | 200/200 recent runs failed |

**Coherence verdict:** the repository doesn't have one coherent build model. Python packaging, Docker and CI each describe a different file set. The front end mixes served inline code with unused modular sources and a hand-synced copy.

## 2. Python dependencies

| Package | Declared in | Constraint | Actually imported by HEAD code? | Notes |
|---|---|---|---|---|
| `pyyaml` | core | `>=6.0` | Yes (persona YAML) | Only mandatory runtime dependency |
| `pytest` | `dev` | `>=7.0.0` | Tests | CI resolved 9.1.1 |
| `pytest-cov` | `dev` | `>=4.0.0` | CI | CI resolved 7.1.0 |
| `ruff` | `dev` | `>=0.4.0` | CI | Unpinned upper bound, so new rules can break CI |
| `boto3` | `ai` | `>=1.28.0` | Yes, lazily (`ai_backends/bedrock_backend.py:44,102`) | |
| `ollama` | `ai` | `>=0.1.0` | **No**: Ollama backend uses `urllib` | Unused dependency |
| `google-genai` | `ai` | `>=1.0.0` | **No**: Gemini backend uses `urllib` | Unused dependency |
| `pypdf` | `docs` | `>=4.0.0` | Yes, lazily (`processors/parsers/pdf_parser.py:39`, `processors/artifact_store.py:349`) | Silent degraded text "[PDF extraction unavailable – install pypdf]" if missing |
| `python-docx` | `docs` | `>=1.1.0` | Yes, lazily (`processors/parsers/docx_parser.py`, `processors/artifact_store.py:362`) | Same pattern |
| `strands-agents`, `strands-agents-tools` | `agents` | `>=0.1.0` | **No** (only in `_archive/`) | Unused optional group |

- **No lockfile** (`requirements*.txt`, `poetry.lock`, `uv.lock`, `pip-tools` output): none. Builds aren't reproducible.
- `requires-python = ">=3.9"`; CI tests 3.9, 3.11, 3.12; the local machine has Python 3.14.7. 3.14 isn't in the CI matrix.
- Standard-library-only HTTP client (`urllib.request`) for Groq, OpenRouter, Gemini and Ollama.

## 3. Browser runtime dependencies

| Dependency | Source | Class |
|---|---|---|
| None | — | WORKING: no CDN, no vendor library, no web fonts |

The one external URL in the served UI is an `<a href="https://app.diagrams.net">` hyperlink (`static/index.html:3010`), which isn't loaded automatically.

## 4. Build and deployment defects

| ID | Defect | Class | Path / line | Evidence | Risk | Conf. | Runtime |
|---|---|---|---|---|---|---|---|
| D-1 | Docker image omits required packages | BROKEN | `Dockerfile:40-50` | Copies `admin ai_backends models personas processors static sample_data server.py project_manager.py cli.py`; **not** `core/ db/ services/ handlers/ contracts/ version.py`. `server.py:31-53` imports `core.logging_config`, `db.decision_log`, `handlers.*`, `services.*` and `version`. | Container fails at import | High | Yes (`docker build` / `run`) |
| D-2 | Non-editable install omits packages | BROKEN | `pyproject.toml:35` | `include = ["models*", "processors*", "personas*", "ai_backends*", "admin*"]`, which misses `core db services handlers contracts` | `pip install .` produces a server that can't import | High | Yes |
| D-3 | Docker installs extras with `|| true` | PARTIAL | `Dockerfile` `pip install -e ".[ai]" || true`, `".[docs]" || true` | Failures hidden; PDF/DOCX silently degrade | Medium | High | Yes |
| D-4 | Admin config path ignores `PROJECTS_DATA_DIR` | BROKEN in containers | `admin/config.py:16` | `/app/projects_data` (root-owned `WORKDIR`) isn't writable by user `contexta` | Config saves fail in Docker | Medium | Yes |
| D-5 | Four independent data-path globals | PARTIAL | `core/paths.py`, `db/database.py:15-16`, `services/project.py` (via `server.py:82-90` mutation), `admin/config.py:16` | Each computes its own base dir | Split-brain storage if env changes after import | Medium | Yes |
| D-6 | `docker-compose` uses `ollama/ollama:latest` | PARTIAL | `docker-compose.yml` | Unpinned image tag; port 11434 published | Non-reproducible; exposure | High | No |
| D-7 | CI lint gate fails (1,810 findings) | BROKEN | `.github/workflows/ci.yml` lint job | `gh run view 35325690280 --log-failed`: "Found 1810 errors." (F401, I001, E702, …) | No lint signal | High | No |
| D-8 | CI test job fails at collection | BROKEN | `tests/test_persona_engine.py:10-16` | `ImportError: cannot import name 'AVAILABLE_PERSONAS' from 'personas.engine'`; pytest "Interrupted: 1 error during collection" | **Zero tests execute in CI** | High | No |
| D-9 | CI uses `actions/checkout@v4`, `setup-python@v5` on deprecated Node 20 | LOW | `ci.yml` | Runner warning in logs | Future breakage | High | No |
| D-10 | No front-end tooling in CI | Gap | — | No JS lint, syntax check or browser test, although commits #114–#118 were all "page-load / SyntaxError" fixes | Repeated UI breakage undetected | High | No |
| D-11 | No release or versioning process | Gap | `version.py` `3.3.0`, `pyproject.toml` `3.3.0`; no tags other than the assessment baseline; no CHANGELOG | Uncontrolled releases | High | No |

## 5. Startup paths

| Path | Command | Class | Notes |
|---|---|---|---|
| Local dev | `pip install -e .` → `python scripts/seed_sqlite.py` → `python server.py` | WORKING (per README; not executed here) | Editable install hides D-2 because cwd is on `sys.path` |
| UI selection | `--ui v1|v2`, `UI_VERSION`, `?ui=` | WORKING | Two UIs |
| CLI | `python cli.py …` | UNKNOWN | Imports `project_manager`; not exercised |
| Docker | `docker build` / `docker run` | BROKEN | D-1 |
| Docker Compose | `docker compose up` | BROKEN | D-1; README's compose example differs from the actual file (service/image names `delivery-accelerator` vs `contexta`) |
| Healthcheck | `GET /api/health` | UNKNOWN | Depends on D-1 |

There are several documented startup paths, and only the editable local path is plausibly working. That contravenes charter §3 ("multiple competing startup paths without documentation").

## 6. Environment and configuration

| File | Content | Risk |
|---|---|---|
| `.env.example` | `ADMIN_PIN=changeme`; blank AI keys; `PORT`, `APP_NAME` | `changeme` will be used verbatim if copied without editing |
| `.gitignore` | Ignores `.env`, `projects_data/`, `outputs/*`, logs | Adequate |
| `.dockerignore` | Excludes `.git`, `_archive`, `tests`, `.env*` | Adequate |
| Env vars read | `HOST`, `PORT`, `APP_NAME`, `UI_VERSION`, `PROJECTS_DATA_DIR`, `ADMIN_PIN`, `LOG_LEVEL`, `OLLAMA_HOST`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `AWS_*` | `UI_VERSION` and `LOG_LEVEL` undocumented in README |

## 7. Licensing

| Item | Status |
|---|---|
| Project licence | **No `LICENSE` file**. README badge and Docker label say MIT. |
| Third-party code shipped | None in the browser. Python dependencies are installed at build time, not vendored. |
| Licence compatibility review | Not performed; no lockfile to enumerate transitive dependencies. |

## 8. Vulnerability posture

- No advisory scan was possible offline, and without a lockfile the resolved versions are undefined.
- Direct runtime surface is small (`pyyaml`, optional `boto3`, `pypdf`, `python-docx`). The dominant risk is first-party code (see `SECURITY_PRIVACY_ASSESSMENT.md`), not dependencies.
- `pypdf` and `python-docx` parse untrusted documents; parser vulnerabilities would be reachable via upload and via `/api/ingest`.
