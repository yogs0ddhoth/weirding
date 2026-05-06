# ADR Authoring Skill

Write and index Architecture Decision Records.

## When to Invoke

- A design decision has cross-cutting impact across multiple components
- A decision is hard to reverse — migration cost is significant
- A decision involves protected files or core interfaces
- Two credible alternatives exist and a trade-off must be made
- A future reader would find the constraint arbitrary without explanation

When in doubt: write the ADR. The cost of writing an ADR is low. The cost of a future
agent or developer unknowingly reversing a decision with non-obvious rationale is high.

## Process

### Step 1 — Read the ADR Index

Read `docs/adr/README.md` to find:
- The next available ADR number (increment by 1 from the highest existing number)
- Any existing ADRs that are related to the decision being documented

If an existing ADR already covers this decision and would be superseded, note it. ADRs
are never edited or deleted — if superseded, write a new ADR and note the supersession
in both the old and new ADR's status field.

### Step 2 — Read the Template

Read `docs/adr/template.md` for the required format. The template defines the structure
that all ADRs must follow. Do not deviate from it.

### Step 3 — Draft the ADR

Copy the template to `docs/adr/NNNN-short-title.md`.

Fill in each section:

**Context**: Self-contained description. A future reader with no prior context must
understand the situation completely after reading this section. Include:
- What problem required a decision
- What constraints existed (from CLAUDE.md, from technical reality, from prior ADRs)
- What alternatives were considered and why each was ruled out
- Why the decision was non-obvious (if it were obvious, an ADR would not be needed)

Do not assume the reader knows the current state of the system. Do not assume the reader
has read any other document. Context sections that require cross-referencing to understand
are incomplete.

**Decision**: Plain statement of what was decided. "We will use X for Y." Then: what was
explicitly rejected, and why. What is the scope of this decision — does it apply
everywhere or only in specific contexts?

**Consequences**: Both positive AND negative. An ADR with only positive consequences is
not honest — every real decision has costs. Include:
- What becomes easier or safer
- What becomes harder or more expensive
- What future options this forecloses
- What process changes this requires (if any)

### Step 4 — Update the Index

Add the new ADR to the index table in `docs/adr/README.md`:
- Number, title, status (Accepted), date, one-sentence summary

### Step 5 — Report Reference Locations

State where this ADR should be cited:
- Which files in the codebase should reference this ADR number in a comment
- Whether CLAUDE.md or AGENTS.md should be updated to reference it
- Whether MEMORY.md should note this decision

## ADR Quality Checklist

Before completing:
- [ ] Context is self-contained — a reader with no prior knowledge can understand it
- [ ] Alternatives are explicitly listed and their rejection is explained
- [ ] Consequences section includes both positive and negative entries
- [ ] Status is set (Proposed or Accepted)
- [ ] Index table in README.md is updated
- [ ] Reference locations are reported

## On Superseded ADRs

If writing an ADR that supersedes an existing one:
1. In the new ADR's status field: "Accepted. Supersedes ADR-NNNN."
2. In the old ADR's status field: add "Superseded by ADR-MMMM." (edit the status line only)
3. Do not delete or otherwise modify the old ADR's content
