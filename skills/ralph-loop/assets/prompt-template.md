# Prompt Template — Structural Reference

This file is NOT meant to be copied verbatim. It shows the structural elements every ralph loop prompt should include. Generate a tailored version based on the user's specific goal and workflow.

---

## Required Sections

### 0. One Item Per Iteration
Every generated prompt must open with a clear constraint that the agent handles exactly one work item per iteration and then stops. The loop harness will invoke the agent again for the next item. Example:
```
CRITICAL: Handle exactly ONE item per iteration. After updating progress, STOP. Do not pick up the next item — the loop harness will invoke you again.
```
This must also be reinforced in the completion/stop section (see section 7).

### 1. Source of Truth + Progress Check
```
Read items.md for the full list of work items.
Read progress.md to see what has already been completed.
Pick the next unfinished item to work on.
```

### 2. Grouping Rules (if applicable)
```
If items share the same root cause or are closely related, group them into a single iteration.
Reference all related item IDs in the branch name and description.
```

### 3. Work Strategy
```
[Describe HOW the agent should approach each item. Examples:]

- Use multiple sub-agents (opus) to study the codebase before making changes.
- Write a failing test first, then implement the fix.
- Research the topic thoroughly before writing content.
```

### 4. Validation (if applicable)
```
Run these validations and do not proceed until they pass:
1. [command 1]
2. [command 2]
3. [command 3]
```

### 5. PR/Output Creation (if applicable)
```
Create a draft PR with:
- Branch name: [convention, e.g., fix/ITEM-ID-short-description]
- Description linking to the original item
- Summary of what was done and why
```

### 6. Progress Update
```
Update progress.md with:
- Item ID and status
- What was done and why
- Link to PR or output (if applicable)
```

### 7. Completion Signal / Stop
```
If all items in items.md are complete (verified via progress.md), output <promise>COMPLETE</promise> and stop.
Otherwise, STOP IMMEDIATELY. Do not continue to the next item. The loop harness will start a new iteration.
```

---

## Example: Bug Fix Loop

```markdown
Read items.md and progress.md. Pick the next unresolved bug.

If bugs share the same root cause, group them into one branch/PR.

Use branch names like `fix/ISSUE-ID-short-description`.

Use multiple opus sub-agents to study the codebase. Write a failing test first,
then implement the fix. The test must pass after your change.

Run these validations:
1. pnpm build
2. pnpm test
3. pnpm typecheck

Create a draft PR linking to the issue(s). Update progress.md.

If all items are complete, output <promise>COMPLETE</promise> and stop.
```

## Example: PRD Implementation Loop

```markdown
Read items.md (PRD sections) and progress.md. Pick the next unimplemented section.

For each section, study the requirements carefully. Break it into sub-tasks if needed.
Implement the feature following the project's existing patterns and conventions.

Run these validations:
1. npm run build
2. npm run test
3. npm run lint

Create a draft PR for each section. Update progress.md with status and PR link.

If all sections are complete, output <promise>COMPLETE</promise> and stop.
```

## Example: Content Generation Loop

```markdown
Read items.md (list of articles/pages to write) and progress.md.
Pick the next unwritten item.

Research the topic using web search. Write the content following the style guide
in the project's STYLE.md. Save the output to the specified file path.

Update progress.md with the item status and output file path.

If all items are complete, output <promise>COMPLETE</promise> and stop.
```
