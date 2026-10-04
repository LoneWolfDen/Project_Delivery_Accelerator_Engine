# Security and Privacy Assessment

| Field | Value |
|---|---|
| Assessment date | 2026-10-01 |
| Commit | `1ca4319` (`main`, tag `pwa-assessment-baseline-2026-10-01`) |
| Method | Static, read-only. Path-resolution behaviour was simulated in a pure Python expression without starting the server. No requests were sent to a running instance. Every finding marked "Runtime: Yes" must be reproduced against a running server before remediation is prioritised as final. |

Severity scale: **BLOCKER** (must be fixed before any release or any non-loopback exposure), **HIGH**, **MEDIUM**, **LOW**.

---

## 1. Threat boundaries

| Boundary | Exists today | Notes |
|---|---|---|
| Browser ↔ local Python server (same machine) | Yes | HTTP, no TLS, **no authentication on any endpoint**. Default bind `localhost` (`server.py:59`). |
| Browser ↔ server across a network | Yes when `HOST=0.0.0.0` | Docker and compose set `HOST=0.0.0.0` (`Dockerfile`, `docker-compose.yml`). The external-feedback feature (`/feedback?token=`) only works if an outside reviewer can reach the server, which implies network exposure. |
| Any website the user visits ↔ local server | Yes | Wildcard CORS (`Access-Control-Allow-Origin: *`, `server.py:568,600`) plus no auth lets a malicious page read API responses from `http://localhost:8080`. Browser Private/Local Network Access protections may mitigate this in current Chrome/Edge; that is unverified. |
| Server ↔ third-party AI providers | Yes, on user choice | Groq `api.groq.com`, OpenRouter `openrouter.ai`, Google `generativelanguage.googleapis.com`, AWS Bedrock (boto3), Ollama (`OLLAMA_HOST`, default `http://localhost:11434`). |
| Server ↔ Microsoft 365 tenant | No | No Graph, MSAL, OneDrive or SharePoint code. |
| Server ↔ server filesystem | Yes, unrestricted | `/api/ingest` accepts arbitrary absolute paths; static handler traverses outside `static/`. |

## 2. Data flow

```
User files (upload / paste / server path)
   │  POST /api/v1/projects/{id}/artifacts/upload | /artifacts/text | POST /api/ingest {file_paths}
   ▼
PROJECTS_DATA_DIR/<pid>/uploads|context/*.json   +   SQLite accelerator.db (artifacts, versions…)
   │  POST /api/projects/{id}/build-context  → intelligence (regex/heuristic extraction, local)
   ▼
Review / deep dive / proposal / synthesis
   │  ai_backend == files_only → local heuristics (no egress)
   │  ai_backend in {groq, openrouter, gemini, bedrock} → FULL context summary + persona prompt sent to provider
   │  ai_backend == ollama → OLLAMA_HOST (local unless reconfigured)
   ▼
SQLite reviews / prompt_log (final_prompt stored verbatim) / decision_log
   ▼
Browser renders via innerHTML (escaped with escHtml in most places)
```

## 3. External requests

| Destination | Source | Trigger | Data sent | Visible to user? |
|---|---|---|---|---|
| `https://api.groq.com/openai/v1` | `ai_backends/groq_backend.py:17,96` | Review/proposal/synthesis with backend `groq` | System prompt plus full context summary; `Authorization: Bearer` key | Backend chosen in UI; no per-send boundary warning |
| `https://openrouter.ai/api/v1` | `ai_backends/openrouter_backend.py:24,106` | Same | Same; also `HTTP-Referer` GitHub repo URL | Same |
| `https://generativelanguage.googleapis.com/v1beta` | `ai_backends/gemini_backend.py:17,66-68` | Same | Same; **API key in URL query string** | Same |
| AWS Bedrock | `ai_backends/bedrock_backend.py:44,102` (boto3) | Same | Same; AWS credential chain | Same |
| `OLLAMA_HOST` | `ai_backends/ollama_backend.py:14,67,98` | Same; also `is_available()` probe (3 s) on every `/api/backends` call | Same | Same |
| `https://app.diagrams.net` | `static/index.html:3010` | User clicks a link | Nothing automatically | Yes |
| CDN scripts, fonts, analytics | — | **None found** | — | — |

No hidden analytics or telemetry were found.

## 4. Findings

### BLOCKER

| ID | Finding | Path / symbol | Evidence | Impact | Conf. | Runtime |
|---|---|---|---|---|---|---|
| **B-1** | **Static file path traversal**: arbitrary file read | `server.py:146-151` → `_serve_static` `server.py:604-606` | Any path starting with `/static/` is passed as `static_dir / filename` with no normalisation or containment check. Simulated: `/static/../server.py` → `<repo>/server.py` (exists). `/static/../projects_data/accelerator.db` and `/static/../projects_data/admin_config.json` resolve the same way. Enough `../` segments reach any file readable by the process. `http.server` does not normalise `self.path`; clients such as `curl --path-as-is` send raw `..`. | Full disclosure of the database, admin config (PIN and API keys), `.env`, and any user-readable file on the host. Combined with B-2 (0.0.0.0) this is remotely exploitable. | High | Yes |
| **B-2** | **No authentication on any endpoint while Docker/compose bind `0.0.0.0`** | `Dockerfile` `ENV HOST=0.0.0.0`; `docker-compose.yml` `HOST: "0.0.0.0"`; `server.py:638` | All read, write, AI-spend and delete endpoints are reachable from the network. Ollama port `11434` is also published unauthenticated. | Anyone on the network can read all project content, run paid AI calls, change config, and delete data (with the PIN obtained via H-1). | High | Yes |

### HIGH

| ID | Finding | Path / symbol | Evidence | Impact | Conf. | Runtime |
|---|---|---|---|---|---|---|
| **H-1** | **Admin PIN disclosed in plaintext** | `admin/config.py:77-87` `to_safe_dict`; `services/admin.py` `get_admin_config`; route `GET /api/admin/config` (`server.py:172`) | `to_safe_dict` masks `api_keys` but returns every other dataclass field, including `admin_pin` | The only control on archive/delete is readable by any caller | High | Yes |
| **H-2** | **PIN can be replaced without knowing it** | `admin/config.py:163-164`; `handlers/admin.py` `handle_update_config`; `POST /api/admin/config` (`server.py:409`) | `update_config` sets `admin_pin` from the body with no PIN check | Full bypass of destructive-action protection | High | Yes |
| **H-3** | **Wildcard CORS on every JSON response and OPTIONS** | `server.py:568`, `server.py:600`, `server.py:369` | `Access-Control-Allow-Origin: *`; `_read_body` parses JSON regardless of `Content-Type`, so `text/plain` "simple" POSTs avoid preflight | A malicious web page can read project data and the PIN (H-1) from `localhost:8080`, then issue state-changing POSTs (CSRF), e.g. delete projects | Medium (browser Local Network Access may block parts) | Yes |
| **H-4** | **Arbitrary server-side file ingestion** | `server.py:393` → `handlers/ingest.py` → `services/ingest.py:33-36` | `file_paths` from the request body; relative paths joined to repo root, absolute paths used as-is; any file with a supported extension (`.txt .md .csv .eml .pdf .docx`) is parsed and stored in the project, then readable via the context APIs | Disk read outside user intent (charter §6 forbids unrestricted disk access) | High | Yes |
| **H-5** | **Secrets and PIN stored in plaintext JSON at a cwd-relative path** | `admin/config.py:16-17` `CONFIG_DIR = Path("projects_data")`; `save_config` writes `asdict(config)` including `api_keys` and `admin_pin` | Not under `PROJECTS_DATA_DIR`; location depends on where the process was started; readable via B-1 | Credential exposure; config written to an unexpected directory | High | Yes |
| **H-6** | **Irreversible delete with no backup or export** | `services/project.py:205-243` | `shutil.rmtree(project_dir)`; `DELETE FROM` 10 tables; exceptions swallowed. No backup or export capability exists anywhere | Permanent data loss, partly silent on DB error | High | Yes |

### MEDIUM

| ID | Finding | Path / symbol | Evidence | Impact | Conf. | Runtime |
|---|---|---|---|---|---|---|
| M-1 | **DOM XSS via filename in inline `onclick`** | `static/index.html:1112` `onclick="…toggleFileActive('${escHtml(fn)}',…)"`; `escHtml` at `static/index.html:423-426` | `escHtml` escapes `& < > "` but not `'`. A file named `x');alert(document.domain);//.txt` breaks out of the JS string. The HTML parser decodes entities before JS runs, so attribute-context escaping isn't sufficient anyway. ~70 other `onclick` interpolations exist; most use server IDs, but the pattern is unsafe. | Script execution in the app origin, which then has unauthenticated full API access | Medium | Yes |
| M-2 | Unescaped server strings in `feedback.html` | `static/feedback.html` `${ver.status}`, `${r.error||…}` (innerHTML) | External-reviewer page renders some values without `escH` | XSS on the externally shared page if those values are attacker-controlled | Medium | Yes |
| M-3 | **No Content Security Policy** or other security headers | `server.py` `_serve_static`, `_json_response` | No `Content-Security-Policy`, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options` | XSS has no mitigation; clickjacking possible | High | No |
| M-4 | **Full prompts (containing document content) retained after "permanent" delete** | `processors/prompt_logger.py:83-95` (`prompt_log.final_prompt`); `services/project.py:232-235` table list omits `prompt_log` | Delete purges 10 tables, not `prompt_log` | Residual sensitive content after the user believes it's deleted | High | Yes |
| M-5 | **Silent archive eviction** | `services/project.py:33,180-190` | 6th archive marks the oldest archived project `deleted` without confirmation | Unexpected loss of access to data | High | Yes |
| M-6 | **Silent overwrite on ingest** | `services/ingest.py:39` | Output keyed by `path.stem` | Data loss / wrong context in reviews | High | Yes |
| M-7 | **Swallowed storage errors / SQL–JSON divergence** | `services/project.py:66-93`; numerous `except Exception: pass` | Failures don't surface to the user | Silent rollback or loss; charter §5 "visible storage failures" unmet | High | Yes |
| M-8 | **Third-party transmission without a per-send boundary notice** | callers listed in §3 | Backend selection is a dropdown; no "this sends N documents to <provider>" confirmation; no record of what was sent other than `prompt_log` | Charter §4 "no external transmission without explicit user action": partially met (user picks a backend) but not informed | Medium | Yes |
| M-9 | **Review and artefact deletes require no PIN and have no server-side guard** | `db/hierarchy_store_sql.py:432-439` `delete_review`; `db/artifact_store_sql.py:272-286` (`unlink` plus `DELETE`) | UI uses `confirm()` only (`static/index.html:1313,1743`) | Reachable via CORS/CSRF (H-3) | High | Yes |
| M-10 | Gemini API key in URL query string | `ai_backends/gemini_backend.py:66-68` | `?key=<API key>` | Keys can surface in proxy logs or exception text | Medium | Yes |
| M-11 | Admin-entered API keys partially echoed | `admin/config.py:83` | First 4 chars plus mask returned in `GET /api/admin/config` | Minor key disclosure; combined with B-1 the full key is exposed anyway | High | No |

### LOW

| ID | Finding | Path / symbol | Evidence | Conf. | Runtime |
|---|---|---|---|---|---|
| L-1 | PIN comparison isn't constant-time; no rate limiting or lockout | `services/project.py:59` | `pin != configured_pin` | High | No |
| L-2 | Unbounded request body read | `server.py:503`, `server.py:588` | `rfile.read(Content-Length)` with no cap | High | Yes |
| L-3 | Upload filename used in the storage path | `processors/artifact_store.py:103`, `db/artifact_store_sql.py:108` | `f"{artifact_id}_{file_name}"`; `../` sequences produce a non-existent intermediate directory so writes likely fail, but there's no explicit sanitisation | Medium | Yes |
| L-4 | Error messages returned verbatim (`str(e)`) | `handlers/*.py` | May leak filesystem paths | High | No |
| L-5 | Historical default PIN in Git history | Git history: `ADMIN_PIN = "1234"` | Not present at HEAD | High | No |
| L-6 | Single-threaded server | `server.py:638` | One slow AI call blocks every request (availability, not confidentiality) | High | Yes |
| L-7 | Diagram download sets `Access-Control-Allow-Origin: *` | `server.py:369` | Same class as H-3 | High | No |

## 5. Topic checklist (charter §11)

| Topic | Status | Reference |
|---|---|---|
| Content leaving the origin | Only to user-selected AI providers | §3, M-8 |
| External scripts / fonts / CDN | None | §3 |
| Insecure CORS | Present | H-3, L-7 |
| Services bound to all interfaces | Docker/compose | B-2 |
| Tokens/credentials in source | None at HEAD (`.env.example` uses placeholders `changeme`, blank keys) | — |
| Credentials in browser storage | None (localStorage holds UI prefs only) | — |
| Credentials on server disk | Plaintext `admin_config.json` | H-5 |
| Secret-like values in Git history | Scan of `git log --all -p` for Groq, OpenRouter, Google, AWS, GitHub and Slack key patterns and private keys: **no matches**. Only placeholder PINs (`1234`, `changeme`, `dev-pin-1234`, `your-secure-pin`). No `.db`, `.env`, `projects.json` or log file ever committed. | L-5 |
| Unsafe HTML rendering / XSS | ~140 `innerHTML` sinks; escaping mostly present but incomplete | M-1, M-2 |
| Path traversal | Present | B-1, H-4, L-3 |
| Dependency advisories | Not assessable offline; no lockfile; see `DEPENDENCY_BUILD_REGISTER.md` | — |
| PII handling | No classification, retention or redaction; sample data is synthetic | M-4 |
| Logs containing content | Python logging at INFO doesn't log bodies (`log_message` → DEBUG). `prompt_log` DB table stores full prompts by design. | M-4 |
| Destructive actions / confirmation | `confirm()`/`prompt()` in UI only; no server-side two-step; PIN bypassable | H-1, H-2, H-6, M-5, M-9 |
| Source maps / debug artefacts | None exist | — |
| Backups | None | H-6 |
| Authentication | None | B-2 |
| CSP | None | M-3 |

## 6. Git content risks

| Item | Risk |
|---|---|
| `_archive/migration_demo/**` (~70 files, ~600 KB) | Contains an older standalone server with its own `localStorage` persistence. Not served, but excluded only by `.dockerignore`. Low risk, cleanup candidate. |
| `sample_data/*`, `_archive/**/sample_data` | Synthetic healthcare/CPG scope docs; no real PII observed. Low. |
| `.kiro/` agent specs and steering | Not sensitive; describes intended constraints. |
| ~120 remote branches | Old branches may contain divergent copies of code with the same vulnerabilities; not individually audited. |
| Untracked `.claude/prompts/`, charter | Not committed; no secrets observed. |

## 7. Priority summary

1. B-1 path traversal and B-2 network exposure: fix before any use beyond a single trusted loopback session.
2. H-1, H-2, H-3 together form a full "malicious web page reads the PIN, then deletes data" chain on a developer's own machine.
3. H-4 to H-6 and M-4 to M-7: the data-integrity and privacy foundations the charter requires before release.
