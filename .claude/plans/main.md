# IMPLEMENTATION PLAN: MCP Server Environment Fix

**Feature:** MCP server fix — template-only: gitignore, hook fix, token docs, SETUP.md prereqs, TEMPLATE.md upgrade path enablement  
**Branch to create:** `melange/mcp-server-fix` (from `main`)  
**Complexity:** S  
**Date:** 2026-05-05

---

## Context

Two of three MCP servers (`github`, `context-creator`) fail in every new Claude Code session:
- `github`: `${GITHUB_TOKEN}` in `.mcp.json` requires the env var in the process environment at launch; no current mechanism injects it
- `context-creator`: `npx` is a `.cmd` file on Windows — not directly executable when Claude Code spawns child processes without a shell

Research confirmed (2026-05-05):
- `settings.local.json` `env` key propagates to MCP child processes via OS inheritance (empirically confirmed)
- Most robust Windows token injection: `[System.Environment]::SetEnvironmentVariable`
- `npx` fix is documentation-only — no `.mcp.json` change needed
- Pre-existing bug: `inject_claude_md.sh` runs `source .env` with `set -euo pipefail` — fails hard if `.env` absent in a fresh clone

All changes are in the Melange template repo only. Initialized projects receive the fix via the TEMPLATE.md upgrade path. `.mcp.json` and `.gitignore` are not currently listed in TEMPLATE.md — adding them to universal files is what enables the upgrade path.

**Relevant ADRs:** None existing for MCP config. Two new framework-layer ADRs required.

---

## Protected Files Check

No files in this plan appear in the Protected Files table. Melange's CLAUDE.md protected files section contains only `{{PLACEHOLDER}}` values (project uninitialized). No real guarded paths exist.

**Protected files requiring approval: none.**

---

## Branch Prerequisite

```bash
git checkout main
git pull origin main
git checkout -b melange/mcp-server-fix
```

All changes go on `melange/mcp-server-fix`.

---

## Phase 1 — Safety Gate

**Ordering constraint:** Must complete before Phase 2. Phase 2 documentation tells users to put tokens in `settings.local.json`. That file must be gitignored before any docs reference it — otherwise `git add -A` in an initialized project could commit a secret.

### Files modified

- `.gitignore` — add `.claude/settings.local.json`
- `.claude/hooks/inject_claude_md.sh` — fix `source .env`; add `GITHUB_TOKEN` warning

### Change detail

**.gitignore:** Add one line:
```
.claude/settings.local.json
```

**inject_claude_md.sh:** Two changes:

1. Replace hard `source .env` with graceful version:
   ```bash
   # Before:
   source .env
   # After:
   [ -f .env ] && source .env || true
   ```

2. Add GITHUB_TOKEN warning block (after injecting CLAUDE.md content, before final exit):
   ```bash
   if [ -f "$proj/.mcp.json" ] && grep -q 'GITHUB_TOKEN' "$proj/.mcp.json" 2>/dev/null; then
     if [ -z "${GITHUB_TOKEN:-}" ]; then
       printf "\nWARNING: GITHUB_TOKEN is not set. The 'github' MCP server will fail.\n"
       printf "Set it in .claude/settings.local.json under the 'env' key, or run:\n"
       printf "  [System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN','ghp_...','User')\n"
       printf "Then restart Claude Code. See CLAUDE.md > MCP Servers for full instructions.\n\n"
     fi
   fi
   ```
   The warning checks env var presence only — never logs the token value.

### Protected files
None.

### Completion signal
1. `git check-ignore .claude/settings.local.json` exits 0
2. Running `inject_claude_md.sh` with no `.env` file present produces no error
3. Running it with `GITHUB_TOKEN` unset produces the warning message
4. Running it with `GITHUB_TOKEN` set produces no warning

### Estimate
45 minutes

---

## Phase 2 — Documentation + Framework Manifest

### Files modified

- `CLAUDE.md` — update MCP Servers section
- `SETUP.md` — add Windows prerequisites section and token setup instructions
- `TEMPLATE.md` — add `.mcp.json` and `.gitignore` to universal files list
- `TEMPLATE_VERSION` — bump from `0.1.0` to `0.2.0`

### Change detail

**CLAUDE.md MCP Servers section:** Replace the last sentence:
```
The `github` MCP requires `export GITHUB_TOKEN=<your-token>` in your shell.
```
With a structured token setup block covering:
- Windows (recommended): `[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "ghp_...", "User")` — persists at user-environment level, inherited by all processes including VS Code, Windows Terminal, Claude Code desktop
- All platforms (file-based): `settings.local.json` under `"env"` key (file is gitignored)
- `context-creator` Windows prerequisite: Node.js must be installed via official installer so `npx` is in system-level PATH; verify with `where npx` in a plain terminal

**SETUP.md:** Add a "### Windows: MCP server prerequisites" subsection under "### 8. Verify hooks" covering:
- GitHub token: `SetEnvironmentVariable` command with explanation of why shell `export` is insufficient
- Node.js PATH: require official installer; validate with `where npx`; explain why nvm-windows/fnm PATH injection doesn't propagate to subprocess spawners
- Verification step for each

**TEMPLATE.md:** In the universal files code block, add after `TEMPLATE_VERSION`:
```
.gitignore
.mcp.json
```
Both files have no project-specific content — safe to overwrite during upgrades.

**TEMPLATE_VERSION:** Bump `0.1.0` → `0.2.0` (minor — new capability for existing users: upgrade path now covers `.gitignore` and `.mcp.json`).

### Protected files
None.

### Completion signal
1. CLAUDE.md MCP section no longer mentions `export GITHUB_TOKEN`; contains both Windows and cross-platform instructions
2. SETUP.md has the Windows prerequisites subsection with validation commands
3. TEMPLATE.md universal files list contains `.gitignore` and `.mcp.json`
4. `TEMPLATE_VERSION` reads `0.2.0`

### Estimate
1.5 hours

---

## Phase 3 — ADRs

Two framework-layer architectural decisions to document. Author after implementation since decisions are already made from research.

### Files created
- `docs/adr/melange/0005-mcp-secret-injection.md`
- `docs/adr/melange/0006-npx-mcp-command-retained.md`

### Files modified
- `docs/adr/melange/README.md` — add both entries to index

### ADR 0005 — MCP secret injection: settings.local.json + Windows user env

The decision to use `settings.local.json` `env` key as the file-based injection mechanism, with Windows `SetEnvironmentVariable` as the primary recommendation for Windows users.

Alternatives documented: shell profile `export` (lost across non-interactive launches), launcher script (per-project wrapper; cross-platform fragile), literal token in `.mcp.json` (git-tracked; rejected), `.mcp.json` gitignored (conflicts with universal-file status).

Caveat recorded: `env` key → child process propagation is empirically confirmed (mid-2025) but not explicitly documented as a guaranteed API contract. Fallback: Windows registry via `SetEnvironmentVariable`.

### ADR 0006 — Retain `npx` in `.mcp.json` (not switching to `node` + pre-install)

The decision to keep `"command": "npx"` and fix the Windows PATH issue via documentation rather than changing the command.

Alternatives documented: `node` with absolute pre-installed path (machine-specific; breaks template portability), full path to `npx.cmd` (machine-specific), global pre-install + bare name (fragile with nvm/fnm version switches), HTTP/SSE transport (operational complexity; inappropriate for local dev).

Rationale: `npx` is correct on macOS/Linux and correct on Windows with official Node.js installer. A documentation prerequisite is less disruptive than a command change that breaks cross-platform parity.

### Protected files
None.

### Completion signal
1. Both ADR files exist and are complete (decision, alternatives, rationale, date, status: Accepted)
2. `docs/adr/melange/README.md` index shows ADR 0005 and ADR 0006

### Estimate
1 hour

---

## ADR Candidates

- **MCP secret injection** (ADR 0005): Four credible alternatives with real trade-offs; empirically-confirmed behavior not in writing warrants recording the caveat and fallback
- **Retain `npx` command** (ADR 0006): Decision to fix via docs rather than code; cross-platform implications; would be expensive to revisit once documentation is distributed

---

## Simplicity Check

**Could this be one phase?** No. The gitignore entry must land before docs reference `settings.local.json`. If a developer reads the updated CLAUDE.md and adds a token before their project's `.gitignore` is updated (via the upgrade path), they could commit a secret. The phase boundary enforces the ordering constraint.

**Could Phase 2 and 3 merge?** Yes — documentation and ADRs could be one phase. Split here because ADRs are governance artifacts reviewed differently from user-facing docs. The split also allows shipping Phase 2 (docs) sooner if ADR authoring takes longer.

**Is three phases the minimum?** Yes: safety (Phase 1) → user-facing changes (Phase 2) → governance (Phase 3).

---

AWAITING HUMAN APPROVAL BEFORE PROCEEDING.
State: PROCEED, MODIFY [description], or REJECT.
