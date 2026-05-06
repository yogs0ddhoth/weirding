# {{PROJECT_NAME}}

{{PROJECT_DESCRIPTION}}

> **New to Melange?** See [SETUP.md](SETUP.md) for Claude-assisted and manual setup paths.

---

## Getting Started

<!-- Fill this in as the project takes shape. A complete Getting Started covers:
     prerequisites, how to install dependencies, required environment variables,
     and how to run the project locally. Example structure:

### Prerequisites
- Node.js ≥ 18
- Postgres 15

### Install

```bash
git clone <repo-url>
cd <project>
npm install
cp .env.example .env   # then fill in values
```

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Postgres connection string |
| `SESSION_SECRET` | Yes | Random string for signing sessions |

### Run locally

```bash
npm run dev
```
-->

_Getting Started instructions coming soon._

---

## Architecture

<!-- Fill this in once the project has structure worth describing. Keep it to one
     paragraph and a directory map — point to docs/adr/ for the reasoning behind
     key decisions. -->

_Architecture overview coming soon. See [`docs/adr/`](docs/adr/) for architectural decisions._

---

## Contributing

Anyone can contribute — with or without Claude Code. Both paths follow the same branch and review process.

### Branch and PR workflow

Never push directly to `main`:

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
# ... make changes ...
git push -u origin feature/your-feature-name
gh pr create --title "Brief description" --body "Details"
```

### Before committing

Run the quality gate (see the Commands table in `CLAUDE.md` for the exact command). It runs lint, build, and tests in sequence. Do not commit with warnings or failing tests.

If you close a Claude Code session with uncommitted changes, the project's session-end hook will remind you to run the gate before committing.

### Commit messages

All commits on deployable branches must follow this format:

```
type(scope): description

[optional body]

[optional footer — BREAKING CHANGE: description]
```

| Type | Semver | When to use |
|------|--------|-------------|
| `feat` | minor | New user-visible capability |
| `fix` | patch | Bug fix |
| `feat!` or `BREAKING CHANGE:` footer | major | Breaking change |
| `perf` | patch | Performance improvement |
| `revert` | patch | Reverts a prior commit |
| `docs` | — | Documentation only |
| `refactor` | — | No behavior change |
| `test` | — | Test additions or fixes |
| `chore` | — | Build, tooling, maintenance |
| `ci` | — | CI/CD configuration |

**Implied version bump:** the highest bump across all commits since the last release tag.
`feat!` or `BREAKING CHANGE` footer → major; any `feat` → minor; any `fix`, `perf`, or
`revert` → patch. Commits using only internal types carry no version bump.

The `/quality` full gate validates commit messages and reports the implied bump. The
`/changelog` skill reads commit types to categorize changes automatically — no manual
categorization needed.

**Co-authorship trailers**

Every commit produced with Claude assistance must carry co-authorship for both the human
and the model. Add these two trailers to every Claude-assisted commit message:

```
Co-Authored-By: Your Name <you@example.com>
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Use the human identity from `git config user.name` and `git config user.email`. Use the
exact Claude model ID from the active session (e.g. `claude-sonnet-4-6`). This applies
to all commits on Claude-assisted branches — not just the merge commit.

### Without Claude Code

You do not need Claude Code to contribute. Use the commands in `CLAUDE.md`'s Commands table directly in your terminal — build, test, lint, and format are all plain shell commands. Read `docs/adr/` before touching a component that has a recorded decision, and open a PR when your branch is ready.

### With Claude Code

If you have Claude Code installed, you get a structured workflow on top of the standard git process. Open Claude Code in the project directory:

```bash
claude         # terminal
# or open the project in VS Code / JetBrains with the Claude Code extension
```

**What happens automatically**

- Every prompt injects `CLAUDE.md` into the session context — Claude already knows the stack, commands, protected files, and quality rules without you explaining them.
- When you approve a plan (respond to `/plan` with `PROCEED`), Claude enters the Develop phase automatically. It dispatches build, test, and implementation work to background agents and reports results back to your session. There is no command to trigger this — it follows directly from your approval.
- When you close a session with uncommitted changes, the session-end hook reminds you to run the quality gate before committing.

**How commands work**

Slash commands are self-contained substeps — you type the command and receive a structured result. Each command handles its own agent dispatch internally; you never manually invoke agents or manage dispatch yourself. Your main session always shows synthesized output, never raw build or command output.

| Command | What happens internally |
|---------|------------------------|
| `/ideate` | Synthesizes scope in main session; proactively dispatches `researcher` agent for any identified unknowns |
| `/research` | Dispatches `researcher` specialist agent; returns structured research report |
| `/plan` | Synthesizes plan in main session; dispatches `planner` agent for review; stops for your approval — Develop phase begins automatically once you approve |
| `/quality` | Dispatches quality execution agent; returns structured pass/fail report |
| `/adr` | Synthesizes decision record in main session |
| `/ship` | Runs checklist in main session; stops for your approval; dispatches deploy agent after approval |

**The workflow — a worked example:**

```
/ideate add CSV export to the reports page
```

Claude produces a scope document: what the feature does, what it does not do, open questions, complexity estimate. If technical unknowns appear in the scope — uncharacterized dependencies, unresolved design choices — Claude dispatches the `researcher` agent for each in parallel without waiting for you to ask, and includes the summaries inline in the document.

```
/research best approach for streaming large CSV exports in <your stack>
```

Claude dispatches the `researcher` specialist agent, which returns a structured report: recommendation, how named production systems solve this, trade-offs per approach, known failure modes, and a privacy check. Every claim is traceable to a real system or source.

```
/plan
```

Claude produces a phased implementation plan in the main session — phases, files, protected file flags, ADR candidates, simplicity challenge — then dispatches the `planner` agent to review it. The planner returns a verdict (`PROCEED`, `PROCEED WITH MODIFICATIONS`, or `REDESIGN REQUIRED`) before anything is shown to you. You see the plan and the verdict together. No code is written until you explicitly approve.

Reply `PROCEED` and the Develop phase begins automatically. Claude dispatches implementation, build, and test work to background agents without you triggering anything further. Your session receives structured agent reports — what was built, what passed, what needs attention — not raw output.

```
/quality
```

Claude dispatches a quality execution agent that reads the project's lint, build, and test commands from `CLAUDE.md`, runs them in sequence, checks the staged diff for privacy violations, and returns a structured report:

```
QUALITY GATE: FAST
Format:   PASS
Lint:     PASS
Build:    PASS
Test:     FAIL — src/export.test.ts line 42: expected 200, got 500
Privacy:  PASS
RESULT:   BLOCKED
Blocking Issues: test failure in src/export.test.ts
```

If blocked, Claude lists the issues and waits for your instruction. It does not attempt fixes without being asked.

```
/adr
```

Claude documents the architectural decision in the main session: the decision, the alternatives considered, the trade-offs, and the rationale. ADRs are append-only and live in `docs/adr/`.

```
/ship
```

Claude runs a pre-deploy checklist (quality gate passed, changelog present, no uncommitted changes, rollback plan documented), presents it to you, and stops. After your explicit approval, it dispatches a deploy agent, monitors for errors, and reports the outcome.

**Key files to know:**

| File | What it is |
|------|------------|
| `CLAUDE.md` | Project instructions injected into every Claude session — source of truth for commands, protected files, quality rules |
| `AGENTS.md` | Operational guide for Claude subagents — read this before making code changes via Claude |
| `ETHOS.md` | Non-negotiable operating principles for every agent session: honest builds, privacy by architecture, completeness over speed |
| `.claude/memory/MEMORY.md` | Cross-session project state: current phase, confirmed standards, non-obvious constraints. Git-tracked and updated by agent sessions |
| `docs/adr/` | Architecture Decision Records — explains _why_ the project is structured the way it is |
| `docs/planning/PROJECT_ROADMAP.md` | Current phase status |
| `CHANGELOG.md` | User-facing release notes |
| `TEMPLATE.md` | Framework manifest: lists every universal file, every project file, and the step-by-step upgrade guide for pulling in new framework versions |
| `TEMPLATE_VERSION` | Canonical framework version anchor — stamped into `MEMORY.md` at `/init` time so initialized projects can trace their baseline |

**Team note:** `.claude/memory/MEMORY.md` is git-tracked. When a Claude session discovers a non-obvious constraint or confirmed standard, it commits an update to this file. Treat merge conflicts in MEMORY.md like any other conflict — keep whichever version reflects current truth, and manually merge if both sides added valid facts.

### Upgrading the framework

Framework improvements — new skills, hooks, agents, governance files — are published as
tagged releases in the Melange repository. Universal files (listed in
[`TEMPLATE.md`](TEMPLATE.md)) contain no project-specific content and can be overwritten
directly. Project files (`CLAUDE.md`, `README.md`, `.claude/memory/MEMORY.md`, etc.)
diverged at `/init` time and require manual merge.

**1. Find your current version**

```bash
grep "Framework version" .claude/memory/MEMORY.md
```

**2. Review what changed**

```bash
# Clone from the same URL you originally used to set up this project
git clone <melange-repo-url> melange-upstream
git -C melange-upstream diff v0.1.0..v0.2.0 -- AGENTS.md   # repeat for each universal file
```

**3. Apply universal files**

```bash
cp melange-upstream/AGENTS.md AGENTS.md
cp melange-upstream/ETHOS.md ETHOS.md
# repeat for each universal file listed in TEMPLATE.md
```

**4. Merge project files manually**

```bash
# Read the diff; apply relevant changes by hand — do not overwrite
git -C melange-upstream diff v0.1.0..v0.2.0 -- CLAUDE.md
```

**5. Update the version record and commit**

Edit `.claude/memory/MEMORY.md` and update `Framework version` to the new version, then:

```bash
git add -A
git commit -m "chore: upgrade Melange framework to v0.2.0"
```
