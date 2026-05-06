# Context Save Skill

Capture current session state to a file so a future session can restore it exactly.

## When to Invoke

- Before ending a session with in-progress work
- Before switching to a different branch or task
- Whenever "I'll pick this up tomorrow" is true

## What to Capture

Run the following before writing the save file:

```bash
git branch --show-current
git status --short
git log --oneline -10
```

Then write a Markdown file to `.claude/context/<branch-slug>.md`, overwriting any
previous save for this branch:

```markdown
---
branch: <current branch name>
phase: <current phase from MEMORY.md>
timestamp: <ISO 8601 datetime>
---

## Goal

[One paragraph: what is this branch/session trying to accomplish?]

## Progress

[What has been completed? Be specific — file names, functions written, tests passing,
PRs opened. Not "worked on X" but "implemented X in Y, tests pass."]

## Decisions

[Design choices made during this session that should not be re-litigated next session.
Format: "Decision: [what was decided]. Reason: [why]."]

## Remaining Work

[Prioritized list of what is left before this branch/phase is complete. Most important
first. Be specific enough that a cold reader knows exactly what to do next.]

## Notes

[Gotchas discovered, things tried that didn't work, surprising behaviors, blocked items
with the specific blocker, context that would surprise someone picking this up cold.]
```

## Rules

- Do NOT include credential values, PII, API keys, or raw user inputs in any field
- Do NOT write "nothing to note" — if a section is genuinely empty, omit it entirely
- The file is git-tracked — it travels with the branch and is readable by teammates
- Overwrite the previous save for this branch (one file per branch, latest wins)

## After Writing

Report the save file path and a one-line summary of Remaining Work so the user can
confirm the save captured what matters before closing the session.
