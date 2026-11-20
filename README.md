# Skills

Curated agent skills for iterative coding workflows.

## Included Skills

| Skill | Description |
| --- | --- |
| [bench](skills/bench) | Define reproducible optimization studies, run isolated experiments, track multiple metrics, and inspect results in a bundled viewer. |
| [pr-comments](skills/pr-comments) | Processes PR review comments with parallel analysis and sequential resolution. |
| [ralph-loop](skills/ralph-loop) | Scaffolds a task-oriented loop that repeatedly picks the next unfinished work item until the backlog is complete. |
| [ui-pr](skills/ui-pr) | Captures and attaches current UI evidence for pull requests with user-visible changes. |

## bench

`bench` replaces the previous `experiments` skill. Use it to optimize application performance, LLM quality and cost, or agent skills with explicit objectives, guardrails, and representative evaluation cases.

```sh
npx skills add galElmalah/skills --skill bench

# Install globally for Codex
npx skills add galElmalah/skills --skill bench --agent codex --global
```

The installation includes the entire skill: instructions, playbooks, Python CLI, report schema, runnable examples, and the prebuilt light/dark viewer. No npm or pip setup is needed to run the installed toolkit; Python 3.10+ and Git on macOS/Linux are required. The installer itself requires Node.js 22.20+.

### Workflow

1. Define a main metric, other objectives, workload scopes, correctness checks, and guardrails.
2. Freeze a small training suite, a full training suite, and separate held-out cases.
3. Measure the unchanged baseline and try each change in an isolated Git worktree.
4. Screen candidates, validate promising results, and record why each experiment was kept or discarded.
5. Combine independent wins in a new integration experiment and measure the combination.
6. Check the selected result on held-out cases before claiming it generalizes.

The viewer shows metric history, experiment quick views and detailed evidence, a branch map, and a table of the versions and contributions behind the current champion. Workloads keep their own measurements; unrelated units are not collapsed into a single score.

### Included resources

```text
skills/bench/
  SKILL.md
  agents/openai.yaml
  scripts/             Python CLI, validation, context, and read-only MCP server
  schema/              Versioned JSON report contract
  examples/            Runnable study and measurement adapter
  references/          Study design, instrumentation, performance, LLM and skill evals
  assets/viewer/       Prebuilt browser viewer and native UI resource
```

Start with [SKILL.md](skills/bench/SKILL.md). See the [toolkit reference](skills/bench/references/toolkit.md) for commands and the [codebase preparation guide](skills/bench/references/prepare-codebase.md) for harnesses, fixtures, and OpenTelemetry. Native Codex panes and chat widgets require separate plugin registration; a skills-only installation includes the local browser viewer.

### Try a measured example

Set `BENCH_SKILL` to the installed directory containing `SKILL.md`:

```sh
BENCH_SKILL=/absolute/path/to/installed/bench
python3 "$BENCH_SKILL/examples/create_demo.py" --output /tmp/bench-example
python3 "$BENCH_SKILL/scripts/bench.py" serve --study /tmp/bench-example/study --port 4318
```

The example runs real small/full measurements against a deliberately small fixture. Open the localhost URL printed by the server. Keep study data outside the installed skill directory.

## Benchmark Sandboxes

Two small projects under [sandboxes](sandboxes) provide targets for trying `bench` before using it on a real codebase. They start without a dedicated benchmark harness so the skill can define a representative evaluation contract first.

| Sandbox | Purpose | Setup |
| --- | --- | --- |
| [catalog-project](sandboxes/catalog-project) | Catalog code with several performance bottlenecks. | Use `bench` to define latency workloads and correctness guardrails. |
| [tests-project](sandboxes/tests-project) | Test runtime affected by fixtures, disk I/O, sleeps, and serial execution. | Use `bench` to measure runtime while preserving required test coverage. |

## Installation

Install using [Vercel's skills CLI](https://github.com/vercel-labs/skills):

```bash
# From local path
npx skills add ./path/to/my-skills

# From GitHub
npx skills add galElmalah/skills

# Install to a specific agent
npx skills add galElmalah/skills -a claude-code

# Install globally
npx skills add galElmalah/skills -g

# List available skills before installing
npx skills add galElmalah/skills -l
```

Useful commands:

```bash
npx skills list
npx skills check
npx skills update
npx skills remove pr-comments
```
