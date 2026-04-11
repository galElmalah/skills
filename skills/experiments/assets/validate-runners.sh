#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_DIR="$SCRIPT_DIR/runners"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

PROMPT_FILE="$TMP_DIR/prompt.txt"
echo "Reply with READY and nothing else." > "$PROMPT_FILE"

run_check() {
  local name="$1"
  local runner="$2"
  local raw="$TMP_DIR/$name.raw"
  local final="$TMP_DIR/$name.txt"

  echo "[validate] $name"
  "$runner" "$PROMPT_FILE" "$raw" "$final" > "$TMP_DIR/$name.stdout"
  if ! grep -qx 'READY' "$final"; then
    echo "[validate] $name failed: expected READY in $final" >&2
    echo "[validate] raw output:" >&2
    sed -n '1,120p' "$raw" >&2 || true
    exit 1
  fi
  echo "[validate] $name ok"
}

run_check "claude" "$RUNNER_DIR/claude.sh"
run_check "codex" "$RUNNER_DIR/codex.sh"
run_check "opencode" "$RUNNER_DIR/opencode.sh"

CUSTOM_FAKE="$TMP_DIR/custom-runner.sh"
cat > "$CUSTOM_FAKE" <<'EOF'
#!/bin/bash
set -euo pipefail
PROMPT_FILE="$1"
RAW_OUTPUT_FILE="$2"
FINAL_OUTPUT_FILE="$3"
printf 'custom raw for: %s\n' "$(cat "$PROMPT_FILE")" > "$RAW_OUTPUT_FILE"
printf 'READY' > "$FINAL_OUTPUT_FILE"
printf 'READY\n'
EOF
chmod +x "$CUSTOM_FAKE"

CUSTOM_RUNNER_SCRIPT="$CUSTOM_FAKE" run_check "custom" "$RUNNER_DIR/custom.sh"

echo "[validate] all runners passed"
