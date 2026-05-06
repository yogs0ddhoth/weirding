# /canary

Run post-deploy health verification for: $ARGUMENTS

Read `.claude/skills/canary/SKILL.md` and follow its process.

- If $ARGUMENTS is a URL: use it as the base URL for endpoint checks
- If $ARGUMENTS is empty: read smoke test endpoints from CLAUDE.md; if not configured, ask

Check each endpoint with curl: HTTP status, response time, body error indicators.
Scan logs if a log command is defined in CLAUDE.md.

Report: ALL GREEN / DEGRADED / DOWN. Do not roll back or modify anything — report and
let the developer decide.
