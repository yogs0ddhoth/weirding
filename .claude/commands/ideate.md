# /ideate

Invoke the ideation skill for: $ARGUMENTS

Produce a structured scope document covering:
1. Problem — stated in user terms
2. Success criteria — specific and observable
3. Scope — explicit in/out
4. Dependencies — what must exist first
5. Complexity estimate — S/M/L/XL with justification
6. Risks — technical, dependency, scope, and privacy/integrity risks

If research questions are identified during ideation — technical unknowns, uncharacterized
dependencies, or unresolved design choices — dispatch the researcher agent for each without
waiting for the user to ask:

Agent(subagent_type="researcher", prompt="Research this question for the project: [specific question]. Read CLAUDE.md for project constraints. Read .claude/memory/MEMORY.md for current stack and phase. Return the full structured research report.")

Include research summaries inline in the scope document under the relevant risk or
dependency. Run multiple researcher dispatches in parallel if there are independent
questions.

End with a suggested next step: `/research [question]` if unknowns remain after dispatch,
or `/plan [feature name]` if scope is clear.

Do NOT produce implementation details, file lists, or phase breakdowns. That is the
planning skill's job.
