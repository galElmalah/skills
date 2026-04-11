# Runner Adapters

The loop should not hardcode one backend.

Use a runner adapter contract:

- argument 1: `prompt_file`
- argument 2: `raw_output_file`
- argument 3: `final_output_file`

Requirements:

- write raw backend output to `raw_output_file`
- write the final assistant text to `final_output_file`
- print the final assistant text to stdout
- exit non-zero on failure

## Built-In Adapters

### Claude

- Uses `claude --print --output-format json`
- Final text is extracted from `.result`

### Codex

- Uses `codex exec --json -o <final_output_file>`
- Raw JSONL events go to the transcript
- Final text comes from the last-message file

### OpenCode

- Uses `opencode run --format json`
- Final text is reconstructed from `text` events

### Custom

Set `CUSTOM_RUNNER_SCRIPT` to an executable that follows the same 3-argument contract.

## Validation

Use `validate-runners.sh` after scaffolding to smoke-test the adapters.

If the chosen backend is not installed, the validation should fail early and visibly.
