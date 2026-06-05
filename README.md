# weirding

weirding is a production-grade Python library for XML ↔ Pydantic v2 conversion. It provides `compile(xml)` to convert XML schema documents — using a plain-attribute annotation convention or XSD — into a JSON Schema IR dict, `define_model(xml)` to compile that IR into Pydantic v2 `BaseModel` classes, `parse(xml, model)` to validate and bind XML data against those models, and `to_xml(instance)` for round-trip serialization. The XML schema you author once becomes a single source of truth with first-class structured-output interop across the ecosystem: `to_json_schema()` exports provider-ready schemas for OpenAI/Azure, Databricks `ai_query`, and open-weight runtimes (vLLM/Ollama); generated models drop straight into LangChain/LangGraph; and prompt utilities (`prompt.to_template()`, `prompt.format_error()`, `RetryContext`) drive any provider's retry loop, Claude included. Designed for Databricks, Kubernetes, serverless, and edge environments.

---

## Getting Started

```bash
pip install weirding
```

```python
import weirding

Model = weirding.define_model("""
<Response>
  <name type="string" required="true"/>
  <score type="integer" required="true"/>
</Response>
""")

instance = weirding.parse("<Response><name>Alice</name><score>42</score></Response>", Model)
```

See the [documentation](https://yogs0ddhoth.github.io/weirding/) for the full guide including XSD support and LLM retry workflows.

---

## Architecture

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

**`JsonSchemaIR` format stability contract**

`compile()` returns a public `JsonSchemaIR` dict. Changes to that dict's format follow the same semver rules:

- **Major:** removing or renaming existing keys (breaks downstream callers that read the dict)
- **Minor:** adding new optional keys, including new `x-weirding-*` extension keys
- **No bump:** adding keys that are only consumed internally and never appear in `compile()` output

See ADR-0002 for rationale.

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
| `TEMPLATE_VERSION` | Canonical framework version anchor — stamped into `MEMORY.md` at `/init` time so initialized projects can trace their baseline |

**Team note:** `.claude/memory/MEMORY.md` is git-tracked. When a Claude session discovers a non-obvious constraint or confirmed standard, it commits an update to this file. Treat merge conflicts in MEMORY.md like any other conflict — keep whichever version reflects current truth, and manually merge if both sides added valid facts.

### Upgrading the framework

Framework improvements — new skills, hooks, agents, governance files — are published as
tagged releases in the Melange repository. Universal files contain no project-specific
content and can be overwritten directly. Project files (`CLAUDE.md`, `README.md`,
`.claude/memory/MEMORY.md`, etc.) diverged at `/init` time and require manual merge.

**1. Find your current version**

```bash
grep "Framework version" .claude/memory/MEMORY.md
```

**2. Review what changed**

```bash
git clone <melange-repo-url> melange-upstream
git -C melange-upstream diff v0.3.0..v0.4.0 -- AGENTS.md
```

**3. Apply universal files, merge project files manually, update the version record and commit.**
