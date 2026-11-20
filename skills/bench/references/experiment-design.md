# Design an optimization study

## Freeze the decision before seeing the result

Describe the user-visible task, the suspected bottleneck or failure, the candidate change, and the smallest meaningful improvement. Record the run budget and stopping condition: time, spend, trial count, plateau, or an achieved target. Changing a metric, dataset, judge, workload mix, or measurement boundary creates a new protocol version; retain the previous results under their original contract. The bundled toolkit freezes its protocol and split fingerprints: initialize a new managed study for those changes rather than editing an existing report in place.

Define each measurement by **metric × scope × suite**. A scope can be an endpoint (`search`, `write`), task family (`retrieval`, `editing`), input-size band, or deployment condition. Metric definitions include unit, minimize/maximize direction, reducer, required scopes, and objective/guardrail role. Choose one objective as the study’s `mainMetricId` before measuring. It identifies the intended improvement; other objectives must not regress, and guardrails still apply. The main metric is frozen with the protocol. Describe what one observation measures. `latency_ms` for one request differs from `batch_p95_ms` for a whole load-test run.

Example: minimize latency and storage reads for `search` and `detail`, while keeping successful responses above 99.9% and quality at least as high as the recorded floor. Show all four objective series and their guardrails. A gain on one endpoint must not hide a regression on another.

Do not average endpoint p95 values and label the result global p95. Derive a combined percentile from compatible request samples or mergeable distributions under a fixed request mix. If a weighted score is needed, write down normalization, weights, and constraints before experimentation and also expose the original metrics. This is a study-design rule; the bundled CLI does not calculate a weighted utility score.

## Small set, full set, final held-out set

| Suite | Purpose | Selection |
| --- | --- | --- |
| `screen` | Cheap feedback while implementing | A fixed subset of training cases covering every required scope and important difficulty band |
| `full` | Candidate decisions with wider coverage | All training cases, including failures found during development |
| `heldout` | Final check on unseen cases | Separate case groups, withheld from iterative diagnosis and selection |

Split by the source of correlation: customer, document, repository, session, query template, or problem family. Near-duplicates and paraphrases belong in the same split. Choose proportions from coverage and uncertainty needs, not a universal percentage. A handful of cases can reveal broken behavior; it rarely supports a precise estimate of rare failures. Freeze a seed, case IDs, fixture hashes, grouping rules, and suite membership. Do not repeatedly edit the screen set to favor the latest idea.

Keep final cases and expected answers out of the optimizing agent's working context where possible. The local JSON format is an organizational boundary, not an access-control mechanism; for stronger separation, run the final evaluator in a separate checkout/account and import its result. If final results inform another change, that set has become development evidence. Reserve a new final set. This applies the same leakage principle as keeping test data out of model selection. [scikit-learn: data leakage](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).

## Measurements that support a decision

Use the same cases, repetitions, load, timeouts, resets, warm/cold policy, and environment for parent and candidate. Save raw observations and failures. Warmups are separate observations and do not belong in the scored sample. Validate useful work before trusting faster timings: expected responses, rows, artifacts, or task outcomes must still exist.

For a noisy local system, prefer matched parent/candidate blocks in randomized or alternating order. Randomizing repetition order can reduce time-drift effects; Google Benchmark supports this directly. [Google Benchmark: random interleaving and repetitions](https://google.github.io/benchmark/user_guide.html#random-interleaving). The bundled runner shuffles case order within each serial suite; its two independent commands do **not** implement a paired or randomized parent/candidate scheduler. Use an existing harness and import observations when that design is required.

Treat independent cases or independent run blocks as the resampling unit. Repeated timings on one case are not new workload coverage. Report sample counts and variability. A repeat range is not a confidence interval. Use paired case/block differences and a suitable interval only when the harness actually computes it; label the method and seed. Do not invent confidence from a handful of p95 scalars. A small effect inside ordinary run-to-run variation is inconclusive.

The current CLI compares medians of per-repeat aggregates and uses separated repeat ranges as a conservative improvement heuristic. Its successful promotion gate means the configured measured constraints and that heuristic passed; it does not establish significance or generalization. When noise can reverse a decision, collect more independent evidence or retain the current champion.

## Isolation, chains, and promotion

Keep E00 immutable. Each candidate names one exact parent snapshot and runs in its own worktree. The moving champion identifies the best accepted integrated state so far. An experiment may build on another experiment even before either becomes champion; its reported change effect is still against its actual parent.

Two sibling wins do not prove their combination wins. Start an integration experiment from the current champion, apply the other change, resolve conflicts, and rerun. A stale candidate must not overwrite a newer champion. Preserve rejected branches and results long enough to explain what was tried; do not rewrite their recorded snapshots.

For multiple objectives, first reject incorrect or constraint-violating candidates. Among feasible candidates, retain the Pareto tradeoff: a candidate dominates another only when it is no worse on every objective and better on at least one. If neither dominates, explain the tradeoff and apply a priority agreed before measurement. The bundled automatic gate requires a meaningful main-metric improvement in at least one applicable scope with separated repeat ranges, no objective regression in any required scope, and all constraints satisfied. It does not choose between Pareto alternatives or allow a favorable weighted average to hide a regression.

## Parallelism is a resource decision

Parallelize independent edits, research, and lightweight correctness checks. Budget measurement slots separately for CPU cores, memory, I/O device, database instance, accelerator, service account, API rate limit, and spend. Git worktrees isolate files, not these resources. Give workers separate ports, fixture stores, output directories, and credentials when relevant.

On a shared laptop, default to one performance measurement at a time and avoid simultaneous builds. Use multiple isolated hosts for independent runs only when their hardware/software identities are recorded and comparisons remain matched. For hosted LLMs, bound concurrent requests and preserve concurrency, retries, rate limits, and pricing versions on both sides. The CLI has a per-study mutation lock and a per-user local measurement lock across studies; unrelated processes, other users, and external harnesses can still compete for resources.
