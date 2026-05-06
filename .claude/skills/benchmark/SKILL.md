# Benchmark Skill

Performance regression detection from build artifacts and timing. No browser required.
Compares against a stored baseline to flag regressions.

## When to Invoke

- Before merging a branch that touches the build pipeline or adds dependencies
- When bundle size or build time feels noticeably slower
- As part of a pre-release check

## Baseline File

Baselines are stored at `.claude/benchmarks/baseline.json`. Create it on first run.
Format:

```json
{
  "updated": "2026-04-29",
  "branch": "main",
  "build_time_ms": 12400,
  "test_time_ms": 8200,
  "bundle_sizes": {
    "dist/main.js": 142000,
    "dist/vendor.js": 891000
  },
  "total_bundle_bytes": 1033000,
  "dependency_count": 47
}
```

## Process

### Step 1 — Build time

Time the build command from CLAUDE.md:

```bash
start=$(date +%s%3N)
<BUILD_COMMAND>
build_ms=$(($(date +%s%3N) - start))
```

### Step 2 — Test time (fast tests only)

Time the test command. If the project has separate fast/slow test targets, use the fast
target only (ask if unclear):

```bash
start=$(date +%s%3N)
<TEST_COMMAND>
test_ms=$(($(date +%s%3N) - start))
```

### Step 3 — Bundle size (if applicable)

Check for output directories (`dist/`, `build/`, `out/`, `.next/`, `public/`). For each
JavaScript/CSS/WASM file found, record its size in bytes:

```bash
find dist/ -name "*.js" -o -name "*.css" -o -name "*.wasm" 2>/dev/null | \
  xargs du -b 2>/dev/null | sort -rn | head -20
```

If no output directory exists (backend projects), skip this step.

### Step 4 — Dependency count

```bash
# Node.js
cat package-lock.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('packages',d.get('dependencies',{}))))" 2>/dev/null
# Go
go list -m all 2>/dev/null | wc -l
# Python
pip list 2>/dev/null | wc -l
# Rust
cargo metadata --no-deps --format-version 1 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['packages']))" 2>/dev/null
```

### Step 5 — Compare and report

If a baseline file exists, compare current values against it:

```
BENCHMARK: <branch> vs baseline (<baseline date>)

Build time:    12.8s  →  14.1s   +14%   ⚠ REGRESSION (threshold: +10%)
Test time:      8.1s  →   8.3s    +2%   ✓
Bundle size:   1.01MB →  1.48MB  +46%   ✗ REGRESSION (threshold: +25%)
  └ dist/vendor.js: 891KB → 1.34MB (+50%)
Dependencies:     47  →     51    +4    ✓ (4 new packages added)

RESULT: [BASELINE | REGRESSIONS DETECTED]
```

Thresholds (configurable in baseline.json or accepted via argument):
- Build time: warn at +10%, flag at +25%
- Test time: warn at +15%, flag at +30%
- Bundle size (total): warn at +10%, flag at +25%
- Dependencies: flag if +5 or more added since last baseline

If no baseline exists, create one from current values and report:
`Baseline created. Re-run /benchmark after future changes to detect regressions.`

## Rules

- Never modify source code or build config to improve benchmark results
- A regression does not block the build — it is information for the developer to act on
- Update the baseline explicitly when a regression is intentional: `/benchmark --update-baseline`
- Do not benchmark inside a tight loop — one measurement per skill invocation
