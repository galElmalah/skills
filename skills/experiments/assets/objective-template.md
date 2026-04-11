# Objective

## Summary

- Goal:
- Metric:
- Direction: `min` | `max`
- Cheap eval command:
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
- Known noise or uncertainty:

## Evaluation Policy

### Cheap Eval

```bash
# Replace with the repeated search eval
./evaluate.sh
```

Expected artifact(s):

- `.eval-logs/latest/eval.log`
- `.eval-logs/latest/metric.txt`

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

## Git Policy

- Auto-commit winners: `yes` | `no`
- Auto-revert losers: `yes` | `no`
- Keep logs untracked: `yes` | `no`

## Notes

- Start with the cheap benchmark.
- If the experiment workspace or its log directories live inside the repo but should stay local, add them to `.git/info/exclude` or the repo `.gitignore` before the first loop run so `git status` stays focused on candidate code.
- If only the cheap benchmark exists, recommend building a fuller benchmark before long optimization loops.
- After any very large kept win on the cheap benchmark, add a holdout follow-up before treating the result as representative.
