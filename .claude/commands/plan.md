# /plan

Produce an implementation plan for: $ARGUMENTS, then dispatch the planner agent to review
it before presenting to the user.

## Step 1 — Produce the plan

Before writing anything:
1. Read `.claude/memory/MEMORY.md` for current phase, confirmed standards, and active constraints
2. Read `docs/adr/README.md` and any ADRs relevant to the components being changed
3. Check every proposed file against the Protected Files list in CLAUDE.md — flag Tier 1
   files and confirm approval before including them

Break the implementation into discrete phases. Each phase must be:
- Completable and buildable in isolation
- Testable in isolation with a clear completion signal
- Estimable in hours, not days

For each phase list: files created, files modified, protected files (with tier), completion
signal, estimate.

Flag ADR candidates: any decision involving trade-offs between credible alternatives,
cross-component impact, or changes that are hard to reverse.

Apply the simplicity challenge: state the simplest approach considered and why more phases
are needed if the plan has more than two.

## Step 2 — Persist the plan

The planning skill saves the plan to `.claude/plans/<branch-slug>.md` as part of Step 6.
Confirm the file exists before continuing. If it does not exist, create it now:

```bash
branch=$(git rev-parse --abbrev-ref HEAD | tr '/' '-')
mkdir -p .claude/plans
# write plan content to .claude/plans/${branch}.md
```

The `/review` skill uses this file for scope drift detection. The saved plan must reflect
the final agreed plan, not a draft — update it if the user requests modifications.

## Step 3 — Dispatch the planner agent

After persisting the plan, dispatch:

Agent(subagent_type="planner", prompt="Review this implementation plan and return your verdict (PROCEED / PROCEED WITH MODIFICATIONS / REDESIGN REQUIRED) with full justification per your evaluation criteria:\n\n[plan text]")

## Step 4 — Present and stop

Present the plan and the planner's verdict together. End with:

"AWAITING HUMAN APPROVAL BEFORE PROCEEDING. State: PROCEED, MODIFY [description], or REJECT."

Do not write any code until the user approves.
