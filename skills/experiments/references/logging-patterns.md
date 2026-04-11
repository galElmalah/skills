# Logging Patterns

Never trust the scalar metric alone.

Each experiment run should leave enough evidence to explain why the result is valid or invalid.

## Minimum Artifacts

Recommended per-run artifacts:

- `.eval-logs/<run>/eval.log`
- `.eval-logs/<run>/metric.txt`
- `.eval-logs/<run>/summary.json` when the benchmark emits structured output
- measured duration for the eval run
- optional per-case logs
- optional stderr or system logs
- `.experiment-logs/iteration-<n>.raw` for runner transcripts when available
- `.experiment-logs/iteration-<n>.txt` for final runner messages when available
- `progress.json` for dashboard state

Recommended convenience symlink:

- `.eval-logs/latest`

## What To Inspect

After each run, inspect:

- exit status
- timeouts
- obvious stack traces
- zero-work behavior
- silent failures hidden behind an aggregate score
- per-case regressions if the benchmark emits them

## Loop-Level Logs

If using a loop harness, keep separate loop logs from eval logs.

Examples:

- `.experiment-logs/EXP-001.log`
- `.experiment-logs/loop-20260410T101530.log`

## Keep Logs Out Of Revert Paths

If losers are reverted, logs should still survive.

Prefer:

- untracked log directories
- ignored artifacts
- experiment ledgers that are not deleted by reset operations
- a local dashboard fed by a machine-readable status file
- artifact paths in `progress.json` that are relative to the dashboard root or repo root so the UI can open them directly
