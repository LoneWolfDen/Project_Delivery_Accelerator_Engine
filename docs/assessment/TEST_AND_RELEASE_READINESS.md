# Test and Release Readiness

| Field | Value |
|---|---|
| Assessment date | 2026-10-01 |
| Commit | `1ca4319` |
| Tests executed during assessment | **None.** `pytest` isn't installed locally (`ModuleNotFoundError: No module named 'pytest'` under Python 3.14.7), and installing packages was out of scope. CI results were read with `gh run list` / `gh run view` (read-only). |

---

## 1. Verdict

**Not release-ready** under the charter's definition of "production-ready" (maintainable source, predictable startup, safe data handling, observable failures, repeatable tests, recoverable storage, controlled releases, documented limitations).

| Charter criterion | Status | Basis |
|---|---|---|
| Maintainable source | PARTIAL | Readable, but split across two monolithic UIs plus orphaned modules (implementation assessment U1–U3) |
| Predictable startup | BROKEN | Docker and wheel installs can't import the server (dependency register D-1, D-2); only the editable local path is plausible |
| Safe data handling | BROKEN | Path traversal, unauthenticated admin, PIN disclosure, wildcard CORS (security B-1, H-1–H-3) |
| Observable failures | BROKEN | Pervasive `except Exception: pass`; silent AI-to-heuristic fallback; false "✓ Saved" in V2 Admin |
| Repeatable tests | BROKEN | CI has failed 200 of 200 recent runs; the suite aborts at collection |
| Recoverable storage | Absent | No backup, export or restore; irreversible delete |
| Controlled releases | Absent | No release tags, changelog or versioned artefacts |
| Documented limitations | PARTIAL | README overstates capabilities (implementation assessment §11) |

## 2. Test inventory

| Metric | Value | Evidence |
|---|---|---|
| Test files | 32 (`tests/test_*.py`) plus `tests/conftest.py` | `ls tests` |
| Test functions | ~1,422 (CI collected 1,425 items) | AST count; CI log "collected 1425 items / 1 error" |
| Tests asserting on **source text** (reading `.html`, `.js` or `.py` files as strings) | ~470 (approximate, by fixture name) | Fixtures `html`, `api_js`, `detail_js`, `dashboard_js`, `server_src`, etc. in `tests/test_v2_*.py`, `tests/test_html_static_analysis.py`, `tests/test_ms01_sprint5_frontend.py` |
| Tests asserting on **JS files the browser never loads** | ~90 | Fixtures `api_js`, `detail_js`, `dashboard_js`, `accordion_js`, `recon_js` (`tests/test_v2_phase1_and_phase2.py`, `tests/test_v2_phase3_and_phase4.py`) |
| Tests with in-process back-end execution and isolated storage | 14 files use `tmp_path` / `monkeypatch` / `PROJECTS_DATA_DIR` | e.g. `tests/test_e2e_user_journey.py` ("No server process required: backend logic called directly") |
| HTTP-level tests against `AcceleratorHandler` | ~0 | `tests/test_server.py` only checks that `do_GET` / `do_POST` attributes exist |
| Browser / DOM tests | 0 | No Playwright, Selenium, jsdom or Node test runner |
| JS syntax checks | 0 in CI | Assessment ran `node --check` on extracted blocks: all pass at HEAD |
| Security tests (traversal, CORS, auth, XSS) | 0 | — |
| Data-integrity tests for delete / archive / overwrite | Not found for eviction or stem-collision cases | — |
| Skips / xfails | `skip` appears in 6 files (16 occurrences) | `grep` |

## 3. Adequacy findings

| ID | Finding | Class | Path | Evidence | Risk | Conf. | Runtime |
|---|---|---|---|---|---|---|---|
| T-1 | Suite can't run to completion | BROKEN | `tests/test_persona_engine.py:10-16` | Imports `AVAILABLE_PERSONAS`, which no longer exists in `personas/engine.py`; collection error stops the run | No test result is trustworthy; unknown number of other failures behind it | High | Yes (`pytest --continue-on-collection-errors`) |
| T-2 | Large share of "frontend tests" are string-presence checks | PARTIAL | `tests/test_v2_dashboard_frontend.py` (135 tests), `tests/test_ms01_sprint5_frontend.py` (94), `tests/test_html_static_analysis.py` (14) | Assert that substrings or function names appear in HTML/JS source | Pass while the UI is broken at runtime. Commits #114–#118 fixed SyntaxErrors and page-load failures these tests didn't catch. | High | No |
| T-3 | Tests validate dead code | BROKEN (as evidence) | ~90 tests on `static/v2/js/api.js`, `ui/v2/components/DetailPanel.js`, etc. | Those files aren't served (implementation assessment U1, U2) | Green tests "prove" features that users can't reach (U4, U5) | High | No |
| T-4 | No HTTP routing tests | Gap, with one confirmed defect | `server.py` ~70 routes via `endswith`/`in` string matching | Confirmed by reading: `server.py:446` `endswith("/phase")` precedes `server.py:449` `endswith("/hierarchy/phase")`, so the hierarchy route is unreachable. V1 calls it (`static/index.html:3194`, body `{phase_id, reason}`) and gets `400 "new_phase required"` from the wrong handler. | Route-order defects ship undetected | High | Yes |
| T-5 | No security regression tests | Gap | — | B-1, H-1–H-4 would all pass the current suite | High | High | No |
| T-6 | Coverage gate unverifiable | UNKNOWN | `ci.yml` `--cov-fail-under=80` | Never reached because of T-1 | Unknown real coverage | High | No |
| T-7 | Positive: back-end journey tests use real code paths and isolated SQLite | WORKING (design) | `tests/test_e2e_user_journey.py`, sprint regression files | `tmp_path` + `monkeypatch`, `files_only` backend | Good foundation to build compatibility tests on | Medium | Yes |
| T-8 | Python 3.14 (local) not in CI matrix | Gap | `ci.yml` matrix 3.9/3.11/3.12 | Local dev may differ from CI | Low | High | Yes |

## 4. Manual test documentation

`docs/test-plans/` has 10 manual plans (E2E, edge cases, data integrity, UI validation, strict checklist, S3 regression). They describe intended behaviour; there's no record in the repository of their execution or results. Class: **DOCUMENTED ONLY**.

## 5. Release-blocking items (no backlog; reference only)

1. CI red: lint (1,810), test collection error (T-1).
2. Startup paths broken except editable local install (D-1, D-2).
3. Security BLOCKERs B-1, B-2 and HIGHs H-1–H-6.
4. Served V2 UI contains non-functional features (Reconcile, Admin save).
5. No backup or restore before any destructive operation.
6. Documentation claims that contradict the implementation (implementation assessment §11).

## 6. Runtime validation still required

Because nothing was executed, the following need confirmation on a running instance before prioritisation is final:

- Path traversal response for `GET /static/../server.py` with a raw path.
- `GET /api/admin/config` response contains `admin_pin`.
- `POST /api/admin/config {"admin_pin":"x"}` succeeds without a PIN.
- Cross-origin read from a non-localhost page under current Edge/Chrome Local Network Access rules.
- Served V2: Reconcile button shows "API not available"; Admin Save shows "✓ Saved" but the value is unchanged on reload.
- Filename-based XSS in the V1 file list.
- Archive eviction of the 6th project; stem-collision overwrite on `/api/ingest`.
- Full pytest run with `--continue-on-collection-errors` to measure real pass/fail counts.
- `docker build` and container start, to confirm the D-1 import failure.
