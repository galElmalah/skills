# Skills Repository

A collection of Claude Code skills installed via the Vercel skills CLI.

## Structure

```
skills/
  <skill-name>/
    SKILL.md        — skill definition (frontmatter + instructions)
    assets/         — templates, scripts, and other supporting files
```

## Skills

| Skill | Description |
|-------|-------------|
| [autoresearch-create](skills/autoresearch-create) | Primary autoresearch entrypoint. Scaffolds `autoresearch.md`, `autoresearch.sh`, initializes the session, logs the baseline, and starts the loop. |
| [autoresearch-finalize](skills/autoresearch-finalize) | Finalizes kept autoresearch runs into clean reviewable branches from the merge-base. |
| [experiments](skills/experiments) | Secondary guidance skill for metric design, holdouts, noise policy, and advanced experiment methodology around autoresearch sessions. |
| [pr-comments](skills/pr-comments) | Process PR review comments with parallel analysis and sequential resolution. Fetches comments, checks each against current code, then walks through unaddressed ones with proposed fixes. |
| [ralph-loop](skills/ralph-loop) | Automated agent loop that works through a list of tasks iteratively. Scaffolds a bash harness that runs Claude repeatedly, picking up the next work item each iteration until all items are complete. |

## Conventions

- Each skill lives in its own directory under `skills/`
- `SKILL.md` frontmatter must include `name` and `description`
- Assets (templates, scripts) go in an `assets/` subdirectory
- Skills are installed to `~/.claude/skills/` by the Vercel CLI
- When adding a new skill, update the skills table in both `README.md` and this file
