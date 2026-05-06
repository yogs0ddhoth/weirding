# /retro

Run a weekly engineering retrospective.

Read `.claude/skills/retro/SKILL.md` and follow its process.

- Default (no argument): last 7 days
- `--since YYYY-MM-DD`: from that date to today

Collect git history, compute commit metrics, type breakdown, and test discipline score.
Save report to `docs/retros/YYYY-WXX.md` (ISO week number).

Do not include author email addresses or editorialise about individuals.
