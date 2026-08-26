# TRION Scripts

Run scripts from the repository root with Python bytecode generation disabled.
These commands provide mechanical evidence only; they do not replace tests,
independent review, release readiness, or publication authorization.

## Read-only checks

| Script | Purpose | Command |
|---|---|---|
| `check_code_caps.py` | Checks staged, unstaged, and untracked changed code files against the mandatory 200-line cap. | `python -B scripts/check_code_caps.py` |
| `check_doc07_caps.py` | Deprecated compatibility facade for `check_code_caps.py` until 2026-09-15. | `python -B scripts/check_doc07_caps.py` |

The canonical check covers Python, TypeScript, TSX, JavaScript, CSS, HTML, and
shell files. Deleted files do not create false positives. A clean result is a
preflight fact, not an architecture or lifecycle decision.

## Operator tools

| Script | Purpose | Command |
|---|---|---|
| `calibrate_tool_selector.py` | Evaluates selector thresholds against supplied fixtures. | `python -B scripts/calibrate_tool_selector.py --tools-json <file>` |
| `dump_endpoints.py` | Prints generated API-reference Markdown to standard output. | `python -B scripts/dump_endpoints.py` |

New scripts must keep one responsibility and document their read/write boundary
before they are used in CI or review.
