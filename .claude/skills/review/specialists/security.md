# Security Specialist

Review the diff for security vulnerabilities. Apply each check to the actual changed lines only.

## Checklist

**Injection (HIGH if present)**
- SQL: Is user input concatenated into a query string without parameterization?
- Command: Is user input passed to shell execution (`exec`, `os.system`, `subprocess` with `shell=True`)?
- Template/XSS: Is user input rendered without escaping into HTML, JS, or a template engine?
- Path traversal: Is user-supplied path joined without normalization/validation?

**Secrets (HIGH if present)**
- Are API keys, tokens, passwords, or private keys hardcoded in the diff?
- Are credentials logged or included in error responses?
- Are new environment variable names added without a corresponding `.env.example` entry?

**Authentication and authorization (HIGH if present)**
- Is a new endpoint added without authentication middleware?
- Is a permission check removed or weakened?
- Is session validation bypassed or skipped on any code path?
- Is a JWT or session token accepted without signature verification?

**Deserialization and parsing (MEDIUM)**
- Is untrusted input deserialized (JSON.parse, pickle, yaml.load, XML) without validation?
- Are there prototype pollution risks (JavaScript object spread/assign from user input)?

**Privacy (check against CLAUDE.md requirements)**
- Does the diff introduce logging of user inputs, emails, IDs, or query strings?
- Does the diff add a new cookie, fingerprint, or persistent session token?
- Does the diff add a request to a third-party URL from the UI layer?

## Severity Guide

HIGH: Exploitable without special circumstances, or directly violates a privacy requirement.
MEDIUM: Exploitable under specific conditions, or increases attack surface meaningfully.
LOW: Minor hardening gap that is not directly exploitable from the diff alone.
