# 0002: Deterministic-First Hybrid for Codebase Analysis

**Status:** Accepted

**Date:** 2026-04-30

**Authors:** Ben Lin

## Context

When Melange's `/init` Retrofit Mode analyzes an existing codebase to pre-fill the Commands
table and stack description, it must extract build commands, test commands, lint commands,
and format commands from a codebase that may have no documentation.

Two primary approaches were considered:

**LLM-primary approach:** Send codebase content (or a structured summary) to an LLM and ask
it to infer build commands, test commands, and architecture. Post-hoc validate against manifest
files. Pros: handles non-standard layouts, can reason across multiple signals simultaneously,
can identify semantic roles (auth modules, data models) that manifest files don't declare.
Cons: LLM hallucination rate on command extraction is 10–20% for edge cases (observed failure
mode: Copilot Workspace picking the wrong npm script, missing Makefile subtleties, confusing
workspace-level and package-level commands in monorepos); output is nondeterministic — the
same codebase analyzed twice can produce different answers; LLM inference provides no evidence
source the developer can audit. This approach was ruled out as primary because wrong commands
silently written to CLAUDE.md cause every downstream quality gate to fail.

**Deterministic-first hybrid:** Use file-signature scanning as the primary detection layer
(manifest files, lock files, CI configs) and invoke LLM reasoning only for structurally
ambiguous questions where no deterministic signal exists. Pros: file-signature detection is
O(directory listing), fully auditable (the exact rule that fired is attributable), produces
zero hallucinations, and is the pattern used by GitHub Linguist, Renovate, Dependabot, and
IntelliJ IDEA project import. LLM is invoked only on constrained inputs (e.g., "which of
these three npm scripts from package.json is the canonical test command?") where the answer
space is bounded and the failure mode is recoverable.

Lock files are treated as higher-confidence signals than manifests: a `yarn.lock` file
uniquely identifies the package manager, whereas `package.json` alone is ambiguous. This
mirrors Renovate's lock-file-first detection order.

## Decision

We will use a deterministic-first hybrid:

1. **Primary layer:** deterministic file-signature scanning of manifests, lock files, and
   CI config files. All values extracted by this layer are labeled `DETECTED (source)`.
2. **Secondary layer:** LLM reasoning applied only to structurally ambiguous questions on
   constrained inputs — e.g., reading only the `scripts` block of `package.json` and asking
   which entry is the canonical test command. All values from this layer are labeled
   `INFERRED`.
3. **No file body content** is sent to the LLM by default. The LLM receives only structural
   content: file names, manifest key names, directory listings, and script command strings
   (not values). File body analysis requires explicit user opt-in (enforced by the secret-scan
   guard — see ADR 0003).
4. **Confidence is communicated to the developer** via the DETECTED/INFERRED label on every
   pre-filled value in the Phase 2 confirmation screen.

Explicitly rejected: sending the full codebase (or large sections of it) to the LLM as the
primary analysis vehicle. Even for correctly answered cases, this approach provides no
auditable evidence source and scales poorly with repo size.

## Consequences

### Positive

- Command extraction from manifests is zero-hallucination for supported stacks
- Every pre-filled value carries an auditable evidence source
- Detection logic is a lookup table, not a model — future stack additions are a table update
- Aligns with the detection approach used by GitHub Linguist, Renovate, and IntelliJ IDEA

### Negative

- Non-standard project layouts (custom build wrappers, generated Makefiles, monorepos with
  nested manifests) may yield no manifest signal, falling back to INFERRED defaults
- Adding support for a new stack requires updating the manifest detection table in SKILL.md
- LLM reasoning on constrained inputs is still nondeterministic; INFERRED values must always
  be confirmed by the developer before writing

### Neutral

- The DETECTED/INFERRED label discipline must be maintained by any future contributor who
  extends the detection table; omitting labels is a documentation gap, not a blocker
- Monorepo detection (presence of `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`)
  triggers the monorepo ambiguity protocol rather than attempting multi-workspace analysis
