#!/bin/bash
set -euo pipefail

PROMPT_FILE="${1:?prompt file required}"
RAW_OUTPUT_FILE="${2:?raw output file required}"
FINAL_OUTPUT_FILE="${3:?final output file required}"
OPENCODE_BIN="${OPENCODE_BIN:-opencode}"

"$OPENCODE_BIN" run \
  --format json \
  "$(cat "$PROMPT_FILE")" \
  | tee "$RAW_OUTPUT_FILE" > /dev/null

node -e '
const fs = require("fs");
const lines = fs.readFileSync(process.argv[1], "utf8").split(/\r?\n/).filter(Boolean);
let text = "";
for (const line of lines) {
  try {
    const event = JSON.parse(line);
    if (event.type === "text" && event.part && typeof event.part.text === "string") {
      text += event.part.text;
    }
  } catch {}
}
process.stdout.write(text);
' "$RAW_OUTPUT_FILE" | tee "$FINAL_OUTPUT_FILE"

echo ""
