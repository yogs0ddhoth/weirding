# Project Memory

Project-level memory. Loaded for every agent session. Update this file directly (do not
rely on any external memory system) when you learn something worth persisting across
sessions: a design decision, a confirmed standard, a non-obvious constraint, anything a
future agent would need to avoid re-litigating.

## Core Facts

- **Language / Stack:** {{LANGUAGE_AND_STACK}}
- **Current phase:** {{CURRENT_PHASE}}
- **Roadmap:** `docs/planning/PROJECT_ROADMAP.md`
- **ADRs:** `docs/adr/` — read before touching any component

## Non-Negotiable Rules

[Fill in after your first session — add rules that must never be violated.]

1. Zero warnings, zero lint violations on every build
2. No raw PII (user inputs, emails, IDs) in any log statement
3. Never weaken a test threshold to make it pass — fix the code
4. Integration tests must use signal-based completion, not fixed sleeps

## Agent Dispatch Mandate

The top-level session is orchestration only. Dispatch all build, test, and debug work to
agents. Never run verbose or iterative commands in the main session.

## Directory Layout Notes

[Add non-obvious constraints about where things live, naming conventions, or module
boundaries that would not be obvious from reading the code.]

## Confirmed Standards

[Add standards discovered during development that are not obvious from the code or
CLAUDE.md. Examples: "All database queries must go through the repository layer, never
directly from handlers." "Environment-specific config lives in config/ and is never
hardcoded."]
