#!/bin/bash
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: $0 <iterations>"
  echo "Example: $0 10"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="${EXPERIMENT_WORKSPACE_ROOT:-$SCRIPT_DIR}"
RUNNER_NAME="${EXPERIMENT_RUNNER:-claude}"
RUNNER_SCRIPT="${EXPERIMENT_RUNNER_SCRIPT:-$SCRIPT_DIR/runners/$RUNNER_NAME.sh}"
AUTORESEARCH_BIN="${AUTORESEARCH_BIN:-autoresearch}"
LOG_ROOT="${EXPERIMENT_LOG_ROOT:-$WORKSPACE_ROOT/.autoresearch-logs/runner}"
PROMPT_TEMPLATE_FILE="${EXPERIMENT_PROMPT_TEMPLATE:-}"

if [ ! -x "$RUNNER_SCRIPT" ]; then
  echo "Error: runner script not found or not executable at $RUNNER_SCRIPT"
  exit 1
fi

mkdir -p "$LOG_ROOT"
export EXPERIMENT_WORKSPACE_ROOT="$WORKSPACE_ROOT"

status_json() {
  "$AUTORESEARCH_BIN" status --json --workdir "$WORKSPACE_ROOT"
}

iteration_base="$(
  status_file_tmp="$(mktemp)"
  status_json > "$status_file_tmp"
  python3 - "$status_file_tmp" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
print(int(payload.get("summary", {}).get("iterations") or 0))
PY
  rm -f "$status_file_tmp"
)"

build_prompt() {
  local prompt_file="$1"
  local markdown_file="$WORKSPACE_ROOT/autoresearch.md"
  local benchmark_file="$WORKSPACE_ROOT/autoresearch.sh"
  local status_file="$2"
  local log_paths
  local log_path

  if [ -n "$PROMPT_TEMPLATE_FILE" ] && [ -f "$PROMPT_TEMPLATE_FILE" ]; then
    cat "$PROMPT_TEMPLATE_FILE" > "$prompt_file"
    return
  fi

  cat > "$prompt_file" <<EOF
CRITICAL: Handle exactly ONE experiment iteration. After calling \`$AUTORESEARCH_BIN log\`, STOP. Do not propose or execute a second experiment.

Read these sources first:
1. $markdown_file
2. $benchmark_file
3. $status_file
4. The latest benchmark and checks logs referenced below

Goal:
- improve the declared primary metric
- preserve correctness under the configured verification policy
- keep the current champion model intact

Rules:
- Do not manually edit autoresearch.jsonl.
- Use \`$AUTORESEARCH_BIN run --workdir "$WORKSPACE_ROOT"\` to execute the benchmark.
- Use \`$AUTORESEARCH_BIN log --workdir "$WORKSPACE_ROOT"\` to record the decision.
- Inspect the benchmark script and the latest run logs before choosing a mutation.
- If the benchmark output suggests startup noise or wrapper overhead is dominating, fix the benchmark only if autoresearch.md allows it.
- If no materially new experiment remains, output <promise>COMPLETE</promise> and stop.
- Otherwise stop immediately after one logged experiment.
EOF

  if [ -f "$markdown_file" ]; then
    printf '\n--- autoresearch.md ---\n\n' >> "$prompt_file"
    cat "$markdown_file" >> "$prompt_file"
  fi

  if [ -f "$benchmark_file" ]; then
    printf '\n\n--- autoresearch.sh ---\n\n' >> "$prompt_file"
    cat "$benchmark_file" >> "$prompt_file"
  fi

  printf '\n\n--- autoresearch status ---\n\n' >> "$prompt_file"
  cat "$status_file" >> "$prompt_file"

  log_paths="$(
    python3 - "$status_file" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)

paths = []

active = payload.get("active_experiment") or {}
paths.extend(active.get("log_paths") or [])

baseline_runs = payload.get("baseline_runs") or []
if baseline_runs:
    paths.extend((baseline_runs[-1] or {}).get("log_paths") or [])

experiments = payload.get("experiments") or []
for record in experiments[-2:]:
    paths.extend((record or {}).get("log_paths") or [])

seen = set()
for value in paths:
    if not value or value in seen:
        continue
    seen.add(value)
    print(value)
PY
  )"

  if [ -n "$log_paths" ]; then
    printf '\n\n--- latest benchmark logs ---\n' >> "$prompt_file"
    while IFS= read -r log_path; do
      [ -n "$log_path" ] || continue
      if [ -f "$WORKSPACE_ROOT/$log_path" ]; then
        printf '\n[%s]\n\n' "$log_path" >> "$prompt_file"
        tail -n 120 "$WORKSPACE_ROOT/$log_path" >> "$prompt_file"
        printf '\n' >> "$prompt_file"
      fi
    done <<< "$log_paths"
  fi
}

for ((i=1; i<=$1; i++)); do
  iteration_number=$((iteration_base + i))

  echo ""
  echo "======================================"
  echo "  Autoresearch Loop — Iteration $iteration_number"
  echo "======================================"
  echo ""

  raw_file="$LOG_ROOT/iteration-$iteration_number.raw"
  final_file="$LOG_ROOT/iteration-$iteration_number.txt"
  stream_file="$LOG_ROOT/iteration-$iteration_number.log"
  status_file="$LOG_ROOT/iteration-$iteration_number.status.json"
  prompt_file="$LOG_ROOT/iteration-$iteration_number.prompt.md"

  rm -f "$raw_file" "$final_file" "$stream_file" "$status_file" "$prompt_file"
  export EXPERIMENT_ITERATION="$iteration_number"
  export EXPERIMENT_RAW_OUTPUT_FILE="$raw_file"
  export EXPERIMENT_FINAL_OUTPUT_FILE="$final_file"
  export EXPERIMENT_STREAM_OUTPUT_FILE="$stream_file"

  status_json > "$status_file"
  build_prompt "$prompt_file" "$status_file"

  echo "runner: $RUNNER_NAME"
  echo "workspace root: $WORKSPACE_ROOT"
  echo "prompt: $prompt_file"
  echo "runner log: $stream_file"

  if ! "$RUNNER_SCRIPT" "$prompt_file" "$raw_file" "$final_file" 2>&1 | tee "$stream_file"; then
    echo "[loop] runner failed for iteration $iteration_number" | tee -a "$stream_file"
    exit 1
  fi

  result="$(cat "$final_file" 2>/dev/null || true)"
  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    echo ""
    echo "======================================"
    echo "  Autoresearch complete after $i iteration(s)"
    echo "======================================"
    exit 0
  fi
done

echo ""
echo "======================================"
echo "  Autoresearch finished $1 iterations"
echo "======================================"
