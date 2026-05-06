# Debugging Skill

Document-driven, systematic debugging.

## When to Invoke

- A test fails unexpectedly
- A feature does not behave as expected
- A regression appeared after a recent change
- The system emits an error that is not immediately obvious

## Core Principle

Document first. Investigate second.

The instinct to immediately start changing code when something breaks leads to
thrashing — making changes, re-running, seeing different results, losing track of what
was tried. Document the problem precisely before touching anything. This constraint
forces clarity about what is actually wrong and prevents accidental fixes that mask
the real cause.

## Process

### Step 1 — Write the Problem Document

Before any investigation, write down:

```
PROBLEM: [One sentence. What is wrong?]
EXPECTED: [What observable behavior should occur?]
ACTUAL: [What observable behavior actually occurs?]
FIRST SEEN: [When did this start? Commit hash, date, or "since the beginning".]
REPRODUCTION STEPS: [Minimal steps to reproduce. Start from a clean state.]
```

If you cannot fill in all five fields, the problem is not yet understood. Do not
investigate until it is.

### Step 2 — Form Hypotheses

Write at least two competing hypotheses that could explain the problem. This is not
optional — a single hypothesis is confirmation bias waiting to manifest.

For each hypothesis:
- State the mechanism (why would this cause the observed behavior?)
- State the evidence for it (what in the system supports this hypothesis?)
- State the evidence against it (what contradicts it?)
- State how to test it (what would definitively confirm or rule out this hypothesis?)

### Step 3 — Investigate Cheapest First

Work through investigations in order of cost, starting with the cheapest:

1. Read the failing test or error message carefully. Many investigations end here.
   Does the error message actually say what went wrong? Is there a stack trace? A line
   number? A specific assertion that failed?

2. Check git log for recent changes. When did the failure appear? What changed around
   that time?
   ```
   git log --oneline --since="[first seen date]" -- [relevant files]
   ```

3. Create a minimal reproducer. Strip away everything that is not necessary to trigger
   the failure. The minimal reproducer makes the root cause obvious in a way that a
   complex test environment does not.

4. Add targeted logging or tracing. Add one log statement at the precise point of
   divergence — not a cascade of logging throughout the file. "Where does the actual
   value diverge from the expected value?" is the question. Find that exact point.

5. Run the full test suite. Sometimes the failure is a symptom of a broader problem
   that other tests already capture. Knowing which other tests fail narrows the scope
   of the root cause.

### Step 4 — Blame Protocol

Before claiming a failure is pre-existing or unrelated to your change:
1. Check out the base branch
2. Run the failing test
3. Paste the actual output from the base branch

If it fails on the base branch: document it as pre-existing with evidence. If it passes
on the base branch: it is a regression introduced by your change, and finding your
change as the root cause is now the priority.

Never claim pre-existing without evidence. "I didn't touch that file" is not evidence.

### Step 5 — Fix and Verify

Once the root cause is identified:
1. State the root cause precisely (not "something was wrong with X" — what specifically)
2. Make the fix
3. Run the full test suite to confirm the fix resolves the failure and does not introduce
   new failures
4. Verify the fix on the minimal reproducer if one was created

## Output Format

When reporting a debugging investigation:

```
PROBLEM: [one sentence]
EXPECTED: [observable correct behavior]
ACTUAL: [observable incorrect behavior]
FIRST SEEN: [commit hash or date]

HYPOTHESIS 1: [explanation]
  Evidence for: [...]
  Evidence against: [...]
  Test: [how to confirm or rule out]

HYPOTHESIS 2: [explanation]
  Evidence for: [...]
  Evidence against: [...]
  Test: [how to confirm or rule out]

INVESTIGATION LOG:
  [What was tried, what was observed, in order]

ROOT CAUSE: [Specific, precise statement of what caused the failure]

FIX: [What was changed and why]

VERIFICATION: [Test output confirming the fix]
```

## Anti-Patterns to Avoid

- Changing multiple things at once and then not knowing which change fixed it
- Claiming fixed without running the test suite
- Adding log statements throughout a file instead of at the precise divergence point
- Blaming pre-existing issues without checking the base branch
- Weakening the test instead of fixing the code
