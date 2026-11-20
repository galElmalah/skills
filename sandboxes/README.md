# Experiment Sandboxes

These projects exist to test the `bench` skill against controlled, measurable problems.

## Included Projects

| Project | Suggested metric | Direction | Benchmark setup |
| --- | --- | --- | --- |
| [catalog-project](./catalog-project) | `total_duration_ms` | `lower` | Create the cheap benchmark with `bench`. |
| [tests-project](./tests-project) | `test_runtime_ms` | `lower` | Create the cheap benchmark with `bench`. |

## Why These Exist

Both projects are intentionally imperfect, but they start without a fixed benchmark harness.

- `catalog-project` gives the loop a production-style performance target with multiple slow code paths inside `src/catalog.js`.
- `tests-project` gives the loop a test-runtime optimization target with several different reasons for slowness, not just one artificial sleep.

The point is to let the experiment loop define the metric, scaffold the benchmark, propose isolated changes, and keep or discard them using a main metric and explicit correctness guardrails.

## Suggested Starting Flow

1. Pick one sandbox.
2. Use the `bench` skill to scaffold an experiment workspace inside that sandbox.
3. Let the skill define and create the first cheap benchmark or eval command.
4. Freeze that benchmark harness and the mutable scope before the first mutation.
5. Freeze small and full training suites and separate held-out cases before iteration. Use held-out results only for the final check.
