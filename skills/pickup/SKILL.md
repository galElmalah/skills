---
name: pickup
description: Read the latest handoff note left by a previous agent session (Codex, Cursor, another Claude, etc.) and use it as context to resume the work. Looks under `./.agents/handoffs/<project>/` by default, or `~/.agents/handoffs/<project>/` when `--global`. Use when the user says "pickup", "/pickup", "what was I working on", "resume", or wants to continue a session that ended in a different agent.
---

# Pickup

Find the most recent handoff for this project, parse it, and tell the user what to do next. Do not start executing — wait for their go-ahead.

## Steps

1. Run the helper script (add `--global` if the user asked for the global store):

   ```bash
   ~/.claude/skills/pickup/scripts/latest.sh
   # or:
   ~/.claude/skills/pickup/scripts/latest.sh --global
   ```

   The script is worktree-aware: it resolves the canonical project root via `git rev-parse --git-common-dir`, so a handoff written in any worktree of this repo is found from any other worktree.

   It prints the path on the first line, a `---` separator, and the file body underneath. Non-zero exit + `no handoffs at <path>` on stderr means nothing's been saved for this project yet.

2. If there's nothing: tell the user plainly ("No handoff saved for this project yet."). Do not invent context.

3. Otherwise, parse the frontmatter (`from`, `created_at`, `branch`, `worktree` if present) and the body. Reply in 3–5 lines:

   - **Who & when**: `<from>, <relative time, e.g. "~3h ago">` — compute relative time from `created_at`.
   - **What they were doing**: one-sentence synthesis of the "What I worked on" section.
   - **Suggested first move**: pick the first item from "Next steps" (or "How to resume" if Next steps is empty) and surface it as: `Next: <action>`.
   - **Worktree note** (only if the handoff was written from a different worktree than the current `$PWD`): mention which worktree it came from so the user can decide whether to `cd` there before resuming.
   - **Open questions** (only if the section is non-empty): summarize in one bullet so the user can decide before you proceed.

4. End with: `Want me to go ahead, or pick something else?` Wait for the user.

## When to skip the script

If the user already pasted the handoff path or contents into the chat, read that directly instead of running the script.

## Don't

- Don't auto-execute the "Next steps" without confirmation. Pickup is a briefing, not an autopilot.
- Don't read or merge multiple handoffs. The latest is the source of truth — older ones are history.
- Don't show the raw frontmatter to the user. Translate it.
