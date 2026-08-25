# Contributing to TRION

Thank you for helping improve TRION. This repository is a curated public
development snapshot and may lag active development. Before starting a large
change, open an issue so the scope can be checked against the current public
baseline.

## Start with the right issue

- Use a bug report for behavior that contradicts the public code or docs.
- Use an implementation proposal for a bounded change with measurable evidence.
- Use a decision request when the unresolved question is what the product
  should do, who owns a contract, or how far a change may reach.
- Report security vulnerabilities privately as described in
  [SECURITY.md](SECURITY.md).

Do not represent a proposal, local experiment, or private development status as
released public behavior.

## Contribution workflow

1. Base work on the current public `main` branch.
2. Keep the change focused on the issue's declared scope.
3. Preserve existing public documentation, license, CI, and compatibility
   boundaries unless the issue explicitly authorizes changing them.
4. Add or update tests for behavior changes.
5. Run the narrowest relevant tests, then the public test suite when practical:

   ```bash
   pytest -q
   ```

6. Complete the pull-request checklist with commands and observed results.

## Evidence and scope

Every non-trivial contribution should state:

- the accountable owner or leading public contract;
- the exact files or public surface affected;
- the target behavior and acceptance evidence;
- dependencies, known blockers, and out-of-scope work;
- the stop criterion for the proposed change.

Passing tests prove only the tested behavior. They do not by themselves
authorize a release, public status claim, tag, or deployment.

## Licensing

By submitting a contribution, you agree that it may be distributed under the
repository's [AGPL-3.0 license](LICENSE).
