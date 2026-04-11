#!/bin/bash
set -euo pipefail

if [ -z "$1" ]; then
  echo "Usage: $0 <iterations>"
  echo "Example: $0 10"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="$SCRIPT_DIR/prompt.md"
WORKSPACE_ROOT="${EXPERIMENT_WORKSPACE_ROOT:-$SCRIPT_DIR}"
RUNNER_NAME="${EXPERIMENT_RUNNER:-claude}"
RUNNER_SCRIPT="${EXPERIMENT_RUNNER_SCRIPT:-$SCRIPT_DIR/runners/$RUNNER_NAME.sh}"
LOG_ROOT="${EXPERIMENT_LOG_ROOT:-$SCRIPT_DIR/.experiment-logs}"
PROGRESS_JSON="$SCRIPT_DIR/progress.json"
CURRENT_RUN_FILE="$LOG_ROOT/current-run.json"

if [ ! -f "$PROMPT_FILE" ]; then
  echo "Error: prompt.md not found at $PROMPT_FILE"
  exit 1
fi

if [ ! -x "$RUNNER_SCRIPT" ]; then
  echo "Error: runner script not found or not executable at $RUNNER_SCRIPT"
  exit 1
fi

mkdir -p "$LOG_ROOT"
export EXPERIMENT_WORKSPACE_ROOT="$WORKSPACE_ROOT"

cleanup_current_run() {
  rm -f "$CURRENT_RUN_FILE"
}
trap cleanup_current_run EXIT INT TERM

write_current_run_file() {
  python3 - "$CURRENT_RUN_FILE" "$SCRIPT_DIR" "$1" "$2" "$3" "$4" <<'PY'
import json
import pathlib
import sys
from datetime import datetime, timezone

current_run_file = pathlib.Path(sys.argv[1])
root = pathlib.Path(sys.argv[2]).resolve()
iteration = int(sys.argv[3])
stream_file = pathlib.Path(sys.argv[4]).resolve()
raw_file = pathlib.Path(sys.argv[5]).resolve()
final_file = pathlib.Path(sys.argv[6]).resolve()

def relpath(target):
    return target.relative_to(root).as_posix()

payload = {
    "status": "RUNNING",
    "iteration": iteration,
    "experiment_id": f"EXP-{iteration:03d}",
    "started_at": datetime.now(timezone.utc).isoformat(),
    "stream_output_path": relpath(stream_file),
    "raw_output_path": relpath(raw_file),
    "final_output_path": relpath(final_file),
}
current_run_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

iteration_base="$(
  python3 - "$PROGRESS_JSON" <<'PY'
import json
import pathlib
import re
import sys

progress_path = pathlib.Path(sys.argv[1])
if not progress_path.exists():
    print(0)
    raise SystemExit

try:
    payload = json.loads(progress_path.read_text())
except Exception:
    print(0)
    raise SystemExit

values = []
summary_iterations = payload.get("summary", {}).get("iterations")
if isinstance(summary_iterations, (int, float)):
    values.append(int(summary_iterations))

for experiment in payload.get("experiments", []):
    match = re.match(r"^EXP-(\d+)$", str(experiment.get("id", "")))
    if match:
        values.append(int(match.group(1)))

active = payload.get("active_experiment") or {}
match = re.match(r"^EXP-(\d+)$", str(active.get("id", "")))
if match:
    values.append(int(match.group(1)))

print(max(values, default=0))
PY
)"

for ((i=1; i<=$1; i++)); do
  iteration_number=$((iteration_base + i))
  echo ""
  echo "======================================"
  echo "  Experiments Loop — Iteration $iteration_number"
  echo "======================================"
  echo ""

  raw_file="$LOG_ROOT/iteration-$iteration_number.raw"
  final_file="$LOG_ROOT/iteration-$iteration_number.txt"
  stream_file="$LOG_ROOT/iteration-$iteration_number.log"

  rm -f "$raw_file" "$final_file" "$stream_file"
  export EXPERIMENT_ITERATION="$iteration_number"
  export EXPERIMENT_RAW_OUTPUT_FILE="$raw_file"
  export EXPERIMENT_FINAL_OUTPUT_FILE="$final_file"
  export EXPERIMENT_STREAM_OUTPUT_FILE="$stream_file"
  echo "runner: $RUNNER_NAME"
  echo "workspace root: $EXPERIMENT_WORKSPACE_ROOT"
  echo "raw transcript: $raw_file"
  echo "final output: $final_file"
  echo "runner log: $stream_file"
  write_current_run_file "$iteration_number" "$stream_file" "$raw_file" "$final_file"
  if ! "$RUNNER_SCRIPT" "$PROMPT_FILE" "$raw_file" "$final_file" 2>&1 | tee "$stream_file"; then
    echo "[loop] runner failed for iteration $iteration_number" | tee -a "$stream_file"
    exit 1
  fi
  rm -f "$CURRENT_RUN_FILE"
  result="$(cat "$final_file" 2>/dev/null || true)"

  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    echo ""
    echo "======================================"
    echo "  Experiments complete after $i iteration(s)"
    echo "======================================"
    exit 0
  fi
done

echo ""
echo "======================================"
echo "  Experiments finished $1 iterations"
echo "======================================"
