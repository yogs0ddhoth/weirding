# Changelog Skill

Write user-facing CHANGELOG entries.

## When to Invoke

- A feature is complete and about to merge to main
- Preparing a release — summarizing what shipped
- After a session that made user-visible changes
- As part of the session completion protocol (AGENTS.md)

## Core Rule

Write for the user, not for the developer. The CHANGELOG is read by people who use the
product, not people who maintain the codebase. They do not know what a crate is, what
a refactor is, or why an internal pipeline change matters.

User language: "You can now search by date range."
Developer language: "Added date range filtering to the query AST." (Do not use this.)

## Process

### Step 1 — Gather Commits

Read the commits since the last CHANGELOG entry:

```bash
git log --oneline [last-changelog-commit]..HEAD
```

If the last changelog commit is unknown, read `CHANGELOG.md` to find the last version
and use:

```bash
git log --oneline [last-version-tag]..HEAD
```

### Step 2 — Categorize Changes

Map each commit's type prefix to a changelog category:

| Commit type | Category | Include? |
|-------------|----------|---------|
| `feat` | **Added** | Yes |
| `feat!` or `BREAKING CHANGE:` footer | **Breaking** | Yes |
| `fix` | **Fixed** | Yes |
| `perf` | **Changed** | Yes |
| `revert` | **Fixed** | Yes (describe what was reverted in user terms) |
| `docs`, `style`, `refactor`, `test`, `build`, `ci`, `chore` | **Internal** | No |

If a commit has no type prefix (non-conventional), use judgment: ask whether the user
would notice the change in the running product. If yes, include it; if no, exclude it.
Flag non-conventional commits in the version bump recommendation.

### Step 3 — Write Entries

Write one CHANGELOG entry per user-visible change. Each entry should:
- Start with a verb: "You can now...", "Fixed a problem where...", "Changed how..."
- State the specific capability or behavior in concrete terms
- Not mention code artifacts (function names, module names, crate names)
- Not require the user to understand the implementation to understand the change

For Breaking changes: also state what action the user must take. "Changed X — you will
need to update your configuration file's Y setting to Z."

### Step 4 — Determine Version Bump

Derive the version bump from commit types — take the highest bump across all included commits:

| Signal | Bump |
|--------|------|
| Any `feat!` suffix, or any commit with `BREAKING CHANGE:` in body/footer | **major** |
| Any `feat` commit | **minor** |
| Any `fix`, `perf`, or `revert` commit | **patch** |
| Only `docs`, `style`, `refactor`, `test`, `build`, `ci`, `chore` | **none** (internal release) |

Non-conventional commits: treat as **patch** and flag them so the author can reclassify.

State the derived bump and list the highest-signal commit that drove it.

### Step 5 — Update CHANGELOG.md

Add the new entries under the `[Unreleased]` section (or a new version section if
releasing). Format:

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added
- [Entry]

### Fixed
- [Entry]

### Changed
- [Entry]

### Breaking
- [Entry]
```

If there is already an `[Unreleased]` section, append to it. Do not create a new section
for each session — accumulate entries until a release.

## Quality Check

Before completing:
- [ ] All entries are in user-facing language
- [ ] No crate names, function names, or internal module names appear in any entry
- [ ] Breaking changes include the action the user must take
- [ ] Internal-only changes are excluded
- [ ] Version bump is stated with justification
