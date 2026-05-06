#!/usr/bin/env bash
set -euo pipefail
proj="${CLAUDE_PROJECT_DIR:-$PWD}"
cd "$proj" 2>/dev/null || exit 0
if git diff --cached --quiet 2>/dev/null && git diff --quiet 2>/dev/null; then
  exit 0
fi
printf "\n[Quality Reminder] Uncommitted changes detected.\n"
printf "Run your project's quality gate before committing.\n"
printf "Check the Commands table in CLAUDE.md for the exact command.\n\n"
