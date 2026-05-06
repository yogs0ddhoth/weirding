# Init Skill

Initialize a Melange framework for a specific project. Run once, on an uninitialized
repository. The end state is identical to completing the manual path in SETUP.md.

## When to Invoke

- First session on a freshly cloned Melange framework
- When `{{PLACEHOLDER}}` strings are still present in CLAUDE.md
- Retrofit: when adopting the framework on an existing codebase (see Retrofit Mode below)

## Guard: already initialized?

Before doing anything, check CLAUDE.md for `{{` strings. If none exist, report:

```
This project appears to already be initialized — no {{PLACEHOLDER}} values found in CLAUDE.md.
If something looks wrong, open CLAUDE.md directly and check for any remaining placeholders.
```

Then exit the skill. Do not proceed.

---

## Adoption Modes

At the start of any init run, detect which mode the user invoked. Inspect `$ARGUMENTS` for
mode flags:

- No flag or `--full` → **Full mode** (default)
- `--governance-only` → **Governance-only mode**
- `--commands-only` → **Commands-only mode**

Store the detected mode. Every phase that writes files must consult this mode before writing.

### Mode scope table

| CLAUDE.md section          | `--full`        | `--governance-only`   | `--commands-only` |
|----------------------------|-----------------|-----------------------|-------------------|
| Commands table             | write           | skip                  | write             |
| Protected files table      | write           | write                 | skip              |
| README.md update           | write           | skip                  | skip              |
| MEMORY.md                  | write           | write (partial)       | skip              |
| Roadmap (Phase 3)          | write           | skip                  | skip              |
| `.claude/settings.json`    | write           | skip                  | write             |

**Partial MEMORY.md for `--governance-only`:** Write the stack entry (Language/stack line)
but skip the roadmap entry and current-phase entry.

### Mode-aware Phase 5 gate

- `--governance-only`: Commands table not checked; Roadmap not checked; Permissions not
  checked. Gate passes if: protected files written, quality requirements present, privacy
  requirements present.
- `--commands-only`: Protected files not checked; Roadmap not checked. Gate passes if:
  Commands table written and `.claude/settings.json` has a non-empty `permissions.allow`
  array.
- `--full`: existing gate logic unchanged (all checks apply).

---

## Retrofit Mode

Detect whether this is an existing codebase vs. a greenfield project before Phase 1.

Check for any of the following in the working directory:

**Manifests (lower confidence — may be ambiguous):**
- `go.mod` (Go)
- `package.json` (Node.js / frontend)
- `requirements.txt` or `pyproject.toml` (Python)
- `Cargo.toml` (Rust)
- `pom.xml` or `build.gradle` (JVM)
- `*.csproj` or `*.sln` (C#/.NET)
- `Gemfile` (Ruby)

**Lock files (higher confidence — uniquely identify package manager):**
- `yarn.lock` → Yarn (Node.js)
- `package-lock.json` → npm (Node.js)
- `pnpm-lock.yaml` → pnpm (Node.js)
- `poetry.lock` → Poetry (Python)
- `Pipfile.lock` → Pipenv (Python)
- `Gemfile.lock` → Bundler (Ruby)
- `Cargo.lock` → Cargo (Rust)

If any of these exist, this is a **retrofit** — an existing codebase is adopting the
framework. In retrofit mode, the standard Phase 1 (Ideation) and Phase 2 (Technical
Interview) are replaced by the Retrofit Detection and Confirmation flow described below.

Notify the user:
```
Retrofit mode: existing codebase detected. Skipping ideation — analyzing your codebase
to pre-fill commands and stack information.
```

Then ask once:
> "I see this is an existing project. In one or two sentences, describe what it does and
> who uses it. I'll use that as the project description."

---

## Secret-Scan Guard

This guard applies to ALL file body analysis in Retrofit Mode. It fires before any file
body content enters LLM context.

### Default policy: structural content only

By default, the LLM receives ONLY structural content:
- File names and directory listings
- Manifest key names (e.g., `scripts.build`, `[tool.taskipy]`)
- Script command strings (the value of a script key, such as `npm run build`)

No file body content (actual source lines, documentation, configuration values) is sent
to LLM context without explicit user opt-in.

### Opt-in gate

If any analysis step would require reading file body content (not manifest keys, not file
names), prompt the user first:

> "To improve detection accuracy I can read the contents of [list specific files]. These
> will be scanned for secrets before any content is used. Proceed?"

Do not read file bodies without an affirmative response. If the user declines, proceed
with structural-only analysis and label all affected values `INFERRED`.

### Secret-pattern pre-check

This check fires for each file body individually, before any part of that file is added
to LLM context. Scan the file for:

| Pattern | Matches |
|---------|---------|
| AWS access key | `AKIA[0-9A-Z]{16}` |
| GitHub token | `ghp_[a-zA-Z0-9]{36}` or any string containing `github_pat_` |
| Generic secret variables | Lines matching `SECRET=`, `TOKEN=`, `PASSWORD=`, `API_KEY=`, `PRIVATE_KEY` (case-insensitive) |
| High-entropy string | Any 40+ character alphanumeric string on a single line |

### On pattern match

- Exclude the file from LLM context entirely — do not include any part of the file
- Record the filename and match category for inclusion in the confirmation screen warning
- The warning format is:
  `⚠️  [filename] excluded from analysis — [match category] detected. Review manually.`
- The warning shows ONLY the filename and match category — never the matched string,
  matched line number, or surrounding context
- Do NOT log matched content, matched strings, or any characters from the matched line

---

## Retrofit Detection: Pre-filling Commands and Stack

Run this analysis BEFORE showing the confirmation screen.

### Step 1: Monorepo check (halt if detected)

Check for workspace config files: `pnpm-workspace.yaml`, `turbo.json`, `nx.json`,
`lerna.json`, `rush.json`.

If any of these exist:
1. Show the developer which workspace config files were detected
2. Ask a single targeted question:
   > "Which workspace is the primary application? (e.g., `apps/web` or `packages/api`)"
3. **Halt until answered** — do not proceed with command extraction
4. Once answered, treat that workspace as the root for all subsequent command extraction

### Step 2: CI config detection (supplemental signal)

Check for CI configuration files and parse `run:` lines to surface canonical commands:
- `.github/workflows/*.yml` — parse `run:` lines; label values as `DETECTED (CI config)`
- `.gitlab-ci.yml` — parse `script:` lines; label as `DETECTED (CI config)`
- `.circleci/config.yml` — parse `run:` lines; label as `DETECTED (CI config)`
- `Makefile` — surface as supplemental signal; label as `DETECTED (CI config)`

CI config values supplement manifest detection — they do not override it.

### Step 3: Per-stack extraction

Apply the extraction rules for the detected stack. Lock files take precedence over
manifests when identifying the package manager.

**Node.js (package.json exists):**
- Read the `scripts` block (structural content — key names and values are both safe)
- Build: `scripts.build` value if present → `DETECTED (package.json scripts.build)`;
  else → `INFERRED: npm run build`
- Test: `scripts.test` value if present → `DETECTED (package.json scripts.test)`;
  else → `INFERRED: npm test`
- Lint: `scripts.lint` value if present → `DETECTED (package.json scripts.lint)`;
  else → `INFERRED: npm run lint`
- Format: `scripts.format` or `scripts.prettier` value if present →
  `DETECTED (package.json scripts.format)`; else → `INFERRED: npm run format`
- Package manager: `yarn.lock` → Yarn; `pnpm-lock.yaml` → pnpm;
  `package-lock.json` → npm; none found → `INFERRED: npm`

**Python with pyproject.toml:**
- Check for `[tool.taskipy]` section — extract task names as commands →
  `DETECTED (pyproject.toml [tool.taskipy])`
- Check for `[tool.poetry.scripts]` — extract as build candidates →
  `DETECTED (pyproject.toml [tool.poetry.scripts])`
- Fallback INFERRED: `python -m build`, `pytest`, `ruff check .`, `ruff format .`

**Python with requirements.txt (no pyproject.toml):**
- All INFERRED: `pip install -e . && python -m build`, `pytest`, `flake8 .`, `black .`

**Go (go.mod):**
- All INFERRED: `go build ./...`, `go test ./...`, `golangci-lint run`, `gofmt -l .`

**Rust (Cargo.toml):**
- All INFERRED: `cargo build`, `cargo test`, `cargo clippy`, `cargo fmt`

**Ruby (Gemfile):**
- Check Gemfile for `gem 'rails'` or `gem 'rspec'` to specialize
- Rails INFERRED: `bundle exec rails assets:precompile`, `bundle exec rspec`,
  `bundle exec rubocop`, `bundle exec rubocop -A`
- Non-Rails INFERRED: `bundle exec rake`, `bundle exec rspec`,
  `bundle exec rubocop`, `bundle exec rubocop -A`
- If Gemfile was read to check gem names, apply the secret-scan guard first

**JVM with build.gradle or gradlew:**
- If `gradlew` file exists: `./gradlew build`, `./gradlew test`,
  `./gradlew checkstyleMain` — all INFERRED
- If only `build.gradle`: `gradle build`, `gradle test` — all INFERRED

**JVM with pom.xml:**
- All INFERRED: `mvn package`, `mvn test`, `mvn checkstyle:check`
- Format: N/A (no standard Maven format command)

### Label discipline — enforce strictly

Every pre-filled value in the confirmation screen must carry one of exactly two labels:

- `DETECTED (source)` — value read directly from a file. Always name the specific source
  in parentheses, e.g., `DETECTED (package.json scripts.test)` or
  `DETECTED (CI config: .github/workflows/ci.yml)`. No DETECTED label without a source.
- `INFERRED` — LLM-reasoned default for this stack; no file evidence. No source needed.

Never mix labels. Never omit a label.

### Step 4: Protected files inference

Run this step before showing the confirmation screen. This step uses only structural
content (no file bodies) unless the user opts in.

1. **Shallow-clone check:** Run `git rev-list --count HEAD`. If fewer than 10 commits
   exist, skip the most-modified-files analysis entirely. Label all protected file
   suggestions as `INFERRED (directory listing only)`. Proceed to step 3.

2. **Most-modified files (deep clone only):** Run:
   ```
   git log --diff-stat --format="" | grep " | " | awk '{print $1}' | sort | uniq -c | sort -rn | head -20
   ```
   This surfaces the 20 most-modified file paths. No file body is read.

3. **LLM semantic classification:** Present to the LLM:
   (a) top-level directory listing
   (b) most-modified file paths from step 2 (or skipped if shallow clone)

   Ask the LLM to classify directories and files by semantic role:
   - auth/session
   - core data model
   - privacy-sensitive
   - performance hot path
   - schema migrations
   - "no signal" if unclear

4. **Draft output — always labeled INFERRED:**

```
── PROTECTED FILES (INFERRED draft — review carefully) ──────────────────
Tier 1 (ask before any change):
  - src/auth/           [INFERRED: auth — directory name]
  - src/models/user.ts  [INFERRED: data model — most-modified]

Tier 2 (explain why alternative approaches are insufficient):
  - src/api/search.ts   [INFERRED: hot path — highest churn]
  - migrations/         [INFERRED: migrations — directory name]

⚠️  This is a draft. Add any security-critical files I missed. Remove any that
    are misclassified.
```

Do not write the protected files table to CLAUDE.md until the developer explicitly
confirms it in the Phase 2 confirmation screen.

### Step 5: Show the pre-filled confirmation screen

Present all pre-filled values in a single screen. Include any secret-scan exclusion
warnings from the Secret-Scan Guard.

```
I analyzed your codebase and pre-filled the following values. Correct anything wrong
and use "N/A" for anything that doesn't apply.

── COMMANDS ─────────────────────────────────────────────────────────────
1. Language/stack:   [value]  [DETECTED from go.mod / INFERRED]
2. Build:            [value]  [DETECTED from package.json scripts.build / INFERRED]
3. Test:             [value]  [DETECTED from package.json scripts.test / INFERRED]
4. Lint:             [value]  [INFERRED]
5. Format:           [value]  [INFERRED]
6. Deploy:           [value or N/A]  [DETECTED from .github/workflows/deploy.yml / INFERRED]
7. Docs:             N/A  [no docs tooling detected]
8. Git remote:       [DETECTED from git remote -v / skip]

── PROTECTED FILES (draft — review carefully) ────────────────────────────
[show the INFERRED protected files draft from Step 4]

[If any files were excluded by secret-scan guard:]
⚠️  [filename] excluded from analysis — [match category] detected. Review manually.

Reply with corrections. Reply "ok" to accept all pre-filled values.
```

Wait for the user's response. Do not proceed to Phase 3 until the user replies.

After the user replies, treat corrected values as confirmed. Treat "ok" as accepting all
pre-filled values. Proceed to Phase 3 (Roadmap) if mode requires it, else skip to
Phase 4 (Fill Placeholders).

---

## Phase 1 — Ideation

**(Greenfield path only — skip in Retrofit Mode)**

Accept the project description from the `/init` argument. If no argument was provided,
ask once:

> "Describe what you want to build in one or two sentences. Include the domain, who uses
> it, and the primary capability."

Then follow the ideation skill process (`.claude/skills/ideation/SKILL.md`) on that
description. Work through all six questions: problem, success criteria, scope, dependencies,
complexity estimate, and risks.

Extract from the ideation output:
- **Project description** — synthesize a single clean paragraph: what the project is, who
  uses it, and its primary capability. This is `{{PROJECT_DESCRIPTION}}`. Do not paste the
  entire scope document — write one paragraph that a contributor could read in 10 seconds.
- **Complexity estimate** — used in Phase 3 to determine roadmap depth (S → 2 phases, M →
  3, L → 4, XL → 4–5)
- **Risks and non-obvious constraints** — captured in MEMORY.md rules section

If the ideation process identifies technical unknowns (stack choice, auth pattern, data
model approach), dispatch the researcher agent per the ideation skill's instructions and
include the summaries inline before moving to Phase 2.

---

## Phase 2 — Technical Interview

**(Greenfield path only — replaced by Retrofit Confirmation Screen in Retrofit Mode)**

Ask ONLY the questions ideation cannot answer. Ask them all at once in a single message —
never one at a time.

If the stack was clearly stated in the project description (e.g., "in Go", "using React"),
skip question 1 or pre-fill it and confirm.

```
To finish initialization I need a few technical specifics. Answer what you know — use
"N/A" or "skip" for anything that doesn't apply yet.

1. Language and stack (e.g., "Go 1.22 + PostgreSQL 15", "Node.js 20 + React 18 + SQLite")
2. Build command (exact shell command, e.g., `go build ./...` or `npm run build`)
3. Test command (exact, e.g., `go test ./...` or `npm test`)
4. Lint command (exact, e.g., `golangci-lint run` or `npm run lint`)
5. Format command (exact, e.g., `gofmt -l .` or `npm run format`)
6. Deploy command (exact, or "N/A")
7. Docs command (exact, or "N/A")
8. Path to authentication/session code (e.g., `src/auth/`, or "N/A")
9. Path to core data model (e.g., `src/models/`, or "N/A")
10. Path to privacy-sensitive code (e.g., `src/user/`, or "N/A")
11. Path to performance hot path (e.g., `src/handlers/search.go`, or "N/A")
12. Path to schema migrations (e.g., `migrations/`, or "N/A")
13. Git remote URL (e.g., `git@github.com:org/repo.git`, or "skip")
```

Wait for the user's response. Do not proceed to Phase 3 until the user replies.

If any command is ambiguous (e.g., "I'll use Jest but haven't set it up yet"), record it
as N/A and note it in the verification gate output so the user knows to revisit it.

---

## Phase 3 — Generate Roadmap Phases

**(Skip in `--governance-only` and `--commands-only` modes)**

From the ideation scope and complexity estimate, derive roadmap phases:

- Phase 00 is always "Foundation — project setup, CI, core types" (pre-filled by Melange)
- Add 2–4 more phases based on complexity: what must be built, in what order, at what granularity
- Each phase name is one line: capability delivered, not implementation detail
- S complexity → 2 total phases; M → 3; L → 4; XL → 4–5

Examples:
- "Phase 01 — Core API — CRUD endpoints for primary resources, authentication"
- "Phase 02 — Data pipeline — ingestion, validation, storage layer"
- "Phase 03 — UI — dashboard views, user-facing query interface"

---

## Phase 4 — Fill Placeholders

Fill every `{{PLACEHOLDER}}` across the files below, respecting the active mode scope table.
Never leave a `{{PLACEHOLDER}}` string in any tracked file — either fill it with a real
value or remove the row/section.

### CLAUDE.md

**Commands table** (`--full` and `--commands-only` only):
- `{{PROJECT_NAME}}` — short name, extracted from description or asked once if ambiguous
- `{{PROJECT_DESCRIPTION}}` — synthesized paragraph from Phase 1 (greenfield) or user
  description (retrofit)
- All six command placeholders — exact values from Phase 2 or Retrofit Confirmation; if
  N/A, remove that table row
- Protected file placeholders (`--full` and `--governance-only` only):
  - If a path was confirmed: fill the placeholder
  - If N/A: **remove the entire table row** — do not write "N/A" in the table, as agents
    interpret every row as a real, guarded file path
- Delete the template instruction comment block (the `<!-- TEMPLATE INSTRUCTIONS ... -->`
  block). The gate will fail if any `<!-- TEMPLATE` string remains in a tracked file.

### README.md

**(`--full` mode only)**
- `{{PROJECT_NAME}}` h1
- `{{PROJECT_DESCRIPTION}}` paragraph
- Remove the `> **New to Melange?**` notice line

### `.claude/memory/MEMORY.md`

**(`--full` mode: full write; `--governance-only`: stack entry only; `--commands-only`: skip)**
- `{{LANGUAGE_AND_STACK}}` — from Phase 2 or Retrofit Confirmation
- `{{CURRENT_PHASE}}` — "Phase 00 — Foundation (not started)" (`--full` only)
- `**Framework version:**` — read `TEMPLATE_VERSION` from the repo root and add the value
  to Core Facts (`--full` only)
- Add non-obvious constraints from ideation risks to the Non-Negotiable Rules section
  (`--full` only)

### `docs/planning/PROJECT_ROADMAP.md`

**(`--full` mode only)**
- `{{PHASE_01}}` through available phase slots — phase descriptions from Phase 3
- `{{CURRENT_FOCUS}}` — "Phase 00 — Foundation"
- Remove any `{{PHASE_XX}}` rows that were not filled

### `.claude/settings.json`

**(`--full` and `--commands-only` modes only)**

Add a `permissions` block. Merge with the existing `hooks` block — do not overwrite it.

```json
{
  "permissions": {
    "allow": [
      "Bash(<build command>)",
      "Bash(<test command>)",
      "Bash(<lint command>)",
      "Bash(<format command>)"
    ]
  },
  "hooks": { ...existing hooks content unchanged... }
}
```

Include only non-N/A commands. Use exact command strings — no wildcards, no prefixes.

### Git remote (if provided)

If a git remote URL was given in Phase 2 or Retrofit Confirmation:
```bash
git remote remove origin 2>/dev/null || true
git remote add origin <url>
```

Do NOT push — pushing requires explicit user approval and is outside init scope.

### Framework-layer cleanup (all modes)

Delete files that belong to Melange's own development and must not appear in initialized
projects. These deletions apply in all modes (`--full`, `--governance-only`, `--commands-only`).

```bash
# Framework-layer ADRs — Melange design decisions, not the project's decisions
rm -rf docs/adr/melange/

# Initialization guide — consumed, no longer needed
rm -f SETUP.md

# Template manifest — consumed during init, not needed in the project
rm -f TEMPLATE.md
```

After deletion, rewrite `docs/adr/README.md` to a clean empty project index:

```markdown
# Architecture Decision Records

ADRs explain *why* this project is designed the way it is.

## How to Read ADRs

Read ADRs before touching a component — not to discover current state, but to understand
why the constraints exist.

## How to Write an ADR

Use the `/adr` command. Copy `template.md` to `NNNN-short-title.md` and fill it in.
ADRs are append-only.

## Index

| # | Title | Status | Date | Summary |
|---|-------|--------|------|---------|
| — | — | — | — | No ADRs yet. |
```

The Phase 5 gate verifies that `docs/adr/melange/` does not exist and `SETUP.md` does not
exist in the working directory after cleanup.

---

## Phase 5 — Init Verification Gate

Run each check. Read the actual file content to determine pass/fail — do not infer.
Apply mode-aware gate logic as defined in the Adoption Modes section above.

### Full mode gate (default)

```
INIT GATE

Placeholders:      [PASS | FAIL] — no {{ strings in CLAUDE.md, README.md, MEMORY.md, PROJECT_ROADMAP.md
Template comments: [PASS | FAIL] — no <!-- TEMPLATE blocks remaining in any tracked file
Permissions:       [PASS | FAIL] — .claude/settings.json has non-empty permissions.allow array
Memory:            [PASS | FAIL] — MEMORY.md Core Facts has real stack and phase values
Framework version: [PASS | FAIL] — MEMORY.md Core Facts includes "Framework version:" matching TEMPLATE_VERSION
Roadmap:           [PASS | FAIL] — PROJECT_ROADMAP.md has no {{PHASE_XX}} placeholders remaining
Git remote:        [PASS | SKIP] — git remote -v shows a remote (SKIP if user chose to skip)
Cleanup:           [PASS | FAIL] — docs/adr/melange/ does not exist; SETUP.md does not exist; TEMPLATE.md does not exist

RESULT: [INIT COMPLETE | BLOCKED]

Blocking Issues:
[List each FAIL with the specific file, line, or value that must be fixed]
```

### Governance-only mode gate

```
INIT GATE (--governance-only)

Protected files:   [PASS | FAIL] — CLAUDE.md Tier 1 and Tier 2 tables have real paths (not placeholders)
Quality rules:     [PASS | FAIL] — CLAUDE.md Quality Requirements section is present and not placeholder text
Privacy rules:     [PASS | FAIL] — CLAUDE.md Privacy Requirements section is present and not placeholder text
Template comments: [PASS | FAIL] — no <!-- TEMPLATE blocks remaining in any tracked file
Memory (stack):    [PASS | FAIL] — MEMORY.md has stack entry (phase entry not required)

Cleanup:           [PASS | FAIL] — docs/adr/melange/ does not exist; SETUP.md does not exist; TEMPLATE.md does not exist

SKIPPED (governance-only): Commands table, Permissions, Roadmap, README, Framework version

RESULT: [INIT COMPLETE | BLOCKED]

Blocking Issues:
[List each FAIL with the specific file, line, or value that must be fixed]
```

### Commands-only mode gate

```
INIT GATE (--commands-only)

Commands table:    [PASS | FAIL] — CLAUDE.md Commands table has at least one non-N/A command
Permissions:       [PASS | FAIL] — .claude/settings.json has non-empty permissions.allow array
Template comments: [PASS | FAIL] — no <!-- TEMPLATE blocks remaining in any tracked file

Cleanup:           [PASS | FAIL] — docs/adr/melange/ does not exist; SETUP.md does not exist; TEMPLATE.md does not exist

SKIPPED (commands-only): Protected files, Roadmap, README, Memory, Framework version

RESULT: [INIT COMPLETE | BLOCKED]

Blocking Issues:
[List each FAIL with the specific file, line, or value that must be fixed]
```

If INIT COMPLETE:

```
Initialization complete.

Next steps:
1. Delete SETUP.md — it is no longer needed (`rm SETUP.md` or delete in your editor)
2. Run /ideate [first feature or first phase goal] to begin development
3. Run /quality before your first commit

The project roadmap is at docs/planning/PROJECT_ROADMAP.md.
ADRs live in docs/adr/ — use /adr for any architectural decision.
```

---

## Rules

- Ask all technical questions in one batch (Phase 2 or Retrofit Confirmation) — never piecemeal
- Never guess commands — if a command is unclear, accept N/A and flag it in the gate
- Never write "N/A" into a protected files table row — remove the row entirely
- Never push to git remote during init — report the remote was set, let the user push
- Do not invoke `/plan` during init — the roadmap is generated from ideation output,
  not from a feature planning run
- Do not begin Phase 4 until the user has answered Phase 2's questions or confirmed the
  Retrofit Confirmation screen
- All flag enforcement and mode-gate logic lives in this file — `init.md` is a pure router
- Never send file body content to LLM context without running the Secret-Scan Guard first
- Never omit the DETECTED/INFERRED label on any pre-filled value in the confirmation screen
- Monorepo detected → halt for workspace clarification before any command extraction
