# Public Update and Release Governance

This document defines how TRION's public repository is updated. It applies to
branch updates, releases, tags, and public announcements.

## Core rule

Completing an issue, milestone, test run, implementation checkpoint, or private
development branch does not authorize publication. Every public update requires
an explicit candidate, current evidence, and a separate human publication
decision.

## Candidate record

Before a public update, record:

1. the exact public base commit and target branch;
2. the complete file scope and public behavior affected;
3. the required tests, security checks, and documentation review;
4. known limitations and deliberately excluded work;
5. the relevance of milestones M0 through M5;
6. the explicit human publication decision for that candidate.

Milestones M0 and M1 are required by default. M2 through M5 must be classified
as `REQUIRED`, `NOT_REQUIRED`, or `DECIDE` with current evidence. Classification
is candidate-specific and does not close a milestone by itself.

## Required separation

Keep these judgments separate:

- **Builder evidence** shows that the candidate was produced and tested.
- **Independent review** checks scope, contracts, documentation, and risks.
- **Release readiness** checks whether all required public gates are satisfied.
- **Publication authorization** is the final human decision to update a public
  branch, create a tag, publish a release, or make an announcement.

No earlier judgment implies a later one.

## Public-history safety

- Build public candidates from the current public branch, not by force-pushing
  an unrelated private history.
- Preserve public-only license, CI, images, and documentation unless their
  removal is explicitly in scope.
- Never use a force push to replace public `main` as a synchronization shortcut.
- Import product code through a reviewed public candidate with an explicit
  allowlist and provenance.
- Keep the private export branch and public `main` on the exact same candidate
  commit so future comparisons have a shared Git ancestor. The private product
  branch is not that shared branch and must never be pushed to the public
  repository.

The branch topology, allowlist, exclusions, and verification sequence are
defined in [Public Snapshot Synchronization](public-sync.md).

## Documentation consistency

Before publication, the README, architecture overview, deployment guidance,
status statements, and known limitations must describe the same candidate.
Historical snapshots must be clearly separated from current public claims.

## Stop conditions

Stop the publication flow when:

- a required milestone is unresolved;
- the candidate contains unreviewed files or credentials;
- public and candidate documentation disagree;
- tests or security checks required by the candidate fail;
- the public branch changed after the candidate was reviewed;
- the explicit human publication decision is missing.

The release-readiness work is tracked in
[M6: Public release readiness](https://github.com/danny094/TRION-system/issues/8).
