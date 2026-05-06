# Canary Skill

Post-deploy health verification using curl-based endpoint checks and log scanning.
No browser or external binary required.

## When to Invoke

- Immediately after a production or staging deploy
- When a deploy is suspected of causing degradation
- As part of the `/ship` post-deploy verification step

## Configuration

Read smoke-test configuration from CLAUDE.md if defined:

```
## Smoke Tests [PROJECT]
| Endpoint | Expected Status | Max Response Time |
|----------|----------------|-------------------|
| GET /health | 200 | 500ms |
| GET /api/v1/status | 200 | 1000ms |
```

If no smoke tests are defined in CLAUDE.md, ask the user for:
1. The base URL to check (required)
2. 1–3 key endpoints to verify (required)
3. Whether to tail logs (optional, requires a log command defined in CLAUDE.md)

## Process

### Step 1 — Endpoint checks

For each configured endpoint, run:

```bash
start=$(date +%s%3N)
response=$(curl -s -o /tmp/canary_body -w "%{http_code}" \
  --max-time 10 --connect-timeout 5 <url>)
elapsed=$(($(date +%s%3N) - start))
```

Check:
- HTTP status matches expected (default: 200)
- Response time is within threshold (default: 2000ms)
- Response body does not contain error indicators (default: grep for "error", "exception",
  "traceback", "500" in body — suppress if false positives are expected)

Retry once on timeout before reporting failure.

### Step 2 — Log scan (if log command defined)

If a log command is defined in CLAUDE.md (e.g., `kubectl logs -l app=myapp --since=5m`),
run it and scan for:
- ERROR or FATAL log lines
- Stack traces or exception patterns
- Unusual volume of WARN lines

Report: line count per level in the post-deploy window.

### Step 3 — Report

```
CANARY: <environment> — <timestamp>

Endpoint checks:
  GET /health          200  142ms  ✓
  GET /api/v1/status   200  89ms   ✓
  GET /api/v1/users    500  —      ✗  FAIL

Log scan:
  ERROR: 3 lines (0 before deploy baseline)
  WARN:  12 lines
  FATAL: 0

RESULT: [ALL GREEN | DEGRADED | DOWN]

Issues:
  [List each failing check with exact response and recommended action]
```

**ALL GREEN:** All endpoints returned expected status within threshold; no new errors in logs.
**DEGRADED:** Some endpoints pass but response times are elevated, or error count is above baseline.
**DOWN:** One or more critical endpoints failed.

On DEGRADED or DOWN: present findings and ask whether to proceed, roll back, or investigate.
Do not roll back automatically.

## Rules

- Never assume success without reading actual curl output
- Retry once before declaring a failure (transient blips happen)
- Do not flag pre-existing errors from before the deploy window as post-deploy issues
- Do not modify the running system — report only, decide with the user
