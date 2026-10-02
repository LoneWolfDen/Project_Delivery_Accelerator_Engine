# Browser-First PWA Architecture Charter
Status: mandatory architecture guidance.
This charter applies to this repository unless a repository-specific constraint is documented with evidence.
## 1. Product target
The target is a maintainable browser-based Progressive Web App for use on a managed corporate laptop.
The application must:
- require no traditional desktop installer
- work in current Microsoft Edge and Google Chrome
- use Safari where practical
- remain usable without administrator rights
- have a clear offline or degraded mode
- support one primary user first
- preserve a path to approved Microsoft enterprise integration
- never claim that a mocked or placeholder integration is live
“Production-ready” in this repository means:
- maintainable source
- predictable startup
- safe data handling
- observable failures
- repeatable tests
- recoverable storage
- controlled releases
- documented limitations
It does not automatically mean:
- multi-tenant SaaS
- tenant-wide Microsoft Graph access
- cloud hosting
- enterprise identity
- unrestricted background automation
- unattended access to corporate systems
## 2. Human-readable source
Application source must be directly maintainable by a human engineer.
Rules:
- minified application code must not be the source of truth
- generated application code must have a checked-in generator
- minified third-party vendor files are permitted only under a vendor directory
- each vendor file must have name, version, licence, source and hash recorded
- compiled CSS must not be treated as editable source unless its generator and source configuration exist
- do not patch inaccessible minified code indefinitely with override layers
- restore readable source or replace the inaccessible component through a controlled migration
- do not introduce a new framework merely to make the repository appear modern
- prefer the smallest architecture that is maintainable and demonstrably works
## 3. Build strategy
Claude must determine which model fits the repository:
A. No-build PWA:
- plain JavaScript ES modules
- local React or another local browser library
- readable HTML and CSS
- no transpilation required
B. Reproducible built PWA:
- human-readable source under src/
- explicit package-lock or equivalent
- documented build and test commands
- generated output clearly separated
- generated output never edited manually
The repository must use one coherent model. It must not mix:
- generated output edited by hand
- source files that are never used
- minified application code plus unrelated readable substitutes
- multiple competing startup paths without documentation
## 4. Data boundaries
The default state is private and local.
Rules:
- no external transmission without explicit user action
- no hidden analytics
- no stored API keys in localStorage
- no passwords, session cookies or access tokens in logs
- no browser automation that captures credentials
- no automated login or circumvention of corporate controls
- every outbound integration must be visible and documented
- development and demo data must be synthetic
- source files remain read-only unless the user explicitly approves an export or update
Every boundary change must be identified:
- device to Microsoft 365 tenant
- tenant to device
- device to approved corporate API
- device to public or third-party service
## 5. Storage model
The assessment must distinguish:
1. Runtime browser storage
2. User-controlled backup and restore
3. User-selected OneDrive or SharePoint content
4. Approved live Microsoft Graph storage
5. Application-managed enterprise storage
Minimum local requirements:
- visible storage failures
- backup and restore
- schema versioning
- corruption preservation
- reset confirmation
- storage usage
- no silent overwriting
- exact rollback instructions
## 6. OneDrive and SharePoint input
The PWA must support staged capability levels:
### V1: User-selected local or synced content
- standard file picker
- drag and drop
- multi-file selection
- user chooses files from a locally synced OneDrive or SharePoint folder
- browser reads only files explicitly chosen by the user
- content is previewed before retention
- no Microsoft Graph requirement
### V2: User-selected folder refresh
- only if supported and allowed by browser policy
- user explicitly selects a folder
- no unrestricted disk scan
- changed files are shown before import
- unsupported browsers fall back to multi-file selection
### V3: Microsoft file picker or Microsoft Graph
- requires validated authentication design
- requires an Entra application registration
- delegated permissions preferred
- least privilege
- tenant consent and administrator requirements recorded
- no implementation until approvals are known
Every imported file must create provenance including:
- source system
- file name
- content hash
- imported time
- modified or as-of date
- parser and version
- sheet, row, page, paragraph or message identifier where relevant
## 7. OneDrive and SharePoint output
The application must distinguish:
### V1: Download and user-save
- PWA creates an export
- user chooses where to save it
- OneDrive or SharePoint sync may copy it to the tenant
- the interface warns that this changes the data boundary
### V2: Browser-supported save workflow
- user chooses the destination
- no silent background upload
- overwrite requires confirmation
- export has a manifest, version and checksum
### V3: Direct Microsoft Graph write
- approved Entra registration
- delegated permissions
- explicit destination picker
- no hard-coded personal drive or site
- write confirmation
- conflict and version handling
- audit information
- revocable access
- rollback and recovery
## 8. Microsoft 365 Copilot
Do not assume an interactive Copilot licence is a general JavaScript API.
Assess separately:
### Pattern A: Manual package workflow
- application exports a grounded package
- user saves or uploads it to Microsoft 365
- Copilot reviews or rewrites it
- generated text returns as Draft or Recommendation
- Copilot output never silently becomes Fact
### Pattern B: Microsoft-native grounding
- approved outputs stored in OneDrive or SharePoint
- Copilot uses existing permissions
- source documents remain governed by Microsoft 365 controls
### Pattern C: Agent or API integration
- declarative agent
- Agent Builder
- Copilot Studio
- Microsoft 365 Copilot APIs
- Work IQ APIs
- Microsoft Graph
- Copilot connectors
- plugins or supported remote tools
Pattern C requires the assessment to record:
- licensing
- preview status
- application registration
- delegated or application permissions
- administrator consent
- hosting
- data boundary
- tenant policy
- operational ownership
- audit and retention
No unsupported Copilot browser automation is permitted.
## 9. Chat assistant
A chatbot must not invent answers.
Required behaviour:
- cite stored sources
- distinguish Fact, Inference, Recommendation, Not found and Needs confirmation
- quote or link to the evidence
- show the search scope
- report when no evidence exists
- never present demo fallback text as project truth
- operate usefully when AI is unavailable
AI providers must be behind an interface.
Default provider:
- none or local deterministic retrieval
Future provider slots may include:
- approved Microsoft 365 Copilot capability
- approved Azure-hosted model
- another approved corporate endpoint
## 10. PWA requirements
Assess:
- manifest
- icons
- scope and start URL
- service worker
- cache versioning
- stale-cache recovery
- update prompt
- offline shell
- degraded mode
- storage persistence
- browser support
- installation policy
- Content Security Policy
- same-origin resources
- no runtime CDN dependency
- accessible fonts
- keyboard navigation
- contrast
- reduced motion
- readable screen-sharing mode
Do not replace a service worker shortly before release without tests and a kill-switch.
## 11. Security and privacy
Assess:
- content leaving the origin
- external scripts
- external fonts
- CDN calls
- insecure CORS
- services bound to all interfaces
- tokens or credentials in source or browser storage
- secret-like values in Git history
- unsafe HTML rendering
- XSS
- path traversal
- dependency advisories
- PII handling
- logs containing content
- destructive actions
- missing confirmation
- missing access boundaries
- source-map and debug artefact exposure
## 12. Quality and testing
Every executable backlog item must include:
- unique ID
- evidence
- current behaviour
- target behaviour
- smallest safe change
- files likely affected
- dependencies
- tests
- manual verification
- acceptance criteria
- rollback
- data migration impact
- privacy impact
- external approval
- explicit exclusions
A smaller model should be able to execute one item without interpreting the entire roadmap.
## 13. Change control
For each implementation item:
- one dedicated branch or one contained commit
- no unrelated cleanup
- no opportunistic refactor
- tests before and after
- inspect the diff
- update continuity documents
- do not commit automatically unless expressly instructed
- stop after the approved scope

