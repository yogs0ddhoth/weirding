# Project Setup

This project was scaffolded from Melange. Before writing any code, complete
initialization below. Both paths produce an identical result — choose one.

---

## Git History

If you **cloned** this repository directly (rather than using GitHub's "Use this template"
button), your project's git log contains Melange's own development commits. These are
framework-internal and unrelated to your project.

To start with a clean history before your first commit:

```bash
git checkout --orphan clean-main
git add -A
git commit -m "chore: initialize project from Melange"
git branch -D main
git branch -m main
```

If you used "Use this template" on GitHub, your history is already clean — skip this.

---

## Path 1 — Claude-assisted (recommended)

**Prerequisites:** Claude Code installed and open in this directory.

**Step 1.** Run:

```
/init [describe what you want to build in one or two sentences]
```

Example:

```
/init a REST API for tracking personal finances, built in Go with PostgreSQL
```

**Step 2.** Answer Claude's follow-up questions about commands and file paths (asked all
at once, not one at a time).

**Step 3.** When Claude reports `INIT COMPLETE`, delete this file.

Claude will run ideation on your description, ask for exact build/test/lint commands and
protected file paths, fill in all `{{PLACEHOLDER}}` values across CLAUDE.md, README.md,
MEMORY.md, and the roadmap, update `.claude/settings.json` with agent permissions, and
run a verification gate before reporting complete.

---

## Path 2 — Manual

Complete these steps in order.

### 1. Ideate first

Before filling in any placeholder, write a one-paragraph problem statement: what are you
building, who uses it, and what is its primary capability. This becomes your
`{{PROJECT_DESCRIPTION}}` and the basis for your roadmap phases.

If you have Claude Code, run `/ideate [your project description]` to produce a structured
scope document. Use its "Problem" and "Scope" output as your description and roadmap.

### 2. Wire up git

```bash
git remote remove origin
git remote add origin <your-new-repo-url>
git push -u origin main
```

### 3. Fill in `CLAUDE.md`

Replace every `{{PLACEHOLDER}}` with real values. Delete the framework instruction comment
block at the top when done.

| Placeholder | What to put |
|-------------|-------------|
| `{{PROJECT_NAME}}` | Short project name |
| `{{PROJECT_DESCRIPTION}}` | One paragraph from your ideation output |
| `{{BUILD_COMMAND}}` | Exact command, e.g. `npm run build` |
| `{{TEST_COMMAND}}` | Exact command, e.g. `npm test` |
| `{{LINT_COMMAND}}` | Exact command, e.g. `npm run lint` |
| `{{FORMAT_COMMAND}}` | Exact command, e.g. `npm run format` |
| `{{DEPLOY_COMMAND}}` | Exact command, or remove row if not applicable |
| `{{DOCS_COMMAND}}` | Exact command, or remove row if not applicable |
| `{{AUTH_FILE}}` | Path to auth/session code, or **remove the row** if N/A |
| `{{CORE_DATA_MODEL_FILE}}` | Path to core data model, or **remove the row** if N/A |
| `{{PRIVACY_FILE}}` | Path to privacy-sensitive code, or **remove the row** if N/A |
| `{{HOT_PATH_FILE}}` | Path to performance-critical code, or **remove the row** if N/A |
| `{{MIGRATION_FILE}}` | Path to schema migrations, or **remove the row** if N/A |

Protected file rows should be **removed entirely** when N/A — do not leave an "N/A" value
in the table, as agents treat every row as a real file path.

### 4. Update `.claude/settings.json`

Add a `permissions` block with the exact commands from your Commands table:

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run build)",
      "Bash(npm test)",
      "Bash(npm run lint)",
      "Bash(npm run format)"
    ]
  },
  "hooks": { "...existing hooks..." }
}
```

Use exact command strings — no wildcards. Omit entries for any command that is N/A.
Git read commands (`git diff`, `git log`, `git status`) are auto-allowed and do not
need entries here.

### 5. Fill in `.claude/memory/MEMORY.md`

- Replace `{{LANGUAGE_AND_STACK}}` with your stack (e.g., `Go 1.22, PostgreSQL 15`)
- Replace `{{CURRENT_PHASE}}` with `Phase 00 — Foundation (not started)`
- Add `**Framework version:** <contents of TEMPLATE_VERSION>` to the Core Facts section
- Add any non-obvious constraints discovered during ideation to the rules section

### 6. Fill in `docs/planning/PROJECT_ROADMAP.md`

Replace `{{PHASE_01}}` etc. with phase descriptions from your ideation scope. Phase 00
(Foundation) is already defined. Add 2–4 more phases based on the complexity estimate
from ideation. Remove unused `{{PHASE_XX}}` rows.

### 7. Fill in `README.md`

Replace the `{{PROJECT_NAME}}` h1 and `{{PROJECT_DESCRIPTION}}` paragraph. Remove the
"New to Melange?" notice line. Fill in Getting Started as the project develops.

### 8. Verify hooks

On macOS/Linux:

```bash
chmod +x .claude/hooks/*.sh
```

On Windows: hooks run via Git Bash — no chmod needed.

Verify by opening Claude Code and sending any message. You should see
`### INSTRUCTIONS (from .../CLAUDE.md)` in the response context.

### Windows: MCP server prerequisites

Two of the three MCP servers need one-time setup on Windows.

#### `github` MCP — GITHUB_PERSONAL_ACCESS_TOKEN

The MCP server requires a GitHub personal access token with `repo` scope set as
`GITHUB_PERSONAL_ACCESS_TOKEN`. A shell `export` does not reach Claude Code's child
processes on Windows. Use the Windows user-environment registry instead — it propagates
to all processes including VS Code, Windows Terminal, and Claude Code desktop:

```powershell
[System.Environment]::SetEnvironmentVariable("GITHUB_PERSONAL_ACCESS_TOKEN", "ghp_...", "User")
```

Restart Claude Code after setting. Verify the token is live:

```powershell
[System.Environment]::GetEnvironmentVariable("GITHUB_PERSONAL_ACCESS_TOKEN", "User")
```

Alternatively, add it to `.claude/settings.local.json` (gitignored — safe to write secrets
here):

```json
{
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
  }
}
```

Note: use `GITHUB_PERSONAL_ACCESS_TOKEN`
exactly. The `.mcp.json` file has no `env` block for the github server; the token must be
in the process environment directly.

#### `context-creator` MCP — Node.js PATH

`context-creator` runs via `npx`. On Windows, `npx` is a `.cmd` file that only resolves
correctly when Node.js is in the system-level PATH. Install Node.js from **nodejs.org**
(the official installer) — do not use nvm-windows or fnm, as their PATH injection is
session-scoped and does not propagate to subprocess spawners like Claude Code.

Verify after installing:

```powershell
where npx
```

If `where npx` returns a path (e.g. `C:\Program Files\nodejs\npx.cmd`), `context-creator`
will work. If not, reinstall Node.js from nodejs.org and open a new terminal before
retrying.

### 9. Delete this file

```bash
rm SETUP.md
```

---

## Initialization Checklist

Use this to confirm init is complete before starting development.

- [ ] No `{{PLACEHOLDER}}` strings remain in CLAUDE.md, README.md, MEMORY.md, or PROJECT_ROADMAP.md
- [ ] `.claude/settings.json` has a non-empty `permissions.allow` array
- [ ] `.claude/memory/MEMORY.md` Core Facts section has real values (stack, current phase, framework version)
- [ ] `docs/planning/PROJECT_ROADMAP.md` has real phase descriptions
- [ ] Git remote is set (`git remote -v` shows your repo URL)
- [ ] Hooks verified (INSTRUCTIONS header appears in Claude Code)
- [ ] This file deleted
