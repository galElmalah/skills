# LLM optimization playbook

## Choose the task and grader

Define success for the actual application: answer grounded in the supplied sources, valid structured extraction, correct tool execution, solved task, or usable generated artifact. Separate the final outcome from intermediate retrieval, routing, and tool-argument checks. Task-specific evaluations and human calibration are preferable to a generic score or an agent's own assertion that it succeeded. [OpenAI: evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).

Use deterministic checks where they fit: schema validation, exact fields, executable tests, database state, permitted actions, and artifact inspection. For judgment-based quality, write a rubric with concrete pass/fail examples and grade a calibration sample with a human. Freeze the rubric and judge configuration before candidate comparison. If using a model judge, blind candidate identities, randomize answer order for pairwise judgments, and check whether swapping the order changes the result. A longer or more confident answer should not win merely for its presentation.

Do not make judge self-confidence the quality metric. Keep expected answers and grader instructions outside the evaluated agent's input. Treat an unavailable or malformed grade as a failure to evaluate, not a passing result.

## Build cases that transfer

Group cases by actual task families and failure modes: ordinary requests, ambiguous requests, missing evidence, long contexts, difficult retrieval, tool errors, and relevant boundary conditions. Use the source document, conversation, template family, or repository as the split group, so near-duplicates cannot straddle training and final held-out sets. Use [the shared split protocol](experiment-design.md#small-set-full-set-final-held-out-set).

For a small initial study, select enough training cases to cover every family and at least one meaningful failure. Pick the screen subset from those same families. Expand full training coverage when new failures are discovered; version the changed protocol and remeasure the parent. Keep the final held-out set separate from that debugging loop.

Save the complete reproducibility context: model/provider version where available, system and task prompts, retrieval index and corpus snapshot, tool definitions, generation settings, judge version, stop conditions, retry policy, and token/time budget. A fixed random seed may reduce variability but does not guarantee identical responses from a hosted system.

## Metrics and cost

Use quality or task completion as an objective or hard floor, with separate latency, input/output token, tool-call, and monetary cost metrics. Define units and denominators: cost per attempted task and cost per successful task answer different questions. Include failed attempts and retries in the accounting. Record the pricing schedule used for derived dollar cost; token counts are the more durable raw evidence.

A prompt that responds quickly by skipping necessary tool work must fail its outcome check. Compare by task scope so an easy extraction task cannot conceal a regression in complex reasoning. If quality and cost move in opposite directions, show the feasible tradeoff rather than blending them into an unexplained score.

Run repeated independent generations when stochastic variation matters. Pair cases across parent and candidate, preserve all outputs and grades, and distinguish repeat variability from coverage across different tasks. The bundled CLI summarizes observations and thresholds; it does not implement a model judge, provider adapter, significance test, or dollar-cost estimator. Implement these in the project's evaluation adapter or import results from its established harness.

Bound concurrency by provider limits, budget, and latency goals. Keep the same settings for parent and candidate; compare contention-free latency separately from throughput at a chosen concurrency. Retry settings and rate-limit waiting belong in the report.

## Experiment explanation

The quick view should name the changed prompt/model/retriever/tool policy, show small/full quality and resource effects, and state whether the final held-out result exists. The detailed view should include case-level failures, grader reasons, input/output or sanitized artifact references, token usage, retries, tool traces, and the exact evaluated snapshot. Describe a generalization claim only after the candidate survives unseen cases.

The playbook is provider-neutral. Reuse a supported evaluation harness rather than making the study depend on a specific hosted eval product; verify current platform availability before adding a service integration.
