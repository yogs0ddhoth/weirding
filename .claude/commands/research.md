# /research

Dispatch the researcher agent for the technical question: $ARGUMENTS

Do not run the research process in this session. Dispatch:

Agent(subagent_type="researcher", prompt="Research this question for the project: $ARGUMENTS\n\nRead CLAUDE.md for project constraints and non-negotiable requirements. Read .claude/memory/MEMORY.md for the current stack and phase. Return the full structured research report.")

Present the agent's report to the user verbatim.
