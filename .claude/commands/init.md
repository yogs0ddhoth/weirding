# /init

Initialize this Melange framework for: $ARGUMENTS

Read `.claude/skills/init/SKILL.md` and follow its process exactly.

Supported flags: `--full` (default), `--governance-only`, `--commands-only`. See SKILL.md for behavior.

## Sequence

1. **Guard** — check CLAUDE.md for `{{` strings; if none, report already initialized and exit
2. **Phase 1: Ideation** — run the ideation skill on the provided description (or ask once
   if no argument was given); extract project description and complexity estimate
3. **Phase 2: Technical interview** — ask ALL questions in one batch: commands, file paths,
   git remote; wait for the user's response before continuing
4. **Phase 3: Roadmap** — derive 2–5 phase names from ideation scope and complexity
5. **Phase 4: Fill placeholders** — write real values into CLAUDE.md, README.md, MEMORY.md,
   PROJECT_ROADMAP.md, and `.claude/settings.json`; remove N/A rows entirely
6. **Phase 5: Verification gate** — check all files for remaining placeholders, confirm
   permissions are set, report INIT COMPLETE or BLOCKED with specific issues

Do not begin Phase 4 until the user has answered Phase 2's questions.
Do not report INIT COMPLETE with any failing gate check.
