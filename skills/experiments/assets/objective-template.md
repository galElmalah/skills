# Objective

## Summary

- Goal:
- Metric:
- Direction: `min` | `max`
- Cheap eval command:
- Correctness verification command:
- Verification policy: `required_before_keep` | `advisory` | `none`
- Full or holdout eval command:
- Runtime budget per run:
- Allowed write scope:
- Frozen files or directories:
- Promotion rule:
- Confirmation rule:
- Crash or timeout rule:

## Metric Contract

- The source-of-truth scalar is:
- Lower or higher is better because:
- A meaningful improvement is:
  Prefer a rule relative to the current champion, not a fixed delta anchored to the original baseline.
- Known noise or uncertainty:
  Record whether the current noise estimate is still representative of the current champion.

## Evaluation Policy

### Cheap Eval

```bash
# Replace with the repeated search eval
./evaluate.sh
```

Expected artifact(s):

- `.eval-logs/latest/eval.log`
- `.eval-logs/latest/metric.txt`

### Correctness Verification

```bash
# Replace with tests or checks that must pass before promotion
# npm test -- --runInBand
```

Expected artifact(s):

- `.eval-logs/latest/verify.log`
- repo-native test output or summaries, when applicable

Policy notes:

- Verification is required before keep: `yes` | `no`
- Verification files, tests, fixtures, snapshots, or contract checks are frozen during loop iterations unless explicitly unlocked here.

### Full Or Holdout Eval

```bash
# Replace with the broader confidence check
# ./evaluate.sh --full
```

Expected artifact(s):

- `.eval-logs/latest/full.log`

## Write Boundaries

Allowed files or directories:

- `TODO`

Frozen files or directories:

- `TODO`
- Include verification assets here unless the user explicitly wants the loop to edit them.

## Git Policy

- Auto-commit winners: `yes` | `no`
- Auto-revert losers: `yes` | `no`
- Keep logs untracked: `yes` | `no`

## Notes

- Start with the cheap benchmark.
- If the experiment workspace or its log directories live inside the repo but should stay local, add them to `.git/info/exclude` or the repo `.gitignore` before the first loop run so `git status` stays focused on candidate code.
- If only the cheap benchmark exists, recommend building a fuller benchmark before long optimization loops.
- If no correctness verification exists and behavior can break, ask whether to create a minimal verification step before long optimization loops.
- Prefer a champion-relative promotion rule. Obvious stable wins should promote immediately; tiny wins should get a couple of confirmation runs.
- Recompute fixed thresholds after each new champion. Do not keep using an absolute delta derived from an old, much slower baseline.
- After any very large kept win on the cheap benchmark, add a holdout follow-up before treating the result as representative.
