# /debug

Debug: $ARGUMENTS

Invoke the debugging skill (`.claude/skills/debugging/SKILL.md`).

Write the problem document first (PROBLEM / EXPECTED / ACTUAL / FIRST SEEN /
REPRODUCTION STEPS). Do not touch code until all five fields are filled in.

Form at least two competing hypotheses. Investigate cheapest first: read the error,
check git log, create a minimal reproducer, add targeted logging.

Report: ROOT CAUSE + FIX + VERIFICATION (actual test output).
