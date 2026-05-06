# Melange Framework ADRs

Architecture decisions made during the development of the Melange framework itself. These
document WHY Melange is designed the way it is — they are NOT decisions belonging to any
project initialized from the framework.

**These files are deleted from initialized projects during `/init`.**

If you are reading this in an initialized project, this directory should not be here.
Delete it and open an issue at the Melange repository.

## Index

| # | Title | Status | Date | Summary |
|---|-------|--------|------|---------|
| [0001](0001-discrete-adoption-modes.md) | Discrete Adoption Modes for Codebase Import | Accepted | 2026-04-30 | Three named flags (--full, --governance-only, --commands-only) over a continuous spectrum |
| [0002](0002-deterministic-first-codebase-analysis.md) | Deterministic-First Hybrid for Codebase Analysis | Accepted | 2026-04-30 | File-signature scanning as primary detector; LLM only for structurally ambiguous gaps |
| [0003](0003-secret-scan-opt-in-body-analysis.md) | Secret-Scan Guard and Opt-In File Body Analysis | Accepted | 2026-04-30 | Structural content only to LLM by default; file body requires opt-in + secret pre-scan |
| [0004](0004-project-framework-identity.md) | Melange Identity: Project Framework, Not Template | Accepted | 2026-04-30 | "Project framework" over "template", "platform", or "SDK" — matches Projen/Nx precedent; `melange/` branch prefix for framework-layer development |
| [0005](0005-mcp-secret-injection.md) | MCP Secret Injection: settings.local.json + Windows User Environment | Accepted (Amended 2026-05-05) | 2026-05-05 | SetEnvironmentVariable (Windows) + settings.local.json env key; `${VAR}` interpolation in `.mcp.json` env blocks does not work — set `GITHUB_PERSONAL_ACCESS_TOKEN` directly |
| [0006](0006-npx-mcp-command-retained.md) | Retain `npx` in `.mcp.json` | Accepted | 2026-05-05 | Fix Windows context-creator failure via docs (require nodejs.org installer) rather than changing the command; hardcoded paths break cross-platform portability |
