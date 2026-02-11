# My Skills

My curated list of markdowns for agents :P 

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

## Skills

### pr-comments

Process PR review comments with a hybrid parallel-analysis / sequential-decision workflow. Fetches all comments from a PR, spawns subagents to check each against the current code in parallel, then walks through unaddressed comments one at a time — showing a proposed fix and asking how to handle it (accept, custom fix, won't fix, skip). Replies on each PR comment with the decision taken.

**Trigger phrases:** "address PR comments", "handle PR feedback", "review PR comments", "resolve PR comments", "fix PR comments"
