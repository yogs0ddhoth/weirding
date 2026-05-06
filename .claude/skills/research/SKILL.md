# Research Skill

The research process for this project is defined in and executed by the `researcher`
specialist agent: `.claude/agents/researcher.md`.

## How to invoke

**From a slash command or the main session:**
Use `/research [question]` — the command dispatches the researcher agent automatically.

**From an agent context:**
Dispatch with `Agent(subagent_type="researcher", prompt="Research: [question]...")`.

Do not duplicate the research process here. `.claude/agents/researcher.md` is the
authoritative source. Any changes to the research process belong there.
