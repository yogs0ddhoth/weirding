#  Quality Check Skill

Pre-commit quality gate. Run before every commit.

## When to Invoke

- Before every commit (mandatory)
- After completing a feature, before opening a PR
- When CI fails with a quality violation and you need to reproduce it locally
- Any time "is this ready to commit?" is the question

## Two Gate Levels

### Fast Gate (run always)

Run every time, regardless of branch:
1. Format check — code is formatted per project standard
2. Lint — zero violations
3. Build — zero warnings, zero errors
4. Test — all tests pass

### Full Gate (run on deployable branches)

Run before merging to main or deploying to any environment:
1. All fast gate checks
2. Privacy check (see below)
3. Commit message check (see below)
4. Any additional integrity checks defined in CLAUDE.md
5. Dependency audit if defined in CLAUDE.md

## Process

### Step 1 — Read Commands

Read the Lint and Test commands from the Commands table in CLAUDE.md.

If a quality command is defined separately, use that. If not, run lint + build + test
in sequence.

If a command is not defined, use AskUserQuestion before proceeding. Do not guess.

### Step 2 — Run Fast Gate

Run format, lint, build, and test in sequence. For each:
- Run the command
- Read the actual output — do not infer from exit code alone
- Record pass or fail with the specific output that determined the result

Stop on first failure: if lint fails, fix it before running the build. Running a broken
build is not informative and wastes time.

### Step 3 — Privacy Check

If CLAUDE.md defines privacy requirements (or the project has a privacy section), check
the staged diff for violations:

- New log statements that contain raw user inputs, query strings, or identifiers
- New cookies or persistent session tokens
- New external resource loads (CDN links, analytics scripts, tracking pixels)
- New endpoints that accept and echo back user data without sanitization

Run the check against the actual diff, not the full codebase. Report specific lines if
violations are found.

### Step 4 — Commit Message Check (full gate only)

Validate every commit since the last release tag on this branch. Find the last tag with:

```bash
git describe --tags --abbrev=0
```

If no tag exists, use the root commit. Then get commits since that tag:

```bash
git log <last-tag>..HEAD --format="%H %s"
```

For each commit subject line, check that it matches the Conventional Commits pattern:

```
^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?(!)?: .+
```

A `!` suffix on any type, or a `BREAKING CHANGE:` line in the commit body/footer, signals
a major bump.

Compute the implied version bump:
- Any `feat!`, `fix!`, or `BREAKING CHANGE` → **major**
- Any `feat` (without `!`) → **minor**
- Any `fix`, `perf`, `revert` → **patch**
- Only `docs`, `style`, `refactor`, `test`, `build`, `ci`, `chore` → **none** (internal)

Report: pass/fail, implied bump, and any non-conforming commit hashes + subjects.

### Step 5 — Full Gate (additional checks)

If on a deployable branch, run any additional checks defined in CLAUDE.md. Report each
check with its result.

## Output Format

```
QUALITY GATE: [FAST | FULL]

Format:   [PASS | FAIL] — [evidence]
Lint:     [PASS | FAIL] — [evidence]
Build:    [PASS | FAIL] — [evidence]
Test:     [PASS | FAIL] — [evidence]
Privacy:  [PASS | FAIL | SKIPPED] — [evidence or reason skipped]

[Full gate only:]
Commits:   [PASS | FAIL] — implied bump: [major|minor|patch|none] | [list non-conforming commits]
Integrity: [PASS | FAIL | N/A]
Audit:     [PASS | FAIL | N/A]

RESULT: [ALL PASS — safe to commit | BLOCKED — fix required]

Implied version bump: [major | minor | patch | none — internal only]

Blocking Issues:
[List every issue that must be fixed before committing. Empty if all pass.]
```

## Rules

- Never claim "should be fine" — run the checks and report what they say
- Never commit with warnings — fix them or document why they cannot be fixed (rare)
- Never skip the privacy check because the change "obviously doesn't touch user data"
  — read the diff

## On Failure

When a check fails:
1. State the check that failed
2. State the exact error or violation (file, line, message)
3. State what must be fixed — be specific
4. Do NOT attempt to fix the issue within this skill — report it and let the developer
   decide. Exception: trivial formatting fixes that the format tool can apply automatically
   may be applied, but must be reported.
