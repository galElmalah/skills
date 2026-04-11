# Tests Project

Small Node project with intentionally slow tests caused by multiple independent problems.

Use it to test the `experiments` skill against test-runtime optimization.

## Goal

Create a cheap benchmark with the skill, then reduce end-to-end test runtime while keeping the tests passing.

## Benchmark Setup

This project keeps only the ordinary test command:

```bash
npm test
```

Use the `experiments` skill to turn that into a cheap repeatable benchmark or eval command.

Suggested scalar metric once the harness exists:

- metric: `test_runtime_ms`
- direction: `min`

## Why The Tests Are Slow

- every test rebuilds a large fixture in `beforeEach`
- every test burns CPU with repeated `pbkdf2Sync` calls
- every test writes JSON fixtures to disk
- every test waits on multiple fixed sleeps
- the runner forces serial execution with `--test-concurrency=1`
- the end-to-end test rewrites artifacts on every run

## Suggested Mutable Scope

- `test/helpers/slow-fixture.js`
- `test/*.test.js`
- `package.json`

## Suggested Frozen Scope

- `src/reporting.js`
- the benchmark harness created during setup

The point is not product logic. The point is giving the experiment loop several real, measurable ways to improve runtime.
