# 0003: Secret-Scan Guard and Opt-In File Body Analysis

**Status:** Accepted

**Date:** 2026-04-30

**Authors:** Ben Lin

## Context

When Melange's Retrofit Mode analyzes an existing codebase, it reads file content to extract
build commands, stack information, and protected file candidates. Real codebases routinely
contain secrets embedded in source: AWS access keys in `.env.example`, GitHub tokens in CI
configs, API keys in test fixtures, and credentials in seed data. If file body content is
sent to an LLM API (including Claude), those secrets travel with it.

This is not a hypothetical risk. In April 2023, Samsung engineers inadvertently transmitted
proprietary source code — including credentials — to ChatGPT during AI-assisted debugging.
The incident resulted in an internal ban on generative AI tools. The failure mode is
invisible at the moment it occurs: there is no error, no warning, and no recovery path once
content has been transmitted.

The alternative to a secret-scan guard is to rely on developers to manually exclude sensitive
files before running `/init`. This is insufficient because: (a) developers may not know which
files contain secrets (auto-generated credentials, inherited configs); (b) the failure has no
observable signal at the time it occurs; (c) Melange's Privacy Requirements explicitly require
that no user data is logged or transmitted without explicit consent.

## Decision

We will apply a secret-scan guard to all file body content before it enters LLM context:

1. **Default policy: structural content only.** By default, the LLM receives only structural
   content — file names, manifest key names, directory listings, and script command strings
   (not values). No file body is sent to LLM context without explicit user opt-in.

2. **Secret-pattern pre-check on any file body.** If file body content is to be sent (user
   opted in), each file is scanned for the following patterns before inclusion:
   - AWS access key: `AKIA[0-9A-Z]{16}`
   - GitHub personal access token: `ghp_[a-zA-Z0-9]{36}` or `github_pat_`
   - Generic secret variable indicators: lines matching `SECRET=`, `TOKEN=`, `PASSWORD=`,
     `API_KEY=`, `PRIVATE_KEY` (case-insensitive)
   - High-entropy strings: any 40+ character alphanumeric string on a single line

3. **On pattern match: exclude and warn, never transmit.** Files matching any pattern are
   excluded from LLM context entirely. A warning is shown in the confirmation screen
   displaying only the **filename and match category** — never the matched string, matched
   line, or surrounding context. The warning format is:
   `⚠️  [filename] excluded from analysis — [match category] detected. Review manually.`

4. **Opt-in gate before any file body analysis.** Before reading file body content, the skill
   must prompt the user explicitly: "To improve detection accuracy I can read the contents of
   [files]. These will be scanned for secrets first. Proceed?" File body analysis does not
   begin without an affirmative response.

Explicitly rejected: secret scanning as a post-hoc filter applied after content is assembled
for the LLM prompt. Post-hoc filtering has a race condition: if content is assembled into a
large context object before scanning, partial transmission on timeout or error could expose
secrets. The guard must be applied per-file before any LLM prompt assembly.

## Consequences

### Positive

- Secrets embedded in source files cannot be transmitted to LLM APIs during Retrofit Mode
  initialization by default
- The opt-in gate makes the data transmission explicit — developers make an active choice
  before file body content is sent
- Warning messages are designed to not create a secondary disclosure path (filename only,
  not matched content)
- Satisfies Melange's Privacy Requirements: no user data transmitted without explicit consent

### Negative

- Structural-only analysis (the default) cannot detect semantic roles — auth modules, hot
  paths, and data models are invisible to file-name scanning. Protected file inference
  quality is lower than full-body analysis.
- The secret-pattern list covers common credential formats but is not exhaustive — custom
  API key formats, internal token schemes, and PEM-encoded keys may not match the patterns
- Opt-in gate adds one interaction step before file body analysis

### Neutral

- The secret-pattern list in SKILL.md must be updated when new credential formats become
  common; this is a maintenance commitment, not a one-time decision
- This guard applies only to Retrofit Mode's codebase analysis phase; it does not apply to
  other Claude sessions operating on the project after initialization
