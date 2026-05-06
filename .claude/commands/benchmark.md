# /benchmark

Run performance regression detection.

Read `.claude/skills/benchmark/SKILL.md` and follow its process.

- Default: measure build time, test time, bundle size, dependency count; compare to baseline
- `--update-baseline`: update `.claude/benchmarks/baseline.json` with current values

Baseline file: `.claude/benchmarks/baseline.json` — create on first run if absent.

Report regressions against thresholds (build: +10% warn / +25% flag; bundle: +10% warn / +25% flag).
A regression is information — do not modify source or config to improve numbers.
