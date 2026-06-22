---
description: Convert existing tasks into actionable, dependency-ordered GitHub issues for the feature based on available design artifacts.
tools: ['github/github-mcp-server/issue_write']
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Load prerequisites and validate**: Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root. Check the script exit code — if non-zero, abort with the error message. Parse the JSON output and validate that `FEATURE_DIR` is an absolute path and `AVAILABLE_DOCS` is a non-empty list. If JSON parsing fails or required keys are missing/invalid, abort with a clear error instructing the user to run the prerequisite commands. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. From the parsed output, extract the path to **tasks** (from AVAILABLE_DOCS) and retain FEATURE_DIR and AVAILABLE_DOCS for use in later steps.

3. **Get and validate the Git remote**:

   ```bash
   git config --get remote.origin.url
   ```

   Validate the remote URL matches a GitHub pattern (`github.com[:/]<owner>/<repo>`). Extract `owner` and `repo` from the URL. If the URL does not match, stop the workflow with an error: "Remote URL is not a GitHub repository. Task-to-issue conversion requires a GitHub remote."

   > [!CAUTION]
   > ONLY PROCEED TO NEXT STEPS IF THE REMOTE IS A GITHUB URL

4. **Parse tasks and resolve dependencies**: Read the tasks file (Markdown checklist format: `- [ ] T### [P?] [US?] Description with file path`). For each task, extract:
   - Task ID (e.g., T001)
   - Description
   - Phase and user story label (if present)
   - Parallel marker [P] (if present)
   - File paths referenced in the description
   - Dependencies: detect explicit markers (e.g., "depends on T002") from `$ARGUMENTS` or task descriptions, and infer implicit dependencies from phase ordering and task references. Perform a topological sort to produce a creation order. If cycles are detected, flag the involved tasks for human review and create them without dependency links.

5. **Create issues in dependency order**: For each task (in topological order), use the GitHub MCP server (`github/github-mcp-server/issue_write`) with `owner` and `repo` extracted in step 3:
   - **Title**: `[T###] <task description>` (e.g., `[T001] Create module stub at plugins/modules/foo.py`)
   - **Body**:
     - Task description from tasks.md
     - **Design context** section: links to relevant entries from AVAILABLE_DOCS (e.g., spec.md, plan.md, data-model.md) using relative paths from FEATURE_DIR
     - Phase and user story information
     - Dependency references: if the task depends on previously created issues, add a "Depends on: #NNN" line referencing the GitHub issue number
   - **Labels**: derive from task metadata (e.g., `phase:1`, `user-story:US1`, `parallel` if [P] marker present) or use defaults
   - **Milestone**: include if present in task metadata or `$ARGUMENTS`
   - **Assignees**: include if specified in `$ARGUMENTS`

   > [!CAUTION]
   > UNDER NO CIRCUMSTANCES EVER CREATE ISSUES IN REPOSITORIES THAT DO NOT MATCH THE REMOTE URL

6. **Report**: Output a summary of created issues with their GitHub URLs, dependency links, and any tasks flagged for human review.
