# Metric Design

Choose the smallest scalar that still reflects the behavior the user cares about.

Good search metrics are:

- cheap enough to run repeatedly
- stable enough to compare
- hard to game accidentally
- directly connected to the user goal

Prefer:

- one scalar metric
- one declared direction: `min` or `max`
- one cheap repeated benchmark

If a broader eval exists, treat it as a holdout or release metric, not the per-iteration search metric.

## Cheap First

If the repo has no benchmark, bootstrap the cheapest useful benchmark first.

Examples:

- a small representative eval subset
- one latency benchmark
- one regression test bundle
- one prompt benchmark slice

After that baseline is working, recommend building a broader benchmark for confidence before investing heavily in optimization.

## Avoid Bad Metrics

Avoid metrics that are:

- too slow to run every iteration
- easy to inflate without improving real behavior
- mostly binary when the search space needs gradation
- ambiguous to extract from logs

## Search Metric vs Release Metric

When possible:

- search metric: cheap, repeated, used every iteration
- release metric: broader, slower, run periodically for confidence

Do not pretend these are the same if they are not.
