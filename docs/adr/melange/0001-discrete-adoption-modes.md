# 0001: Discrete Adoption Modes for Codebase Import

**Status:** Accepted

**Date:** 2026-04-30

**Authors:** Ben Lin

## Context

The Melange `/init` skill's Retrofit Mode needs to support varying degrees of template
adoption. A developer adopting Melange onto an existing project might want:

- Full adoption: all CLAUDE.md sections populated (commands, protected files, roadmap, README)
- Governance-only: hooks, quality gates, protected files — but not touch their existing README,
  commands table, or roadmap (common when the project already has documented build tooling)
- Commands-only: populate only the Commands table so Claude agents can run builds correctly,
  nothing else

Two design approaches were considered:

**Continuous spectrum approach:** A numeric "adoption depth" parameter (e.g., `--depth 0.7`)
where higher values populate more sections. Pros: handles arbitrary intermediate cases.
Cons: users cannot form a mental model of what 0.7 means vs. 0.6; the implementation must
define a mapping from a continuous value to discrete section writes; future skills that need
to know "is this section populated?" now have to query depth rather than check a flag.
This approach was ruled out because it requires users to know the internal section ordering
to pick a meaningful depth value, and because production tooling in this space (Renovate's
preset system, Dependabot's configuration levels, Docker BuildKit's cache modes) universally
uses named discrete options.

**Discrete modes approach:** Three named flags map to fixed section write scopes:
`--full`, `--governance-only`, `--commands-only`. Each flag has an explicit write/skip table
that is defined in SKILL.md and enforced by the Phase 5 verification gate.

The research finding from production tooling is directly applicable here: GitHub Linguist,
Renovate, and Dependabot all converge on discrete flags rather than spectra for adoption/
configuration scope. The reason is that discrete modes can be documented, tested in isolation,
and referenced by name in future skills — continuous spectra cannot.

## Decision

We will use three discrete adoption modes as named flags on `/init`:

- `--full` (default, no flag required): populate all CLAUDE.md sections
- `--governance-only`: write protected files, quality requirements, and privacy requirements
  only; skip Commands table, roadmap, and README update
- `--commands-only`: write Commands table and `.claude/settings.json` only; skip all other
  sections

All flag enforcement and write-scope logic lives in `.claude/skills/init/SKILL.md`. The
`.claude/commands/init.md` router may reference flag names in a one-line note but must not
contain enforcement logic.

The Phase 5 verification gate is mode-aware: a missing Commands table is not a FAIL when
mode is `--governance-only`.

Explicitly rejected: a `--custom` mode that allows per-section selection. The maintenance
cost of arbitrary section combinations is high and the use case is narrow. If an intermediate
combination is needed, the user should run `--governance-only` and manually fill the remaining
sections.

## Consequences

### Positive

- Developers with existing build tooling can adopt Melange's agent governance without
  disrupting their current README or command documentation
- Each mode is independently testable and auditable
- Future skills that check "is this section populated?" can check the flag rather than
  inspecting section content
- Aligns with production tooling conventions that developers already understand

### Negative

- Three modes may not cover every legitimate combination (e.g., a developer who wants
  protected files + commands but not quality rules has no clean path)
- Adding a fourth mode later requires updating the scope table, Phase 5 gate, and this ADR

### Neutral

- All flag logic lives in SKILL.md — any future mode additions must update SKILL.md's
  scope table and the Phase 5 gate together; they cannot be added to `init.md` alone
