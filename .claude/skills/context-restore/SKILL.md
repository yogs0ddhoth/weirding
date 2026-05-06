# Context Restore Skill

Resume a previous session from a saved context file.

## When to Invoke

- At the start of a session to restore where work left off
- When picking up a branch someone else was working on
- After returning to a branch that was set aside for more than a day

## Process

### Step 1 — Find the save file

Check `.claude/context/` for a file matching the current branch:

```bash
git branch --show-current
ls .claude/context/
```

If a file matching the current branch exists, read it. If no exact match exists, list all
available context files and present them to the user — do not guess which one applies.

If no context files exist at all, say so and proceed without context. Do not invent prior
state.

### Step 2 — Read and present the briefing

Read the save file and present a concise briefing:

```
CONTEXT RESTORED: <branch name>
Saved: <timestamp>
Phase: <phase from save file>

Goal: [one sentence]

Progress: [key completed items]

Remaining Work:
  1. [highest priority item]
  2. [next item]
  [...]

Notes: [any gotchas or blockers from the save file]
```

Keep the briefing to one screen. If the save file has extensive notes, summarize rather
than dump — the developer can read the full file at `.claude/context/<branch>.md`.

### Step 3 — Cross-check with current state

After presenting the briefing, run:

```bash
git log --oneline -5
git status --short
```

Report any discrepancy between what the save file says was completed and what git
history shows. If commits were made after the save was written, note what changed.

### Step 4 — Suggest next action

Based on the Remaining Work list, suggest the most specific next step:

> "Based on the context, the next action is [specific task]. Would you like to continue?"

Wait for the user to confirm before proceeding.

## Rules

- Never fabricate prior state if no context file exists — say "no saved context found"
- Never silently skip the git cross-check — prior state may have changed
- Never claim work is done based on the save file alone — verify against git log
