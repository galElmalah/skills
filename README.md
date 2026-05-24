# Skills

A collection of Claude Code skills installed via the Vercel skills CLI.

## Included Skills

| Skill | Description |
| --- | --- |
| [handoff](skills/handoff) | Write a focused handoff note so a different agent (Codex, Cursor, another Claude) can resume the session. Worktree-aware. |
| [pickup](skills/pickup) | Read the latest handoff for this project and brief the user before resuming. Worktree-aware. |
| [pr-comments](skills/pr-comments) | Process PR review comments with parallel analysis and sequential resolution. |
| [ralph-loop](skills/ralph-loop) | Scaffold a task-oriented loop that repeatedly picks the next unfinished work item until the backlog is complete. |
| [ui-pr](skills/ui-pr) | Capture and attach current UI evidence for pull requests with user-visible changes. |
| [autoresearch-create](skills/autoresearch-create) | Primary entrypoint for creating an autoresearch session, scaffolding the session files, running the baseline, and starting the loop. See [experiments/](experiments) for the full autoresearch story. |
| [autoresearch-finalize](skills/autoresearch-finalize) | Turn kept autoresearch runs into clean, reviewable branches from the merge-base. |

## Installation

Install via [Vercel's skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add ./path/to/my-skills
npx skills add galElmalah/skills
npx skills add galElmalah/skills -a claude-code
```

Useful commands:

```bash
npx skills list
npx skills check
npx skills update
```

## Experiments

The autoresearch runtime, loop model, dashboard, runner adapters, and sandbox projects all live under [experiments/](experiments). Start there if you want the long-form view of how the experiment loop works or want to exercise it against the included sandboxes.
