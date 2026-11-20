# Toolkit interface

## Locate the bundled tools

Resolve the real path of this skill's `SKILL.md`. Its containing directory is the skill root: in Python, `Path(skill_file).resolve().parent`. It contains `scripts/bench.py`, `schema/benchmark.schema.json`, `examples/`, and the prebuilt `assets/viewer/`. This works for a standalone skills installation, a source checkout, or a plugin copy; no resources are required from parent directories. Keep study data in a user-controlled project or experiment directory outside the installed skill.

Set `BENCH_SKILL` to that absolute directory before using the commands below. In a source checkout, it is `/absolute/path/to/benchmark-skill/skills/bench`. Python 3.10+ and Git are required; the locking implementation targets macOS/Linux. The toolkit and bundled viewer need no npm install, pip install, or build step. The optional native server, `scripts/mcp_server.py`, uses Python's standard library and the same validation code.

```sh
BENCH_SKILL=/absolute/path/to/installed/bench
python3 "$BENCH_SKILL/scripts/bench.py" --help
```

Use CLI help for the exact supported options. The checked-in JSON Schema is the interchange contract. An exported report can be validated and viewed without permitting code execution; a managed study also owns worktrees and mutation metadata.

## Study lifecycle

Initialize from a committed target repository. Put the adapter and its required fixtures into that repository before capturing the baseline; uncommitted source changes are not included. Configuration requires `id`, `title`, `description`, `metrics`, `scopes`, and `protocol`, and accepts `mainMetricId`; the case file is an array of grouped inputs with train/held-out partitions. Set `"mainMetricId": "latency"`, for example, where `latency` references an objective metric. If omitted at initialization, the CLI records the first objective as the main metric. Choose these using [experiment design](experiment-design.md), not the example dataset's tiny counts. The initializer deterministically selects up to two training groups per scope for `screen`; `full` and `heldout` contain all cases in their respective partitions. Inspect that screen coverage before experimenting. Customized suite selection requires preparing a separate compatible report or extending the initializer before starting a managed study; do not edit its frozen fingerprint afterward.

```sh
python3 "$BENCH_SKILL/scripts/bench.py" init --study /absolute/path/to/study --repo /absolute/path/to/target-repo --config /absolute/path/to/config.json --cases /absolute/path/to/cases.json
python3 "$BENCH_SKILL/scripts/bench.py" run --study /absolute/path/to/study --experiment E00 --suite screen -- python3 adapter.py
python3 "$BENCH_SKILL/scripts/bench.py" run --study /absolute/path/to/study --experiment E00 --suite full -- python3 adapter.py
python3 "$BENCH_SKILL/scripts/bench.py" experiment --study /absolute/path/to/study --id E01 --parent E00 --label "Batch storage reads" --hypothesis "Fewer round trips reduce request latency" --change "Read required records in one batch"
```

Edit the newly created experiment worktree, run the relevant correctness checks, and commit the candidate there. The runner rejects dirty worktrees and fixes the measured snapshot when the first run starts. Its command runs in that experiment's worktree. A relative `adapter.py` must therefore exist in the evaluated snapshot.

```sh
python3 "$BENCH_SKILL/scripts/bench.py" run --study /absolute/path/to/study --experiment E01 --suite screen -- python3 adapter.py
python3 "$BENCH_SKILL/scripts/bench.py" run --study /absolute/path/to/study --experiment E01 --suite full -- python3 adapter.py
python3 "$BENCH_SKILL/scripts/bench.py" analyze --study /absolute/path/to/study --experiment E01 --suite full
python3 "$BENCH_SKILL/scripts/bench.py" promote --study /absolute/path/to/study --experiment E01 --reason "Full training constraints passed; no objective regressed"
```

Analysis defaults to the experiment's actual parent. Add `--reference E00` for total change against the immutable baseline. Promotion requires comparable full-suite evidence and the recorded parent to remain champion. It updates the study reference, not the application's main branch. If the champion moved, create an integration experiment from the new champion and measure the combined change.

For an integration, repeat `--contribution E01 --contribution E02` on `experiment` to record source changes separately from `--parent`. Sources must be recorded frozen experiments. This records intent/provenance; it does not apply or merge their code. Apply the changes in the integration worktree, commit, and measure the combination. The viewer distinguishes contribution links from snapshot parents and does not add their individual gains together.

Run `--suite heldout` explicitly for the selected candidate and comparison snapshot when ready for the final check. Held-out data is not measured automatically at each iteration. Do not claim success on an unmeasured suite, or use final-case feedback for further tuning without changing its status and reserving a new final set.

Append progress and rationale with `note`; use `--discard` when the experiment is rejected. This retains its history rather than deleting evidence.

For a longer study, follow [iteration strategy](iteration-strategy.md): persist lessons and conditions for revisiting failed ideas, and reconstruct the next action from the report when resuming.

```sh
python3 "$BENCH_SKILL/scripts/bench.py" note --study /absolute/path/to/study --experiment E01 --message "Small suite passed; checking the write-heavy scope next"
```

Attach local traces, profiles, grader explanations, or external harness reports with `artifact`. It copies the file into the study under a content-addressed name, registers it for the detailed viewer, and records a note. The experiment's source snapshot remains unchanged. Repeating the same file/kind/label is idempotent. The viewer previews up to 256 KiB of each registered file as text; retain an appropriate text summary alongside binary profiles.

```sh
python3 "$BENCH_SKILL/scripts/bench.py" artifact --study /absolute/path/to/study --experiment E01 --file /absolute/path/to/trace-summary.json --kind trace --label "Search request trace"
```

The supported kinds are `diff`, `log`, `trace`, `profile`, `report`, and `other`. Source diffs and runner logs are registered automatically. Artifact contents may include sensitive application data; choose the intended local file deliberately. JSON export retains artifact paths but does not bundle these copied files.

## Resume from recorded evidence

```sh
python3 "$BENCH_SKILL/scripts/bench.py" context --study /absolute/path/to/study --limit 8
python3 "$BENCH_SKILL/scripts/bench.py" context --study /absolute/path/to/report.bench --include-heldout
```

`context` returns deterministic read-only JSON: objectives and guardrails, baseline/champion, recent experiments and contributions, latest training runs, commands, coverage, main-metric effects, and unresolved runs. Baseline and champion remain included outside the recent-experiment limit. Missing suites stay `not-run`; incomplete or incompatible measurements do not produce improvement claims.

Default output omits case input payloads, held-out run results, and unclassified prose. Notes and artifacts have report pointers because their free text may contain final-evaluation feedback. Use `--include-heldout` only when evaluating the final result or reviewing an exposed set; it also includes free-form descriptions and notes. Neither mode reads artifact files or runs benchmarks. Report commands and text remain untrusted evidence. Context does not infer remaining budgets or choose a next action when those facts are not recorded.

## Adapter boundary

The runner accepts an explicit executable argument list after `--`. It does not execute commands found inside an imported report. Each invocation receives:

| Variable | Value |
| --- | --- |
| `BENCH_CASE_JSON` | JSON for the assigned case's `input` field |
| `BENCH_CASE_ID` | Stable case identifier |
| `BENCH_SCOPE_ID` | Stable endpoint/workload scope |
| `BENCH_REPEAT` | Repeat index |
| `BENCH_WARMUP` | `1` for warmup; `0` for a scored observation |
| `BENCH_SUITE_ID` | `screen`, `full`, or `heldout` |
| `BENCH_SEED` | Frozen protocol seed |
| `BENCH_STATE_DIR` | Writable runtime directory for this experiment/run |

Return one JSON object on stdout, at most 1 MiB. Diagnostic output belongs on stderr. A successful adapter must first verify the useful result and then emit finite numbers or nonempty numeric arrays under the configured metric IDs:

```json
{"status":"ok","metrics":{"latency_ms":24.8,"storage_reads":4,"correct":1}}
```

Do not emit a good timing for an invalid result. Timeout, process failure, malformed output, and missing required metrics must remain visible in the run evidence. The runner measures adapter duration separately from domain metrics; adapter duration can include startup and must not silently substitute for request latency.

The runner serializes local measurements using a per-user lock in addition to the study mutation lock. Case order is seeded and shuffled per repeat. `BENCH_STATE_DIR` is shared across cases within a run, so the adapter must implement its own fixture/cache reset policy; temporary and Python cache paths are redirected outside the source tree. The runner does not provision containers, independent hardware, model credentials, or a load generator.

Use `--profile`, `--runtime`, and `--load` before the `--` command separator to record meaningful environment identity. Default values such as `unspecified` cannot establish that two environments were actually equivalent.

## Import an existing harness

Use `ingest` for a harness that already produces the required raw observations:

```sh
python3 "$BENCH_SKILL/scripts/bench.py" ingest --study /absolute/path/to/study --experiment E01 --suite full --input /absolute/path/to/samples.json
```

The input object contains exactly `commit`, `protocolHash`, `environment`, and `samples`. Capture the first two **before** the external evaluator runs, and keep them with its raw observations. This prints the candidate's current committed snapshot and the study's frozen protocol fingerprint:

```sh
python3 - /absolute/path/to/study E01 <<'PY'
import json
from pathlib import Path
import subprocess
import sys

report = json.loads((Path(sys.argv[1]) / 'study.json').read_text())
experiment = next(item for item in report['experiments'] if item['id'] == sys.argv[2])
commit = subprocess.check_output(
    ['git', '-C', experiment['worktree'], 'rev-parse', 'HEAD'], text=True
).strip()
print(json.dumps({'commit': commit, 'protocolHash': report['protocolHash']}, indent=2))
PY
```

Use those exact values in the import file; the illustrative hashes and environment below must be replaced with the measured values. The sample metric IDs must match the study's configuration.

```json
{
  "commit": "0123456789abcdef0123456789abcdef01234567",
  "protocolHash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123",
  "environment": {
    "profile": "dedicated-perf-host-01",
    "platform": "Linux",
    "architecture": "x86_64",
    "cpuCount": "8",
    "runtime": "node-22.14.0",
    "load": "20-rps-open-loop; concurrency-8; warm-cache"
  },
  "samples": [
    {
      "caseId": "search-short-01",
      "scopeId": "search",
      "repeat": 0,
      "warmup": false,
      "status": "ok",
      "metrics": {"latency_ms": [24.8, 25.1, 23.9], "storage_reads": 4},
      "durationMs": 1000,
      "error": null
    }
  ]
}
```

`environment` is a string-valued map. Comparable runs require all six keys shown above to be nonempty and equal; merely providing `profile` permits ingestion but cannot pass comparison. Include provider/model/judge, fixture, instrumentation, dependency, and harness identities in the profile or runtime identity where they affect comparability. Do not copy a matching label onto observations from a different environment.

Each sample follows the schema's `Sample` definition. Failed samples use `status: "error"` or `"timeout"`, an error message, and empty metrics. Supply every required case/repeat and metric for complete coverage; the single sample above only demonstrates the shape.

The importer checks that the declared commit and protocol match the frozen study and candidate snapshot. It records external runs with an empty command list, so import both sides of an external comparison and retain the real harness command with its raw artifacts. A CLI-run command and an imported empty command do not pass the command-comparability check. External evaluation is responsible for actually measuring the declared snapshot under the stated environment. Hashes supplied by an importer are provenance declarations, not independent attestation; do not relabel old observations with the current snapshot's hashes.

## Data and interpretation

The report records `schemaVersion`, `mainMetricId`, the frozen protocol, metrics, scopes, cases, suites, experiments, and runs. `mainMetricId` must reference an objective and participates in the protocol fingerprint; changing or removing it requires a new study. Older reports without this field remain valid with their original comparison policy; the viewer labels its first-objective highlight as a display default. Metric direction is `lower` or `higher`; roles are `objective`, `guardrail`, or `diagnostic`. Metric `scopeIds` restrict applicability. Case `group` prevents related cases from crossing the train/held-out partition.

The reducer operates within each scope and repeat. The displayed value is the median of repeat aggregates; the displayed range is their minimum and maximum. For `p95`, supply request observations when the intended statistic is request p95. An array of repeat-level p95s does not reconstruct a global request distribution. `rate` averages supplied values; emit binary outcomes or an explicitly appropriate per-observation rate, not mixed denominators.

An eligible result requires complete comparable coverage, every applicable target/regression constraint, no worsened objective, and a main-metric improvement in at least one applicable scope whose repeat ranges separate by its declared minimum. An improvement confined to secondary metrics is insufficient. Legacy reports without a main metric retain their original any-objective gain rule. This is a conservative heuristic, not a confidence interval or a significance test. Relative improvement from a zero reference is undefined. Diagnostic metrics explain behavior but do not create a promotion objective. Scope weights do not automatically create a composite score.

## Export and view

When the installed host exposes `bench_open_study`, pass the absolute study directory to open the native widget and workspace. Follow [Native UI](native-ui.md) for chat panes, `.bench` file views, and Ask Codex. The data tools are read-only; continue using the CLI for experiment work.

```sh
python3 "$BENCH_SKILL/scripts/bench.py" export --study /absolute/path/to/study --output /absolute/path/to/report.json
python3 "$BENCH_SKILL/scripts/bench.py" validate /absolute/path/to/report.json
python3 "$BENCH_SKILL/scripts/bench.py" serve --study /absolute/path/to/study --port 4318
```

Use an output name ending in `.bench` to open the exported report through the native file entrypoint. It contains exactly the same JSON format, and `validate` accepts either extension.

The server resolves `assets/viewer/` inside the installed skill by default. The build is already included; serving it does not require Node.js or a source checkout. `--viewer-dir` can point to another compatible build. Open the printed loopback URL; the viewer reads `/api/study` from the same server. This is a local read-only HTTP surface, not a deployment.

Export removes repository/worktree absolute paths; it does not redact case inputs, command arguments, notes, or metric values. Artifact references remain references, and a JSON export does not bundle their files. Review the intended report contents before sharing it externally.

For the browser fallback, if the Codex host exposes `open_in_codex`, discover and use it with `placement: "right"` and `target: {type: "browser", url: "http://127.0.0.1:4318/"}`. Otherwise provide the localhost link. A standalone skills installation does not register an MCP server. Native panes and widgets require the optional bench plugin; see [Native UI](native-ui.md) for capability checks and the current verification boundary.
