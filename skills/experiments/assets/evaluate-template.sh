#!/usr/bin/env bash
set -euo pipefail

LOG_ROOT="${EVAL_LOG_ROOT:-.eval-logs}"
RUN_ID="${EVAL_RUN_ID:-$(date +%Y%m%dT%H%M%S)-$$}"
RUN_DIR="${EVAL_RUN_LOG_DIR:-$LOG_ROOT/$RUN_ID}"
RUN_LOG="${EVAL_RUN_LOG:-$RUN_DIR/eval.log}"
METRIC_FILE="${EVAL_METRIC_FILE:-$RUN_DIR/metric.txt}"

mkdir -p "$RUN_DIR"
ln -sfn "$(cd "$RUN_DIR" && pwd)" "$LOG_ROOT/latest"

export EVAL_RUN_ID="$RUN_ID"
export EVAL_RUN_LOG_DIR="$RUN_DIR"
export EVAL_RUN_LOG="$RUN_LOG"
export EVAL_METRIC_FILE="$METRIC_FILE"

exec > >(tee -a "$RUN_LOG") 2>&1

echo "[eval log] run id: $EVAL_RUN_ID"
echo "[eval log] run dir: $EVAL_RUN_LOG_DIR"
echo "[eval log] main log: $EVAL_RUN_LOG"

# Replace this section with the repo's cheapest trustworthy benchmark.
# Examples:
#   npm test -- --runInBand
#   bun run eval --hideTable
#   pytest tests/bench/test_latency.py -q
#   python bench.py

echo "TODO: replace evaluate-template.sh with the repo's cheap benchmark command"
exit 1

# After the real command runs, write the scalar metric to "$METRIC_FILE".
# Examples:
#   grep '^score:' "$RUN_LOG" | tail -n1 | awk '{print $2}' > "$METRIC_FILE"
#   jq -r '.score' result.json > "$METRIC_FILE"
