# Risk Register

| Field | Value |
|---|---|
| Date | 2026-10-04 |
| Scale | Likelihood and Impact: Low / Medium / High |
| Rule | Review at every phase gate. Add rows; don't delete them. Close a risk by setting Status to Closed with evidence. |

| ID | Risk | Likelihood | Impact | Affected items | Mitigation (built into the backlog) | Owner | Status |
|---|---|---|---|---|---|---|---|
| R-01 | Browser storage is cleared or evicted (Safari inactivity, user clears site data, profile reset) and the user loses projects | Medium | High | DAT-05, BAK-01–03 | Persistence request; visible "last backup" indicator and reminders; backup/restore round trip tested; help text | Owner (users told to back up) | Open |
| R-02 | A service-worker release pins a broken version on users' machines | Medium | High | PWA-02, PWA-03, PWA-04 | Recovery page and remote kill-switch ship before the SW (PWA-04 → PWA-02); user-confirmed updates; e2e for both kill routes | Maintainer | Open |
| R-03 | A schema migration corrupts or loses data | Low | High | DAT-01, ODI-02 | Atomic `upgradeneeded`; downgrade guard; quarantine; backup prompt in the update panel; migration e2e from fixture DB | Maintainer | Open |
| R-04 | Corporate policy blocks PWA install, `.bat`/`.command` launchers or File System Access | Medium | Medium | PWA-01, BLD-02, ODI-02, EXP-03 | App works in a normal tab; V1 fallbacks everywhere; manual verification on the owner's laptop recorded as UNVERIFIED until done | Owner | Open |
| R-05 | Hosted (HTTPS) and local (127.0.0.1) copies hold separate data, and users think data was lost | Medium | Medium | BLD-02, REL-01, DOC-02 | Origin shown on start page and in help; backup/restore documented as the transfer route; fixed port (ADR-022) | Maintainer | Open |
| R-06 | OpenRouter rejects browser-origin requests (CORS), so OD-6 can't be met without a server | Medium | Medium | AI-02–04 | Spike first; stop and decide via new ADR; no silent proxy | Owner | Open |
| R-07 | Users send confidential content to OpenRouter | Medium | High | AI-01–04 | Off by default; exact-payload preview and per-request consent; minimised payloads; warning text; key in memory only | Owner / users | Open |
| R-08 | Copilot output treated as fact in project records | Medium | High | CPL-02, CPL-03, CPL-04 | Paste-back is always Draft; FACT impossible by construction (unit tests); acceptance only as Recommendation with name and time | Maintainer | Open |
| R-09 | Copilot paste or Agent Builder limits differ from assumed defaults (12,000 chars; 8,000 chars) | High | Low | CPL-01, CPL-04 | Limits are settings; manual trials record the real values in DECISION_REGISTER | Owner | Open |
| R-10 | Ported extraction or review behaviour silently differs from legacy | Medium | Medium | MIG-01, MIG-02 | Golden parity tests; every difference listed in `ACCEPTED_DIFFERENCES.md` and accepted by the owner | Maintainer | Open |
| R-11 | XSS through imported content or file names | Medium | High | SEC-01, SEC-02, UI-01, IMP-05, EXP-01 | No HTML sinks (CI), Trusted Types, safe DOM builder, hostile fixtures, CSP-violation e2e listener | Maintainer | Open |
| R-12 | Legacy code with BLOCKER vulnerabilities is published | Low | High | CLN-02, REL-02 | Publication checklist depends on legacy removal; owner-only visibility change; history note | Owner | Open |
| R-13 | Personal identifiers in Git history become public on publication | High (if published) | Medium | REL-02 | Checklist lists all author identities for explicit acknowledgement; no history rewrite by the model | Owner | Open |
| R-14 | A small model widens scope or "cleans up" unrelated files | Medium | Medium | All | `SMALL_MODEL_EXECUTION_RULES.md`; per-item "files that must not change"; diff inspection; one commit per item | Owner reviewer | Open |
| R-15 | Tests pass but the real browser behaves differently (policy, OneDrive client, Copilot apps) | Medium | Medium | ODI-01, ODI-02, CPL-01, CPL-03, CPL-04, BLD-02 | Manual verification fields with UNVERIFIED markers; phase-2 exit requires the owner's corporate-laptop checks | Owner | Open |
| R-16 | Zip, DOCX or PDF parsing of hostile files hangs or exhausts memory | Low | Medium | IMP-06, IMP-07, EXP-02 | Size caps, zip-bomb guards, yielding import loop, vendored pdf.js only | Maintainer | Open |
| R-17 | The owner can't maintain Node/Playwright tooling | Medium | Medium | TST-01, TST-02 | Dev-only, pinned, CI runs everything; no runtime dependency; the app runs without Node | Owner | Open |
| R-18 | Large session cost or rework because the backlog is too long for one pass | Medium | Low | All | Phases with gates; release points; items independently shippable | Owner | Open |
| R-19 | Microsoft Graph or Copilot API work starts before approvals | Low | High | GRA-*, CPL-05 | Items BLOCKED; Phase 4 entry criterion; rules forbid partial implementation | Owner | Open |
| R-20 | `EXP-01` widens the forbidden-API allow-list too broadly | Low | Medium | EXP-01 | Allow-list scoped to one file and one API; reviewer checks the diff | Maintainer | Open |
