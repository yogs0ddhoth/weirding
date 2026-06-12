# weirding

@AGENTS.md
@ETHOS.md
@README.md

## Project

weirding is a production-grade Python library for XML ↔ Pydantic v2 conversion. It provides `compile(xml)` to convert XML schema documents — using a plain-attribute annotation convention or XSD — into a JSON Schema IR dict, `define_model(xml)` to compile that IR into Pydantic v2 `BaseModel` classes, `parse(xml, model)` to validate and bind XML data against those models, and `to_xml(instance)` for round-trip serialization. The reverse edges `to_schema(model)` (model → IR) and `dump_xml(ir)` (IR → XML schema document) close the XML ↔ JSON Schema ↔ Pydantic loop for genuine 3-way fungibility (ADR-0012). The XML schema you author once becomes a single source of truth with first-class structured-output interop across the ecosystem: `to_json_schema()` exports provider-ready schemas for OpenAI/Azure, Databricks `ai_query`, and open-weight runtimes (vLLM/Ollama); generated models drop straight into LangChain/LangGraph; and prompt utilities (`prompt.to_template()`, `prompt.format_error()`, `RetryContext`) drive any provider's retry loop, Claude included. Designed for Databricks, Kubernetes, serverless, and edge environments.

## Commands

Skills read this table to discover project-specific commands. Keep values exact and
runnable — no prose, no approximations.

| Command    | Value                          |
|------------|--------------------------------|
| Build      | uv sync --extra dev            |
| Test       | uv run pytest                  |
| Lint       | uv run ruff check .            |
| Format     | uv run ruff format .           |
| Type Check | uv run pyright                 |
| Deploy     | uv publish                     |

## Development Workflow [UNIVERSAL]

### Agent-Based Development (MANDATORY)

The main conversation is for ORCHESTRATION ONLY. Never execute builds, long tests, or
iterative debugging directly in the top-level session. This burns token context and leads
to session exhaustion.

ALWAYS dispatch to agents:
- Build verification and compilation checks
- Test runs and performance profiling
- Log analysis and quality evaluation
- Code exploration and codebase research
- Any task that may require multiple iterations or produce verbose output

The orchestrator session should only:
- Plan and decompose work into agent-dispatchable tasks
- Review agent reports and synthesize findings
- Make high-level decisions based on agent results
- Coordinate multiple parallel agent investigations
- Communicate summaries and next steps to the user

Anti-pattern (NEVER DO THIS):
```
# Do not run long builds or test suites in the main session
uv run pytest 2>&1 | head ...
```

Correct pattern:
```
# Dispatch to an agent
Agent(prompt="Run the test suite, report failures and their root cause")
```

### Feature Branches (REQUIRED)

Never push directly to main. Always:

```bash
git checkout main
git pull origin main
git checkout -b feature-name
# ... do work ...
git push -u origin feature-name
gh pr create --title "Brief description" --body "Details"
```

When developing Melange itself (skills, hooks, governance files — the framework layer), use
the `melange/` prefix: `melange/feature-name`. Use standard type prefixes (`feat/`, `fix/`,
etc.) for initialized-project work.

### Commit Convention [UNIVERSAL]

All commits on deployable branches must follow the Conventional Commits format. The type
table, format specification, and version bump rules are documented in the **Commit
messages** section of `README.md` — that is the canonical source of truth. Do not
duplicate the table here.

The `/quality` full gate validates commit messages and reports the implied version bump.
The `/changelog` skill reads commit types to categorize changes automatically.

## Protected Files [PROJECT]

Files that require explicit approval before modification. Agents check this list before
any change.

### Tier 1 — Ask before ANY change

| File | Reason |
|------|--------|
| `src/weirding/_parser.py` | Secure XML parsing — XMLParser configuration is the primary security boundary |
| `src/weirding/__init__.py` | Public API surface — any change here is a potential breaking change |

### Tier 2 — Explain why alternative approaches are insufficient

| File | Reason |
|------|--------|
| `src/weirding/_schema.py` | r: namespace → JSON Schema IR pipeline — hot path for all schema compilation |
| `src/weirding/_models.py` | JSON Schema → Pydantic model engine — changes risk silent model generation regressions |

## Quality Requirements [UNIVERSAL]

### Zero-Warning Policy

Every build must be completely clean. Zero warnings, zero errors. This is non-negotiable.
When you observe warnings or errors during any build, fix them before proceeding. Do not
continue with a broken build.

Honest fixes only. Do NOT suppress warnings dishonestly:
- Suppression annotations are NOT acceptable for code that should be removed or actually used
- These annotations hide problems instead of fixing them

### Testing Integrity

NEVER fake a passing test. If a test fails, it fails. Do not:
- Weaken thresholds or assertions to match broken behavior
- Accept "task completed" as proof of "task completed correctly"
- Disable flaky tests without root-cause investigation

If a test cannot pass because the underlying code is broken: fix the code.

## Privacy Requirements [UNIVERSAL]

These are architectural constraints, not optional features.

- NO logging of raw user inputs (queries, form data, messages) associated with any identifier
- NO fingerprinting — no client fingerprinting, timing attacks, or covert channel leakage
- NO third-party requests from the UI — no external fonts, analytics, or CDN resources
- NO persistent session state beyond what the user explicitly requests
- Any code path that handles user data requires a privacy review comment

Violation of privacy requirements blocks PR merge regardless of other quality.

## Project Memory and ADRs [UNIVERSAL]

### Memory Priority

| Source | Answers | Update when |
|--------|---------|-------------|
| `.claude/memory/MEMORY.md` | What is true NOW — current phase, confirmed standards, active constraints | Any session that changes project state |
| `docs/adr/` | WHY a decision was made — rationale, trade-offs, alternatives | Any significant architectural decision |

`.claude/memory/MEMORY.md` is the primary source. When the two conflict, MEMORY.md governs
current behavior. ADRs are never deleted or edited retroactively — they are append-only.

### When to Create an ADR

Any decision involving:
- Trade-offs between credible design alternatives
- Cross-component impact
- Changes to protected files
- Anything that would take significant effort to reverse

Use `/adr` to author one. Use `/plan` when in doubt — the planning skill flags ADR candidates.

## Lifecycle

| Phase | Command | Purpose |
|-------|---------|---------|
| Initialize | `/init` | One-time setup: ideation, fill all placeholders, generate roadmap, configure agent permissions |
| Ideate | `/ideate` | Scope the feature, define success criteria, estimate complexity |
| Research | `/research` | Find authoritative answers before committing to an approach |
| Plan | `/plan` | Write a phase-by-phase plan; get human approval before coding |
| Develop | (agent dispatch) | Implement per the approved plan |
| Quality | `/quality` | Pre-commit gate: lint, build, test, privacy check |
| ADR | `/adr` | Document significant architectural decisions |
| Ship | `/ship` | Pre-deploy checklist, human approval, post-deploy verification |

## Utility Commands [UNIVERSAL]

Commands available at any time, not phase-gated.

| Command | Purpose |
|---------|---------|
| `/review` | Multi-specialist code review (security, performance, migrations, API contract, maintainability, testing, red-team) |
| `/configure` | Modify Claude configuration (skills, hooks, commands, permissions) with UNIVERSAL/PROJECT guardrails |
| `/context-save` | Save session state to `.claude/context/<branch>.md` for cross-session restore |
| `/context-restore` | Restore session context for the current branch and cross-check with git |
| `/security` | Security audit — secrets, CVEs, OWASP Top 10, STRIDE threat model |
| `/canary` | Post-deploy health check via curl endpoint verification |
| `/benchmark` | Build and bundle performance regression detection vs. saved baseline |
| `/retro` | Weekly engineering retrospective from git history |
| `/changelog` | Write user-facing CHANGELOG entry for recent changes |
| `/debug` | Systematic document-driven debugging |
| `/test` | Write or audit tests for a component |
| `/careful` | Explain the always-on destructive command interception hook |

## MCP Servers [UNIVERSAL]

Three MCP servers are configured in `.mcp.json` and available in every Claude Code session:

| Server | Purpose |
|--------|---------|
| `context-creator` | Codebase analysis — `analyze_local`, `analyze_remote`, `semantic_search`, `diff`, `search` |
| `github` | GitHub API — PRs, issues, reviews, checks (requires `GITHUB_PERSONAL_ACCESS_TOKEN` env var) |
| `git` | Local git operations — log, blame, diff, status with structured output |

Use `context-creator` when researching unfamiliar codebases, analyzing remote repositories for patterns, or performing semantic search across large source trees. Requires no authentication.

### Setting up the `github` MCP token

The `github` MCP requires `GITHUB_PERSONAL_ACCESS_TOKEN` (a personal access token with
`repo` scope). A shell `export` is insufficient — Claude Code spawns MCP servers as child
processes that do not inherit interactive shell state.

**Important:** use the exact env var name `GITHUB_PERSONAL_ACCESS_TOKEN`. The `.mcp.json` has no `env` block — the token must be in the
process environment directly.

**Windows (recommended):** Persist the token at the user-environment level so all processes
including VS Code, Windows Terminal, and Claude Code desktop inherit it automatically:

```powershell
[System.Environment]::SetEnvironmentVariable("GITHUB_PERSONAL_ACCESS_TOKEN", "ghp_...", "User")
```

Then restart Claude Code.

**All platforms (file-based):** Add the token to `.claude/settings.local.json` (gitignored):

```json
{
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
  }
}
```

### Setting up `context-creator` on Windows

`context-creator` runs via `npx`. On Windows, `npx` is a `.cmd` wrapper that is only
executable when the PATH is inherited correctly. Ensure Node.js was installed via the
**official installer** (nodejs.org) — not nvm-windows or fnm — so `npx` lands in the
system-level PATH. Verify with:

```powershell
where npx
```

If `where npx` returns a path, `context-creator` will work. If not, reinstall Node.js from
nodejs.org and restart your terminal and Claude Code.
