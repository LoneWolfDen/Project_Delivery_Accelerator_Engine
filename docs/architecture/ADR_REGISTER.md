# Architecture Decision Register

| Field | Value |
|---|---|
| Date | 2026-10-04 |
| Statuses | **Accepted** (backed by an explicit owner decision OD-n from `CURRENT_IMPLEMENTATION_ASSESSMENT.md` §14), **Proposed** (architect recommendation; needs owner confirmation), **Blocked** (waiting on external prerequisites), **Superseded** |
| Rule | Decisions are appended or superseded, never edited away. A change of mind gets a new ADR that supersedes the old one. |

---

| ID | Decision | Status | Basis / evidence | Consequences | Alternatives rejected |
|---|---|---|---|---|---|
| ADR-001 | Target is a **browser-only PWA**; the Python server is retired at cutover | Proposed (strongly implied by OD-1, OD-2, OD-4) | OD-1 (non-technical users, no terminal); server-class vulnerabilities B-1, B-2, H-1–H-4 disappear with no server; Docker out of scope (OD-4) | Domain logic ported to JS; all data on the device; no multi-device sync | Keep Python server behind a one-click launcher (still requires Python on every laptop, plus the server attack surface); Electron/desktop app (installer, charter §1) |
| ADR-002 | **Build model A: human-readable no-build** (native ES modules); Node only as dev tooling for tests | Proposed | `TARGET_ARCHITECTURE.md` §1 evidence table; no healthy build exists (D-1–D-8) | No transpiling or bundling; one generated file (`precache-manifest.js`) with a checked-in generator | Model B with Vite or similar (adds toolchain the owner can't maintain; no existing build to keep) |
| ADR-003 | **IndexedDB** single database `pdae`; IndexedDB version = schema version; atomic migrations; quarantine; Trash | Proposed | Charter §5 minimums; legacy silent-loss defects M-4–M-7 | Data is per browser profile and origin; backup is essential | OPFS-only (less inspectable, Safari gaps); `localStorage` (size and charter) |
| ADR-004 | **Backup file** `.pdae-backup.json` with manifest, per-record and whole-file SHA-256; restore with preview, no silent overwrite | Proposed | Charter §5; legacy had no backup (H-6) | Large backups when originals are included ("text only" option provided) | ZIP backup (more code; possible later as format v2) |
| ADR-005 | **Hosting:** static files on GitHub Pages once the repo is public; **local launcher** (`python -m http.server` on `127.0.0.1:8765`, double-click) as fallback and pre-public route | Proposed | OD-1 (Python allowed, UI-driven start); OD-5 (going public under MIT) | Hosted and local copies have separate data (origin); corporate approval of the hosting origin may be needed (P6) | `file://` (modules and SW don't work); corporate SharePoint hosting (doesn't serve executable web apps); paid static host |
| ADR-006 | **Single external AI provider: OpenRouter**, off by default; key in session memory only; consent token per request with exact-payload preview | **Accepted (OD-6)** for the provider choice; mechanism Proposed | OD-6; charter §4, §9 | Groq, Gemini, Bedrock and Ollama adapters not ported; browser-to-OpenRouter CORS to be confirmed in S10 spike | Multiple providers (more surface, OD-6 says generic single provider); persisted key (charter §4) |
| ADR-007 | **Microsoft 365 Copilot via Pattern A only** (package plus paste-back, stored as Draft); Pattern B by user-saved files; Pattern C blocked | **Accepted (OD-6)** for "without API"; details Proposed | OD-6; charter §8 | No Copilot API, automation or identity in V1/V2 | Browser automation of Copilot (forbidden by charter §8) |
| ADR-008 | **Deterministic retrieval by default**: quoted evidence or Not found, never generated prose; every statement labelled and cited; external output never Fact | Proposed | Charter §9; legacy C5–C7 | Answers are evidence lists without AI, which is less fluent but trustworthy | Local small language model in browser (size, quality, device policy) |
| ADR-009 | **No runtime third-party code** except `pdf.js` (vendored, hash-pinned) in a later slice; DOCX parsed with built-ins | Proposed | Charter §2 vendor rules; no CDN today (dependency register §3) | Some parsing code to maintain in-house (ZIP, DOCX) | mammoth.js / JSZip (extra vendor surface for small gain) |
| ADR-010 | **Security baseline:** meta CSP (`script-src 'self'`, no inline), Trusted Types with one script-URL policy, no `innerHTML` (CI-enforced), text-only rendering of document content | Proposed | Security M-1–M-3 | Rendering helpers must be used everywhere; Markdown shown via a safe subset renderer | Sanitiser library (vendor surface); header-based CSP (not possible on GitHub Pages) |
| ADR-011 | **Service worker:** precache shell, cache-first, no user data, versioned cache, user-confirmed update with backup prompt, `reset.html` and remote `kill-switch.json` | Proposed | Charter §10 ("kill-switch"); no SW exists today, so no legacy pinning risk | Every release regenerates the precache manifest | No SW (no offline, not installable); network-first (fails offline) |
| ADR-012 | **First-release scope:** projects, import with provenance, extraction, Ask, snapshots, deterministic persona reviews, exports, Copilot package, backup and restore; optional OpenRouter. **Deferred:** proposals and versions workflow, presales feedback, reconciliation, synthesis, decision log, diagrams, phases and gates | Proposed (**owner to confirm**) | OD-2 (owner unsure what works); these features are large and partly unreachable today (U4, U5, U13) | Some legacy capabilities are temporarily absent after cutover | Port everything (high cost, unverified value) |
| ADR-013 | **No automated migration of legacy data**; users re-import documents | Proposed (**owner to confirm**) | Legacy data appears to be seeded demo data; importer would need Python | If real legacy data exists, add one developer script producing a backup file | Full SQLite → IndexedDB migrator |
| ADR-014 | **Side-by-side migration in vertical slices**; legacy untouched until cutover; tag `legacy-final` | Proposed | Charter §13; migration strategy §4–5 | Two apps coexist in the repo for a period | Big-bang rewrite (violates "never replace the entire UI in one untested change") |
| ADR-015 | **Remove Docker** and container start-up paths | **Accepted (OD-4)** | OD-4; D-1 broken | `Dockerfile`, `docker-compose.yml`, `.dockerignore` removed (may happen early) | — |
| ADR-016 | **MIT licence**; add `LICENSE` before publishing | **Accepted (OD-5)** | OD-5; licence file missing (B7) | Pre-publication checklist: security BLOCKER/HIGH fixed, synthetic data only, author identities in history become public | — |
| ADR-017 | **External-reviewer feedback link out of scope** | **Accepted (OD-3)** | OD-3 | No network-exposed features in target | — |
| ADR-018 | **Testing:** `node --test` (unit), Playwright Chromium plus WebKit (e2e), characterization against legacy golden outputs; CI is the release gate | Proposed | Test assessment T-1–T-8 | Dev-only `package.json` and lockfile | Keep pytest for the new app (no Python in target); source-string tests (proven ineffective, T-2) |
| ADR-019 | **Microsoft Graph / File Picker (V3)** only after prerequisites P1–P8 are recorded | Blocked | Charter §6–7 V3; `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §5 | Connector interfaces reserve the slot | Building Graph code speculatively |
| ADR-020 | **No application authentication in V1/V2**; MSAL.js with PKCE, delegated only, in V3 | Proposed | Single user on own device; no server | Device and OS sign-in is the access control; app lock deferred | Passphrase app lock now (forgotten-passphrase data-loss risk for non-technical users) |
| ADR-021 | **Patch legacy B-1, H-1, H-2 minimally** while the legacy app remains in use; everything else via usage restriction | Proposed (**owner to confirm**) | OD-5 (public repo), OD-8 (treat H-3 as unmitigated) | Small contained legacy changes before cutover | Leave legacy unpatched while public |
| ADR-022 | **Fixed local port 8765** for the launcher | Proposed | IndexedDB per origin | Changing the port "loses" data unless backup and restore are used | Random free port |

## Open items needing owner input

| Item | ADR | Question in plain words |
|---|---|---|
| Q-A | ADR-012 | Is the first-release feature list right? Anything in "Deferred" that you actually rely on? |
| Q-B | ADR-013 | Do you have any real project data in the old app that must be kept? |
| Q-C | ADR-021 | Will you keep using the old app for a while, and should it get the three small safety fixes? |
| Q-D | ADR-005 | Is a public GitHub Pages address acceptable to open on your work laptop, or will IT need to approve it? |
| Q-E | ADR-007 | Do your users have a Microsoft 365 Copilot licence, or only Copilot Chat? This decides whether Copilot V2 (grounding on saved files) works. |

---

## Owner answers and status changes (2026-10-04)

The owner answered Q-A to Q-E. Entries above are left unchanged as history; the status changes and new ADRs below take precedence.

| Question | Owner answer | Effect |
|---|---|---|
| Q-A (ADR-012 scope) | Deferred features aren't relied on; "each of them breaks at some point" | **ADR-012 → Accepted** |
| Q-B (ADR-013 legacy data) | No real data in the old app | **ADR-013 → Accepted** |
| Q-C (ADR-021 legacy patches) | Won't keep using the old app | **ADR-021 → Superseded by ADR-023** |
| Q-D (ADR-005 hosting) | GitHub is reachable without approval in the owner's organisation, but this mustn't be assumed for other organisations | **ADR-005 → Amended by ADR-024** |
| Q-E (ADR-007 Copilot) | All users have a **Microsoft 365 Copilot (premium) licence**, but **no API access**. Copilot is used through the Copilot desktop app, Teams, SharePoint and **Agent Builder** | **ADR-007 → Amended by ADR-025** |

| ID | Decision | Status | Basis | Consequences |
|---|---|---|---|---|
| ADR-023 | **Retire the legacy app early, without patching it.** The legacy Python app isn't run by anyone. Its value is captured first (golden outputs of extraction and persona heuristics; persona definitions converted to JSON). It's then tagged `legacy-final` and removed in one contained cleanup item, once the JavaScript ports of extraction and persona review pass their parity tests. **The repository must not be made public before that removal**, because legacy security BLOCKERs (B-1, B-2, H-1–H-3) would otherwise be published as runnable code. | Accepted (Q-C, OD-5) | Owner doesn't use the legacy app; ADR-014's side-by-side period no longer protects any user | No legacy security patches; the old app stays retrievable via `git checkout legacy-final` |
| ADR-024 | **Hosting-neutral app.** The PWA must run unchanged from **any static HTTPS origin** or from the **local launcher** (`127.0.0.1:8765`). No code, URL, documentation step or test may assume GitHub Pages. GitHub Pages is documented as one example deployment, used by the owner's organisation. The local launcher is the organisation-neutral route. | Accepted (Q-D) | Owner: "don't want this expectation possible across organisations" | All asset paths relative; no absolute origins in code except `https://openrouter.ai` in CSP and `ai/openrouter.js`; deployment workflow optional and separable |
| ADR-025 | **Copilot through licensed desktop surfaces, no API.** Users have M365 Copilot licences, so **Pattern B (grounding on files the user saves to OneDrive/SharePoint) is viable for all users**. Agent Builder is in use, so the app may additionally export an **Agent Builder kit**: instructions text plus a recommended knowledge-folder layout that the *user* pastes and configures manually in Agent Builder. The app never calls Copilot, Agent Builder or Graph, and never automates their UIs. Paste-back remains the return path; returned text stays Draft. | Accepted (Q-E, OD-6) | Charter §8 Patterns A and B; no API available | Copilot V1 (package and paste-back) and V2 (Copilot-ready export layout, Agent Builder kit) are P2. Pattern C (APIs, connectors, programmatic agents) stays Blocked. Agent Builder limits (instruction length, knowledge-source types, sharing policy) must be verified on the tenant during the kit item. |

## Owner approval of proposed decisions (2026-10-04)

The owner approved all architecture decisions still marked **Proposed** (ADR-001 to ADR-004, ADR-008 to ADR-011, ADR-014, ADR-018, ADR-020, ADR-022) and **delegated architecture authority**: "I will rely on you acting as enterprise architect, solution architect and full-stack developer to adapt the best possible architecture." Those ADRs are now **Accepted**. Future changes follow the same rule: a new ADR that supersedes, never an edit.
