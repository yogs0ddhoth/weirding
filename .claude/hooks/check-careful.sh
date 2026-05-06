#!/usr/bin/env bash
# PreToolUse hook: intercept destructive Bash commands and ask for confirmation.
# Outputs {"permissionDecision":"ask",...} to stdout when a dangerous pattern is detected.
# Exit 0 (no output) to allow the command through without prompting.
set -euo pipefail

input=$(cat)

# Only intercept Bash tool calls
printf '%s' "$input" | grep -q '"Bash"' || exit 0

# match: returns 0 if $input contains the pattern
match() {
  printf '%s' "$input" | grep -qiE "$1" 2>/dev/null
}

warning=""

# Broad rm -rf (allow rm -rf on safe targets like node_modules, .next, dist, __pycache__)
if match 'rm[[:space:]]+-[a-zA-Z]*r[a-zA-Z]*f[[:space:]]+(\/[^n]|~|\.\.|\*|\/\*)' && \
   ! match 'rm[[:space:]]+-[a-zA-Z]*rf[[:space:]]+(node_modules|\.next|dist|build|__pycache__|\.cache|tmp|temp)'; then
  warning="rm -rf on broad path"
fi

# Force push — allow if clearly scoped to a non-main branch already stated in the command
if [ -z "$warning" ] && match 'git[[:space:]]+push[[:space:]].*(-f[^i]|--force[^-]|--force$)'; then
  warning="git force push"
fi

if [ -z "$warning" ] && match 'git[[:space:]]+reset[[:space:]]+--hard'; then
  warning="git reset --hard"
fi

if [ -z "$warning" ] && match 'git[[:space:]]+clean[[:space:]]+-[a-zA-Z]*f'; then
  warning="git clean -f"
fi

if [ -z "$warning" ] && match '\b(DROP|TRUNCATE)[[:space:]]+(TABLE|DATABASE|SCHEMA)\b'; then
  warning="destructive SQL (DROP/TRUNCATE)"
fi

if [ -z "$warning" ] && match 'kubectl[[:space:]]+(delete|destroy)\b'; then
  warning="kubectl delete/destroy"
fi

if [ -z "$warning" ] && match 'terraform[[:space:]]+destroy\b'; then
  warning="terraform destroy"
fi

if [ -z "$warning" ] && match 'dd[[:space:]]+if=/dev/(zero|urandom)[[:space:]].*of=/dev/[a-z]'; then
  warning="dd to block device"
fi

# Pipe to shell (curl/wget | bash pattern)
if [ -z "$warning" ] && match '(curl|wget)[[:space:]].*\|[[:space:]]*(bash|sh|zsh)\b'; then
  warning="pipe to shell (curl/wget | bash)"
fi

if [ -n "$warning" ]; then
  printf '{"permissionDecision":"ask","reason":"Destructive command detected (%s) — review the full command before proceeding"}\n' "$warning"
fi

exit 0
