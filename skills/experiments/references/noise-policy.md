# Noise Policy

Metric noise is the main failure mode in iterative experimentation.

## Recommended Defaults

- Run the unmodified baseline at least 2 times if budget allows.
- Treat tiny deltas as suspicious by default.
- Rerun marginal wins once before promotion.
- Discard crashes and timeouts immediately.

## Promotion Heuristic

Use one of these rules in `objective.md`:

- absolute epsilon: keep only if improvement exceeds a fixed delta
- noise band: keep only if improvement is larger than observed variation
- confirmation mean: keep only if two runs beat the champion mean

If the user has not decided, recommend a conservative policy instead of auto-promoting tiny wins.

## Simplicity Bias

If the metric improvement is very small:

- prefer the simpler change
- prefer the change with fewer moving parts
- avoid promoting complexity for a near-zero gain

## Holdouts

If optimization runs only on a cheap benchmark, periodically recommend a broader holdout run.

Examples:

- every few kept wins
- before declaring success
- before merging or publishing results
