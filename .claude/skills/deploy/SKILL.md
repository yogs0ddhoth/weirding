# Deploy Skill

Deployment readiness check with mandatory human approval.

## When to Invoke

- About to deploy to a staging or production environment
- As part of the `/ship` command
- When a PR is approved and ready to go to production

## Hard Rule

Never execute the deploy command without explicit human approval. This rule has no
exceptions. The purpose of this skill is to ensure that a human has reviewed and
confirmed the deployment, not to automate it away.

## Process

### Step 1 — Read Deploy Command

Read the Deploy command from the Commands table in CLAUDE.md.

If not defined, use AskUserQuestion to get the deploy command and the target environment
before proceeding. Do not attempt to infer the deploy command from the project structure.

### Step 2 — Pre-Deploy Checklist

Complete every item before requesting approval. If any item is not complete, fix it
before continuing — do not request approval for a deployment that fails pre-checks.

- [ ] Quality gate passed (run `/quality` if not already done in this session)
- [ ] All commits since last tag follow Conventional Commits format (reported by `/quality` full gate)
- [ ] CHANGELOG entry present for every user-visible change in this release
- [ ] Version bump in CHANGELOG matches the implied bump from commit types (as reported by `/quality`)
- [ ] ADRs written for any significant architectural decisions made in this release
- [ ] No uncommitted changes (run `git status` and confirm clean)
- [ ] Target environment confirmed (staging vs. production — never assume)
- [ ] Rollback plan documented (see below)

### Step 3 — Document the Rollback Plan

Before requesting approval, write a rollback plan. A rollback plan must state:
- What command or procedure reverts this deployment
- How long the rollback is expected to take
- Whether data migrations are involved and whether they are reversible
- What the user impact is during rollback

Do not deploy if the rollback plan includes "not reversible" without explicit user
acknowledgment. Data loss is not acceptable without explicit consent.

### Step 4 — Request Human Approval

Present the following to the user and STOP:

```
DEPLOYMENT REQUEST

Target environment: [staging | production]
Deploy command: [exact command]
Changes included:
  [summary of CHANGELOG entries for this release]

Pre-deploy checklist: [COMPLETE | INCOMPLETE — list missing items]

Rollback plan:
  [rollback command or procedure]
  [estimated rollback time]
  [data reversibility: fully reversible | partial | not reversible (with details)]

---
Proceed with deployment? [yes / no / modify]
```

Do not execute the deploy command until the user responds with explicit approval ("yes"
or equivalent). "Sounds good" and "ok" are explicit approval. Silence is not.

### Step 5 — Execute and Monitor

After approval:
1. Run the deploy command
2. Monitor for the initial success signal — do not assume success from exit code alone
3. Run the smoke test defined in CLAUDE.md (or ask if not defined)
4. Verify the health endpoint if one exists
5. Scan for error spikes in logs for the first 2-5 minutes post-deploy

Report the outcome:
- Success: deploy command exit code, smoke test result, health check result
- Failure: exact error output, whether automatic rollback occurred, recommended action

### Step 6 — Post-Deploy Verification

After a successful deploy:
- Confirm the version is reported correctly by the health or version endpoint
- Confirm that the user-visible changes from CHANGELOG are observable in the running system
- Note any unexpected behavior observed during monitoring

If unexpected behavior is observed, do not dismiss it. Report it and ask the user whether
to continue monitoring, roll back, or investigate further.

## Environments

Always confirm the target environment before deploying. When CLAUDE.md defines multiple
environments (local, staging, production), ask explicitly which environment is the target.
Never assume "next environment" or "the obvious one."

Production deployments require more scrutiny:
- Rollback plan must be confirmed reversible or explicitly accepted as irreversible
- Smoke test must cover the critical user path, not just a health endpoint
- Error monitoring must run for at least 5 minutes before the session ends
