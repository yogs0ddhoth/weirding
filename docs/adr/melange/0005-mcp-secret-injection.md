# ADR 0005 — MCP Secret Injection: settings.local.json + Windows User Environment

**Status:** Accepted  
**Date:** 2026-05-05

---

## Context

Three MCP servers are bundled in `.mcp.json`. The `github` server requires a
`GITHUB_PERSONAL_ACCESS_TOKEN` env var to authenticate. Four injection mechanisms were
evaluated.

The previous documentation recommended `export GITHUB_TOKEN=<token>` in the shell profile.
Empirical testing revealed this is unreliable: Claude Code (desktop) and VS Code extensions
launch MCP child processes via their own spawners, which do not inherit interactive-shell
state on Windows. The token set in a PowerShell or bash profile does not propagate to these
processes.

---

## Decision

**Primary recommendation for Windows:** `[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "ghp_...", "User")`. This writes the token to the Windows user-environment registry hive (`HKCU\Environment`), which is inherited by all new processes — including Claude Code desktop, VS Code extensions, and Windows Terminal — without requiring a shell restart.

**Cross-platform file-based fallback:** `.claude/settings.local.json` with an `"env"` key. Claude Code propagates values in this key to MCP child processes via OS-level environment inheritance at spawn time. The file is gitignored (as of this PR) so tokens are never committed.

The `env` key → child-process propagation behavior was empirically confirmed in mid-2025 but is not explicitly documented as a guaranteed API contract in the Claude Code public docs. The Windows registry method is the more durable guarantee because it operates at the OS level, independent of Claude Code internals.

---

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Shell profile `export GITHUB_TOKEN=...` | Not inherited by non-interactive process spawners (VS Code, Claude Code desktop) on Windows. Works on macOS/Linux for terminal-launched sessions only. |
| Launcher wrapper script | Requires per-project wrapper; cross-platform fragile; adds operational overhead. |
| Literal token in `.mcp.json` | `.mcp.json` is a universal file (git-tracked, template-distributed). A literal token would be committed and published. Rejected outright. |
| Gitignore `.mcp.json` | `.mcp.json` contains no secrets — only server definitions. Gitignoring it would prevent the upgrade path from delivering MCP server improvements to initialized projects. |

---

## Consequences

- `.claude/settings.local.json` is now gitignored. Existing projects that committed this file with `enabledMcpjsonServers` must migrate that setting to `settings.json` (tracked).
- The hook `inject_claude_md.sh` emits a warning when `GITHUB_TOKEN` is absent at session start, so users know immediately why the github MCP server failed.
- The `env` key behavior should be re-evaluated if Claude Code changes its MCP spawn model. The Windows registry approach is the durable fallback.

---

## Amendment — 2026-05-05

**Finding:** The `${GITHUB_TOKEN}` interpolation in the `.mcp.json` `env` block does not work. Claude Code passes the literal string `${GITHUB_TOKEN}` to the MCP server process rather than resolving it. Confirmed by: auth failure with a valid token in `settings.local.json` + zero error output from the server (indicating it received a malformed credential string, not an empty one).

**Fix applied:**
1. Removed the `env` block from the `github` entry in `.mcp.json`. The server now inherits the full process environment from Claude Code at spawn time.
2. `settings.local.json` must set `GITHUB_PERSONAL_ACCESS_TOKEN` directly — the exact name the `@modelcontextprotocol/server-github` package reads. `GITHUB_TOKEN` is not an accepted alias.

**Supersedes:** The Consequences item "The hook `inject_claude_md.sh` emits a warning when `GITHUB_TOKEN` is absent" is superseded. The hook now detects the github MCP server by searching for `"github"` in `.mcp.json` and checks `GITHUB_PERSONAL_ACCESS_TOKEN` instead. All user-facing documentation uses `GITHUB_PERSONAL_ACCESS_TOKEN` throughout.

**Constraint for future MCP servers:** Do not use `${VAR}` syntax in `.mcp.json` `env` blocks — interpolation does not work. Set secrets directly in `settings.local.json` or the Windows user-environment registry.
