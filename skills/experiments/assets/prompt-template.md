CRITICAL: Handle exactly ONE experiment per iteration. After updating `progress.md` and `progress.json`, STOP. Do not propose or execute a second experiment in the same iteration.

During an active iteration, the loop is the only writer for `progress.md`, `progress.json`, candidate code, and the eval decision. Do not assume a human will patch those files while you are running.

Read `objective.md` first.
Read `progress.md` second.
Read `progress.json` third.

Goal:

- Improve the declared scalar metric.
- Preserve correctness under the configured verification policy.
- Respect the allowed write scope.
- Do not modify frozen files.

Rules:

- One mutation only.
- One idea family only.
- Prefer the smallest plausible change with high information value.
- Do not repeat an experiment already discarded in `progress.md` unless the new variant is materially different and you explain why.
- If the allowed files in the working tree do not match the recorded champion, restore those allowed files to the champion version before choosing the next mutation. Do not carry a discarded candidate forward as the next baseline.
- Do not edit tests, verification scripts, fixtures, snapshots, or other verification assets unless `objective.md` explicitly marks them writable.
- If `EXPERIMENT_RAW_OUTPUT_FILE`, `EXPERIMENT_FINAL_OUTPUT_FILE`, `EXPERIMENT_STREAM_OUTPUT_FILE`, or `EXPERIMENT_ITERATION` are available, record them in the experiment log paths when you update `progress.md` and `progress.json`.
- In `progress.json`, include `stream_output_path`, `raw_output_path`, and `final_output_path` on `active_experiment` as soon as you mark the run `IN PROGRESS`, and keep those same fields on the final experiment record.
- Capture stdout/stderr from the eval run.
- Capture stdout/stderr from the verification run too, when one is configured.
- Inspect logs and artifacts before deciding.
- Do not trust the scalar alone if the logs suggest failure, zero-work behavior, or a broken flow.
- If `objective.md` requires correctness verification before keep and no verification command is configured, stop and report that setup is incomplete instead of guessing.
- Treat the current champion as the comparison point. Do not let a fixed absolute threshold derived from an old baseline block an obviously better stable candidate.

Workflow:

1. Read `objective.md`, `progress.md`, and `progress.json`.
2. Choose one new experiment.
3. Record it as `IN PROGRESS` in `progress.md` and `progress.json`, including the current loop transcript and runner output paths when available.
4. Apply the mutation only within the allowed scope.
5. Commit the candidate if `objective.md` says winners are kept by commit semantics.
6. Run the cheap eval command from `objective.md`.
7. Run the correctness verification command from `objective.md` when the objective requires it before promotion.
8. Read the emitted logs and artifacts.
9. If the candidate is an obvious stable win over the current champion, keep it.
10. If the improvement is tiny or marginal, run a couple of confirmation measurements before promotion, and rerun the champion too when the existing noise estimate is stale or weak.
11. Keep only if the candidate satisfies both the performance rule and the correctness verification policy after any required confirmations.
12. Otherwise revert to the current champion.
13. Update `progress.md` and `progress.json` with the result, duration, evidence, verification result, lesson, log paths, and commit pair (`parent_commit`, `candidate_commit`) when available.
14. If the run is kept and no holdout eval is configured, record a follow-up recommendation when the win is large enough that overfitting risk is real.
15. STOP.

Keep / discard:

- Keep only if the candidate beats the champion under the declared rule.
- If correctness verification is required, keep only if the verification command passes too.
- Rerun tiny or marginal wins a couple of times if `objective.md` requires confirmation.
- Crashes and timeouts are discards.
- Ties are discards unless the change clearly simplifies the system and `objective.md` allows that.

Completion:

- If there is no materially new experiment left to try, output `<promise>COMPLETE</promise>` and stop.
- Otherwise stop after one experiment.
