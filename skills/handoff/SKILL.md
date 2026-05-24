---
name: handoff
description: Write a handoff note for the next agent session (Codex, Cursor, another Claude, etc.) so it can pick up where this one left off. Captures what was worked on, current state, next steps, and open questions. Stored in `.agents/handoffs/<project>/<timestamp>-handoff.md` (project-local by default; global if the user says so). Use when the user says "handoff", "/handoff", "wrap this session", "save context for later", or wants to switch to a different agent / tool.
---

# Handoff

Write one focused markdown handoff so a different agent can resume this work. Synthesize — don't dump the conversation.

## Where to write

1. **Resolve the canonical project root** (this is what makes worktrees work — without it, a handoff written in worktree A is invisible from worktree B):

   ```bash
   if git_common="$(git rev-parse --git-common-dir 2>/dev/null)"; then
     # `--git-common-dir` returns the *main* repo's .git, even from a linked worktree.
     # Its parent is the main worktree path — the same canonical root for every worktree.
     project_root="$(cd "$git_common/.." && pwd -P)"
   else
     project_root="$PWD"
   fi
   project="$(basename "$project_root")"
   ```

2. **Base directory**:
   - **Default (local)**: `<project_root>/.agents/handoffs/<project>/` — note this uses `project_root`, not `$PWD`, so handoffs land in the main worktree and are visible from every linked worktree.
   - **Global** (when the user said "global", "globally", or passed `--global`): `~/.agents/handoffs/<project>/`
3. **Filename**: `YYYY-MM-DD-HHMMSS-handoff.md` using the user's local time. Example: `2026-04-29-143022-handoff.md`. Lexical sort = chronological sort, which `/pickup` relies on.
4. `mkdir -p` the base directory, then `Write` the file.

## File contents

```markdown
---
from: <model id, e.g. claude-opus-4-7 or "claude-code">
created_at: <ISO-8601 with offset, e.g. 2026-04-29T14:30:22-07:00>
project: <project name>
cwd: <absolute path to current working directory>
worktree: <absolute path to current worktree, if different from project_root — omit otherwise>
branch: <git branch --show-current, or omit if not a git repo>
---

# Handoff — <one-line subject>

## What I worked on
<1–3 bullets — the arc of this session, not a transcript>

## Current state
<what's done · what's pending · what's broken or blocked>

## Next steps
<concrete, ordered actions for the next agent>

## Open questions
<decisions deferred · things needing user input · anything you'd ask the user before acting>

## Files touched
<paths only, grouped if many; mark created vs modified. If the session was in a worktree, prefer paths relative to project_root so they resolve from any worktree.>

## How to resume
<one short paragraph: "Read X, then Y, then run Z." Make this self-contained. If a specific worktree matters, name it.>
```

## After writing

Print one line: `Handoff written: <path>`. Stop. Do not summarize the handoff back at the user — the file is the artifact.

## Don't

- Don't include secrets, tokens, OAuth artifacts, or DB credentials.
- Don't paste long log dumps or full file bodies — link by path.
- Don't write a handoff for trivial conversations (pure Q&A, single typo fix). If the user asks anyway, do it but keep it to 5–6 lines.
- Don't write into `~/.agents/handoffs/<project>/` unless the user explicitly opted in to global. Default is local.
- Don't anchor to `$PWD` or `git rev-parse --show-toplevel` for the project root — both return the *linked worktree* path, which silos handoffs per worktree and is the most common cause of `/pickup` finding nothing.
