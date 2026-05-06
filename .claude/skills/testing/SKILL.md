# Testing Skill

Language-agnostic test authoring with signal-based completion.

## When to Invoke

- Writing tests for a new feature
- Fixing a failing test
- Establishing a test harness for a new component
- Auditing test quality for an existing module

## Two-Tier Test Structure

### Fast Tests (always run)

Characteristics:
- Unit tests and mock-based tests
- Run in under 30 seconds per test
- No external dependencies (no network, no real database, no filesystem beyond temp files)
- Run on every commit, locally and in CI

When writing fast tests, prefer:
- Testing behavior through the public API of the unit, not internal state
- One assertion per test where possible — each test should have one clear failure mode
- Meaningful names: `test_{component}_{scenario}_{expected_outcome}`

### Slow Tests (integration and end-to-end)

Characteristics:
- Integration and end-to-end tests
- May take more than 30 seconds
- May use real external services or a real database
- Run in CI on every PR and on demand locally

When writing slow tests, require:
- Signal-based completion (never fixed sleeps — see below)
- Documented setup and teardown that leaves no persistent side effects
- Explicit tagging or grouping so they can be skipped during fast local iteration

## Process

### Step 1 — Read Test Command

Read the Test command from the Commands table in CLAUDE.md.

If not defined, use AskUserQuestion to get the correct command. Do not assume a test
runner or file naming convention based on the language.

### Step 2 — Identify What to Test

Before writing any test code, identify:
- What behavior is being tested? (Not "what code" — what observable behavior.)
- What inputs trigger the behavior?
- What outputs or side effects confirm the behavior occurred?
- What edge cases exist? (Empty input, boundary values, failure paths, concurrent access.)

Write this down before writing test code. Tests written without a clear behavioral
specification tend to test implementation details rather than behavior, and break when
the implementation changes even when the behavior is correct.

### Step 3 — Write Tests

Follow the naming convention: `test_{component}_{scenario}_{expected_outcome}`

Examples:
- `test_auth_expired_token_returns_unauthorized`
- `test_search_empty_query_returns_empty_results`
- `test_crawler_robots_txt_disallow_skips_url`

Each test should:
- Have one clear assertion (or a small number of related assertions with one failure mode)
- Be independent — it should not depend on the order of test execution
- Clean up after itself — no shared state left between tests
- Fail for the right reason — if you break the behavior, this test should catch it

### Step 4 — Signal-Based Completion

Never use fixed sleeps to wait for an asynchronous operation.

Instead, wait for an observable signal:
- A specific log line that indicates the operation completed
- A health or status endpoint returning a specific value
- A file appearing in a known location
- An observable state change that can be polled

Polling with a timeout is acceptable. Fixed sleeps are not. A test with `sleep 5` is
a flaky test waiting to reveal itself.

### Step 5 — Run and Verify

Run the test suite after adding tests. Confirm:
- New tests pass
- Existing tests still pass (no regressions from test infrastructure changes)
- Tests fail for the right reason when the behavior is broken (optional: temporarily
  break the implementation and verify the test catches it)

## Never Weaken Tests

If a test fails because the underlying code is broken, fix the code. Do not:
- Weaken assertions or thresholds to match broken behavior
- Mark tests as skipped without a documented reason
- Narrow the test inputs to avoid triggering the failure

The point of a test is to detect when behavior regresses. A test that cannot detect a
regression is not a test — it is overhead.

## Blame Protocol

Before claiming a test failure is pre-existing or unrelated to your change:
1. Run the test on the base branch
2. Paste the actual output
3. Compare to the failure you are observing

If the test was failing on the base branch, document it as pre-existing with evidence.
If it was passing on the base branch, it is a regression introduced by your change.
