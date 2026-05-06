# /changelog

Write a user-facing CHANGELOG entry for: $ARGUMENTS

Invoke the changelog skill (`.claude/skills/changelog/SKILL.md`).

Read the current `CHANGELOG.md` to understand the format in use. Write an entry for
the changes described in $ARGUMENTS, or if empty, infer from recent git commits on
the current branch since last tag.

Follow the existing format (Keep a Changelog, semantic versioning, or project convention).
