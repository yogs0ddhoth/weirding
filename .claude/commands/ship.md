# /ship

Run the deploy skill.

Process:
1. Read the Deploy command from the Commands table in CLAUDE.md
   - If not defined, use AskUserQuestion before proceeding
2. Complete the pre-deploy checklist:
   - [ ] Quality gate passed
   - [ ] CHANGELOG entry present for user-visible changes
   - [ ] Version bumped appropriately
   - [ ] ADRs written for significant decisions in this release
   - [ ] No uncommitted changes
   - [ ] Target environment confirmed
3. Document the rollback plan (command, estimated time, data reversibility)
4. Present the deployment request and STOP:
   "Proceed with deployment? [yes / no / modify]"
5. After explicit human approval: execute, monitor, run smoke test, verify health
6. Report outcome: success with verification, or failure with rollback recommendation

Never execute the deploy command without explicit human approval.
Never assume "sounds reasonable" is approval -- wait for a direct yes.
