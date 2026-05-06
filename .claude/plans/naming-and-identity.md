# Plan: naming-and-identity

**Branch:** `melange/naming-and-identity` (to be created)
**Date:** 2026-04-30

## Background

Melange is currently self-described as a "template," which connotes a one-shot copy with
no ongoing relationship. Melange actually behaves as a project framework: it maintains an
ongoing relationship with initialized projects (planned `/upgrade` command), has a two-tier
layer structure (UNIVERSAL files vs project files), and delivers operational workflows as
permanent infrastructure. Research confirms "project framework" is the accurate vocabulary,
used by Projen and Nx for the same structural pattern. "Template" is retained only where
it refers to the GitHub Template Repository delivery mechanism — a proper name for the copy
action, not Melange's identity.

## Simplicity challenge

All changes are file edits with no runtime dependencies and no build step. A single phase
is possible. The split into two phases is justified by reviewability: Phase 1 is a
systematic vocabulary audit across 7 files; Phase 2 is a new ADR. They are independently
verifiable with distinct completion signals.

## ADR candidate

Choosing "project framework" over "template," "platform," or "SDK" involves trade-offs
between credible alternatives (Projen precedent, CRA cautionary tale), has cross-component
impact across 7 files, and is the kind of decision future contributors will relitigate
without documented rationale. ADR 0004 is required.

---

## Phase 1 — Vocabulary audit + branch convention

**Goal:** Replace "template"-as-identity with "framework" or "project framework" across
all governance files. Add `melange/<feature>` branch prefix convention.

### Vocabulary rules

- "template" as identity → "framework" or "project framework"
- "template-layer" → "framework-layer"
- "Melange template" (referring to Melange itself) → "Melange framework" or "Melange"
- "template version" → "framework version"
- "template-internal" → "framework-internal"
- KEEP unchanged: "GitHub Template Repository", "'Use this template' button" (GitHub UI
  terms), `TEMPLATE.md` and `TEMPLATE_VERSION` filenames, any quoted file path containing
  these names

### Files modified

| File | Change summary |
|------|---------------|
| `README.md` | "Initializing this template?" → "New to Melange?"; TEMPLATE.md/TEMPLATE_VERSION description lines: "template" → "framework" where identity |
| `ETHOS.md` | "every project built on this template" → "every project built on this framework" |
| `CLAUDE.md` | Template instructions block: "Melange universal project template" → "Melange project framework"; Feature Branches section: add `melange/<feature>` convention |
| `AGENTS.md` | Specific lines: "template-level" (line 27) → "framework-level"; "modifying the template" (line 30) → "modifying the framework"; "Melange template only" (line 56) → "Melange framework only"; "Melange template itself" (line 57) → "Melange framework"; "template-layer ADRs" (lines 60–61) → "framework-layer ADRs"; skill description "One-time template initialization" (line 178) → "One-time framework initialization"; "Modify template configuration" (line 179) → "Modify framework configuration"; add `melange/<feature>` branch convention note |
| `TEMPLATE.md` | Title: "Melange Template Manifest" → "Melange Framework Manifest"; line 3: "Current template version" → "Current framework version" (identity use, not a filename); "owned by the template" → "owned by the framework"; "template upgrade" → "framework upgrade"; "from the template immediately" → "from the framework immediately" |
| `SETUP.md` | h1: "Template Initialization" → "Project Setup"; body: "Melange template" → "Melange framework" (3 instances); "template-internal" → "framework-internal"; "Template version:" → "Framework version:"; checklist: "Initializing this template?" reference → "New to Melange?"; commit message: "from Melange template" → "from Melange" |
| `docs/adr/melange/README.md` | Title: "Melange Template ADRs" → "Melange Framework ADRs"; prose: "Melange template itself" → "Melange framework"; "template-layer" → "framework-layer" |
| `.claude/skills/init/SKILL.md` | "Melange template" → "Melange framework" (lines 3, 8); "adopting the template" → "adopting the framework" (lines 10, 87) |
| `.claude/skills/configure/SKILL.md` | "Melange template configuration" → "Melange framework configuration" (line 3) |
| `.claude/commands/init.md` | "Initialize this Melange template" → "Initialize this Melange framework" (line 3) |

### Files created

None.

### Protected files

None. (Protected Files list in CLAUDE.md contains only `{{PLACEHOLDER}}` values — no real
paths are designated until after `/init`.)

### Completion signal

```bash
grep -ri "melange template\|the template\|this template\|template-layer\|template version\|template-internal" \
  README.md ETHOS.md CLAUDE.md AGENTS.md TEMPLATE.md SETUP.md \
  docs/adr/melange/README.md \
  .claude/skills/init/SKILL.md \
  .claude/skills/configure/SKILL.md \
  .claude/commands/init.md
```
Returns zero matches. (GitHub Template Repository / "Use this template" / TEMPLATE.md
filename / TEMPLATE_VERSION filename references are excluded from this check and will
appear in results — they are intentional retentions.)

### Estimate

1.5 hours

---

## Phase 2 — ADR 0004

**Goal:** Document the identity decision as an append-only architecture record.

### Files created

- `docs/adr/melange/0004-project-framework-identity.md` — covers: the decision, alternatives
  considered (template, platform, SDK), rationale (Projen/Nx precedent, CRA failure mode),
  the retained "template" carve-out for GitHub mechanism language, and the `melange/<feature>`
  branch naming convention

### Files modified

- `docs/adr/melange/README.md` — add index entry for 0004

### Protected files

None.

### Completion signal

`docs/adr/melange/README.md` index has entry for 0004; `0004-project-framework-identity.md`
exists with Decision, Alternatives, and Rationale sections populated.

### Estimate

30 min

---

## Total estimate

S — 2 hours
