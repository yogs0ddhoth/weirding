# Retro Skill

Weekly engineering retrospective from git history. No external tools required.

## When to Invoke

- End of week
- End of a sprint or phase
- Before a team review meeting

## Process

### Step 1 — Collect git history

```bash
# All commits in the last 7 days across all branches
git log --all --since="7 days ago" \
  --format="%H|%an|%ae|%ad|%s" --date=short

# Files changed per commit
git log --all --since="7 days ago" --name-only --format="%H"
```

If the user provides a date range argument (e.g., `/retro --since 2026-04-01`), use that
instead of the 7-day default.

### Step 2 — Compute metrics

From the collected history, compute:

**Volume**
- Total commits: by author and overall
- Total files changed, lines added, lines deleted

**Type breakdown** (from commit message prefixes)
- feat/feature: new functionality
- fix/bug: bug fixes
- refactor: internal improvements
- test: test additions
- docs/chore: maintenance

If commit messages don't follow a convention, attempt to classify by reading the subject
line and list unclassifiable commits separately.

**Test discipline**
- For each feature/fix commit: were test files also touched in that commit?
  (Heuristic: check if any `*_test.*`, `*.test.*`, `spec/`, or `test/` files appear in the same commit)
- Report: `N of M feature/fix commits included test changes`

**Activity pattern**
- Days with commits vs. days with no commits
- Largest single commit by files changed (flag as potential review concern if >20 files)

### Step 3 — Compose the report

```
RETROSPECTIVE: <date range>
Generated: <today's date>

## Summary

Commits: N total (by author: Alice: N, Bob: N, ...)
Changes: +N lines added, -N lines removed across N files
Types: N feat, N fix, N refactor, N test, N chore/docs

## Highlights

[List 3–5 most significant commits based on subject line and scope — not largest, most meaningful]

## Test discipline

N of M feat/fix commits included test file changes.
[If < 70%: flag as "below threshold — consider adding tests to recent untested commits"]

## Concerns

[Any of the following, if observed:]
- Commits with >20 files changed (potential for hard-to-review PRs)
- Commits directly to main without a PR (if detectable)
- Long gaps in activity (>3 days) mid-week
- Commits with subject lines that don't describe what changed

## Suggested focus for next week

[Based on the type breakdown and MEMORY.md current phase: what should the team prioritize?
Keep to 2–3 specific, actionable items.]
```

Save the report to `docs/retros/YYYY-WXX.md` (ISO week number).

## Rules

- Never include author email addresses in the report (use name only)
- Never editorialize about individual contributors — focus on patterns, not people
- If the repository has no commits in the period, report "No commits in this period" and stop
