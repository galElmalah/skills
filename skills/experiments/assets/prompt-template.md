CRITICAL: Handle exactly ONE experiment per iteration. After updating `progress.md` and `progress.json`, STOP. Do not propose or execute a second experiment in the same iteration.

Read `objective.md` first.
Read `progress.md` second.
Read `progress.json` third.

Goal:

- Improve the declared scalar metric.
- Respect the allowed write scope.
- Do not modify frozen files.

Rules:

- One mutation only.
- One idea family only.
- Prefer the smallest plausible change with high information value.
- Do not repeat an experiment already discarded in `progress.md` unless the new variant is materially different and you explain why.
- Capture stdout/stderr from the eval run.
- Inspect logs and artifacts before deciding.
- Do not trust the scalar alone if the logs suggest failure, zero-work behavior, or a broken flow.

Workflow:

1. Read `objective.md`, `progress.md`, and `progress.json`.
2. Choose one new experiment.
3. Record it as `IN PROGRESS` in `progress.md` and `progress.json`.
4. Apply the mutation only within the allowed scope.
5. Commit the candidate if `objective.md` says winners are kept by commit semantics.
6. Run the cheap eval command from `objective.md`.
7. Read the emitted logs and artifacts.
8. If the result is a verified win under the promotion rule, keep it.
9. Otherwise revert to the current champion.
10. Update `progress.md` and `progress.json` with the result, duration, evidence, lesson, and commit pair (`parent_commit`, `candidate_commit`) when available.
11. STOP.

Keep / discard:

- Keep only if the candidate beats the champion under the declared rule.
- Rerun marginal wins if `objective.md` requires confirmation.
- Crashes and timeouts are discards.
- Ties are discards unless the change clearly simplifies the system and `objective.md` allows that.

Completion:

- If there is no materially new experiment left to try, output `<promise>COMPLETE</promise>` and stop.
- Otherwise stop after one experiment.
