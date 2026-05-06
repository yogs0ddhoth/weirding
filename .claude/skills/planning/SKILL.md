# Planning Skill

Produce a written implementation plan before any coding begins.

## When to Invoke

- After ideation and research are complete for a feature
- Before starting any non-trivial implementation
- When a feature touches protected files or has cross-cutting impact
- Whenever "what are we building?" is clear but "how?" is not

## Hard Rule

Do not write any code. This skill produces a plan artifact only. The calling command
(`/plan`) is responsible for routing the plan through the planner agent for review and
presenting the plan + verdict to the user for explicit approval before any code is written.

## Process

### Step 1 — Read Current Context

Before proposing anything:
- Read `.claude/memory/MEMORY.md` for current phase, confirmed standards, and active constraints
- Read `docs/adr/README.md` and any ADRs relevant to the components being changed
- Confirm the feature scope from ideation output (or ask if missing)

### Step 2 — Identify Protected Files

Check every file the plan proposes to modify against the Protected Files list in CLAUDE.md.

For each protected file:
- State which tier (Tier 1 or Tier 2)
- State whether explicit user approval has been obtained
- If Tier 1 and no approval: do NOT include that file in the plan — flag it and ask

### Step 3 — Break Into Phases

Decompose the implementation into discrete phases. Each phase must be:
- Completable and buildable in isolation (no half-implemented dependencies blocking the build)
- Testable in isolation (there is a clear signal of correctness for this phase alone)
- Estimable (you can state roughly how long this phase should take)

Phase granularity: aim for phases that take hours, not days. Long phases hide complexity
and make it harder to detect problems early.

For each phase, list:
- Files to be created
- Files to be modified
- Any protected files (with tier)
- The test or signal that confirms this phase is complete

### Step 4 — Identify ADR Candidates

Flag any decision in the plan that warrants an Architecture Decision Record:
- Trade-offs between two credible alternatives where a choice must be made
- Cross-component impact (the decision constrains future work in other areas)
- Changes to protected files or core interfaces
- Anything that would take significant effort to reverse

For each ADR candidate: state the decision topic and why it warrants an ADR. The ADR
should be written before coding the affected phase begins.

### Step 5 — Simplicity Challenge

Before finalizing the plan, ask: is there a simpler approach?

Complexity has real costs: more debugging surface area, more agent comprehension burden,
more maintenance. If a two-phase plan achieves the same goal as a five-phase plan for the
current requirements, the two-phase plan is correct.

State what was considered and rejected, and why.

### Step 6 — Save plan artifact

Determine the current branch slug:
```bash
git rev-parse --abbrev-ref HEAD | tr '/' '-'
```

Save the completed plan to `.claude/plans/<branch-slug>.md`. Create the `.claude/plans/`
directory if it does not exist. The `/review` skill reads this file to detect scope drift —
the saved plan must reflect what was actually approved, not a draft.

Then return the plan artifact to the calling command. Do not present it to the user
directly — the `/plan` command dispatches the planner agent to review it first.

## Output Format

```
IMPLEMENTATION PLAN: [Feature name]

Context:
[One paragraph: what problem this solves, current phase, relevant ADRs]

Phase 1 — [Name]
Files created: [list]
Files modified: [list]
Protected files: [list with tier, or "none"]
Completion signal: [specific observable outcome]
Estimate: [hours]

Phase 2 — [Name]
[Same structure]

[Additional phases...]

ADR Candidates:
- [Decision topic]: [Why it warrants an ADR]

Protected Files Requiring Approval:
- [File] (Tier 1): [Current approval status]

Simplicity Check:
[What was considered and rejected]

---
AWAITING HUMAN APPROVAL BEFORE PROCEEDING.
State: PROCEED, MODIFY [description], or REJECT.
```
