This is an architecture-design task only.
Do not modify application code.
Read:
docs/architecture/PWA_ARCHITECTURE_CHARTER.md
docs/assessment/CURRENT_IMPLEMENTATION_ASSESSMENT.md
docs/assessment/SECURITY_PRIVACY_ASSESSMENT.md
docs/assessment/MINIFIED_AND_GENERATED_CODE_REGISTER.md
docs/assessment/DEPENDENCY_BUILD_REGISTER.md
docs/assessment/TEST_AND_RELEASE_READINESS.md
Design the smallest maintainable target architecture for this repository.
The target must be:
- browser-based PWA
- no traditional desktop installation
- suitable for a managed corporate laptop
- human-readable source
- no minified application code as source of truth
- no hidden external data transmission
- usable without AI
- compatible with future approved Microsoft integration
- recoverable
- testable
- supportable
- operable by one primary user first
Do not force a no-build architecture if the existing repository has a healthy reproducible build system.
Choose explicitly between:
A. Human-readable no-build PWA
B. Reproducible built PWA
Explain the choice using repository evidence.
Design:
1. Source structure
2. Runtime architecture
3. Build or no-build strategy
4. Module boundaries
5. State management
6. Local storage
7. backup and restore
8. schema versioning and migration
9. file import
10. provenance
11. OneDrive and SharePoint input
12. OneDrive and SharePoint output
13. chat and retrieval
14. AI provider boundary
15. Microsoft 365 Copilot patterns
16. authentication options
17. Microsoft Graph future path
18. service worker
19. manifest and installability
20. cache lifecycle
21. configuration
22. logging and diagnostics
23. security controls
24. testing
25. release packaging
26. startup on Windows and macOS
27. browser compatibility
28. accessibility
29. screen-sharing readability
30. migration from the current implementation
OneDrive and SharePoint must be designed in levels:
V1:
- select local files
- select files from locally synced OneDrive or SharePoint folders
- standard file input and drag-drop
- preview before retention
- download export and user chooses the destination
V2:
- optional folder selection and user-triggered refresh
- browser policy permitting
- no unrestricted scanning
- changed-file preview
- graceful fallback to multi-file selection
V3:
- approved Microsoft picker or Graph integration
- delegated access
- least privilege
- explicit destination selection
- administrator and tenant prerequisites
- conflict handling
- explicit data-boundary notice
Microsoft 365 Copilot must be designed in levels:
V1:
- app creates grounded Markdown, HTML, JSON and source manifest
- user intentionally saves or uploads the package
- Copilot review remains external to the app
- returned text is Draft or Recommendation only
V2:
- approved exports stored in a user-selected OneDrive or SharePoint location
- Copilot grounds on the files through existing permissions
- document governance and sharing are explicit
V3:
- approved APIs, agents or connectors
- identity, consent, hosting, operations and audit defined
- no unsupported browser automation
For the chatbot:
- no invented fallback answers
- deterministic retrieval when AI is unavailable
- source citations
- Fact / Inference / Recommendation / Not found / Needs confirmation
- search scope shown
- external AI disabled by default
- future approved corporate AI behind an interface
For minified code migration:
- identify what can be recovered
- identify what must be reconstructed
- preserve working behaviour with characterization tests
- migrate vertical slices
- retain a rollback route
- never replace the entire UI in one untested change
Create only:
docs/architecture/TARGET_ARCHITECTURE.md
docs/architecture/DATA_AND_STORAGE_ARCHITECTURE.md
docs/architecture/ONEDRIVE_SHAREPOINT_ARCHITECTURE.md
docs/architecture/COPILOT_AND_CHAT_ARCHITECTURE.md
docs/architecture/MINIFIED_CODE_MIGRATION_STRATEGY.md
docs/architecture/ADR_REGISTER.md
Do not create implementation code.
Stop after the documents and summary.

