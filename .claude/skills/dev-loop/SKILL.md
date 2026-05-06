# Dev Loop Skill

Fast iteration with signal detection and time-bounded execution.

## When to Invoke

- Verifying that a code change compiles and its tests pass
- Running a quick end-to-end cycle to check that a feature emits the expected signal
- Confirming a build is clean before committing
- Any "does this work?" check that would pollute the main session with verbose output

## Process

### Step 1 — Read Commands

Read the Commands table in CLAUDE.md for the project's build and test commands.

If the relevant command is not defined in CLAUDE.md, use AskUserQuestion to get the
correct command from the user. Do not guess, infer, or try common commands speculatively.

### Step 2 — Set Bounds

Set a timeout before running:
- Build commands: 30 seconds default. If the project's build is known to be longer,
  note the expected duration and set the timeout accordingly.
- Test commands: 60 seconds default for fast tests, 300 seconds for integration tests.

If a command exceeds its timeout, report that it timed out — do not wait indefinitely
or retry silently.

### Step 3 — Run and Wait for Signal

Run the command. Wait for a signal — do not use fixed sleeps.

A signal is a specific, observable output:
- Build: exit code 0 with no warning lines
- Test: "X tests passed, 0 failed" or equivalent
- Server: health endpoint returns 200, or specific log line indicating readiness
- Feature: the specific log line or response that confirms the feature is working

If the expected signal does not appear within the timeout, report the timeout and the
last N lines of output. Do not claim success.

### Step 4 — Report Concisely

Do not flood the main session with full build or test logs.

Report:
- Pass: command, duration, signal observed
- Fail: command, failure output (relevant lines only), suggested next step

If the output is too long for the main session, note that it was dispatched to an agent
and summarize the result.

## Long-Running Task Discipline

If a task will take more than 5 minutes:

1. Note the expected duration and check back at approximately 270-second intervals
2. Report progress at each check: "Still running. Elapsed: Xs. Last output: ..."
3. Never silently abandon — if the task exceeds 3x the expected duration, report it
   and ask whether to continue or cancel

Never use fixed sleeps. The check interval should be based on expected task duration,
and progress reports should reflect actual output, not time elapsed.

## Key Rules

- Never use fixed sleeps (`sleep 30` while waiting for a server to start is wrong)
  Wait for the actual readiness signal instead
- Never tail logs in the main session — dispatch to an agent if log monitoring is needed
- Never log raw PII — if a test or debug run would emit user data, sanitize it or
  redirect output to a file and summarize
- Never claim done without reading actual output — "should be fine" is not a result

## Common Failure Patterns

These patterns indicate the dev loop is being misused. Avoid them:

- Running the full test suite in the main session and pasting all output
- Using `sleep 10` to wait for a service instead of polling the health endpoint
- Running a build and interpreting warnings as "clean"
- Claiming a feature works based on no error output rather than a positive signal
