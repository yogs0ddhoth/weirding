# 0009: PyPI Publish Authentication — OIDC Trusted Publishing vs. API Token

**Status:** Accepted

**Date:** 2026-06-02

**Authors:** Ben Lin

## Context

weirding is being published to PyPI for the first time as part of Phase 04 Distribution.
Publishing requires authenticating to PyPI from a GitHub Actions workflow. Two credible
alternatives exist.

**Alternative 1 — OIDC trusted publishing (keyless)**

PyPI supports OpenID Connect (OIDC) trusted publishing via its trusted publisher registry.
A publisher entry maps a specific GitHub repository, workflow file, and Actions environment
to a PyPI project. At publish time, the Actions workflow requests a short-lived OIDC token
from GitHub (`permissions: id-token: write`), exchanges it for a PyPI upload token via
PyPI's token endpoint, and `pypa/gh-action-pypi-publish` handles the exchange transparently.
No long-lived credential is ever stored anywhere.

**Alternative 2 — PyPI API token**

A PyPI project-scoped API token is generated once, stored as a GitHub Secret
(e.g. `PYPI_API_TOKEN`), and passed to the publish action via the `password:` input.
This is the traditional approach and is still widely supported.

The choice is effectively a one-way door. Once a trusted publisher is registered on PyPI,
the workflow structure (`permissions: id-token: write`, `environment: pypi`) diverges from
the token-based approach in ways that cannot be silently swapped — both the workflow and
the PyPI configuration must change together. Starting with the token approach and migrating
to OIDC later requires a deliberate two-step change. Starting with OIDC and reverting to
tokens is a deliberate downgrade.

## Decision

We will use OIDC trusted publishing via `pypa/gh-action-pypi-publish` with the GitHub
Actions `id-token: write` permission. The `publish.yml` workflow declares
`environment: pypi` and carries no `password:` input and no `PYPI_API_TOKEN` secret.

API token authentication is explicitly rejected. A long-lived token stored in GitHub
Secrets creates a persistent credential that, if leaked, must be manually revoked and
rotated. OIDC eliminates this risk by design: tokens are ephemeral, scoped to a single
workflow run, and require no secret storage.

Preconditions for this decision to remain valid:

- PyPI continues to support OIDC trusted publishing for GitHub Actions (current policy,
  no announced deprecation).
- The GitHub Actions `id-token: write` permission remains available to public repositories.
- The `environment: pypi` Actions environment is not deleted or renamed without updating
  the trusted publisher entry on PyPI.

## Consequences

### Positive

- No long-lived credential is stored in GitHub Secrets — there is nothing to leak, revoke,
  or rotate.
- The trusted publisher registry on PyPI makes it explicit which repository and workflow
  are authorized to publish, providing an auditable access control boundary.
- `pypa/gh-action-pypi-publish` handles the OIDC token exchange internally; the workflow
  stays concise and does not require manual token management.
- Defense-in-depth is available at no extra cost: the `environment: pypi` GitHub Actions
  environment can be configured with a required reviewer, adding a human gate before any
  publish proceeds.

### Negative

- First publish requires a manual one-time setup step on PyPI: create the project (or
  claim the name) and add a Trusted Publisher entry specifying the GitHub owner
  (`yogs0ddhoth`), repository (`weirding`), workflow filename (`publish.yml`), and
  environment name (`pypi`). This step cannot be automated and must be performed by a
  maintainer with PyPI project ownership.
- Future maintainers who are only familiar with the token-based approach may be surprised
  that there is no `PYPI_API_TOKEN` secret and that the workflow has no `password:` input.
  This ADR is the reference explaining the omission.

### Neutral

- Future maintainers must never add a `password:` input or create a `PYPI_API_TOKEN`
  GitHub Secret. Doing so would create a parallel credential path and undermine the
  no-stored-secrets guarantee.
- Any rename of the `publish.yml` workflow file or the `pypi` Actions environment requires
  a corresponding update to the trusted publisher entry on PyPI before the next publish
  will succeed.
- TestPyPI publishes, if introduced, require a separate trusted publisher entry on
  TestPyPI and a separate workflow environment.
