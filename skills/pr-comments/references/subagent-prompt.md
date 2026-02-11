# Subagent Prompt Template

## Full Prompt for Comment Analysis

Use the Task tool with `subagent_type: "general-purpose"` for each comment.

### Template

```
Analyze this PR review comment and determine if the requested change has already been addressed in the current codebase.

## Comment Details

- **Author:** {author}
- **File:** {path}
- **Line:** {line}
- **Comment:**

> {comment_body}

**Diff context:**
```
{diff_hunk}
```

## Instructions

1. Read the file `{path}` in the current codebase
2. Focus on the area around line {line} and understand the current state of the code
3. Compare against what the comment is requesting
4. Determine if the change was already implemented

If the change was NOT implemented, propose a specific fix:
- Describe exactly what needs to change
- Reference specific lines and code
- Keep the fix minimal and focused on what the comment asks for

## Output Format

Return ONLY a JSON object (no markdown fencing, no extra text):

{
  "addressed": true or false,
  "summary": "One-line summary of what the comment requests",
  "evidence": "What you found in the current code that supports your conclusion",
  "file": "{path}",
  "line": {line},
  "proposed_fix": "Detailed description of the proposed fix if not addressed, null if already addressed",
  "comment_id": {comment_id},
  "comment_type": "{review|issue}",
  "author": "{author}"
}
```

### Adapting for Issue Comments (No File Context)

For general PR comments without file/line context, adjust the prompt:

```
Analyze this PR comment and determine if the requested change has already been addressed in the current codebase.

## Comment Details

- **Author:** {author}
- **Comment:**

> {comment_body}

## Instructions

1. Understand what the comment is requesting
2. Search the codebase for relevant files
3. Determine if the change was already implemented

If the change was NOT implemented, propose a specific fix:
- Identify which file(s) need changes
- Describe exactly what needs to change
- Keep the fix minimal and focused

## Output Format

Return ONLY a JSON object (no markdown fencing, no extra text):

{
  "addressed": true or false,
  "summary": "One-line summary of what the comment requests",
  "evidence": "What you found in the current code",
  "file": "primary file that needs changes (or null if addressed)",
  "line": null,
  "proposed_fix": "Detailed description of the proposed fix if not addressed, null if already addressed",
  "comment_id": {comment_id},
  "comment_type": "issue",
  "author": "{author}"
}
```

## Dispatching Multiple Subagents

Dispatch all comment analysis subagents in a single message using multiple Task tool calls. This ensures they run in parallel:

```
[In a single response, call Task for each comment:]

Task 1: "Analyze PR comment #1" → subagent with comment 1 details
Task 2: "Analyze PR comment #2" → subagent with comment 2 details
Task 3: "Analyze PR comment #3" → subagent with comment 3 details
...
```

All subagents run concurrently and return their JSON results.

## Parsing Subagent Results

After all subagents return, parse each JSON result and categorize:

- `addressed: true` → Add to "already addressed" list
- `addressed: false` → Add to "needs input" list with proposed fix

Sort "needs input" by file path to group related changes together when presenting to the user.
