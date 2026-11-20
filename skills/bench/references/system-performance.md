# System performance playbook

## Define the workload and useful work

Inventory the relevant endpoints or operations. Choose representative input sizes, read/write mix, cache states, request rates, concurrency, and data distributions. Make each materially different behavior a scope. Freeze the workload before comparing candidates; a global average can otherwise improve merely because the easier endpoint received more traffic.

For each scope, choose a small set of interpretable measurements:

| Question | Candidate metric | Required context |
| --- | --- | --- |
| How long does useful work take? | Median/tail request duration | Client/server boundary, timeout, request count, warm/cold policy |
| How much work can finish? | Successful operations per second | Offered load, concurrency, errors, saturation |
| How much storage work happens? | Logical reads, writes, bytes, physical I/O | Measurement layer and denominator per attempted or successful operation |
| How much resource does it consume? | CPU time, peak resident memory, allocation bytes | Process scope, child processes, sampling/reset method |
| Is it still correct? | Success rate, output equivalence, recall, invariants | Explicit validator and expected behavior |

Use an external load generator for an end-to-end service question; a function microbenchmark cannot prove an endpoint improved. Ensure the generator is not saturated. Record offered and achieved throughput. A closed-loop client that waits before sending the next request can hide queueing during stalls; use an arrival-rate-aware harness when real traffic arrives independently. [Grafana k6: open and closed models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/).

Do not silently drop errors to improve latency. Report their count and rate next to latency and throughput; distinguish retries, failed attempts, and completed logical operations. Use the same timeout and retry policy for both variants.

## Locate and change the bottleneck

Profile a representative case to decide whether time is spent on CPU, allocations/GC, locks, network waits, database work, or storage. Use [codebase preparation](prepare-codebase.md) for optional OpenTelemetry boundaries. Confirm that the proposed change affects the measured path; cache hit counters or executed-row counts can catch a benchmark that skips the work.

Change one causal idea per experiment: an index, batching strategy, data representation, algorithm, cache policy, or concurrency limit. If an idea requires multiple code edits, keep them together but describe the mechanism. Separate “less work” from “same work completed faster.” A cache experiment needs hit/miss and invalidation/correctness coverage, not just a warm happy path.

## Run and interpret

Warm up only when steady-state behavior is the objective. Benchmark cold start separately if users experience it. Freeze fixture size, cache reset procedure, background services, and instrumentation. Allow a long enough sample window to observe the percentile of interest and natural cycles; five request durations cannot establish p99 behavior.

Use paired/randomized blocks for drift-sensitive comparisons as described in [experiment design](experiment-design.md). On a shared host, serialize performance runs. A separate worktree does not provide resource isolation. Separate build parallelism from measurement concurrency.

When importing one aggregate per load-test repeat, name it honestly (`run_p95_ms`, for example). The CLI may summarize those repeat-level scalars, but that summary is not the p95 of all requests. Keep the harness's raw request distribution or compatible histogram as an artifact when a combined tail metric matters.

Reject candidates that violate output correctness, error rate, or a required endpoint's guardrail. Show latency and I/O improvements independently. A lower-latency candidate with more storage reads is a tradeoff; use the study's declared resource priorities. For sibling changes that both pass, measure the integrated snapshot before promotion.

The quick view should answer: what changed, which endpoint improved, which resource paid for it, whether the small/full suites agree, and whether final held-out coverage exists. The detailed view should retain the load command, hardware/service identity, fixture reset, raw observations, profile/trace links, and decision rationale.

## Optimizing a test suite

Distinguish benchmark cases from application tests: one adapter case may execute an entire test runner. Record wall time, actual tests executed, failed tests or exit status, and the effective worker count and pool for each runner. If deleting redundant tests is part of the experiment, treat test count as a diagnostic, retain an explicit critical-flow inventory, and evaluate unseen seeded bugs. A mutation is caught only when the expected failure is verified; an unrelated crash does not establish coverage.

If the goal is an end-to-end time budget, measure that exact command as its own metric, including the agreed build, static checks, setup, and cleanup. Keep component timings alongside it; do not present a sum of independently measured medians as an end-to-end measurement. Show whether the reference passed its correctness checks. Separate gains from doing less work, changing concurrency, and executing the same work faster in the experiment description.

When worker count is itself an optimization, record the effective before/after settings as experiment configuration. Preserve the harness version and measurement environment. A held-out run at a different worker count is a separate condition and needs its own matching reference before claiming an improvement. Record contributions to an integrated experiment explicitly; an unpromoted sibling is not automatically a discarded experiment.
