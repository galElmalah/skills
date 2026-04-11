---
name: autoresearch-create
description: Primary autoresearch entrypoint. Use when the user wants to start an autonomous experiment loop, optimize a metric in a loop, run autoresearch, or set up a keep/discard benchmark workflow.
---

# Autoresearch Create

Set up an autoresearch session, log the baseline, and start the loop.

## Workflow

1. Infer or ask for:
   - goal
   - benchmark command
   - metric name and direction
   - mutable scope
   - constraints
   - correctness gate, if needed
2. Before scaffolding any new benchmark or checks script, inspect the repo for an existing benchmark, eval harness, or prior experiment workspace that already measures the intended target.
   - Prefer reusing an existing benchmark when it already encodes the workload the user cares about.
   - If a legacy workspace exists under paths like `.experiments/`, read its objective, benchmark script, and verification path before inventing a new one.
   - Only replace or broaden the benchmark if the user explicitly wants a different target; otherwise preserve the existing incentive structure.
3. Create a branch named `autoresearch/<goal>-<date>`.
4. Read the target files before writing session scaffolding.
5. Write:
   - `autoresearch.md`
   - `autoresearch.sh`
   - `autoresearch.checks.sh` only when correctness gating is required
6. Initialize the session with:

```bash
autoresearch init \
  --workdir <target-dir> \
  --name "<session name>" \
  --goal "<goal>" \
  --metric "<metric name>" \
  --direction lower|higher \
  --command "bash ./autoresearch.sh" \
  --verify-command "bash ./autoresearch.checks.sh"
```

Only pass `--verify-command` when checks are required.

7. Run and log the baseline:

```bash
autoresearch run --workdir <target-dir>
autoresearch log --workdir <target-dir> --status discard --description "Baseline measurement before mutations."
```

The first logged run becomes the baseline even if its status is `discard`.

8. Copy the shared loop assets into the target dir:
   - `skills/experiments/assets/loop.sh`
   - `skills/experiments/assets/validate-runners.sh`
   - `skills/experiments/assets/runners/`
9. Validate the selected runner.
10. Start the loop.

## `autoresearch.md`

Make this the human source of truth for the session. It should include:

- goal
- primary and secondary metrics
- how to run the benchmark
- mutable scope
- off-limits files
- constraints
- holdout or broader eval notes
- what has been tried

## `autoresearch.sh`

Requirements:

- use `set -euo pipefail`
- run the cheap benchmark
- emit structured `METRIC name=value` lines
- stay fast enough for repeated iteration
- add instrumentation that helps future runs make better decisions
- if the repo already has a validated benchmark or holdout harness for the same target, wrap or call it instead of recreating it

## Loop Rules

- One experiment per iteration.
- Use `autoresearch run` and `autoresearch log` rather than editing `autoresearch.jsonl`.
- Keep only verified wins.
- Write deferred ideas to `autoresearch.ideas.md`.
- Stop after one logged experiment or output `<promise>COMPLETE</promise>`.
