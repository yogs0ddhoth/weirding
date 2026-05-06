# Review Skill

Structured code review using parallel specialist analysis. Stack-agnostic.

## When to Invoke

- Before opening a PR — catch issues before reviewers see them
- During PR review — provide structured, evidence-backed feedback
- After completing an implementation — verify it matches the approved plan

## Input

Accepts: a PR number, a branch name, or no argument (reviews current branch vs. main).

- PR number (e.g. `/review 42`): fetch diff via GitHub MCP
- Branch name (e.g. `/review feature/csv-export`): `git diff <branch>...HEAD`
- No argument: `git diff $(git merge-base HEAD origin/main)...HEAD`

## Process

### Step 1 — Get the diff

Run the appropriate git command or GitHub MCP call. If the diff is empty, report "nothing
to review" and stop.

Also check for a saved plan file: look in `.claude/plans/` for a file named after the
current branch. If found, read it — it will be used for scope drift detection in Step 4.

### Step 2 — Run specialist analysis in parallel

Dispatch all seven specialists simultaneously. Each specialist reads the diff and returns
findings scoped to its domain. Read each specialist's checklist from:
`.claude/skills/review/specialists/`

Specialists:
1. `security.md` — injection, secrets, auth boundaries
2. `performance.md` — N+1 queries, blocking I/O, unbounded allocations
3. `migration.md` — schema changes, reversibility, lock duration
4. `api-contract.md` — breaking changes, versioning, backwards compatibility
5. `maintainability.md` — complexity, naming, error handling (always run)
6. `testing.md` — coverage gaps, assertion quality, test independence
7. `red-team.md` — adversarial thinking, failure modes, silent failures

For each specialist: apply its checklist to the actual diff. Only report findings that are
present in the diff — do not report theoretical risks that the diff does not introduce.
Mark each finding with file and line number.

Skip a specialist entirely if its domain is not touched by the diff:
- Skip `migration.md` if no schema migration files are changed
- Skip `api-contract.md` if no API interface files are changed
- Run `maintainability.md` on every review without exception

### Step 3 — Scope drift detection

If a plan file was found in Step 1, compare the diff against the plan's scope:

- Is code being changed that was not in the plan's file list?
- Are any planned files absent from the diff?
- Does the size or nature of the diff match the plan's complexity estimate?

Report scope drift as DRIFT DETECTED or NO DRIFT. Scope drift is not automatically a
blocker — it may be legitimate expansion — but it must be surfaced.

### Step 4 — Aggregate and report

```
REVIEW: <branch or PR>
Diff: <N files changed, +X -Y lines>
Plan: <found at .claude/plans/... | not found>

Scope Drift: [NO DRIFT | DRIFT DETECTED — description]

Security:       [PASS | FINDINGS] — <count> findings
Performance:    [PASS | FINDINGS] — <count> findings
Migration:      [PASS | FINDINGS | SKIPPED]
API Contract:   [PASS | FINDINGS | SKIPPED]
Maintainability:[PASS | FINDINGS] — always run
Testing:        [PASS | FINDINGS]
Red Team:       [PASS | FINDINGS]

VERDICT: [APPROVE | REQUEST CHANGES]

---
Findings:

[Security]
  <file>:<line> — <description> — <severity: HIGH/MEDIUM/LOW>

[Performance]
  <file>:<line> — <description>

[...other specialists with findings...]

Recommendations:
  [Any positive findings or suggestions worth highlighting even if not blocking]
```

APPROVE: no HIGH findings, no unresolved scope drift.
REQUEST CHANGES: any HIGH severity finding, or scope drift without explanation.
MEDIUM and LOW findings are noted but do not block APPROVE.

## Rules

- Only report findings present in the diff — never flag pre-existing code not touched
- Every finding must cite file and line number — no vague "the auth module has issues"
- Do not suppress MEDIUM/LOW findings — they belong in the report even if not blocking
- Never APPROVE a diff that introduces a HIGH security finding regardless of other factors
