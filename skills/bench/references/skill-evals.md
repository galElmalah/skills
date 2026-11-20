# Skill and agent-procedure playbook

## Evaluate selection and execution separately

A skill has two distinct jobs: be selected for the right request, then cause useful work. Build a routing set with clear positive requests, plausible neighboring requests that should not invoke it, and ambiguous cases with a defined expected behavior. Separately build execution cases with raw inputs, a resettable environment, and a verifiable final outcome. A perfect execution score says nothing about an overbroad skill description.

Use fresh agent contexts for independent execution cases. Give the evaluated agent the user request, skill, and minimum artifacts that a real user would provide. Do not include the optimizer's explanation, suspected defect, desired tool sequence, or known answer. Keep the baseline and candidate's model, tools, permissions, starting files, time/token budgets, and stopping policy matched.

If the host cannot run fresh isolated agents, mark that limitation. Do not label a continuation in the optimizer's own conversation an independent evaluation. The benchmark CLI can launch a supplied executable adapter; it does not itself provision Codex conversations or model credentials.

## Define observable outcomes

Prefer evidence from the environment over the agent's final text. Examples: a requested artifact exists and opens; a changed application passes the relevant task; a query returns the intended rows; a forbidden unrelated file was left alone. Evaluate the substance of the result. A skill that says “all checks passed” is not evidence that checks ran.

Record outcome quality, required constraint violations, unsupported completion claims, tool failures, elapsed time, token usage when available, and avoidable user interruptions. Distinguish an appropriate clarification from an unnecessary stop. Agent evaluation should inspect tool choice and arguments as well as final output; these are separate possible failure points. [OpenAI: single-agent evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices#single-agent-architectures).

Do not reward mimicking a specific tool sequence when another valid approach accomplishes the task. A trace is diagnostic evidence unless the sequence itself is the contract. For a document or UI task, retain and inspect the rendered artifact, not only source files or screenshots of a success message.

## Build a representative case set

Choose multiple task families, input shapes, and realistic environment conditions. Include missing optional data, a tool that fails, an already-complete task, and a request near the skill's scope boundary where those occur in actual use. Test realistic authorization and side effects within an isolated fixture or existing authorized sandbox.

Keep paraphrases of the same task, artifacts from the same source, and variants of one hidden answer in the same split group. Use a small screen set for edits to the instructions and full training coverage for a candidate. Reserve independent tasks and source artifacts for the final held-out check. Do not give held-out failure explanations to the optimizer and still call later attempts unseen.

Repeat uncertain cases with fresh sessions. Report both task coverage and repeated-run variability. A higher average score that systematically loses one task family should remain visible as a regression, especially if the family is a required scope.

## Change and explain

Try one coherent behavioral change per experiment: narrower selection language, a missing reference, a simpler procedure, a helper script, or a different default. Capture the skill and every referenced asset/script in the snapshot. An external mutable reference breaks reproducibility unless its content or version is retained.

Use a separate worktree for each candidate and clean fixtures per execution. Independent edits can proceed concurrently; evaluation sessions must not share writable artifacts or fight over a browser, credential quota, or application state. Use the resource plan in [experiment design](experiment-design.md#parallelism-is-a-resource-decision).

The quick view should describe the intended behavior change and small/full outcome changes, cost, and coverage. The detailed view should link the skill diff, case setup, actual traces, generated artifacts, evaluator observations, and decision. Preserve failed attempts; they explain why a longer instruction or an extra helper script was justified—or why it should be removed.
