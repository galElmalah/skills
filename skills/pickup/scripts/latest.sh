#!/usr/bin/env bash
# latest.sh — print the most recent handoff note for the current project.
#
# Worktree behavior: handoffs are anchored to the *main* worktree of the repo
# (resolved via `git rev-parse --git-common-dir`), so a note written in any
# linked worktree is found from any other worktree of the same repo.
#
# Usage:
#   latest.sh            # look in <main_worktree>/.agents/handoffs/<project>/
#   latest.sh --global   # look in ~/.agents/handoffs/<project>/
#
# Output (on success):
#   <absolute path to file>
#   ---
#   <file contents>
#
# Exit codes:
#   0  — found a handoff and printed it
#   1  — directory or matching file missing (writes "no handoffs at <path>" to stderr)
#   2  — bad arguments
set -euo pipefail

global=0
for arg in "$@"; do
  case "$arg" in
    --global) global=1 ;;
    -h|--help)
      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "latest.sh: unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

# Canonical project root = main worktree of the repo (stable across worktrees).
# `git rev-parse --git-common-dir` returns the main `.git` (relative when in
# the main worktree, absolute when in a linked worktree); its parent is the
# main worktree path. Falls back to $PWD when not in a git repo.
if git_common="$(git rev-parse --git-common-dir 2>/dev/null)"; then
  project_root="$(cd "$git_common/.." && pwd -P)"
else
  project_root="$PWD"
fi
project="$(basename "$project_root")"

if [ "$global" -eq 1 ]; then
  base="$HOME/.agents/handoffs/$project"
else
  base="$project_root/.agents/handoffs/$project"
fi

if [ ! -d "$base" ]; then
  echo "no handoffs at $base" >&2
  exit 1
fi

# Filenames are YYYY-MM-DD-HHMMSS-handoff.md → lexical sort = chronological sort.
latest=""
while IFS= read -r f; do
  latest="$f"
done < <(find "$base" -maxdepth 1 -type f -name '*-handoff.md' | sort)

if [ -z "$latest" ]; then
  echo "no handoffs at $base" >&2
  exit 1
fi

printf '%s\n---\n' "$latest"
cat "$latest"
