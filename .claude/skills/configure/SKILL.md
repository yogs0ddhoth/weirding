# Configure Skill

Modify the Melange framework configuration according to developer instruction.
Handles: skills, commands, hooks, permissions, CLAUDE.md content, and AGENTS.md.

## Classification: PROJECT vs UNIVERSAL

Before making any change, classify what is being modified:

**PROJECT — free to change:**
- `## Project` section (name, description)
- `## Commands` table (add/remove rows)
- `## Protected Files` tables (add/remove rows)
- `## Lifecycle` table (add rows; existing rows should not be removed)
- Skills: `.claude/skills/` (add/modify/remove)
- Commands: `.claude/commands/` (add/modify/remove)
- Hooks: `.claude/hooks/` (add/modify) and hook entries in `settings.json`
- Permissions: `settings.json` `permissions.allow` array
- `AGENTS.md` Available Skills and Available Agents tables

**UNIVERSAL — gated, requires written justification:**
- `## Development Workflow [UNIVERSAL]` — agent dispatch mandate and feature branch policy
- `## Quality Requirements [UNIVERSAL]` — zero-warning policy, testing integrity
- `## Privacy Requirements [UNIVERSAL]` — all privacy constraints
- `## Project Memory and ADRs [UNIVERSAL]` — memory priority and ADR rules
- `## MCP Servers [UNIVERSAL]` — configured MCP list (extending is fine; removing is gated)
- Core principles in `ETHOS.md`

If the requested change touches a UNIVERSAL section, stop and ask:

> "This change affects a UNIVERSAL section ([section name]), which encodes non-negotiable
> project discipline. Please provide written justification: why is this change necessary
> and why can it not be achieved within the existing constraints?"

Do not proceed until the developer provides justification. Record the justification as a
comment in the changed section and in MEMORY.md.

## Co-location Rules

When adding a new skill:
1. Create `.claude/skills/<name>/SKILL.md`
2. Add a row to the Available Skills table in `AGENTS.md`
3. If it represents a lifecycle step, add a row to the Lifecycle table in `CLAUDE.md`

When adding a new command:
1. Create `.claude/commands/<name>.md`
2. The command file should reference the corresponding skill (or contain the full logic if no separate skill is needed)

When adding a hook:
1. Create the hook script in `.claude/hooks/<name>.sh`
2. Add the hook entry to `settings.json` under the appropriate event key
3. Ensure the script is executable (note in instructions for Unix/macOS; Windows ignores chmod)

When removing a skill or command:
1. Delete the skill/command file
2. Remove the row from AGENTS.md and CLAUDE.md lifecycle table
3. Check whether any other skills or commands reference it — if so, update them

When updating permissions:
1. Read current `settings.json`
2. Add or remove entries from `permissions.allow`
3. Use exact command strings — no wildcards
4. Preserve the existing `hooks` block entirely

## Process

1. Read the current state of all affected files before making any change
2. Classify the change (PROJECT or UNIVERSAL)
3. If UNIVERSAL: ask for justification; stop until received
4. Identify all co-located files that need updating per the co-location rules above
5. Make all changes
6. Run the consistency verification pass (below)

## Consistency Verification

After all changes:

```
CONFIGURE GATE

Skills referenced in AGENTS.md:    [PASS | FAIL — list missing files]
Commands referencing existing skills: [PASS | FAIL — list broken references]
settings.json valid JSON:           [PASS | FAIL]
No new {{PLACEHOLDER}} introduced:  [PASS | FAIL]
UNIVERSAL sections unchanged:       [PASS | FAIL — or MODIFIED WITH JUSTIFICATION]

RESULT: [DONE | BLOCKED]
```

Report DONE only when all checks pass. If FAIL: list exactly what needs fixing.

## Rules

- Never make multiple structural changes in a single operation — one change at a time
- Never modify ADRs (append-only)
- Never delete MEMORY.md entries — add a "superseded by" note instead
- If in doubt whether a change is PROJECT or UNIVERSAL: treat it as UNIVERSAL
