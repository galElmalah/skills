#!/bin/bash
set -euo pipefail

PROMPT_FILE="${1:?prompt file required}"
RAW_OUTPUT_FILE="${2:?raw output file required}"
FINAL_OUTPUT_FILE="${3:?final output file required}"
CODEX_BIN="${CODEX_BIN:-codex}"

"$CODEX_BIN" exec \
  --skip-git-repo-check \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  -o "$FINAL_OUTPUT_FILE" \
  "$(cat "$PROMPT_FILE")" \
  | tee "$RAW_OUTPUT_FILE" > /dev/null

cat "$FINAL_OUTPUT_FILE"
echo ""
