# Choose the next experiment and preserve what was learned

Use this reference for multi-experiment studies or when resuming work. The report's snapshots, runs, and decisions are the evidence; a conversation summary is an index into that evidence.

## Leave a useful result after every experiment

Use the existing `note` command to record the observed mechanism, decision reason, and next action. A failed experiment still teaches something: distinguish a broken harness, an incorrect candidate, an unmet guardrail, and an inconclusive performance effect. Link the relevant run IDs and artifacts. Do not write a positive result for a suite that was never run.

For a rejected idea, say what would make it worth revisiting. Example:

```sh
python3 "$BENCH_SKILL/scripts/bench.py" note --study /absolute/path/to/study --experiment E04 --discard --message 'Full run R04: batching reduced reads but exceeded the memory guardrail. Revisit after streaming removes the retained batch. Next: profile allocation lifetime on the write-heavy scope.'
```

These are ordinary persisted notes, not new learning schema fields. Use `--discard` only for an actual rejection. An experiment incorporated into a later integration may remain `measured`: create the integration with repeated `--contribution` IDs and record why the changes were combined. Do not relabel a source discarded just because it was not separately promoted. For older reports without contribution IDs, retain the source notes and state that the links were not structurally recorded.

## Spend the next run on a question

Choose a hypothesis with an expected mechanism, the evidence that motivates it, and a cheap way to disprove it. Keep a short ranked backlog in a study-local `ideas.md` when the study needs one. For each idea record its parent, expected benefit, main risk, and required measurement. This is an agent-maintained planning file; the CLI does not consume it. Only the coordinating agent edits it when implementation is delegated.

When an idea recurs, identify the earlier experiment and the changed assumption. Record that link in the new experiment's hypothesis or note. Repeating the same snapshot under the same protocol to resolve measurement noise is a verification run, not a new optimization hypothesis. Never infer measurement noise from the spread of different implementations: intended improvements contribute to that spread.

When several attempts fail for the same reason, investigate the shared premise or bottleneck before trying another small variation. Apply the study's predeclared budget and stopping rule. A promising backlog does not reset the budget or override a user stop. The bundled toolkit does not enforce an autonomous iteration budget.

## Resume from persisted evidence

Run `python3 "$BENCH_SKILL/scripts/bench.py" context --study /absolute/path/to/study` before continuing. It extracts objective/guardrails, frozen protocol, E00, current champion, recent candidates and their parents/contributions, latest training evidence, and unresolved runs. It withholds case inputs, held-out feedback, and unclassified free text by default. Follow the returned pointers to relevant training notes; do not inspect reserved inputs or final-evaluation feedback to choose the next optimization. Budget and exposure details may be in the study plan rather than dedicated report fields. Treat an interrupted `running` record as unresolved; inspect the process and use the documented recovery command when appropriate.

For long studies, keep a compact `handoff.md` beside the report with the remaining budget, unresolved questions, and next discriminating experiment. Reference raw evidence instead of copying logs. Refresh it after decisions and reconcile it against `context` on resume. It is an optional agent-written planning aid, not a substitute for the full history. Use `context --include-heldout` only at final evaluation or when reviewing an exposed set.

## Finish with a reviewable outcome

Explain which changes were retained, rejected, inconclusive, or incorporated into an integration. Tie the delivered snapshot to its measurements. If splitting the final work into independently reviewable changes, check dependencies and validate the resulting snapshots: disjoint files alone do not prove independent behavior. A combined measurement cannot establish each component's individual effect.

This workflow adapts the durable lessons, ideas backlog, and conditional retries in [Pi autoresearch's creation skill](https://github.com/davebcn87/pi-autoresearch/blob/04b8a50dac7efe80ffc91648bd00ed9b022e24c2/skills/autoresearch-create/SKILL.md) to bench's isolated experiments and frozen evaluation contract.
