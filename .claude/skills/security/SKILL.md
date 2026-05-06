# Security Skill

Structured security audit covering secrets, dependencies, OWASP Top 10, and STRIDE
threat modeling. No external browser or binary required.

## When to Invoke

- Before any production deployment
- When the codebase handles a new category of user data
- After adding or upgrading authentication, authorization, or session handling
- Monthly as a routine audit

## Two Modes

**Daily (default):** High-confidence findings only (≥8/10 confidence). Fast. Focused on
the highest-risk areas. Use before a deploy.

**Comprehensive (`/security --full`):** All findings including low-confidence observations
and speculative STRIDE threats. Slower. Use monthly or before a major release.

## Process

### Step 1 — Secrets archaeology

Search the codebase for credential patterns:

```bash
# Common secret patterns
grep -rn --include="*.{js,ts,py,go,rb,java,env,yaml,yml,json,toml,sh}" \
  -E "(api[_-]?key|secret[_-]?key|password|token|private[_-]?key|access[_-]?key)\s*[=:]\s*['\"]?[a-zA-Z0-9+/]{20,}" \
  --exclude-dir=".git" .

# High-entropy strings that might be secrets (false positives expected — review carefully)
grep -rn --include="*.{env,env.local,.env.*}" -v "^#\|^$\|PLACEHOLDER\|EXAMPLE\|YOUR_" . 2>/dev/null
```

Report each match with file, line, and the matched string (redacted — show first 4 chars + ***).

### Step 2 — Dependency audit

Run the appropriate audit command for this project's stack (from Commands table or inferred):

- Node.js: `npm audit --json` or `yarn audit --json`
- Python: `pip-audit --json` or `safety check --json`
- Go: `govulncheck ./...`
- Rust: `cargo audit --json`
- Ruby: `bundle audit check --update`
- Java/Maven: `mvn dependency-check:check`

If none of these commands exist, note it as NOT AUDITED and flag for investigation.

Parse the output and report:
- CRITICAL: count + names
- HIGH: count + names
- MEDIUM: count (no need to enumerate all)
- LOW: count only

### Step 3 — OWASP Top 10 scan

For each OWASP category, check the codebase for indicators — focus on the diff since last
audit if one is available, otherwise sample key files (auth, routing, input handling):

1. **Injection** — SQL/command/template injection patterns (grep for string concatenation into queries or shell calls)
2. **Broken Authentication** — hardcoded credentials, weak session management, missing MFA enforcement
3. **Sensitive Data Exposure** — PII in logs (grep for log statements near user data variables), unencrypted storage
4. **XML/Deserialization** — untrusted deserialization, XML external entity processing
5. **Security Misconfiguration** — debug mode in production config, permissive CORS, directory listing enabled
6. **Vulnerable Components** — covered by Step 2
7. **Insufficient Logging** — missing audit logs for security events (login, permission change, data export)
8. **SSRF** — user-controlled URLs passed to server-side HTTP clients without validation
9. **LLM/AI trust boundaries** (if applicable) — user input reaching prompt context without sanitization

### Step 4 — STRIDE threat model (comprehensive mode only)

For each category, identify the most significant threat given the current codebase:

- **Spoofing** — can an attacker impersonate a user or service?
- **Tampering** — can an attacker modify data in transit or at rest?
- **Repudiation** — can an attacker deny performing an action that was recorded?
- **Information Disclosure** — can an attacker read data they should not have?
- **Denial of Service** — can an attacker degrade or stop service availability?
- **Elevation of Privilege** — can an attacker gain permissions beyond their role?

For each identified threat, state: attack vector, affected component, likelihood (H/M/L),
impact (H/M/L), and recommended mitigation.

### Step 5 — Report

```
SECURITY AUDIT: <project name>
Mode: [DAILY | COMPREHENSIVE]
Date: <ISO date>

Secrets:        [CLEAN | FINDINGS — N matches]
Dependencies:   [CLEAN | FINDINGS — N critical, N high | NOT AUDITED]
OWASP:          [CLEAN | FINDINGS — list categories with findings]
STRIDE:         [N/A (daily) | findings summary]

RESULT: [CLEAN | FINDINGS REQUIRE ATTENTION]

---
Findings:
[Grouped by category, with file:line, description, severity, recommended fix]

Privacy Check (per CLAUDE.md requirements):
[Confirm each privacy requirement is met, or flag violations]
```

Save the report to `docs/security/YYYY-MM-DD-audit.md` after generation.

## Rules

- Redact actual secret values — report file:line and first 4 characters only
- Do NOT run `npm audit fix` or apply dependency upgrades automatically — report only
- Daily mode: skip STRIDE, skip LOW/INFO OWASP findings
- Never claim CLEAN without running Steps 1 and 2
