# ADR 0006 — Retain `npx` in `.mcp.json` (Not Switching to `node` + Pre-install)

**Status:** Accepted  
**Date:** 2026-05-05

---

## Context

`context-creator` is configured in `.mcp.json` as:

```json
"command": "npx",
"args": ["-y", "context-creator-mcp@latest"]
```

On Windows, `npx` is a `.cmd` wrapper file. When Claude Code spawns MCP processes,
it resolves commands via the inherited PATH. If Node.js was installed via the official
installer (nodejs.org), `npx` is in the system-level PATH and works correctly. If
installed via nvm-windows or fnm, the PATH injection is session-scoped — it does not
propagate to subprocess spawners like Claude Code desktop.

The failure mode: `context-creator` silently fails to start because `npx` resolves to
nothing, with no obvious error surfaced to the user.

Four alternative command configurations were evaluated.

---

## Decision

**Retain `"command": "npx"`** and fix the Windows failure via documentation (require
official nodejs.org installer; validate with `where npx`).

This is correct behavior on macOS/Linux and correct on Windows when Node.js is installed
via the official installer. The `.mcp.json` format is a template-distributed universal
file; a command change that hardcodes a platform-specific path would break cross-platform
parity and require every initialized project to maintain their own override.

---

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| `"command": "node"` with pre-installed package | Requires a pre-install step and an absolute path to the package entry point — both machine-specific. Breaks template portability entirely. |
| Full path to `npx.cmd` (e.g. `C:\Program Files\nodejs\npx.cmd`) | Machine-specific. Hardcoding breaks the template for any user with a different Node.js install location. |
| Global pre-install + bare command name | `npm install -g context-creator-mcp` works, but is fragile with nvm/fnm version switches (the globally-installed binary disappears when the active Node version changes). |
| HTTP/SSE transport instead of stdio | Adds operational complexity (port management, process lifecycle) inappropriate for a local development tool. No benefit over npx for this use case. |

---

## Consequences

- SETUP.md documents the Node.js installer prerequisite with a validation command (`where npx`).
- CLAUDE.md documents the same prerequisite in the MCP Servers section.
- Users on nvm-windows or fnm who encounter the failure will be directed to reinstall via nodejs.org. This is a one-time migration cost.
- If a future Claude Code release adds `cmd`-aware command resolution on Windows, this decision can be revisited — `npx` remains correct and no `.mcp.json` change would be needed.
