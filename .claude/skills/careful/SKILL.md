# Careful Skill

Documents the destructive-command interception hook that is active in every session.

## What this hook does

The `check-careful.sh` PreToolUse hook intercepts every Bash tool call before it executes.
If the command matches a destructive pattern, Claude Code prompts you to confirm before
proceeding. Patterns intercepted:

- `rm -rf` on broad paths (excludes safe targets: node_modules, .next, dist, build, __pycache__)
- `git push --force` / `git push -f`
- `git reset --hard`
- `git clean -f` / `git clean -fd`
- `DROP TABLE`, `DROP DATABASE`, `TRUNCATE TABLE`
- `kubectl delete` / `kubectl destroy`
- `terraform destroy`
- `dd` writing to a block device
- `curl ... | bash` / `wget ... | bash`

## How to modify the pattern list

Edit `.claude/hooks/check-careful.sh`. The patterns are simple `-E` regex expressions.
To whitelist a specific safe variant of a dangerous command, add a negation check:

```bash
if match 'rm[[:space:]]+-rf' && ! match 'rm[[:space:]]+-rf[[:space:]]+my-safe-dir'; then
  warning="rm -rf"
fi
```

## How to disable for a specific session

Remove the `PreToolUse` hook entry from `.claude/settings.json` temporarily. Re-add it
when done. Never disable it permanently unless you have a compelling reason — the hook
exists because destructive operations are one-way doors.

## Note on the `/careful` command

Invoking `/careful` in a session is informational — it explains this hook. The hook itself
is always-on once it is wired into `settings.json`. It does not need to be activated per
session.
