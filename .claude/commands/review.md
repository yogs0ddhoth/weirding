# /review

Run a structured code review for: $ARGUMENTS

Read `.claude/skills/review/SKILL.md` and follow its process exactly.

- If $ARGUMENTS is a number: fetch the PR diff via GitHub MCP (`github` server)
- If $ARGUMENTS is a branch name: `git diff <branch>...HEAD`
- If $ARGUMENTS is empty: `git diff $(git merge-base HEAD origin/main)...HEAD`

Run all seven specialist checklists in parallel. Read each from
`.claude/skills/review/specialists/`. Skip specialists whose domain is not
represented in the diff (except `maintainability.md` — always run).

Check `.claude/plans/` for a saved plan to enable scope drift detection.

Report: APPROVE or REQUEST CHANGES with evidence-backed findings per specialist.
Every finding must cite file and line number.
