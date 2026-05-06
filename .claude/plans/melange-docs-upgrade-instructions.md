# IMPLEMENTATION PLAN: Document verified MCP token injection pattern

## Context

Today's debugging session revealed that the `${GITHUB_TOKEN}` interpolation in `.mcp.json`'s `env` block does not work — Claude Code passes the literal string to the MCP server process rather than resolving the variable. The fix: remove the `env` block from `.mcp.json` entirely so the github server inherits the full process environment, and set `GITHUB_PERSONAL_ACCESS_TOKEN` directly in `settings.local.json`. Both changes are already committed.

The documentation across multiple files still describes the old (broken) pattern: `GITHUB_TOKEN` as the user-facing env var name, with `.mcp.json` performing the mapping to `GITHUB_PERSONAL_ACCESS_TOKEN`. That mapping no longer exists. Every doc reference, the session-start warning hook, and `settings.local.json` itself must be updated to use `GITHUB_PERSONAL_ACCESS_TOKEN` only.

Relevant prior art: ADR 0005 (`docs/adr/melange/0005-mcp-secret-injection.md`) documents the injection mechanism but does not capture the interpolation failure, the `.mcp.json` env-block removal, or the env var rename.

---

## Phase 1 — Remove GITHUB_TOKEN, update all docs and the session-start hook

### Files modified

| File | Change |
|------|--------|
| `.claude/settings.local.json` | Remove `GITHUB_TOKEN` entry — only `GITHUB_PERSONAL_ACCESS_TOKEN` should remain |
| `docs/adr/melange/0005-mcp-secret-injection.md` | Append "Amendment (2026-05-05)" — document interpolation failure, `.mcp.json` env-block removal, rename from `GITHUB_TOKEN` to `GITHUB_PERSONAL_ACCESS_TOKEN`, and explicitly supersede the Consequences item referencing `GITHUB_TOKEN` in the hook warning |
| `docs/adr/melange/README.md` | Add "Amended" note to ADR 0005 index row |
| `CLAUDE.md` | MCP Servers section: replace `GITHUB_TOKEN` → `GITHUB_PERSONAL_ACCESS_TOKEN` throughout; note `.mcp.json` has no env block |
| `README.md` | Same replacement (separate file; carries old references) |
| `SETUP.md` | Same replacement in Windows prerequisites section |
| `AGENTS.md` | Update MCP table `github` row to reference `GITHUB_PERSONAL_ACCESS_TOKEN` |
| `.claude/hooks/inject_claude_md.sh` | Change detection: grep for `"github"` in `.mcp.json` instead of `GITHUB_TOKEN`; check `GITHUB_PERSONAL_ACCESS_TOKEN` not `GITHUB_TOKEN`; update warning text and remediation instructions |

### Protected files
None — Protected Files table contains only `{{PLACEHOLDER}}` entries.

### ADR candidates
None — this is a documentation amendment to an existing decision, not a new architectural choice.

### Completion signal
1. `grep -r 'GITHUB_TOKEN' CLAUDE.md README.md SETUP.md AGENTS.md .claude/hooks/inject_claude_md.sh .claude/settings.local.json` returns no matches
2. `grep -r 'GITHUB_PERSONAL_ACCESS_TOKEN' CLAUDE.md SETUP.md .claude/settings.local.json` returns matches in all three
3. The inject hook emits the warning when `GITHUB_PERSONAL_ACCESS_TOKEN` is unset; suppresses it when set
4. ADR 0005 has a visible "Amendment" section at the bottom that explicitly supersedes the `GITHUB_TOKEN` Consequences item

### Estimate
30 minutes

---

## Simplicity Check

Single phase — all changes are documentation plus one gitignored config file. No build dependencies between any of these files. A two-phase split would add ceremony without reducing risk.

---

AWAITING HUMAN APPROVAL BEFORE PROCEEDING.
State: PROCEED, MODIFY [description], or REJECT.
