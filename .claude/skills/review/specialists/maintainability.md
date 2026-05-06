# Maintainability Specialist

Review the diff for code quality and maintainability. Always run — skip nothing.

## Checklist

**Complexity (MEDIUM)**
- Does any new function have more than 3 levels of nesting?
- Does any new function handle more than 2–3 distinct responsibilities?
- Are there long chains of conditionals that could be simplified or extracted?
- Are magic constants used where a named constant or enum would make intent clear?

**Naming and clarity (LOW)**
- Are variable and function names descriptive at the appropriate level of abstraction?
- Are boolean variables named as questions (`isValid`, `hasPermission`) rather than states?
- Are error variables named `err` or `e` when there are multiple in scope (causing confusion)?

**Error handling (MEDIUM–HIGH depending on path)**
- Are errors silently swallowed (caught and not logged or re-raised)?
- Are errors returned as generic strings instead of typed errors that callers can match on?
- Is a panic / unhandled exception possible on a code path that should be safe?
- Are resource handles (files, connections) closed in all exit paths, including error paths?

**Dead code and debt (LOW)**
- Is new code unreachable (behind an always-false condition, after an unconditional return)?
- Are deprecated functions called when a current alternative exists?
- Are TODOs introduced without a linked issue or explicit acceptance that they are deferred?
- Is commented-out code added? (Should be deleted; git history preserves it.)

**Consistency (LOW)**
- Does the diff follow the existing style for error handling, naming, and structure?
- Does it use the same patterns as adjacent code in the same file?

## Note

Maintainability findings are almost never blocking on their own. Report them clearly so the
author can address them if they agree, but do not elevate these to HIGH without a concrete
reason they create a real risk (e.g., a silent error swallow on a security-critical path).
