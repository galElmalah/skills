#!/bin/bash
set -euo pipefail

PROMPT_FILE="${1:?prompt file required}"
RAW_OUTPUT_FILE="${2:?raw output file required}"
FINAL_OUTPUT_FILE="${3:?final output file required}"
CODEX_BIN="${CODEX_BIN:-codex}"
WORKSPACE_ROOT="${EXPERIMENT_WORKSPACE_ROOT:-$(pwd)}"
LAST_STREAMED_FILE="$(mktemp)"
STREAM_PARSER_FILE="$(mktemp)"

cleanup() {
  rm -f "$LAST_STREAMED_FILE"
  rm -f "$STREAM_PARSER_FILE"
}
trap cleanup EXIT

mkdir -p "$(dirname "$RAW_OUTPUT_FILE")" "$(dirname "$FINAL_OUTPUT_FILE")"
RAW_OUTPUT_FILE="$(cd "$(dirname "$RAW_OUTPUT_FILE")" && pwd)/$(basename "$RAW_OUTPUT_FILE")"
FINAL_OUTPUT_FILE="$(cd "$(dirname "$FINAL_OUTPUT_FILE")" && pwd)/$(basename "$FINAL_OUTPUT_FILE")"
WORKSPACE_ROOT="$(cd "$WORKSPACE_ROOT" && pwd)"

cat > "$STREAM_PARSER_FILE" <<'PY'
import json
import pathlib
import sys

raw_path = pathlib.Path(sys.argv[1])
last_streamed_path = pathlib.Path(sys.argv[2])
last_message = ""

with raw_path.open("w", encoding="utf-8") as raw_file:
    for line in sys.stdin:
        raw_file.write(line)
        raw_file.flush()

        stripped = line.rstrip("\n")
        try:
            payload = json.loads(stripped)
        except Exception:
            if stripped:
                sys.stdout.write(stripped + "\n")
                sys.stdout.flush()
            continue

        item = payload.get("item") or {}
        event_type = payload.get("type")

        if event_type == "item.started" and item.get("type") == "command_execution":
            command = item.get("command")
            if command:
                sys.stdout.write(f"[cmd] {command}\n")
                sys.stdout.flush()
        elif event_type == "item.completed" and item.get("type") == "agent_message":
            text = (item.get("text") or "").strip()
            if text:
                last_message = text
                sys.stdout.write(text + "\n")
                sys.stdout.flush()
        elif event_type == "error":
            message = payload.get("message") or payload.get("error") or stripped
            if message:
                sys.stdout.write(f"[error] {message}\n")
                sys.stdout.flush()

last_streamed_path.write_text(last_message, encoding="utf-8")
PY

stream_codex_output() {
  python3 "$STREAM_PARSER_FILE" "$RAW_OUTPUT_FILE" "$LAST_STREAMED_FILE"
}

(
  cd "$WORKSPACE_ROOT"
  "$CODEX_BIN" exec \
    --skip-git-repo-check \
    --dangerously-bypass-approvals-and-sandbox \
    --json \
    -o "$FINAL_OUTPUT_FILE" \
    "$(cat "$PROMPT_FILE")"
) | stream_codex_output

if [ -f "$FINAL_OUTPUT_FILE" ]; then
  final_text="$(cat "$FINAL_OUTPUT_FILE")"
  last_streamed="$(cat "$LAST_STREAMED_FILE" 2>/dev/null || true)"
  if [ -n "$final_text" ] && [ "$final_text" != "$last_streamed" ]; then
    printf '%s\n' "$final_text"
  fi
fi
echo ""
