from __future__ import annotations

import logging
import re
import subprocess
from typing import Any


TRUSTED_IMAGE_PATTERNS = [
    r"^(library/)?(ubuntu|debian|alpine|busybox):",
    r"^(library/)?(python|node|ruby|golang|rust|openjdk):",
    r"^(library/)?(postgres|mysql|mariadb|mongo|redis|memcached):",
    r"^(library/)?(nginx|httpd|traefik|caddy):",
    r"^(library/)?(elasticsearch|kibana|logstash):",
    r"^(library/)?(grafana|prometheus):",
    r"^josh5/steam-headless(:|@|$)",
]

OFFICIAL_BLUEPRINT_IDS = frozenset(
    {
        "python-sandbox",
        "node-sandbox",
        "db-sandbox",
        "shell-sandbox",
        "ubuntu-network",
        "runtime-hardware",
        "filestash",
    }
)

_NO_SIG_PATTERNS = (
    "no signatures found",
    "no matching signatures",
    "no signature found",
    "no attestations found",
    "does not have an associated signature",
    "signature not found",
)

_sig_log = logging.getLogger(__name__ + ".signature")


def is_trusted_image(image: str) -> bool:
    for pattern in TRUSTED_IMAGE_PATTERNS:
        if re.match(pattern, str(image or "").lower()):
            return True
    return False


def evaluate_image_trust(image_ref: str) -> dict[str, Any]:
    image_value = str(image_ref or "").strip()
    if is_trusted_image(image_value):
        return {
            "level": "verified",
            "source": "trusted-image-pattern",
            "reason": f"'{image_value}' entspricht einem bekannten vertrauenswürdigen Prefix",
            "image_ref": image_value,
            "image_digest": None,
        }
    return {
        "level": "unverified",
        "source": "user-created",
        "reason": f"'{image_value}' ist nicht in der Trusted-Image-Liste",
        "image_ref": image_value,
        "image_digest": None,
    }


def evaluate_blueprint_trust(blueprint: Any) -> dict[str, Any]:
    image_ref = getattr(blueprint, "image", None) or str(getattr(blueprint, "dockerfile", "") or "")[:80] or ""

    if getattr(blueprint, "id", "") in OFFICIAL_BLUEPRINT_IDS:
        return {
            "level": "verified",
            "source": "official-set",
            "reason": f"'{blueprint.id}' ist ein offiziell eingebauter Blueprint",
            "image_ref": image_ref,
            "image_digest": None,
        }

    if image_ref and is_trusted_image(image_ref):
        return {
            "level": "verified",
            "source": "trusted-image-pattern",
            "reason": f"Image '{image_ref}' entspricht einem bekannten vertrauenswürdigen Prefix",
            "image_ref": image_ref,
            "image_digest": None,
        }

    return {
        "level": "unverified",
        "source": "user-created",
        "reason": f"Blueprint '{getattr(blueprint, 'id', '')}' ist nicht offiziell — Image nicht in Trusted-List",
        "image_ref": image_ref,
        "image_digest": None,
    }


def resolve_image_digest(image_ref: str) -> str | None:
    try:
        import docker as _docker

        client = _docker.from_env()
        img = client.images.get(image_ref)
        digests = img.attrs.get("RepoDigests", [])
        for digest in digests:
            if "@" in digest:
                return digest.split("@", 1)[1]
        return None
    except Exception:
        return None


def verify_image_digest(image_ref: str, expected_digest: str) -> bool:
    if not expected_digest or not image_ref:
        return False
    try:
        actual = resolve_image_digest(image_ref)
        if actual is None:
            return False
        return actual.strip() == str(expected_digest or "").strip()
    except Exception:
        return False


def check_digest_policy(blueprint: Any) -> dict[str, Any]:
    image_ref = getattr(blueprint, "image", None) or ""
    pinned = getattr(blueprint, "image_digest", None)

    if not image_ref:
        return {
            "allowed": True,
            "mode": "no_image",
            "actual_digest": None,
            "reason": "Dockerfile-basierter Blueprint — kein Image-Digest-Check",
        }

    if not pinned:
        actual = resolve_image_digest(image_ref)
        return {
            "allowed": True,
            "mode": "unpinned_warn",
            "actual_digest": actual,
            "reason": (
                f"[Trust-Warn] Blueprint '{getattr(blueprint, 'id', '')}' hat keinen gepinnten Digest — "
                f"Image '{image_ref}' wird ohne Digest-Verifikation gestartet "
                f"(aktueller Digest: {actual or 'nicht auflösbar'})"
            ),
        }

    actual = resolve_image_digest(image_ref)
    if actual is None:
        return {
            "allowed": False,
            "mode": "pinned_strict",
            "actual_digest": None,
            "reason": (
                f"[Trust-Block] Image '{image_ref}' Digest nicht auflösbar — "
                f"erwartet: {pinned}. Start blockiert (fail closed)."
            ),
        }

    if actual.strip() != str(pinned).strip():
        return {
            "allowed": False,
            "mode": "pinned_strict",
            "actual_digest": actual,
            "reason": (
                f"[Trust-Block] Image Digest mismatch für '{image_ref}': "
                f"erwartet={pinned}, gefunden={actual}. Start blockiert."
            ),
        }

    return {
        "allowed": True,
        "mode": "pinned_strict",
        "actual_digest": actual,
        "reason": f"[Trust-OK] Image '{image_ref}' Digest verifiziert: {actual}",
    }


def _detect_no_signature(output: str) -> bool:
    low = str(output or "").lower()
    return any(pattern in low for pattern in _NO_SIG_PATTERNS)


def _try_verify(image_ref: str, timeout: int = 15) -> dict[str, Any]:
    for tool_name, cmd in [
        ("cosign", ["cosign", "verify", image_ref]),
        ("notation", ["notation", "verify", image_ref]),
    ]:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if proc.returncode == 0:
                return {"available": True, "ok": True, "absent": False, "reason": f"{tool_name} verify: OK", "tool": tool_name}
            combined = (proc.stdout + " " + proc.stderr).strip()
            return {
                "available": True,
                "ok": False,
                "absent": _detect_no_signature(combined),
                "reason": f"{tool_name}: {combined[:200] or 'verification failed'}",
                "tool": tool_name,
            }
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            return {"available": True, "ok": False, "absent": False, "reason": f"{tool_name} timeout after {timeout}s", "tool": tool_name}
        except Exception as exc:
            return {"available": True, "ok": False, "absent": False, "reason": f"{tool_name} error: {exc}", "tool": tool_name}

    return {"available": False, "ok": False, "absent": True, "reason": "No signature verification tool (cosign/notation) installed", "tool": None}


def verify_image_signature(image_ref: str) -> dict[str, Any]:
    from config import get_signature_verify_mode

    mode = get_signature_verify_mode()
    if mode == "off":
        _sig_log.debug("[Signature] mode=off image=%s → pass", image_ref)
        return {"verified": True, "mode": "off", "reason": "disabled", "tool": None}

    result = _try_verify(image_ref)
    if not result["available"]:
        if mode == "strict":
            msg = f"strict mode: {result['reason']}"
            _sig_log.warning("[Signature] BLOCK image=%s: %s", image_ref, msg)
            return {"verified": False, "mode": mode, "reason": msg, "tool": None}
        _sig_log.info("[Signature] opt_in allow (no tool) image=%s", image_ref)
        return {
            "verified": True,
            "mode": mode,
            "reason": f"opt_in: {result['reason']}, allowing without verification",
            "tool": None,
        }

    if result["ok"]:
        _sig_log.info("[Signature] VERIFIED image=%s tool=%s", image_ref, result["tool"])
        return {"verified": True, "mode": mode, "reason": result["reason"], "tool": result["tool"]}

    if result["absent"] and mode == "opt_in":
        _sig_log.info("[Signature] opt_in allow (no signature) image=%s tool=%s", image_ref, result["tool"])
        return {
            "verified": True,
            "mode": mode,
            "reason": f"opt_in: no signature for '{image_ref}', allowing",
            "tool": result["tool"],
        }

    return {"verified": False, "mode": mode, "reason": result["reason"], "tool": result["tool"]}
