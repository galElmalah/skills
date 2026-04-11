# Skills

Hybrid `autoresearch` runtime plus agent skills for iterative coding workflows.

## Included Skills

| Skill | Description |
| --- | --- |
| [autoresearch-create](skills/autoresearch-create) | Primary entrypoint for creating an autoresearch session, scaffolding the session files, running the baseline, and starting the loop. |
| [autoresearch-finalize](skills/autoresearch-finalize) | Turns kept autoresearch runs into clean, reviewable branches from the merge-base. |
| [experiments](skills/experiments) | Secondary guidance skill for metric design, noise handling, holdouts, and advanced experiment methodology. |
| [pr-comments](skills/pr-comments) | Processes PR review comments with parallel analysis and sequential resolution. |
| [ralph-loop](skills/ralph-loop) | Scaffolds a task-oriented loop that repeatedly picks the next unfinished work item until the backlog is complete. |

## Autoresearch

`autoresearch` is the primary workflow in this repo.

It is a hybrid package:

- a small runtime CLI that owns session state, run logging, keep/discard behavior, export, and finalize
- skills that set up the session and guide the agent through the loop

This is intentionally closer to `pi-autoresearch` than to the old `experiments` scaffolding model.

### Runtime Files

Autoresearch standardizes on these session artifacts:

- `autoresearch.md`
- `autoresearch.jsonl`
- `autoresearch.sh`
- `autoresearch.checks.sh` when correctness gating is required
- `autoresearch.ideas.md`
- `.autoresearch-logs/`

`autoresearch.jsonl` is the machine source of truth. The dashboard and `autoresearch status` both derive state from it.

### CLI

The runtime CLI is available from the repo root:

```bash
node ./bin/autoresearch.js help
```

Primary commands:

- `autoresearch init`
- `autoresearch run`
- `autoresearch log`
- `autoresearch status`
- `autoresearch export`
- `autoresearch clear`
- `autoresearch finalize`

### Loop Model

The loop is champion-based:

- one current champion
- one mutation per iteration
- one measured decision per iteration
- keep verified wins
- revert losers
- log everything

The runtime owns experiment state and git semantics. The loop harness is only responsible for driving one agent iteration at a time.

### Dashboard

The browser dashboard is the first-class observability surface.

It reads state derived from `autoresearch.jsonl` and shows:

- baseline and champion summary
- run ledger
- confidence/noise context
- artifact links
- git-backed diffs for runs with commit metadata

To serve it for a session:

```bash
node ./bin/autoresearch.js export --workdir /path/to/project
```

### Multi-runner Support

The shared runner adapters live in [skills/experiments/assets/runners](skills/experiments/assets/runners).

Supported runners:

- `claude`
- `codex`
- `opencode`
- `custom`

Validate a runner before a long loop:

```bash
bash skills/experiments/assets/validate-runners.sh
```

## Experiments

`experiments` still exists, but it is no longer the primary product surface.

Keep using it when you need:

- metric design guidance
- noise and confirmation policy
- holdout-eval recommendations
- advanced experiment methodology

For new sessions, prefer `autoresearch-create`.

## Experiment Sandboxes

The repo includes two small sandboxes for end-to-end verification of autoresearch flows.

| Sandbox | Purpose | Suggested primary metric |
| --- | --- | --- |
| [catalog-project](./sandboxes/catalog-project) | Production-style catalog logic with deliberate hot paths in one file. | `total_duration_ms` |
| [tests-project](./sandboxes/tests-project) | Intentionally slow test suite with multiple independent causes. | `test_runtime_ms` |

These sandboxes are for real loop verification rather than synthetic tests.

## Installation

Install the skills using [Vercel's skills CLI](https://github.com/vercel-labs/skills):

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
