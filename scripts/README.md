# TRION Scripts

Run scripts from the repository root. Prefer `.venv/bin/python -B` for Python
checks so imports cannot create bytecode caches. A script that reports `PASS`
or exits `0` is only mechanical evidence. It does not replace tests, an
independent Doc37 audit, lifecycle acceptance, or a human `DECIDE`.

Read-only checks inspect repository and documentation facts only: they do not
write product artifacts, mutate Git state, make runtime or network calls, or
decide architecture or lifecycle status. `REVIEW_REQUIRED` is a fact for a
separate review, not a failed check or a decision.

## Read-only checks

`check_code_caps.py` is the canonical Doc07 line-cap preflight. The deprecated
`check_doc07_caps.py` command delegates to it unchanged until 2026-09-15.

| Script | Purpose | Typical command |
|---|---|---|
| `check_code_caps.py` | Canonical changed-file 200-line cap for `.py`, `.ts`, `.tsx`, `.js`, `.css`, `.html`, and `.sh`. | `.venv/bin/python -B scripts/check_code_caps.py` |
| `check_doc07_caps.py` | DEPRECATED compatibility facade for the canonical cap check. | `.venv/bin/python -B scripts/check_doc07_caps.py` |
| `check_import_boundaries.py` | Checks Doc07 import directions in changed Python files. | `.venv/bin/python -B scripts/check_import_boundaries.py` |
| `check_container_commander_bundle_freshness.py` | Generates the Container Commander bundle in memory and compares it with the tracked `examples/container_commander_bundle` files. | `.venv/bin/python -B scripts/check_container_commander_bundle_freshness.py` |
| `collect_runtime_posture.py` | Reports Compose ports, host mounts, Docker socket presence, and Admin API CORS facts. It makes no security verdict. | `.venv/bin/python -B scripts/collect_runtime_posture.py` |
| `check_deprecation_deadlines.py` | Reports expired or over-30-day `DEPRECATED YYYY-MM-DD` markers outside Markdown code examples. It never deletes code. | `.venv/bin/python -B scripts/check_deprecation_deadlines.py` |
| `check_prompt_provenance_report.py` | Reports changed prompt-building functions and nearby provenance hints. Advisory only. | `.venv/bin/python -B scripts/check_prompt_provenance_report.py` |
| `check_shadow_authorities.py` | Reports changed-code candidates for duplicate routing signals, hardcoded tool truth, or registry writers. It emits warnings only. | `.venv/bin/python -B scripts/check_shadow_authorities.py` |
| `check_pipeline_contracts.py` | Runs the bounded pipeline preflights with fixed Python argv lists; it preserves every child fact and `REVIEW_REQUIRED` unchanged. It forwards `--all` only to children that accept it, and each child retains its documented scope semantics. | `.venv/bin/python -B scripts/check_pipeline_contracts.py` |
| `check_context_contracts.py` | Reports `routing_frame` and `orchestrator_context` producers outside their expected pipeline owners. | `.venv/bin/python -B scripts/check_context_contracts.py` |
| `check_mcp_descriptor_chain.py` | Inventories MCP capability-field projections across its full filesystem source scope in `mcp/`, `adapters/`, `core/`, and `tools/`; it is not limited to tracked or changed paths. It accepts `--all` as a compatibility no-op. | `.venv/bin/python -B scripts/check_mcp_descriptor_chain.py` |
| `check_event_contract_parity.py` | Checks backend and WebUI chat-event literals independently against the Doc10 contract; it does not compare backend and WebUI literals with each other. | `.venv/bin/python -B scripts/check_event_contract_parity.py` |
| `check_guard_test_evidence.py` | Reports changed guard functions with no literal reference in `tests/`; its deterministic changed-product-Python scope is the deduplicated union of unstaged, staged, and untracked Git paths. | `.venv/bin/python -B scripts/check_guard_test_evidence.py` |
| `check_contract_writer_ownership.py` | Reports potential writes to registry, evidence, and conversation-state contracts. | `.venv/bin/python -B scripts/check_contract_writer_ownership.py` |
| `check_api_contract_drift.py` | Reports static Admin API routes, including local router prefixes, absent from the generated API reference. | `.venv/bin/python -B scripts/check_api_contract_drift.py` |
| `check_generated_output_ownership.py` | Runs registered read-only generated-artifact ownership checks. | `.venv/bin/python -B scripts/check_generated_output_ownership.py` |
| `check_doc_links.py` | Checks local Markdown and wiki-style links from active docs; archives and frozen snapshots are targets but not scan sources. | `.venv/bin/python -B scripts/check_doc_links.py` |

## Generators and operator tools

These scripts have a different boundary. Do not run them as generic checks.

| Script | Purpose and write behavior | Typical command |
|---|---|---|
| `build_container_commander_bundle.py` | Generates a Container Commander bundle into the selected output directory. It writes there. | `.venv/bin/python scripts/build_container_commander_bundle.py --out build/generated_bundle` |
| `dump_endpoints.py` | Prints generated API-reference Markdown to stdout. It writes only when shell redirection is used. | `.venv/bin/python -B scripts/dump_endpoints.py` |
| `migrate_mcp_registry_core_entries.py` | Inspects registry collisions by default. Only `--apply` creates a backup and changes the registry. | `.venv/bin/python -B scripts/migrate_mcp_registry_core_entries.py` |
| `project_mcp_protocol_version.py` | Projects the canonical protocol version into bundle source and writes the target. | `.venv/bin/python scripts/project_mcp_protocol_version.py` |
| `calibrate_tool_selector.py` | Evaluates selector thresholds against supplied fixtures. It does not persist selector configuration. | `.venv/bin/python -B scripts/calibrate_tool_selector.py --tools-json <file>` |

## Rule for new scripts

Give every script one responsibility. Reuse an existing contract or generator
instead of reimplementing its semantics. A script may report facts, but it may
not become a second registry, security authority, test selector, or lifecycle
auditor. Document every new executable here before relying on it in a review.

These checks are mechanical builder preflights. Do not run them inside an
absolute Doc37 audit gate when that gate forbids Python execution, imports, or
tests; such a run would invalidate the audit rather than add admissible proof.

`check_shadow_authorities.py` is the single advisory authority scanner. Its
default scope is the union of changed unstaged, staged, and untracked code in
`adapters/`, `config/`, `core/`, `examples/`, `mcp/`, `mcp-servers/`, `memory/`,
`tools/`, and `utils/`; `--all` scans tracked code in those roots. It reports
candidate routing re-derivations, container-reference fallback decisions,
hardcoded tool truth, and registry writers. Every Python `BoolOr` or `IfExp`
selection between `container_id` and `container_name` is conservatively
`REVIEW_REQUIRED` unless it occurs in exactly
`mcp-servers/container-commander/contracts.py::normalize_container_reference`
oder in dessen generatorerzeugter self-contained Projektion
`examples/container_commander_bundle/bundle_dispatch.py::
normalize_container_reference`.
`mcp-servers/container-commander/container_reference.py::
resolve_container_reference` ist nur noch Live-Docker-Consumer und keine
eigene Referenzautoritaet.
Prompt, error, result,
dictionary, return, f-string, keyword, path, and data-flow context do not create
additional exemptions, so `--all` may intentionally report known projection
candidates. The documented owner map is a review aid, not a second authority.
Neither scanner creates files, mutates Git, replaces tests or audits, or decides
architecture, lifecycle, or a human `DECIDE`.
