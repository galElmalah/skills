# Benchmark report v1

`BENCH_SKILL` is the absolute directory containing this skill’s `SKILL.md`.

`benchmark.schema.json` is the shared JSON Schema (draft-07). Regenerate it with `python3 "$BENCH_SKILL/scripts/build_schema.py"`. The viewer's TypeScript type is generated from this schema; the Python CLI validates the same schema vocabulary plus relational constraints. `../scripts/core.py` is the reference reducer. `tests/analysis-fixtures.json` and `tests/digest-fixtures.json` are cross-language parity fixtures.

A report stores one frozen study protocol, multiple objectives/guardrails, applicable scopes, grouped cases, a lineage of exact source snapshots, and append-only measurement attempts. `screen` is a small training subset; `full` contains all training cases; `heldout` contains only the separate final partition. Related case groups cannot cross that partition. Scope `weight` records intended workload mix; v1 never silently uses it to combine endpoints, percentiles, or unlike metrics.

Experiments may declare optional `contributionIds` for source changes incorporated into an integration. These links are distinct from the exact `parentId` / `parentCommit` comparison base. IDs must be unique, known, non-baseline sources; neither self-links nor cycles through parent/contribution edges are valid. An absent or empty array preserves legacy behavior. The links are author-recorded provenance, not proof that a merge was executed or that effects add together. Rejected and measured source decisions remain intact when a later integration uses their changes.

Each non-warmup sample identifies a case, scope, repeat, outcome, and raw observations. Metric values may be scalars or nonempty arrays. Successful samples retain finite observations; failed samples retain an error and no success metrics. Missing is distinct from zero. The latest attempt determines the comparison, including a later failed or running attempt. All planned cases/repeats and applicable metrics must be present before a comparison can pass.

For each scope and repeat, flatten compatible observations and apply the metric's reducer. `p95` uses linear interpolation at sorted index `0.95 * (n - 1)`; provide raw request observations, not precomputed endpoint percentiles. `rate` averages observations in `[0, 1]`; supply binary outcomes or comparable fractions with meaningful equal denominators. Other reducers are `mean`, `median`, and `sum`. Observation counts must match between corresponding successful case/repeat samples for every metric by default. Set a metric’s optional `observationPolicy` to `variable` only for intentionally variable-work protocols, such as fixed-duration throughput; add explicit useful-work/completion guardrails. This choice is frozen in the protocol fingerprint. The summary is the median of repeat aggregates with a min/max repeat range. The range is not a confidence interval. Percent formatting appends `%` to numbers already on a 0–100 scale; ratio metrics on 0–1 should use number formatting.

Each objective and guardrail is checked per applicable scope. Every guardrail must declare at least one `target` or `maxRegressionPct`; use the diagnostic role for a non-gating measurement. A feasible comparison needs at least one objective improvement with separated repeat ranges meeting its declared minimum, no objective worsening, and every target/regression constraint satisfied. Conflicting objectives yield `tradeoff`; insufficient signal yields `inconclusive`; missing, failed, incompatible, or constrained evidence yields `blocked`. Relative changes from a zero reference are null. A worsening from zero still fails a declared maximum-regression constraint. No score merges conflicting objectives. These gates are a conservative screening heuristic, not statistical significance or causal proof.

Environment keys `profile`, `platform`, `architecture`, `cpuCount`, `runtime`, and `load` must be nonempty and equal in compared runs. Explicit command argument arrays must also match. Values are supplied/observed provenance, not independently attested hardware equivalence. External imports must declare the exact `commit` and `protocolHash`; their environment and samples remain the importer's responsibility.

## Portable fingerprints

A fingerprint is SHA-256 of UTF-8 compact JSON for this canonical tagged tree:

- Null becomes `["null"]`.
- Boolean becomes `["boolean", value]`.
- String becomes `["string", value]`.
- Number becomes `["number", hex]`, where `hex` is the 16 lowercase hexadecimal digits of the big-endian IEEE-754 binary64 representation. Negative zero remains distinct. Use strings for identifiers or quantities requiring integers beyond binary64 precision.
- Array becomes `["array", ...encodedElements]`.
- Object becomes `["object", [[key, encodedValue], ...]]`, ordered by Unicode codepoint order of keys.

The encoded tree has no whitespace and retains Unicode characters (`ensure_ascii=False` in Python); its only numbers are inside string encodings. `splitHash` fingerprints the complete `cases` array. `protocolHash` fingerprints the object containing exactly `protocol`, `metrics`, `scopes`, `cases`, and `suites`. Arrays preserve their order. Changing the cases, split, metrics, scopes, or protocol creates a different study instead of rewriting comparable history.
