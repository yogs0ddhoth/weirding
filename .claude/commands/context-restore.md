# /context-restore

Restore session context from a saved context file for: $ARGUMENTS

Read `.claude/skills/context-restore/SKILL.md` and follow its process.

- If $ARGUMENTS names a branch: look for `.claude/context/<branch>.md`
- If $ARGUMENTS is empty: use `git branch --show-current` to find the current branch

Present a concise briefing (one screen). Cross-check against `git log --oneline -5` and
`git status --short`. Report any discrepancy between saved state and git reality.

Suggest the most specific next action based on the Remaining Work list.
