# Skills Repository

A collection of agent skills installed via the Vercel skills CLI.

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
| [bench](skills/bench) | Reproducible optimization studies with isolated experiments, multiple metrics, playbooks, a Python toolkit, and a bundled viewer. |
| [pr-comments](skills/pr-comments) | Process PR review comments with parallel analysis and sequential resolution. Fetches comments, checks each against current code, then walks through unaddressed ones with proposed fixes. |
| [ralph-loop](skills/ralph-loop) | Automated agent loop that works through a list of tasks iteratively. Scaffolds a bash harness that runs Claude repeatedly, picking up the next work item each iteration until all items are complete. |
| [ui-pr](skills/ui-pr) | Capture and attach current UI evidence for pull requests with user-visible changes. |

## Conventions

- Each skill lives in its own directory under `skills/`
- `SKILL.md` frontmatter must include `name` and `description`
- Keep supporting resources inside each skill directory; use `assets/` for templates and prebuilt UI, `scripts/` for executable helpers, and `references/` for playbooks.
- `bench` ships its complete `schema/`, `examples/`, and prebuilt `assets/viewer/` as ordinary Git files. Do not omit generated viewer assets or replace them with Git LFS pointers; installation does not run a build.
- Installation locations depend on the selected agent and project/global mode. Resolve resources relative to the installed `SKILL.md`.
- When adding a new skill, update the skills table in both `README.md` and this file
