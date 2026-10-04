You are performing a forensic technical assessment of this repository.
This is READ-ONLY analysis.
Do not:
- modify source code
- install dependencies
- update packages
- execute destructive commands
- delete, archive, move or rename files
- format the repository
- generate replacement code
- commit or push
- alter Git history
- treat documentation claims as implemented facts
First read:
docs/architecture/PWA_ARCHITECTURE_CHARTER.md
Then inspect the entire repository, including:
- Git status
- Git branches and tags
- recent commit history
- all tracked files
- repository size and large files
- application source
- generated output
- minified files
- source maps
- build files
- package manifests and lockfiles
- dependency versions
- startup scripts
- environment examples
- configuration
- storage
- service workers
- PWA manifest
- icons
- frontend components
- backend services
- chat or AI implementation
- API clients
- authentication
- OneDrive and SharePoint placeholders
- Microsoft Graph code
- tests
- fixtures
- logs
- documentation
- backup files
- runtime folders
- database files
- credentials or secret-like patterns
- CI/CD
- deployment guidance
- architecture diagrams
- duplicate implementations
- dead code
- unreachable code
Run only safe, read-only commands needed to establish evidence.
If a command could modify files, do not run it.
For every conclusion provide:
- classification
- exact path
- symbol, line or component where practical
- observed evidence
- risk
- confidence
- whether runtime validation is still required
Use classifications:
- WORKING
- PARTIAL
- PLACEHOLDER
- MOCKED
- DOCUMENTED ONLY
- BROKEN
- UNUSED
- GENERATED
- UNKNOWN
Pay special attention to:
1. Whether the application is genuinely React, Vue, another framework, or static/generated HTML.
2. Whether readable source exists for what the browser executes.
3. Every minified JavaScript and CSS file.
4. Whether minified application code has a readable source counterpart.
5. Whether generated files can be reproduced.
6. Whether source maps expose readable source.
7. Whether minified application code has been patched through additional CSS or scripts.
8. Whether unminification alone would be misleading because variable names and component structure are already lost.
9. The safest migration from minified application output to maintainable human-readable source.
10. Whether the repository has one coherent build model.
11. Whether runtime dependencies come from CDNs.
12. Whether the PWA operates offline.
13. Whether service-worker caching can pin stale or broken code.
14. All browser storage and data-loss risks.
15. Whether the chatbot sends data externally.
16. Whether the chatbot invents answers or uses hard-coded fallback text.
17. OneDrive and SharePoint import and export readiness.
18. Microsoft 365 Copilot feasibility and limitations.
19. Security and privacy risks.
20. Test adequacy.
21. Release readiness.
22. Repository cleanup candidates.
23. Architecture claims that do not match implementation.
24. Features that look real in the UI but are mocked.
25. Actions that can destroy or silently overwrite user data.
Do not assume the repository README is correct.
Create only:
docs/assessment/CURRENT_IMPLEMENTATION_ASSESSMENT.md
docs/assessment/SECURITY_PRIVACY_ASSESSMENT.md
docs/assessment/MINIFIED_AND_GENERATED_CODE_REGISTER.md
docs/assessment/DEPENDENCY_BUILD_REGISTER.md
docs/assessment/TEST_AND_RELEASE_READINESS.md
docs/assessment/REPOSITORY_CLEANUP_CANDIDATES.md
MINIFIED_AND_GENERATED_CODE_REGISTER.md must include one entry per minified or generated file:
- path
- file type
- size
- likely origin
- application or vendor
- readable source exists
- source map exists
- generator exists
- runtime usage
- licence information
- vulnerability implications
- recommended disposition:
  - KEEP VENDOR
  - RESTORE SOURCE
  - REBUILD
  - REPLACE
  - ARCHIVE
  - REMOVE AFTER VERIFICATION
For minified application code:
- do not claim beautification makes it maintainable
- distinguish formatting recovery from semantic source recovery
- recommend one of:
  - recover source from history
  - recover from source maps
  - reconstruct component by component
  - controlled rewrite behind compatibility tests
SECURITY_PRIVACY_ASSESSMENT.md must include:
- threat boundaries
- data flow
- external requests
- storage
- credentials
- authentication
- CORS
- CSP
- XSS
- insecure HTML
- logging
- backups
- sensitive data
- destructive operations
- Git content risks
- explicit severity:
  - BLOCKER
  - HIGH
  - MEDIUM
  - LOW
Do not write a backlog yet.
After creating the six documents:
- give a concise summary
- list unresolved questions
- stop

