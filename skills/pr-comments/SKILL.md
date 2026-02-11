---
name: pr-comments
description: This skill should be used when the user asks to "address PR comments", "handle PR feedback", "review PR comments", "go through PR comments", "resolve PR comments", "process PR review", "fix PR comments", "respond to review feedback", "address code review comments", or mentions dealing with pull request comments, code review feedback, or reviewer suggestions.
---

# PR Comment Handler

Process PR comments with a hybrid approach: parallel analysis of all comments, then sequential user decisions via AskUserQuestion.

**Core principle:** Analyze fast in parallel, decide carefully one at a time.

## Workflow

### 1. Detect the PR

Auto-detect the PR from the current branch. If no PR is found, use AskUserQuestion to ask for the PR number or URL. See `references/gh-commands.md` for the exact detection command.

### 2. Fetch All Comments

Fetch both review comments (inline code comments) and issue comments (general PR comments) from the PR. See `references/gh-commands.md` for exact commands, field details, and filtering.

Filter out:
- Comments authored by the current user
- Bot comments
- Comments that already have a reply from the current user (already handled)

### 3. Parallel Analysis (Subagents)

Spawn one subagent per comment using the Task tool with `subagent_type: "general-purpose"`. Dispatch all subagents in a single message so they run concurrently. Each subagent:

1. Reads the comment body and understands what change is being requested
2. Identifies the relevant file(s) and line(s) from the comment context
3. Checks the current code to determine if the requested change was already made
4. If not addressed, proposes a concrete fix (the actual code change)
5. Returns a structured JSON result

See `references/subagent-prompt.md` for the full prompt template and JSON output format. Use the complete template from the reference file - it includes fields for threading replies back to the correct comment.

### 4. Present Summary

After all subagents return, present a summary:

```
PR #123: "Add user authentication"
- 8 comments total
- 3 already addressed
- 5 need your input
```

### 5. Sequential Decisions

For each unaddressed comment, use AskUserQuestion:

**Question format:**

```
**Comment by @reviewer on `src/auth.ts:42`:**
> Consider using bcrypt instead of md5 for password hashing

**Proposed fix:** Replace the md5 hash call on line 42 with bcrypt.hash(), add bcrypt import, and update the comparison in verifyPassword() on line 58.

How would you like to handle this comment?
```

**Options:**
- **Accept proposed fix** - Implement the proposed change as described
- **Fix with custom instructions** - User provides their own approach
- **Won't fix** - Disagree or out of scope
- **Skip for now** - Come back to it later

### 6. Apply Fixes

For each accepted fix:
1. Implement the code change
2. Reply on the PR comment via `gh` with what was done

For "Won't fix":
1. Reply on the PR comment explaining the decision

For "Skip":
1. Do nothing, move to the next comment

See `references/reply-formats.md` for reply comment templates.

### 7. Final Summary

After processing all comments, show a summary:

```
Done processing PR #123 comments:
- 3 were already addressed
- 3 fixed (accepted proposed fix)
- 1 fixed (custom instructions)
- 1 won't fix
- 0 skipped
```

## Error Handling

- If `gh` is not authenticated, instruct the user to run `gh auth login`
- If a subagent fails to analyze a comment, present the raw comment and ask the user directly
- If a file referenced in a comment no longer exists, mark as "file removed" and ask the user

## Additional Resources

### Reference Files

- **`references/gh-commands.md`** - Exact `gh` CLI commands for fetching comments, replying, and detecting PRs
- **`references/subagent-prompt.md`** - Full subagent prompt template for comment analysis
- **`references/reply-formats.md`** - Reply comment templates and `gh api` calls for each decision type
