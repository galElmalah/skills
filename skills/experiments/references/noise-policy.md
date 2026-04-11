# Noise Policy

Metric noise is the main failure mode in iterative experimentation.

## Recommended Defaults

- Run the unmodified baseline at least 2 times if budget allows.
- Treat tiny deltas as suspicious by default.
- Rerun marginal wins once before promotion.
- Discard crashes and timeouts immediately.

## Promotion Heuristic

Use one of these rules in `objective.md`:

- champion-relative obvious win: keep immediately if the candidate clearly beats the current champion by more than obvious noise
- absolute epsilon: keep only if improvement exceeds a fixed delta, but recompute it whenever the champion changes
- noise band: keep only if improvement is larger than observed variation
- confirmation mean: keep only if a couple of confirmation runs still beat the champion mean

Avoid fixed thresholds that remain anchored to the very first baseline after the system gets much faster. That policy goes stale and will incorrectly discard real wins.

If the user has not decided, recommend a flexible policy:

- obvious stable wins promote immediately
- tiny wins require confirmation runs
- stale thresholds get recalibrated against the current champion

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
