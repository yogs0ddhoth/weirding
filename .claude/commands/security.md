# /security

Run a security audit for this project.

Read `.claude/skills/security/SKILL.md` and follow its process.

- Default (no argument): daily mode — high-confidence findings only (≥8/10)
- `--full`: comprehensive mode — all findings including STRIDE threat model

Steps: secrets archaeology → dependency audit → OWASP scan → STRIDE (full only).

Save report to `docs/security/YYYY-MM-DD-audit.md`. Redact actual secret values.
Do NOT run `npm audit fix` or apply dependency upgrades automatically — report only.
