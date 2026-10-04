Implement exactly one backlog item: <ITEM_ID>

Repository: Project_Delivery_Accelerator_Engine
Backlog: docs/backlog/MASTER_BACKLOG.md
Rules: docs/backlog/SMALL_MODEL_EXECUTION_RULES.md (they override anything below if they conflict)

Follow these steps in order. Do not skip a step. If any step fails, stop and report.

1. Read one backlog item.
   - Open docs/backlog/MASTER_BACKLOG.md and read the full section for <ITEM_ID>, every field.
   - Read docs/backlog/SMALL_MODEL_EXECUTION_RULES.md.
   - Don't read or act on any other backlog item except to check its status in step 2.

2. Verify prerequisites.
   - For every ID in "Dependencies", confirm it is Done in docs/continuity/PROJECT_STATE.md, or, if that file doesn't exist, in docs/backlog/EXECUTION_LOG.md.
   - Check "Prerequisite decisions" against docs/backlog/DECISION_REGISTER.md and docs/architecture/ADR_REGISTER.md.
   - Check "External approvals". If the item is BLOCKED or anything is missing, stop and list what is missing.
   - Run `git status` and `git branch --show-current`. Report them. If there are uncommitted changes unrelated to <ITEM_ID>, stop.

3. List intended edits.
   - Inspect the current content of every file in "Files expected to change" and the modules they import.
   - Write a short plan: for each file, what you will add or change and which function, symbol or component.
   - Confirm that no file outside "Files expected to change" needs editing. If one does, stop and explain.

4. Add or update tests.
   - Write the tests named in "Automated tests" first (or alongside the change).
   - Each acceptance criterion must map to a test or a named manual check. List the mapping.

5. Implement only that item.
   - Make the smallest safe change described. Respect "Explicit exclusions" and "Files that must not change".
   - No unrelated cleanup, renaming, reformatting or refactoring.

6. Run tests.
   - Run the item's named tests, plus `npm run check` and `npm run test:unit`, and the full `npm run test:e2e` if anything under app/ changed.
   - Report each command and its result summary. Never report a test as passing without running it.

7. Inspect git diff.
   - Run `git diff --stat` and `git diff`.
   - Confirm every changed file is allowed and that there are no unrelated hunks. Revert anything unrelated.

8. Verify acceptance criteria.
   - Go through each criterion: met or not met, and how it was verified (test name or manual step).
   - List every browser or environment behaviour you couldn't observe as UNVERIFIED, with what the owner should check manually ("Manual verification" field).
   - If any criterion isn't met, stop here and report.

9. Update project state.
   - Follow the item's "Continuity update instructions" exactly.
   - Append any decision you took to docs/backlog/DECISION_REGISTER.md section 3 (never edit earlier rows).

10. Stop without committing.
    - Don't commit, push, tag or change settings.
    - End with an execution report:
      - Item: <ITEM_ID> – title
      - Prerequisites checked: …
      - Files changed: (from git diff --stat)
      - Tests run and results: …
      - Acceptance criteria: each with met/not met and evidence
      - UNVERIFIED behaviours for the owner: …
      - Suggested commit message: "<ITEM_ID>: <title>" (owner decides whether to commit)
      - Anything that surprised you or contradicts the backlog
