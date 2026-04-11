#!/bin/bash
set -euo pipefail

if [ -z "$1" ]; then
  echo "Usage: $0 <iterations>"
  echo "Example: $0 10"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="$SCRIPT_DIR/prompt.md"
RUNNER_NAME="${EXPERIMENT_RUNNER:-claude}"
RUNNER_SCRIPT="${EXPERIMENT_RUNNER_SCRIPT:-$SCRIPT_DIR/runners/$RUNNER_NAME.sh}"
LOG_ROOT="${EXPERIMENT_LOG_ROOT:-$SCRIPT_DIR/.experiment-logs}"

if [ ! -f "$PROMPT_FILE" ]; then
  echo "Error: prompt.md not found at $PROMPT_FILE"
  exit 1
fi

if [ ! -x "$RUNNER_SCRIPT" ]; then
  echo "Error: runner script not found or not executable at $RUNNER_SCRIPT"
  exit 1
fi

mkdir -p "$LOG_ROOT"

for ((i=1; i<=$1; i++)); do
  echo ""
  echo "======================================"
  echo "  Experiments Loop — Iteration $i of $1"
  echo "======================================"
  echo ""

  raw_file="$LOG_ROOT/iteration-$i.raw"
  final_file="$LOG_ROOT/iteration-$i.txt"

  rm -f "$raw_file" "$final_file"
  "$RUNNER_SCRIPT" "$PROMPT_FILE" "$raw_file" "$final_file"
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
