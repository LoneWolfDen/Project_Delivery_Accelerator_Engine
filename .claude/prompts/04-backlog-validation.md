Act as a critical architecture and release reviewer.
Do not write code.
Do not create new capabilities merely because they are interesting.
Read:
docs/assessment/
docs/architecture/
docs/backlog/
Review the proposed backlog and challenge it.
Look for:
- circular dependencies
- tasks that are too large
- tasks that require hidden interpretation
- unsafe ordering
- unnecessary framework migrations
- premature cloud integration
- premature Microsoft Graph work
- minified code migration without characterization tests
- storage migration without backup
- PWA service-worker changes without recovery
- Copilot assumptions without licence or tenant evidence
- OneDrive and SharePoint assumptions without authentication evidence
- tasks that silently change data boundaries
- tasks missing manual browser validation
- tasks missing rollback
- security work that could break the app
- repository cleanup scheduled too early
- duplicate backlog items
- acceptance criteria that cannot be tested
- statements not supported by repository evidence
Split any task that cannot safely be completed in one contained implementation cycle.
For every challenged item provide:
- original ID
- issue
- recommended correction
- dependency change
- risk change
Then create:
docs/backlog/BACKLOG_VALIDATION.md
docs/backlog/FINAL_EXECUTION_SEQUENCE.md
Update MASTER_BACKLOG.md only if necessary to correct a confirmed issue.
Do not implement anything.
Stop after the final review.

