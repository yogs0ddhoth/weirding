# ADR 0004 — Melange Identity: Project Framework, Not Template

**Date:** 2026-04-30  
**Status:** Accepted

---

## Context

Melange was initially positioned as a "template" — specifically, a GitHub Template
Repository that developers copy to start a new project. This framing was accurate for
the delivery mechanism (GitHub's "Use this template" button) but inaccurate for the
ongoing relationship Melange maintains with initialized projects.

A template in the classical sense is one-shot: you copy it, you diverge, the relationship
ends. Melange does not behave this way:

- It has a planned `/upgrade` command that propagates framework-layer changes to
  initialized projects — implying an ongoing relationship, not a one-time copy
- Its TEMPLATE.md explicitly separates files into a UNIVERSAL (framework-owned) layer
  and a PROJECT (project-owned) layer — a two-tier architecture with no analog in
  one-shot templates
- Its skills, hooks, and agents deliver operational workflows as permanent infrastructure
  that initialized projects carry forward, not scaffolding to discard after setup

Calling Melange a "template" misled two design decisions in session 1:

1. The SETUP.md orphan-branch history cleanup workaround (a hack around template
   repositories not filtering git history — a non-issue if the mental model had been
   "framework with a versioned release" from the start)
2. The `docs/adr/melange/` two-tier ADR structure, which had to be invented ad hoc
   because "template" offered no vocabulary for a framework-owned documentation layer

---

## Decision

Melange's primary self-description is **project framework**, not template.

The word "template" is retained in exactly two contexts:
1. When describing the GitHub Template Repository delivery mechanism (the action of
   clicking "Use this template" to copy Melange into a new project)
2. As part of the filenames `TEMPLATE.md` and `TEMPLATE_VERSION`, which describe
   the framework manifest and version anchor respectively — renaming these files would
   break the upgrade workflow described in TEMPLATE.md

Everywhere else — in prose, skill descriptions, skill instructions, and agent guidance —
the vocabulary is:
- **Melange** or **Melange project framework** for Melange itself
- **framework layer** for the UNIVERSAL files owned by Melange (skills, hooks, AGENTS.md,
  ETHOS.md, etc.)
- **project layer** for the files that diverge after `/init` (CLAUDE.md content, MEMORY.md,
  ADRs, project-specific configuration)
- **Framework version** for the version anchor stamped into MEMORY.md at init time
- **framework upgrade** for the process of pulling in UNIVERSAL file changes

Branch naming for Melange framework development uses the `melange/` prefix:
`melange/feature-name`. Initialized-project work uses standard prefixes (`feat/`, `fix/`,
etc.). This makes framework-layer branches visually distinct in the GitHub branch list.

---

## Alternatives Considered

### Keep "template"

**Pros:** Matches the GitHub UI term (Template Repository); zero vocabulary cost.

**Cons:** "Template" connotes one-shot delivery with no ongoing relationship. Users
who hear "template" expect to diverge freely and never receive updates. This directly
contradicts the intended `/upgrade` command. Cookiecutter's community (a pure one-shot
template tool) has documented this confusion repeatedly — users who expect template
semantics are surprised when upstream changes do not propagate. The mental model mismatch
is not cosmetic; it shapes how users design their projects and whether they invest in the
upgrade path.

### "Platform"

**Pros:** Implies comprehensive scope, governance, and ongoing relationship.

**Cons:** "Platform" implies hosted infrastructure — a service that your project runs
on. Melange is a local tool that lives entirely in the repo. Calling it a "platform"
sets expectations of hosted services that do not exist. AWS, GitHub, and Heroku use
"platform" for hosted infrastructure; Melange is not in this category.

### "SDK"

**Pros:** "SDK" (Software Development Kit) connotes a curated bundle of tools that you
adopt and then work within.

**Cons:** "SDK" strongly implies a programmatic API — you `import` it and call functions
from it. Melange has no runtime API surface; it delivers behavior through files, hooks,
and skills. The AWS CDK, Pulumi SDKs, and Google Cloud SDK all use this framing because
they expose programmatic APIs. Melange does not.

---

## Rationale

The "project framework" vocabulary is the closest established match to Melange's actual
behavior, validated by production tools with the same structural pattern:

- **Projen** (github.com/projen/projen): self-described as a "project definition
  framework." Distinguishes managed files (framework layer, regenerated on `projen synth`)
  from the `projenrc` file (project layer, owned by the developer). Upgrade path is
  `npm update` on the projen package — the framework layer updates, the project layer
  is preserved.

- **Nx** (nx.dev): self-described as a "workspace framework." Distinguishes Nx plugins
  (framework layer, updated via `nx migrate`) from workspace files (project layer, owned
  by the team). The `nx migrate` command is the canonical framework-layer upgrade path —
  it applies codemods to project files while the plugin layer updates via npm.

Both tools converged on "framework" to describe the same two-tier pattern Melange
implements via TEMPLATE.md's UNIVERSAL/PROJECT split.

**The CRA failure mode** (create-react-app, now archived) is the cautionary tale for
not making this distinction explicit: CRA called itself a "toolchain" but embedded itself
so deeply in generated files that the only escape was `eject` — a one-way door that
destroyed the ongoing relationship. Melange's UNIVERSAL/PROJECT split already prevents
this: universal files are safe to overwrite on upgrade, project files are merged manually.
The vocabulary "project framework" reinforces this boundary; "template" obscures it.

---

## Consequences

- All governance files updated in this session: ETHOS.md, README.md, CLAUDE.md, AGENTS.md,
  TEMPLATE.md, SETUP.md, docs/adr/melange/README.md, `.claude/skills/init/SKILL.md`,
  `.claude/skills/configure/SKILL.md`, `.claude/commands/init.md`
- MEMORY.md Core Facts label changes from `Template version:` to `Framework version:`
  at next `/init` run (SETUP.md updated accordingly)
- The UNIVERSAL/PROJECT boundary in TEMPLATE.md is now the load-bearing definition of
  what "framework layer" means — it must not be eroded by adding project-specific logic
  to universal files, or the upgrade path degrades toward CRA-style ejection
- The `melange/` branch prefix is a convention, not an enforced rule — it requires no
  tooling and can be adopted incrementally
