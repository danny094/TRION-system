#!/usr/bin/env python3
"""Print local runtime configuration facts without making a security verdict.

No service is started, contacted, or changed. The report is evidence for a
human security decision; it is not an authentication or release gate.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def quoted_values(lines: list[str], section: str) -> list[str]:
    values: list[str] = []
    active = False
    for line in lines:
        if re.match(rf"^    {re.escape(section)}:\s*$", line):
            active = True
            continue
        if active and re.match(r"^    [A-Za-z_][\w-]*:", line):
            active = False
        if active and (match := re.search(r"[- ]+['\"]?([^'\"\n]+)", line)):
            values.append(match.group(1).strip())
    return values


def compose_facts(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    ports = quoted_values(lines, "ports")
    volumes = quoted_values(lines, "volumes")
    facts = [f"compose file: {path}"]
    facts.extend(f"port mapping: {value}" for value in ports)
    facts.extend(f"host mount: {value}" for value in volumes if value.startswith("/"))
    if any("/var/run/docker.sock" in value for value in volumes):
        facts.append("docker socket mount: present")
    return facts


def cors_facts(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    match = re.search(r"allow_origins\s*=\s*(\[[^\]]*\])", source)
    if not match:
        return [f"CORS origins: not mechanically located in {path}"]
    return [f"CORS origins: {match.group(1)}"]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose", type=Path, default=root / "docker-compose.yml")
    parser.add_argument("--admin-main", type=Path, default=root / "adapters/admin-api/main.py")
    args = parser.parse_args()
    facts: list[str] = []
    if args.compose.is_file():
        facts.extend(compose_facts(args.compose))
    else:
        facts.append(f"compose file missing: {args.compose}")
    if args.admin_main.is_file():
        facts.extend(cors_facts(args.admin_main))
    else:
        facts.append(f"admin entry point missing: {args.admin_main}")
    print("Runtime posture facts (no security verdict):")
    print("\n".join(f"  {fact}" for fact in facts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
