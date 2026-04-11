---
name: autoresearch-finalize
description: Finalize kept autoresearch runs into clean reviewable branches. Use when the user wants to prepare an autoresearch branch for review or split kept runs into independent branches.
---

# Autoresearch Finalize

Turn a noisy autoresearch branch into clean, reviewable branches.

## Workflow

1. Read the kept runs from `autoresearch.jsonl`.
2. Build a proposal with:

```bash
autoresearch finalize propose --workdir <target-dir>
```

3. Present the groups to the user and wait for approval.
4. Write the approved proposal to `groups.json`.
5. Apply it with:

```bash
autoresearch finalize apply --workdir <target-dir> --groups groups.json
```

## Grouping Rules

- Preserve application order.
- No two groups may touch the same file.
- Each group should be independently reviewable from the merge-base.
- Merge overlapping groups instead of forcing independence.

## Report Back

After apply succeeds, report:

- created branches
- what each branch contains
- baseline to best metric improvement
- any cleanup commands printed by the finalize script
