# Public Snapshot Synchronization

This document defines the reproducible boundary between private development and
the public TRION snapshot. It complements, but does not replace,
[Public Update and Release Governance](publication-governance.md).

## Branch topology

- The private product branch is the source of product code and tests.
- The private `public-sync/main` branch is built from the current public
  `main`, not from private Git history.
- The public `main` branch and private `public-sync/main` must point to the
  exact same candidate commit after publication.
- No private product commit, parent chain, tag, or force-push is used to update
  public history.

This gives future exports a shared Git ancestor while keeping private history
and private-only material outside the public repository.

## Product-path allowlist

Only these product paths are synchronized from the reviewed private source
commit:

```text
.gitignore
LICENSE
adapters/
assets/systemkarte.png
config/
core/
docker-compose.yml
examples/
intelligence_modules/
mcp/
mcp-servers/
memory/
personas/
plugins/
scripts/
tests/
tools/
utils/
```

The candidate mirrors those paths, including deletions, except for the exact
public-boundary sanitizations below. A path not listed here is not imported
merely because it exists in private development.

## Public-boundary sanitizations

- `core/routing_frame/README.md` and `core/self_context/README.md` replace
  private absolute documentation links with public architecture references.
- `tests/test_vendor_commander_docs_drift_migration.py` is excluded because it
  asserts against a private archived document that is not part of this
  snapshot.
- The project-authored synthetic fixtures under `tests/Dokumententest/`
  replace earlier third-party full-text fixtures.

## Preserved public wrapper

Public-only community and release files remain based on public `main`, including
`.github/`, `CONTRIBUTING.md`, `SECURITY.md`, public screenshots, package/CI
metadata, public concept documents, and the public documentation in `docs/`.
The generated Admin API route inventory may be refreshed from the private
source because it documents product code already inside the allowlist.

## Mandatory exclusions

Private instructions, plans, audits, operational notes, credentials, local
settings, generated databases, caches, and private history are excluded. In
particular, synchronization must not import `AGENTS.md`, `CLAUDE.md`, private
`docs/` trees, `.env` files, database files, or plan/audit archives.

Large third-party text fixtures are not part of the public boundary. Retrieval
tests use project-authored synthetic fixtures instead.

## Candidate sequence

1. Fetch the current private source and public `main` heads.
2. Stop if either reviewed base moved unexpectedly.
3. Start the candidate from public `main`.
4. Mirror only the allowlisted product paths from the exact private source
   commit and preserve the public wrapper.
5. Review the full path list, deletions, documentation, dependencies, and known
   limitations.
6. Run credential, private-path, size, architecture, and test checks.
7. Record milestone relevance, independent review, and the explicit human
   publication decision.
8. Push the candidate fast-forward to private `public-sync/main` and public
   `main`; never force-push either branch.
9. Verify both remote refs resolve to the same commit and require public CI to
   pass.

An identical commit is synchronization evidence. It is not a release, tag,
milestone closure, security certification, or lifecycle acceptance.
