# Security Policy

TRION is under active development and does not currently publish a supported
stable release line. Security reports are still welcome and help shape the
public hardening work.

## Report a vulnerability privately

Do not open a public issue for a suspected vulnerability. Send a concise report
to `trlon.devs.dk@gmail.com` with:

- the affected public commit or component;
- the expected security boundary;
- reproducible steps or a minimal proof of concept;
- the observed impact;
- any suggested mitigation, if known.

Please exclude real API keys, personal data, or third-party secrets. Use test
credentials and redact logs where possible.

## Relevant security boundaries

Reports are especially useful when they concern:

- authentication or secret exposure;
- MCP tool authorization or contract bypass;
- container or Docker-socket isolation;
- path traversal, unsafe file access, or sandbox escape;
- prompt-to-tool escalation that bypasses declared capability boundaries;
- public output that exposes internal errors or unverified sensitive data.

## Disclosure

Please allow time for triage before public disclosure. There is currently no
bug-bounty program or guaranteed response-time commitment. Publication of a fix
still follows the repository's documented
[publication governance](docs/publication-governance.md).
