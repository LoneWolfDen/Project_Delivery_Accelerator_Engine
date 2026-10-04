# Copilot and Chat Architecture

| Field | Value |
|---|---|
| Status | Proposed. The provider decision is accepted from owner decision OD-6. |
| Date | 2026-10-04 |
| Parent | `TARGET_ARCHITECTURE.md` §13–15 |
| Current state | No chatbot exists. Legacy AI calls send full project context to the selected provider with no per-send notice. Heuristic fallback text appears as findings without citations or labels (`CURRENT_IMPLEMENTATION_ASSESSMENT.md` C1–C8). |
| Owner decision OD-6 | **OpenRouter** is the single generic API provider. The ideal is working with **Microsoft 365 Copilot licences without an API**. |

---

## 1. Principles

1. **Useful with no AI at all.** "Ask" and "Review" work deterministically and are the default.
2. **No invented answers.** Without AI, the app returns quoted evidence or **Not found**, never generated prose. With AI, every statement must cite stored evidence or be downgraded.
3. **Every statement is labelled** `FACT`, `INFERENCE`, `RECOMMENDATION`, `NOT_FOUND` or `NEEDS_CONFIRMATION`, and carries an `origin` (`deterministic | openrouter | copilot-pasted | user`). See `DATA_AND_STORAGE_ARCHITECTURE.md` §2.
4. **The search scope is always shown** ("Searched 12 sources in Project X, snapshot 'v3 – client review'").
5. **External AI is off by default.** Every transmission shows its exact payload first and needs a click.
6. **External output is never Fact.** OpenRouter or Copilot text is stored as Draft, and can only be promoted by the user to Recommendation, with name and time recorded.

## 2. Deterministic retrieval ("Ask", no AI)

**Index**

- Chunks are built at import: paragraphs and headings for text, Markdown and DOCX; rows for CSV (header kept as context); messages and paragraphs for EML; pages and paragraphs for PDF later.
- Target chunk size is 80–300 words, with locators (`TARGET_ARCHITECTURE.md` §10).
- `search/index.js` builds an in-memory inverted index (lower-case, Unicode-normalised, simple English suffix stemming, stop-word list) and ranks with BM25. It's rebuilt from `chunks` on project open, which is fast enough for the expected corpus (hundreds of documents). It's only persisted if measurement shows the need.

**Query**

The user's question, plus the **scope selector**: project, snapshot, chosen sources, date range.

**Result screen**

```
Question: "What are the data residency constraints?"
Scope: Project "Cloud Migration" · all 12 sources · searched 940 passages
Evidence (5 passages)
  [FACT] "All patient data must remain within UK data centres."   — SoW_v3.docx · §4.2 Constraints · ¶3
  [FACT] "Backups replicate to the EU-West region nightly."        — Infra_notes.md · ## Backup · ¶1
  …
Related extracted items: Constraint #14, Risk #3
Nothing here was written by AI. Passages are quoted exactly from your documents.
```

- **Not found:** "No passage in the 12 searched sources mentions data residency. Searched for: data, residency, region, sovereignty (and variants)." Labelled `NOT_FOUND` with the scope.
- **Weak matches** (score below threshold) are shown under "Possibly related", labelled `NEEDS_CONFIRMATION`.
- **No synthesis sentence** is produced in deterministic mode. That's what guarantees nothing is invented.

## 3. Deterministic reviews (honest labelling of heuristics)

Persona definitions are ported from `personas/definitions/*.yaml` to `app/js/review/personas/*.json`, with their focus areas, core questions and output sections kept. The legacy heuristics (`personas/engine.py` `_heuristic_findings`, `personas/deep_dive.py` `_heuristic_questions`) are reshaped so every finding says what it is:

| Legacy behaviour | Target behaviour |
|---|---|
| Matched item copied into "risks" | `FACT`, quoting the item's source span, with citation |
| Generic sentence when a keyword is absent ("No cost model or FinOps strategy found") | `NOT_FOUND`: "No mention of cost model / FinOps in 12 sources (searched: cost, budget, finops, …)", with scope |
| Fixed advice ("Conduct security threat model") | `RECOMMENDATION`, origin `deterministic`, marked **Checklist guidance, not from your documents** |
| Fixed questions ("Is a CI/CD pipeline defined?") | `NEEDS_CONFIRMATION`: a question for the team, linked to the related `NOT_FOUND` |

The review header always says "Deterministic review: checklist plus keyword evidence. No AI was used." There's no silent AI-to-heuristic fallback (legacy C6). If an AI run fails, the user is told, and can choose to run the deterministic review instead.

## 4. AI provider boundary

```
interface AIProvider {
  id: "none" | "openrouter"
  isConfigured(): boolean                  // openrouter: key present in memory and AI enabled in Settings
  describeEgress(request): EgressPreview   // exact JSON body, destination host, model, size, item list
  complete(request, consentToken): Promise<RawResponse>
}
```

- **Default `none`:** every AI button is hidden or disabled with the text "AI is off (Settings → AI)".
- **`openrouter`** (only external provider, OD-6): `POST https://openrouter.ai/api/v1/chat/completions`, `Authorization: Bearer <key>`, model ID from Settings. No other request headers carry identifying data (no `HTTP-Referer` with a repository URL, unlike legacy). Browser-origin calls to OpenRouter need confirming in the first implementation spike, and are a stated assumption (ADR-006).
- **Key handling:** the user pastes the key in Settings each session. It's held in module memory only, never persisted, logged, exported or backed up (charter §4). The help text explains how to keep it in a password manager.
- **Consent token** (`ai/consent.js`): created only by the click on **Send** in the egress preview dialog, bound to the SHA-256 of the exact request body, single-use. `complete()` refuses without a matching token, so no code path can send data silently.
- **Egress preview dialog:**
  - destination (`openrouter.ai` → routed to model provider `<model>`)
  - number of passages and characters
  - the list of sources involved
  - a collapsible exact payload
  - a warning "This sends the text below outside your device to OpenRouter and the model provider. Don't send content your organisation hasn't approved for external AI."
  - buttons **Send** / **Cancel**
- **Minimisation:** only the top-k evidence passages for the question (default k = 8, max characters a setting), never the whole project. The same applies to AI-assisted reviews: the evidence for each persona section, not full documents.
- **Future slots:** `approved-azure-openai`, `corporate-endpoint`, implementing the same interface, each needing its own ADR and data-boundary entry. No Copilot API provider at V1/V2 (§6).

## 5. AI-assisted Ask and Review (optional, OpenRouter)

**Request:** a system instruction requiring JSON output:

```json
{ "statements": [ { "text": "…", "label": "FACT|INFERENCE|RECOMMENDATION|NOT_FOUND|NEEDS_CONFIRMATION",
                    "citations": [ { "chunkId": "c_…", "quote": "exact substring" } ] } ] }
```

Passages are supplied with their `chunkId`s.

**Validation** (`ai/validate.js`, deterministic, unit-tested):

1. JSON parse failure stores the raw text as one `Draft` statement labelled `NEEDS_CONFIRMATION`, with "AI response wasn't in the expected format".
2. For each citation: the `chunkId` must be in the sent set, and `quote` must be an exact (whitespace-normalised) substring of that chunk. Otherwise the citation is dropped and flagged.
3. `FACT` with no valid citation is downgraded to `NEEDS_CONFIRMATION`.
4. `INFERENCE` and `RECOMMENDATION` without citations are kept, marked "no supporting passage".
5. `NOT_FOUND` from AI is shown only alongside the deterministic search scope.

**Display:** origin badge "AI (OpenRouter · model)", label badges, clickable citations that open the source at the locator, and a **Compare with evidence** toggle. Stored as `Answer` / `Review` with `origin: "openrouter"`. Statements are never auto-merged into extracted items.

## 6. Microsoft 365 Copilot

An interactive Copilot licence isn't a JavaScript API (charter §8). The app never automates Copilot in the browser.

### V1: grounded package; the user takes it to Copilot (no API, no approvals; meets OD-6 "without API")

**Prepare for Copilot** (from Ask, Review or Project):

1. The user picks the purpose (template): "Challenge this review", "Draft client-ready risk summary", "Find gaps against SoW", or custom.
2. The app builds a **package**:
   - `PROMPT.md`: the task, the rules ("Use only the material below. Cite IDs like [S3-P12]. Say 'Not found' if the material doesn't cover it. Mark each point Fact / Inference / Recommendation."), and the user's question.
   - `CONTEXT.md`: the selected extracted items and evidence passages, each prefixed with a stable citation ID `[S<source#>-P<passage#>]`.
   - `SOURCES.json`: the source manifest (name, SHA-256, as-of date, sourceSystem), with no file contents.
   - `context.json`: machine-readable equivalent of `CONTEXT.md`.
   - Optional `REPORT.html`: human-readable view.
3. **Delivery options:**
   - **Copy to clipboard:** `PROMPT.md` plus `CONTEXT.md` as one text, checked against a size limit (setting; default 12,000 characters). Copilot chat input limits vary by tenant and product, so the setting must be tuned on the user's tenant. Over the limit, the app splits into numbered parts ("Part 1 of 3: reply 'continue' after each part") or suggests the file route.
   - **Download package:** `.zip` (stored, no compression, written by `exports/zip-write.js`). The user uploads or attaches the files in Copilot, or saves them to OneDrive first (V2).
4. Boundary notice (same as `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §3 V1), plus "Copilot processes this under your organisation's Microsoft 365 terms."
5. **Paste-back:** **Add Copilot reply** opens a text area. The app stores it as a `Draft` (`origin: "copilot-pasted"`, linked to the package ID and its hash, timestamp). It then:
   - extracts citation IDs present in the reply and marks each as **resolves** or **unknown ID**;
   - splits paragraphs into statements, initially all `NEEDS_CONFIRMATION`, or `RECOMMENDATION` / `INFERENCE` if Copilot labelled them so;
   - **never `FACT`**: a Copilot statement can at most *point to* a passage. The Fact is the passage itself.
6. The user can **Accept as Recommendation** per statement (records who and when), **Discard**, or **Edit**, which keeps the original text plus the edited text.

### V2: Microsoft-native grounding on user-saved outputs

- The user saves approved exports (V2 save picker or V1 download) into a OneDrive or SharePoint location they choose.
- Copilot (with a **Microsoft 365 Copilot licence**; Copilot Chat without that licence may only use uploaded files) can ground on those files through existing permissions.
- The app's role: produce well-structured, citable files (stable IDs, manifest, as-of dates), and show governance guidance: "Files saved to a shared library are visible to everyone with access to it; check sharing before asking Copilot."
- Returned text comes back via the same paste-back (V1 step 5).
- No app code accesses M365.

### V3: agents, APIs and connectors (blocked on approvals)

**Candidates:**

- a declarative agent (Agent Builder / Copilot Studio) grounded on a SharePoint location where the app's exports are saved
- Microsoft 365 Copilot APIs or retrieval APIs
- Copilot connectors indexing exported packages
- a remote tool or plugin calling an approved corporate endpoint

**Must be recorded before any work:**

- licensing (per user)
- preview or GA status of each API used
- Entra app registration
- delegated vs application permissions
- admin consent
- hosting (an agent or API integration may need a service, which conflicts with "no server": a new ADR is needed)
- data boundary
- tenant policy (DLP, sensitivity labels)
- operational owner
- audit and retention

**Fit with this architecture:** a declarative agent pointing at the user-saved export folder is the closest to V2, and needs no app code change. Anything that calls Copilot from the app requires identity (`TARGET_ARCHITECTURE.md` §16) and probably a server. That's out of scope until approved.

## 7. Behaviour when AI is unavailable

| Situation | Behaviour |
|---|---|
| AI off (default) | Deterministic Ask and Review; Copilot package available |
| AI on, no key this session | AI buttons show "Enter your OpenRouter key in Settings (kept only until you close the tab)" |
| Offline / network error / 4xx–5xx | Message with code `AI-NET` / `AI-HTTP-<status>`; the request isn't retried silently; offer the deterministic result |
| Response invalid | Stored as Draft, `NEEDS_CONFIRMATION`, raw text visible |

## 8. Demo and fallback text

- No canned or demo answer text exists anywhere in `app/js/`. A CI check fails on known placeholder phrases.
- Demo data is a **synthetic** sample project loadable from Help → Load sample project, clearly badged "SAMPLE" on every screen.
