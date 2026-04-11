---
name: experiments
description: Secondary guidance skill for metric-driven experimentation. Use when the user needs help designing the metric, cheap eval, noise policy, confirmation policy, or holdout strategy around an autoresearch loop.
---

# Experiments

`experiments` is no longer the primary workflow surface in this repo.

For new sessions, prefer `autoresearch-create`.

Use this skill when the user needs:

- help defining the metric
- help choosing the cheap eval
- confirmation and noise policy
- holdout-eval recommendations
- write-boundary and frozen-file policy
- methodology review for an existing autoresearch session

## Core Model To Preserve

Keep these principles in any autoresearch session:

- one current champion
- one mutation per iteration
- one measured decision per iteration
- keep verified wins
- revert losers
- prefer champion-relative decisions over stale baseline thresholds

## How To Help

When invoked, focus on the decision quality around the loop:

1. Clarify the primary metric and whether lower or higher is better.
2. Define the cheapest trustworthy benchmark.
3. Define the correctness gate and whether it must pass before keep.
4. Recommend a confirmation rule for tiny wins on noisy benchmarks.
5. Recommend a holdout or broader eval when cheap benchmarks are likely to overfit.
6. Recommend the mutable and frozen scope.

Do not reintroduce `objective.md`, `progress.md`, or `progress.json` as the canonical session model. The runtime session model is:

- `autoresearch.md`
- `autoresearch.jsonl`
- `autoresearch.sh`
- `autoresearch.checks.sh` when needed
- `autoresearch.ideas.md`

## Shared Assets

These shared assets are still the supported runner surface for autoresearch loops:

- `assets/loop.sh`
- `assets/validate-runners.sh`
- `assets/runners/`
- `assets/dashboard.html`

Use the references in this skill for methodology guidance only. The runtime owns session state and git behavior.
