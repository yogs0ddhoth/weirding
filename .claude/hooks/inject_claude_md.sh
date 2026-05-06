#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && source .env || true
proj="${CLAUDE_PROJECT_DIR:-$PWD}"
file="$proj/CLAUDE.md"
[ -f "$file" ] || exit 0
printf "\n### INSTRUCTIONS (from %s)\n\n" "$file"
cat "$file"
printf "\n"
if grep -q '{{' "$file" 2>/dev/null; then
  printf "\nNOTICE: This project has not been initialized ({{PLACEHOLDER}} values remain in CLAUDE.md).\n"
  printf "Run /init [describe what you want to build] to complete setup, or see SETUP.md.\n\n"
fi
if [ -f "$proj/.mcp.json" ] && grep -q '"github"' "$proj/.mcp.json" 2>/dev/null; then
  if [ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]; then
    printf "\nWARNING: GITHUB_PERSONAL_ACCESS_TOKEN is not set. The 'github' MCP server will fail.\n"
    printf "Set it in .claude/settings.local.json under the 'env' key:\n"
    printf "  {\"env\": {\"GITHUB_PERSONAL_ACCESS_TOKEN\": \"ghp_...\"}}\n"
    printf "Or persist at the Windows user-environment level:\n"
    printf "  [System.Environment]::SetEnvironmentVariable('GITHUB_PERSONAL_ACCESS_TOKEN','ghp_...','User')\n"
    printf "Then restart Claude Code. See CLAUDE.md > MCP Servers for full instructions.\n\n"
  fi
fi
