---
name: bench
description: Define and run reproducible optimization studies for application performance, LLM systems, or agent skills, with isolated experiments, multiple metrics, representative evaluation sets, and an annotated viewer in Codex or a local browser.
---

# bench

Turn an optimization request into a study that explains what the agent changed, what it measured, and why an experiment was accepted or rejected. Preserve the user's domain, existing harness, and chosen metrics.

## Choose the playbook

Read [experiment design](references/experiment-design.md) for a new study, then only the relevant domain reference.

| Task | Reference |
| --- | --- |
| Prepare a repository, adapter, fixtures, or instrumentation | [Prepare the codebase](references/prepare-codebase.md) |
| Optimize services, endpoints, CPU, memory, latency, or I/O | [System performance](references/system-performance.md) |
| Optimize prompts, models, retrieval, tools, or LLM workflows | [LLM evaluations](references/llm-evals.md) |
| Optimize a reusable skill or an agent's procedure | [Skill evaluations](references/skill-evals.md) |
| Choose the next experiment or resume a longer study | [Iteration strategy](references/iteration-strategy.md) |
| Execute the bundled CLI or open a real report | [Toolkit interface](references/toolkit.md) |
| Open a Codex pane, chat widget, or .bench report | [Native UI](references/native-ui.md) |

## Run the study

1. **Define success before editing.** Write a hypothesis; choose one objective as `mainMetricId`; define metric IDs, units, directions and scope; objective and guardrail thresholds; output correctness checks; resource budget; and stopping rule. The main metric is the improvement the study must achieve; secondary gains cannot substitute for it. Keep endpoint and workload results visible. Do not invent a universal score from unrelated units.
2. **Freeze the evaluation contract.** Create a small representative `screen` subset and a larger `full` training suite. Reserve a separate `heldout` set for a final generalization check. “Training” means available for iterative optimization; it does not imply model fine-tuning. Version cases, fixtures, adapter, environment, and evaluation policy.
3. **Establish E00.** Validate outputs, then measure the unchanged code. Use this immutable baseline for total progress and each experiment's recorded parent for the effect of its change. A measurement failure is evidence to investigate, not a zero-valued improvement.
4. **Create one explainable experiment.** Use a separate Git worktree from a recorded parent snapshot. Record the intended change before implementing it; commit it before measurement. Chain dependent ideas explicitly. Combine sibling changes in a new integration experiment with source `--contribution` IDs and remeasure the combination. Its parent remains the comparison base.
5. **Choose parallelism by phase.** Independent implementation can run in separate worktrees. Measurement can overlap only with independent resources and a recorded scheduling policy. The bundled runner serializes local measurements through a per-user lock; it does not isolate CPU, ports, databases, or external rate limits.
6. **Screen, then validate.** Run the small training suite first, then the full training suite for promising candidates. Compare like-for-like completed runs, correctness, all required scope/metric guardrails, and variability. Keep tradeoffs explicit. The CLI's repeat-range gate is not a statistical significance test.
7. **Promote evidence, retain history.** Promote a measured candidate only against its current champion parent. If that parent moved, create and measure an integration experiment. Promotion updates the study champion reference; it does not publish or merge into the user's main branch. Record what was learned, the decision reason, and the next useful test, including for rejected or failed experiments. Revisit an idea when its assumptions change; distinguish that from repeating a measurement to resolve noise. Run the final held-out check before claiming generalization or readiness to ship.
8. **Show the work.** Open the study using `bench_open_study` when the host exposes it; otherwise serve the local viewer. Use [native UI](references/native-ui.md) for pane, widget, and file entrypoints. Summarize the change, parent-relative and baseline-relative effects, small/full/held-out results, uncertainty, and decision. Preserve commands, snapshots, events, logs and artifacts for the detailed experiment view. Clearly distinguish measured data from a demo.

Do not tune against final held-out failures and continue calling that set unseen. Mark it exposed, move those cases into future training coverage, and obtain a new independent final set before making a new generalization claim.

## Toolkit location

Everything needed to run bench is inside this skill directory: `scripts/`, `schema/`, `examples/`, and the prebuilt `assets/viewer/`. Resolve the directory containing this `SKILL.md`, including when the agent discovered it through a symlink; do not derive a repository or plugin root from its ancestors.

```sh
BENCH_SKILL=/absolute/path/to/installed/bench
python3 "$BENCH_SKILL/scripts/bench.py" --help
```

Python 3.10+ and Git on macOS/Linux are required. The installed toolkit and viewer need no npm or pip setup. Keep studies and target code outside the installed skill. See [the interface reference](references/toolkit.md) for commands and the adapter contract. A normal skills installation includes the browser viewer; native Codex panes and widgets additionally require the optional plugin's MCP registration.
