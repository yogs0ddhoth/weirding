# Melange Agent Development Guide

Operational guide for agents working on this project. Read this before making any code
changes.

## Project Memory

Canonical location: `.claude/memory/MEMORY.md` in this repository.

This file is git-tracked and loaded for every agent session. When you learn something
worth persisting across sessions — a design decision, a confirmed standard, a non-obvious
constraint — update this file directly using the Write or Edit tool. Do not rely on any
external memory system.

What belongs here:
- Corrections to phase status or current branch
- Confirmed production standards discovered during implementation
- Non-obvious constraints that would surprise a future agent
- Anything a future agent would need to avoid re-litigating

What does NOT belong here: code patterns, file paths, git history, or anything already
in ADRs or CLAUDE.md.

## README as Human Entrypoint

`README.md` is the human entrypoint to every source of truth in this repository — both
project-level (commands, ADRs, roadmap) and framework-level (ETHOS.md, TEMPLATE.md,
TEMPLATE_VERSION). It is injected into every Claude session via `@README.md` in CLAUDE.md.

**Rules when modifying the framework:**

- Every governing file must appear in README.md's **Key files** table before it is
  referenced from CLAUDE.md, AGENTS.md, or any skill.
- New sources of truth are documented in README.md first. Cross-references in other files
  point back to README.md — they do not duplicate the content.
- If you add a skill, hook, agent, or governing file and README.md does not mention it,
  that is a documentation gap. Fix it before committing.

This principle applies equally to initialized projects: any new governing document a
project introduces (security policy, API contract, ops runbook) must be registered in
README.md before being referenced elsewhere.

## Branch Naming

When working on Melange itself, use the `melange/` prefix for all branches:
`melange/feature-name`. This distinguishes framework-layer development from
initialized-project work, which uses standard prefixes (`feat/`, `fix/`, etc.).

## Before Starting Any Task

1. Read `.claude/memory/MEMORY.md` for current project state and confirmed standards
2. Read `docs/adr/README.md` and the ADRs relevant to what you are touching
3. Read the relevant section of `CLAUDE.md`
4. Check if the affected files are in the Protected Files list in `CLAUDE.md`
5. Establish a quality and performance baseline if the change touches hot paths or
   user-visible behavior

Priority: `.claude/memory/MEMORY.md` governs current state and confirmed standards. ADRs
govern rationale and historical context. When they conflict, MEMORY.md wins — but never
edit or delete an ADR; they are append-only.

**Two-tier ADR structure (Melange framework only):**
When working on the Melange framework itself, there are two ADR directories:
- `docs/adr/` — project-layer ADRs for the initialized project (starts empty; write here
  for project-level decisions)
- `docs/adr/melange/` — framework-layer ADRs documenting Melange's own design decisions
  (deleted from initialized projects during `/init`; write here for framework decisions)

If you are working in an initialized project, `docs/adr/melange/` will not exist —
that is correct and expected.

## Build and Test

Read the Commands table in `CLAUDE.md` for the project's actual build and test commands.

If the Commands table is empty or a command is not defined, use AskUserQuestion to get the
correct command from the user before proceeding. Never guess or infer commands that are not
explicitly defined.

## Before Committing

Run the quality command from the Commands table in `CLAUDE.md`. If the quality command is
not defined, run lint + build + test in sequence and report the result of each.

Do not commit with warnings or test failures. Do not suppress warnings to make a build
appear clean.

Commit message must follow the Conventional Commits format. See the **Commit messages**
section of `README.md` for the type table, version bump rules, and co-authorship trailer
format. Use the type that accurately reflects the change — do not use `feat` for a bug
fix to inflate the version bump, and do not use `chore` to hide a user-visible change.

Every Claude-assisted commit must include co-authorship trailers for both the human and
the model. Populate the human identity from `git config user.name` and
`git config user.email`.

Check the diff for privacy violations before committing:
- No raw user inputs (query strings, form values, user IDs) in log statements
- No new cookies or persistent session state added without approval
- No external resource loads added to the UI

## Agent-Based Development

The top-level session is orchestration only. For any task that may produce verbose output
or require iteration, dispatch to an agent.

When dispatching:
- Build verification and compilation checks
- Test runs and performance profiling
- Log analysis and quality evaluation
- Any iterative investigation

Never run long-running commands directly in the main session.

## Code Quality — Zero Tolerance

Every build must be clean. Zero warnings, zero errors. Fix before proceeding.

Never suppress warnings dishonestly:
- Suppression annotations only for intentional public API that is not yet called internally
- Never for hiding incomplete work or actual bugs
- No `.unwrap()` equivalents in production paths — use proper error handling
- No dead code left in place — remove it or make it live

## Testing Integrity

Never fake a passing test:
- Do not weaken assertions or thresholds to match broken behavior
- Do not narrow the test set to easy cases to avoid failures
- Do not accept "operation completed" as proof of "operation completed correctly"

If a test cannot pass because the underlying code is broken: fix the code.

Blame protocol: before claiming a failure is pre-existing or unrelated to your change,
run the test on the base branch and paste the actual output.

## Destructive Operations

Pause and confirm with the user before any of the following:
- Force push to any branch
- Branch deletion (local or remote)
- File deletion (outside of test cleanup)
- Database or schema migration in any environment
- Any operation labeled "irreversible" in the project documentation

State the exact command and its effect, and ask "Proceed?" before executing. This applies
even when the user has asked you to "handle it" — irreversible actions require a final
explicit confirmation.

## Long-Running Tasks

If a task will take more than 5 minutes:
- Check back approximately every 270 seconds
- Report progress at each check-in
- Never silently abandon a long-running task
- Use signal-based completion detection, not fixed sleeps

Never claim done without reading actual output. "Should be fine" is not evidence.

## Completion Status Protocol

Every agent response must end with one of these status codes. No exceptions.

| Status | Meaning |
|--------|---------|
| `DONE` | Task completed. All signals confirmed. Evidence included. |
| `DONE_WITH_CONCERNS` | Task completed but flagged concerns the operator should review before proceeding. |
| `BLOCKED` | Cannot proceed. State the exact blocker and what was already attempted. |
| `NEEDS_CONTEXT` | Missing information required to make a correct decision. State exactly what is needed. |

**Escalation path:** If you encounter 3 consecutive BLOCKED states on the same issue,
a security-sensitive change you cannot verify, or scope that has grown beyond the original
plan, escalate with:

```
STATUS: ESCALATING
REASON: [why escalation is needed — be specific]
ATTEMPTED: [what was tried, in order]
RECOMMENDATION: [what the operator should do next]
```

Never claim DONE without reading actual output. "Should work" is not a signal.

## Available Skills

| Skill | Purpose |
|-------|---------|
| `init` | One-time framework initialization: ideation → interview → fill placeholders → verify |
| `configure` | Modify framework configuration (skills, commands, hooks, permissions, CLAUDE.md) with UNIVERSAL/PROJECT guardrails |
| `ideation` | Scope a feature, define success criteria, estimate complexity |
| `research` | Authoritative technical answers before committing to an approach |
| `planning` | Phase-by-phase plan with human approval checkpoint before coding |
| `dev-loop` | Fast iteration with signal detection and time-bounded runs |
| `quality-check` | Pre-commit gate: lint, build, test, privacy check |
| `review` | Multi-specialist code review: security, performance, migration, API contract, maintainability, testing, red-team |
| `testing` | Test authoring: fast vs slow tiers, signal-based completion |
| `debugging` | Document-driven, systematic debugging |
| `adr-authoring` | Write and index Architecture Decision Records |
| `changelog` | Write user-facing CHANGELOG entries |
| `deploy` | Pre-deploy checklist with human approval before execution |
| `canary` | Post-deploy health verification via curl endpoint checks and log scanning |
| `security` | Security audit: secrets, dependency CVEs, OWASP Top 10, STRIDE threat model |
| `benchmark` | Performance regression detection: build time, test time, bundle size vs. baseline |
| `retro` | Weekly engineering retrospective from git history |
| `context-save` | Save session state (goal, progress, decisions, remaining work) for cross-session restore |
| `context-restore` | Restore session context from a saved file; cross-check with git reality |
| `careful` | Documents and explains the PreToolUse destructive-command interception hook |

## Available Agents

| Agent | Purpose |
|-------|---------|
| `planner` | Reviews implementation plans before coding — PROCEED / REDESIGN REQUIRED |
| `researcher` | Finds authoritative answers with real tradeoffs from production systems |
| `validator` | Quality gatekeeper with absolute veto — evidence-based ACCEPT / REJECT |
| `performance-profiler` | Latency bottleneck identification and regression analysis |

## Available MCP Servers

Configured in `.mcp.json` and available to all agents:

| Server | When to use |
|--------|-------------|
| `context-creator` | Analyzing unfamiliar code, exploring remote repositories, semantic search |
| `github` | PR review, issue lookup, CI status (needs `GITHUB_PERSONAL_ACCESS_TOKEN` env var) |
| `git` | Structured log/blame/diff output when Bash git results are too noisy |

Prefer `context-creator` over spawning an Explore subagent when the question is narrow and answerable in one call. Use `analyze_remote` to study reference implementations without cloning.

**GitHub operations use the MCP server exclusively.** Never use `gh` CLI as a fallback. If a `mcp__github__*` call fails, surface the error and stop — do not retry with `gh`. The `gh` binary is not a project dependency and may not be on the PATH.

## Session Completion Protocol

Before ending a session:

1. All modified files must build cleanly per the Build command in `CLAUDE.md`
2. All tests must pass per the Test command in `CLAUDE.md`
3. No uncommitted changes unless explicitly in-progress (and noted in MEMORY.md)
4. Update `.claude/memory/MEMORY.md` if project state changed
5. Add a CHANGELOG entry if a user-visible change shipped
6. Update `docs/planning/PROJECT_ROADMAP.md` if a phase was started or completed
