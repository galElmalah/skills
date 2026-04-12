# Experiment Sandboxes

These projects exist to test `autoresearch-create` against controlled, measurable problems.

## Included Projects

| Project | Suggested metric | Direction | Benchmark setup |
| --- | --- | --- | --- |
| [catalog-project](./catalog-project) | `total_duration_ms` | `min` | Create the cheap benchmark with `autoresearch-create`. |
| [tests-project](./tests-project) | `test_runtime_ms` | `min` | Create the cheap benchmark with `autoresearch-create`. |

## Why These Exist

Both projects are intentionally imperfect, but they start without a fixed benchmark harness.

- `catalog-project` gives the loop a production-style performance target with multiple slow code paths inside `src/catalog.js`.
- `tests-project` gives the loop a test-runtime optimization target with several different reasons for slowness, not just one artificial sleep.

The point is to let the experiment loop define the metric, scaffold the benchmark, propose isolated changes, and keep or discard them using a clear scalar result.

## Suggested Starting Flow

1. Pick one sandbox.
2. Use `autoresearch-create` to scaffold an autoresearch workspace inside that sandbox.
3. Let the skill define and create the first cheap benchmark or eval command.
4. Freeze that benchmark harness and the mutable scope before the first mutation.
5. Start with the cheap benchmark only, then add a fuller holdout if you want more confidence.
