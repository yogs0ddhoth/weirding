# /adr

Author an ADR for the design decision: $ARGUMENTS

Process:
1. Read `docs/adr/README.md` to determine the next ADR number
2. Read `docs/adr/template.md` for the required format
3. Draft the ADR:
   - Context: self-contained, no assumed knowledge, includes alternatives considered
   - Decision: plain statement of what was decided and what was rejected
   - Consequences: both positive AND negative — no honest decision has only upsides
4. Write the ADR to `docs/adr/NNNN-short-title.md`
5. Update the index table in `docs/adr/README.md`
6. Report where in the codebase and documentation this ADR should be cited

ADRs are append-only. If superseding an existing ADR:
- Note "Supersedes ADR-NNNN" in the new ADR's status
- Update only the status line of the old ADR to note the supersession
- Never edit or delete the old ADR's content
