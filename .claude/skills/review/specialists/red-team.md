# Red Team Specialist

Adversarial review — look for what can go wrong that the author didn't anticipate.
Think like an attacker, an impatient user, a flaky network, and a future maintainer.

## Checklist

**Failure modes (MEDIUM–HIGH)**
- What happens when a downstream service is unavailable or returns an unexpected status?
  Does the code fail safely, or does it propagate a confusing error or silently succeed?
- What happens when the input is valid but unexpected (empty string, zero, very large number,
  unicode edge cases, whitespace-only strings)?
- What happens when the operation succeeds partially (write half-completes, connection drops
  mid-stream)? Is there a recovery path or is state left inconsistent?
- Is there an assumed ordering of operations that the runtime may not guarantee?

**Trust boundary violations (HIGH)**
- Does the code trust data from an external source (API, queue, user input) without
  re-validating it at the trust boundary where it enters this component?
- Is data from one security context passed directly into another without sanitization
  (e.g., user-supplied data written to a log query, admin data visible to non-admins)?
- Is there a TOCTOU (time-of-check-time-of-use) race where state is validated but can
  change before it is used?

**Silent failures (HIGH)**
- Is an error returned to the caller but there is no indication it was handled?
- Does a background job/goroutine fail without any observable signal (no log, no metric,
  no retry)?
- Is a configuration value assumed to exist that might be absent in some deployments?

**Operational surprises (MEDIUM)**
- Does the code introduce a new runtime dependency (a service, config key, or env var)
  without a startup check or clear error message when it is absent?
- Does the code increase the blast radius of a bug — e.g., changing a scoped operation
  to a global one?
- Would a 10x traffic spike cause this code to degrade gracefully, or fail catastrophically?

## Note

Red team findings are hypotheticals unless the diff provides clear evidence they can
occur. Distinguish "this code could fail if X" (flag with LOW/MEDIUM) from "this code
will fail because X is guaranteed to happen" (flag with HIGH).
