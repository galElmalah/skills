#!/bin/bash
set -euo pipefail

PROMPT_FILE="${1:?prompt file required}"
RAW_OUTPUT_FILE="${2:?raw output file required}"
FINAL_OUTPUT_FILE="${3:?final output file required}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

"$CLAUDE_BIN" \
  --print \
  --output-format json \
  --dangerously-skip-permissions \
  "$(cat "$PROMPT_FILE")" \
  | tee "$RAW_OUTPUT_FILE" > /dev/null

node -e '
const fs = require("fs");
const data = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
process.stdout.write(data.result || "");
' "$RAW_OUTPUT_FILE" | tee "$FINAL_OUTPUT_FILE"

echo ""
