#!/bin/bash
set -euo pipefail

PROMPT_FILE="${1:?prompt file required}"
RAW_OUTPUT_FILE="${2:?raw output file required}"
FINAL_OUTPUT_FILE="${3:?final output file required}"

if [ -n "${CUSTOM_RUNNER_SCRIPT:-}" ]; then
  exec "$CUSTOM_RUNNER_SCRIPT" "$PROMPT_FILE" "$RAW_OUTPUT_FILE" "$FINAL_OUTPUT_FILE"
fi

echo "Error: set CUSTOM_RUNNER_SCRIPT to an executable that accepts: <prompt_file> <raw_output_file> <final_output_file>" >&2
exit 1
