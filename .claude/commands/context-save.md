# /context-save

Save current session state to `.claude/context/<branch>.md` so the next session can restore it.

Read `.claude/skills/context-save/SKILL.md` and follow its process.

Run `git branch --show-current`, `git status --short`, and `git log --oneline -10` before
writing. Capture: goal, progress, decisions made, remaining work (prioritized), and notes.

Do NOT include credentials, PII, API keys, or raw user inputs in the save file.

Report the save file path and a one-line summary of Remaining Work to confirm the save.
