# /test

Write or audit tests for: $ARGUMENTS

Invoke the testing skill (`.claude/skills/testing/SKILL.md`).

Read the Test command from CLAUDE.md. Identify what behavior to test, write tests
following `test_{component}_{scenario}_{expected_outcome}` naming, and verify
signal-based completion (no fixed sleeps).

Run the test suite after writing. Report: new tests added, pass/fail result.
