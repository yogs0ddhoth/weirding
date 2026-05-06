# Architecture Decision Records

ADRs explain *why* this project is designed the way it is. They are the authoritative
record of reasoning that would otherwise appear arbitrary to a future reader or agent.

## How to Read ADRs

Read ADRs before touching a component — not to discover current state, but to understand
why the constraints exist. If you are about to make a change that seems to violate an
existing constraint, check whether there is an ADR explaining why the constraint was put
there.

Current state lives in `.claude/memory/MEMORY.md`. ADRs explain the *why*.

## How to Write an ADR

Use the `/adr` command or invoke the `adr-authoring` skill directly. Copy `template.md`
to `NNNN-short-title.md` and fill it in.

An ADR is required when a decision involves:
- Trade-offs between two credible alternatives
- Cross-component impact
- Changes to protected files or core interfaces
- Anything hard to reverse

ADRs are append-only. If a decision is superseded, write a new ADR and update the
status line of the old one. Never delete or edit the content of a past ADR.

## Index

| # | Title | Status | Date | Summary |
|---|-------|--------|------|---------|
| — | — | — | — | No ADRs yet. |

---

> **Template note:** If you are working on the Melange template itself (not an initialized
> project), template-layer ADRs about Melange's own design live in `docs/adr/melange/`.
> This directory is deleted during `/init` so initialized projects always start with a
> clean ADR index.
