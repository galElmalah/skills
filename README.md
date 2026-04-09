# My Skills

My curated list of markdowns for agents :P 

## Skills

| Skill | Description |
|-------|-------------|
| [pr-comments](skills/pr-comments) | Process PR review comments with parallel analysis and sequential resolution. Fetches comments, checks each against current code, then walks through unaddressed ones with proposed fixes. |
| [ralph-loop](skills/ralph-loop) | Automated agent loop that works through a list of tasks iteratively. Scaffolds a bash harness that runs Claude repeatedly, picking up the next work item each iteration until all items are complete. |

## Installation

Install using [Vercel's skills CLI](https://github.com/vercel-labs/skills):

```bash
# From local path
npx skills add ./path/to/my-skills

# From GitHub (after pushing to a repo)
npx skills add galElmalah/skills

# Install to a specific agent
npx skills add galElmalah/skills -a claude-code

# Install globally (available across all projects)
npx skills add galElmalah/skills -g

# List available skills before installing
npx skills add galElmalah/skills -l
```

### Other useful commands

```bash
npx skills list              # List installed skills
npx skills check             # Check for updates
npx skills update            # Update all skills
npx skills remove pr-comments  # Remove a skill
```
