# Ideation Skill

Scope a feature or project before any planning begins.

## When to Invoke

- Starting a new feature or project
- Evaluating a vague idea before committing engineering time
- When "what are we actually building?" is unclear
- Before running `/plan` on any non-trivial feature

## Process

Work through these six questions in order. Do not skip ahead to implementation details —
that is the job of the planning skill. The job here is to produce shared understanding of
what is being built and why.

### 1. Problem

State the problem in user terms. What pain does this remove? What capability does this
add? Write one paragraph that a non-technical stakeholder could read and evaluate.

Avoid: "We need to refactor X" or "The current implementation of Y is suboptimal."
These are solutions, not problems. Identify the problem the solution is responding to.

### 2. Success Criteria

Define what "done" looks like with specific, observable outcomes. A success criterion is
testable — you can look at the running system and determine whether it is met.

Examples of good criteria:
- "A user can submit a search query and receive results in under 2 seconds on a reference
  machine with the test dataset."
- "The crawler respects robots.txt Disallow directives 100% of the time in the test suite."

Examples of bad criteria:
- "Performance is improved" (not measurable)
- "Code is cleaner" (not observable)

### 3. Scope

State explicitly:
- What is IN scope: what will be built, changed, or established
- What is OUT of scope: what will NOT be built as part of this work

Scope definition is the primary tool for avoiding scope creep. If something is not listed
as in scope, it is out of scope by default.

### 4. Dependencies

What must exist before this can start?
- Infrastructure: services, databases, credentials, environments
- Code: other features, refactors, or migrations that must land first
- Knowledge: research questions that must be answered before planning

### 5. Complexity Estimate

Assign a size: S (hours), M (1-2 days), L (3-5 days), XL (multiple weeks).

Justify the estimate. What makes this S instead of M? What would push it from M to L?
Estimates that are not justified are not useful.

### 6. Risks

What could make this harder, longer, or impossible?
- Technical unknowns: "We don't know if the third-party API supports this use case"
- Dependency risks: "This requires feature X to land first, which is not scheduled"
- Scope risks: "The definition of done is ambiguous in area Y"
- Privacy or integrity risks: "This feature touches user data — privacy review needed"

## Output

Produce a structured scope document with one section per question above.

End with a suggested next step:
- If research questions exist: suggest `/research [specific question]`
- If the scope is clear and well-understood: suggest `/plan [feature name]`
- If the scope is too large: suggest breaking it into smaller features and ideating each

## Constraint

Do NOT produce implementation details, file lists, or phase breakdowns. That is the
planning skill's job. Producing implementation details prematurely forecloses options
that should remain open during planning.
