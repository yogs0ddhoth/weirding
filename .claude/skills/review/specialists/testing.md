# Testing Specialist

Review the diff for test coverage quality. Apply to changed and new code.

## Checklist

**Coverage gaps (MEDIUM)**
- Does new logic have corresponding tests? (Not "is coverage 80%?" — does this specific
  new function, branch, or handler have at least one test?)
- Are error paths tested, or only the happy path?
- Are boundary values tested (empty input, maximum input, off-by-one conditions)?
- If a bug is fixed, is there a new regression test that would have caught the original bug?

**Assertion quality (MEDIUM)**
- Do tests assert specific values, or do they only assert that "something" happened?
  (`assert result.length > 0` is weaker than `assert result.length == 3`)
- Are tests checking observable behavior or implementation details?
  (Tests that assert internal state break on refactoring without the behavior changing.)
- Is `assert True` or equivalent used as a placeholder without a real assertion?

**Test independence (MEDIUM)**
- Does the test depend on global state that another test might modify?
- Does the test depend on execution order (would it fail if run in isolation)?
- Does the test leave state behind (open files, database rows, running processes)?

**Signal-based completion (HIGH if violated)**
- Does the test use `sleep()` or a fixed wait to synchronize with async behavior?
  (Fixed sleeps are flaky tests waiting to reveal themselves — use polling with a timeout
  or an event signal instead.)

**Scope (LOW)**
- Does the diff remove or weaken existing test assertions without a documented reason?
  (Weakened assertions that match broken behavior are a quality violation per CLAUDE.md.)
- Are tests being skipped or marked as `xfail` / `skip` without a linked reason?
