---
name: experiments
description: Use this skill when the user wants to set up or run iterative experiments to improve a single metric over time, including eval-score optimization, benchmark tuning, prompt iteration, hill-climbing, keep-or-revert workflows, or evolutionary testing. This skill interviews the user, helps bootstrap a cheap benchmark when none exists, scaffolds the experiment workspace, and runs one-mutation keep/discard loops.
---

# Experiments

## Overview

This skill sets up and runs single-metric experiment loops.

It is setup-first. Before any loop starts, define the metric, the evaluation path, the correctness verification path, the allowed edit scope, the logging artifacts, and the promotion rule. If the repo has no usable eval yet, help the user create a cheap benchmark first and recommend building a fuller benchmark before investing heavily in optimization.

## When To Use

Use this skill when the user wants to:

- set up an experiment loop
- optimize a benchmark or eval score
- tune a prompt or agent behavior against a metric
- hill-climb on a single scalar metric
- run keep-or-revert experiments
- bootstrap a benchmark before experimentation

Do not use this skill for ordinary task backlogs or feature delivery work. This is for metric-driven experimentation, not item completion.

## Core Model

This skill is champion-based, not backlog-based.

- One current champion
- One mutation per iteration
- One eval decision per iteration
- Keep verified wins
- Revert losers
- Log every experiment

Start single-worker only. Do not introduce parallel branches, worktrees, or multi-worker coordination unless the user explicitly asks for a more advanced version later.

## Interview Style

Interview the user interactively. Do not dump a long questionnaire all at once unless the user asks for it.

Do not silently infer the experiment contract from vague intent like “it is slow” or “quality is bad.” Before scaffolding files, confirm the metric, cheap eval, correctness verification path, runner, write boundaries, and keep/discard rule with the user, or explicitly state the assumption and get confirmation.

If no correctness verification exists and the optimization can plausibly break behavior, recommend creating a minimal verification step before running the loop for real. Ask the user whether you should add that safety net instead of assuming they are comfortable optimizing without one.

Ask the minimum questions needed to unblock the next setup decision. Good default order:

1. What metric are we optimizing, and is lower or higher better?
2. What is the cheapest trustworthy eval we can run repeatedly?
3. What correctness verification should we run before keeping a candidate, for example tests or contract checks?
4. If a fuller holdout eval exists, what is it?
5. What files may change, and what files are frozen?
6. Which runner should execute the loop: `claude`, `codex`, `opencode`, or a custom runner?
7. What counts as a real win?
8. Should winners auto-commit and losers auto-revert?

## Setup Workflow

Follow these steps in order.

### Step 1: Define The Objective

Create a concrete experiment charter with:

- metric name
- metric direction: `min` or `max`
- cheap eval command
- correctness verification command, if any
- correctness verification policy, for example “must pass before keep”
- fuller eval or holdout command, if available
- timeout or budget per run
- allowed write scope
- frozen files or directories
- promotion rule
- logging locations

Use `objective.md` as the source of truth for these rules.

If the user has not decided the promotion rule, recommend:

- baseline runs: 2 if feasible
- obvious win: keep stable wins that clearly beat the current champion by more than obvious noise; do not block them behind a stale threshold derived from an older baseline
- confirmation: rerun tiny or marginal wins a couple of times before promotion, and rerun the champion too if the noise estimate is stale or weak
- crashes and timeouts: discard

For metric design guidance, read [references/metric-design.md](references/metric-design.md) and [references/noise-policy.md](references/noise-policy.md).

### Step 2: Check Evaluation Reality

Inspect the repo for existing tests, evals, benchmarks, baselines, or scripts.

If a cheap benchmark already exists:

- verify the command
- verify the metric extraction path
- run or recommend baseline measurement

If correctness verification already exists:

- verify the command
- verify that it actually covers the behavior the loop might break
- add it to the objective as the keep gate when appropriate

If no easy eval exists:

- help the user define the smallest cheap benchmark that still measures the intended behavior
- scaffold `evaluate.sh` from [assets/evaluate-template.sh](assets/evaluate-template.sh)
- define a scalar output and log format
- run 1-2 baseline measurements if feasible

When only a cheap benchmark exists, explicitly recommend stopping after setup and baseline to build a fuller benchmark or holdout eval for confidence before long optimization loops.

If no correctness verification exists and the work can plausibly break behavior:

- ask the user whether you should create a minimal verification step, usually tests or a contract check, before starting the loop
- if they agree, add that verification step and capture its baseline behavior before optimization
- if they decline, record that missing safety net explicitly in `objective.md` and recommend a tighter write scope

For logging conventions, read [references/logging-patterns.md](references/logging-patterns.md).

### Step 3: Scaffold The Workspace

Create these files in the target workspace unless the repo already has better equivalents:

- `objective.md`
- `progress.md`
- `progress.json`
- `prompt.md`
- `loop.sh`
- `evaluate.sh` if needed
- `dashboard.html`
- `serve-dashboard.js`
- `runners/`
- `validate-runners.sh`

Use these assets as starting points:

- [assets/objective-template.md](assets/objective-template.md)
- [assets/progress-template.md](assets/progress-template.md)
- [assets/progress-template.json](assets/progress-template.json)
- [assets/prompt-template.md](assets/prompt-template.md)
- [assets/loop.sh](assets/loop.sh)
- [assets/evaluate-template.sh](assets/evaluate-template.sh)
- [assets/dashboard.html](assets/dashboard.html)
- [assets/serve-dashboard.js](assets/serve-dashboard.js)
- [assets/runners/](assets/runners)
- [assets/validate-runners.sh](assets/validate-runners.sh)

Also set up log directories when appropriate:

- `.eval-logs/`
- `.experiment-logs/`

Prefer keeping logs and experiment ledgers outside the revert path so discarded experiments remain visible.

If the experiment workspace or log directories live inside a git repo but should stay local, add them to `.git/info/exclude` or the repo `.gitignore` during setup so `git status` stays focused on candidate code. Prefer `.git/info/exclude` when the ignore should remain local-only.

The dashboard should be accessible by default. Use `progress.json` as the machine-readable source for the dashboard and keep it aligned with `progress.md`.

The loop should also be runner-selectable by default. Do not hardcode Claude if the user wants Codex, OpenCode, or a custom backend.

If the experiment control files live in a dedicated subdirectory like `.experiments/`, set `EXPERIMENT_WORKSPACE_ROOT` so runners execute from the actual project root while the dashboard still serves the experiment assets.

### Step 4: Initialize The Baseline

Before any mutation loop, establish the current baseline.

- Run the cheap eval on the unmodified state
- If the metric is noisy and budget allows, run it twice
- Record the baseline result in `progress.md`
- Record the baseline result in `progress.json`
- Record log paths and notable anomalies

If baseline measurement itself is unstable or ambiguous, pause optimization and fix the evaluator first.

### Step 5: Start The Loop

Once setup is complete, the loop prompt must enforce:

- exactly one experiment per iteration
- one hypothesis only
- one coherent mutation only
- read `objective.md` and `progress.md` first
- keep `progress.json` current enough for the dashboard
- inspect stdout/stderr and case-level artifacts before deciding
- run the configured correctness verification before promotion when the objective requires it
- keep only verified wins
- revert losers to the current champion
- never edit the verification step unless the objective explicitly unlocks it

Before trusting the loop, validate the chosen runner with `validate-runners.sh`.

Once the loop starts, let the loop own the iteration. Do not manually update `progress.md`, `progress.json`, candidate code, or eval results mid-run unless the user explicitly asks you to interrupt or debug the loop itself.

## Iteration Rules

Each iteration should:

1. Read `objective.md`
2. Read `progress.md` and `progress.json`
3. Propose one new mutation not already tried
4. Change only the allowed files
5. Commit the experiment before running eval if the user wants auto-commit semantics
6. Run the cheap eval and capture logs
7. Run the configured correctness verification if the objective requires it
8. Inspect the logs, not just the aggregate scalar
9. Compare against the current champion
10. Keep or discard
11. Update `progress.md` and `progress.json`
12. Stop

One experiment per iteration is mandatory. The loop harness is responsible for invoking the next round.

## Keep / Discard Policy

Default policy:

- Keep only if the metric improves under the declared rule in `objective.md`
- Prefer champion-relative rules over fixed deltas anchored to the original baseline
- Keep obvious stable wins immediately when they clearly beat the current champion
- Discard ties unless they clearly simplify the code or fix a known failure mode
- Rerun suspicious, tiny, or marginal wins a couple of times before promotion
- Discard crashes and timeouts
- Never change frozen files just to make the metric look better

If the declared rule is clearly stale relative to the current champion, stop treating the old baseline threshold as sacred. Recalibrate it or use a champion-relative confirmation policy instead of discarding an obviously better stable candidate.

If the user has no strong preference, prefer simpler winners when the metric delta is very small.

## Progress Logging

`progress.md` is the narrative ledger. `progress.json` is the machine-readable dashboard feed.

At minimum, record:

- experiment ID
- parent or champion commit
- hypothesis
- files touched
- command run
- verification command and result, when configured
- metric result
- keep or discard decision
- log paths
- anomalies
- lesson learned

Prefer log and artifact paths that are relative to the dashboard root or repo root so the UI can open them directly.

When the harness exposes loop transcript paths, record them alongside eval artifacts.

When the loop emits a per-iteration runner stdout/stderr log, treat it as a first-class artifact. Record it early enough that the dashboard can show live runner output for an active experiment.

Keep `progress.json` updated with:

- summary metrics
- baseline runs
- current champion
- active experiment if one is in progress
- experiment history with keep or discard reasons
- `parent_commit` and `candidate_commit` for any run that should support dashboard diff inspection
- latest log paths

Read `progress.md` before proposing the next experiment so you do not repeat known failures.

## Git Behavior

If the user wants automatic experiment selection semantics, recommend:

- commit winners
- revert losers
- do not commit bulky logs

Keep `objective.md`, `progress.md`, `progress.json`, and logs outside destructive reset paths when possible.

If there is no holdout eval and a kept win is very large, explicitly recommend a broader follow-up benchmark before treating the result as representative outside the cheap eval.

## File Reference

- [assets/objective-template.md](assets/objective-template.md): Source-of-truth template for the experiment charter
- [assets/progress-template.md](assets/progress-template.md): Ledger template for baseline and experiment history
- [assets/progress-template.json](assets/progress-template.json): Machine-readable status file for the dashboard
- [assets/prompt-template.md](assets/prompt-template.md): Loop prompt template for one experiment per iteration
- [assets/loop.sh](assets/loop.sh): Bash loop harness
- [assets/evaluate-template.sh](assets/evaluate-template.sh): Eval wrapper template with logging
- [assets/dashboard.html](assets/dashboard.html): Accessible experiment status dashboard
- [assets/serve-dashboard.js](assets/serve-dashboard.js): Tiny local Node server for the dashboard
- [assets/runners/claude.sh](assets/runners/claude.sh): Claude adapter
- [assets/runners/codex.sh](assets/runners/codex.sh): Codex adapter
- [assets/runners/opencode.sh](assets/runners/opencode.sh): OpenCode adapter
- [assets/runners/custom.sh](assets/runners/custom.sh): Custom runner adapter contract
- [assets/validate-runners.sh](assets/validate-runners.sh): Smoke-test adapters
- [references/metric-design.md](references/metric-design.md): How to choose and shape the scalar metric
- [references/noise-policy.md](references/noise-policy.md): Baselines, confirmation runs, and promotion thresholds
- [references/logging-patterns.md](references/logging-patterns.md): Logging and artifact review conventions
- [references/runner-adapters.md](references/runner-adapters.md): Runner contract and backend-specific notes
