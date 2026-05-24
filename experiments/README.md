# Experiments — Autoresearch

`autoresearch` is the experiment-driven workflow in this repo: a runtime + a pair of skills that drive an agent through champion-based iteration loops on a measurable metric.

This folder holds the sandboxes used to exercise that workflow end-to-end. Everything autoresearch-specific that doesn't belong in the top-level overview lives here.

## How autoresearch is packaged

It's a hybrid:

- a small runtime CLI that owns session state, run logging, keep/discard behavior, export, and finalize
- skills (`autoresearch-create`, `autoresearch-finalize`) that set up the session and guide the agent through the loop

This is intentionally closer to `pi-autoresearch` than to the older scaffolding-only model.

### Runtime files

A session standardizes on these artifacts in the working directory:

- `autoresearch.md`
- `autoresearch.jsonl` — machine source of truth; the dashboard and `autoresearch status` derive state from it
- `autoresearch.sh`
- `autoresearch.checks.sh` when correctness gating is required
- `autoresearch.ideas.md`
- `.autoresearch-logs/`

### CLI

The runtime CLI lives at the repo root:

```bash
node ./bin/autoresearch.js help
```

Primary commands:

- `autoresearch init`
- `autoresearch run`
- `autoresearch log`
- `autoresearch status`
- `autoresearch export`
- `autoresearch clear`
- `autoresearch finalize`

When the skill is used in another repo, it installs a workspace-local runtime under `./.autoresearch/bin/autoresearch`. The skill must not assume a globally installed `autoresearch` binary exists.

### Loop model

Champion-based:

- one current champion
- one mutation per iteration
- one measured decision per iteration
- keep verified wins
- revert losers
- log everything

The runtime owns experiment state and git semantics. The loop harness only drives one agent iteration at a time.

### Dashboard

The browser dashboard is the first-class observability surface. It reads state derived from `autoresearch.jsonl` and shows baseline + champion summary, the run ledger, confidence/noise context, artifact links, and git-backed diffs for runs with commit metadata.

Serve it for a session:

```bash
node ./bin/autoresearch.js export --workdir /path/to/project
```

### Multi-runner support

The shared runner adapters live in [../skills/autoresearch-create/assets/runners](../skills/autoresearch-create/assets/runners).

Supported runners:

- `claude`
- `codex`
- `opencode`
- `custom`

Validate a runner before a long loop:

```bash
bash ../skills/autoresearch-create/assets/validate-runners.sh
```

## Sandboxes

Two small projects exist here to test `autoresearch-create` against controlled, measurable problems. Both are intentionally imperfect, and both start without a fixed benchmark harness — the loop defines the metric, scaffolds the benchmark, proposes isolated changes, and keeps or discards them using a clear scalar result.

| Project | Suggested metric | Direction | Why it exists |
| --- | --- | --- | --- |
| [catalog-project](./catalog-project) | `total_duration_ms` | `min` | Production-style performance target with multiple slow code paths in `src/catalog.js`. |
| [tests-project](./tests-project) | `test_runtime_ms` | `min` | Test-runtime optimization target with several different reasons for slowness, not just one artificial sleep. |

### Suggested starting flow

1. Pick one sandbox.
2. Use `autoresearch-create` to scaffold an autoresearch workspace inside it.
3. Let the skill define and create the first cheap benchmark or eval command.
4. Freeze that benchmark harness and the mutable scope before the first mutation.
5. Start with the cheap benchmark only, then add a fuller holdout if you want more confidence.
