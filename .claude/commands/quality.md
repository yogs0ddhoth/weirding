# /quality

Dispatch a quality-check agent. Do not run build, test, or lint commands in this session.

1. Determine gate level:
   - FAST — feature branches, before any commit
   - FULL — before merging to main or before any deployment

2. Dispatch:

   Agent(prompt="Run the quality gate at [FAST|FULL] level using the quality-check skill. Read all commands from the Commands table in CLAUDE.md. Report the complete QUALITY GATE output with evidence for each check.")

3. Present the agent's report to the user verbatim.

4. If RESULT is BLOCKED: list each blocking issue clearly and ask the user how to proceed.
   Do not attempt to fix issues in this session — report and wait for instruction.
