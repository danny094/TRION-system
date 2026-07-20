from __future__ import annotations

import hashlib
import io
import logging
from typing import Any

from commander_deploy_runtime_client import TRION_LABEL, get_runtime_client


logger = logging.getLogger(__name__)

try:
    from docker.errors import BuildError, ImageNotFound
except Exception:  # pragma: no cover - exercised in lightweight import-only test envs
    class BuildError(Exception):
        pass

    class ImageNotFound(Exception):
        pass


def blueprint_image_tag(blueprint: Any) -> str:
    if getattr(blueprint, "image", None):
        return str(blueprint.image)
    dockerfile = str(getattr(blueprint, "dockerfile", "") or "")
    fingerprint = hashlib.sha256(dockerfile.encode("utf-8")).hexdigest()[:12]
    return f"trion/{blueprint.id}:{fingerprint}"


def build_image(blueprint: Any) -> str:
    client = get_runtime_client()
    tag = blueprint_image_tag(blueprint)

    if getattr(blueprint, "image", None):
        try:
            client.images.get(blueprint.image)
        except ImageNotFound:
            logger.info("[CommanderDeployImage] Pulling image: %s", blueprint.image)
            client.images.pull(blueprint.image)
        return str(blueprint.image)

    if not getattr(blueprint, "dockerfile", None):
        raise ValueError(f"Blueprint '{blueprint.id}' has no dockerfile and no image")

    logger.info("[CommanderDeployImage] Building image: %s", tag)
    dockerfile_obj = io.BytesIO(str(blueprint.dockerfile).encode("utf-8"))
    try:
        image, build_logs = client.images.build(
            fileobj=dockerfile_obj,
            tag=tag,
            rm=True,
            forcerm=True,
            labels={TRION_LABEL: "true", "trion.blueprint": blueprint.id},
        )
        _ = image
        for chunk in build_logs:
            if "stream" in chunk:
                logger.debug("[CommanderDeployImage] %s", str(chunk["stream"]).strip())
        return tag
    except BuildError:
        logger.exception("[CommanderDeployImage] Build failed for %s", blueprint.id)
        raise


def image_exists(blueprint: Any) -> bool:
    client = get_runtime_client()
    try:
        client.images.get(blueprint_image_tag(blueprint))
        return True
    except ImageNotFound:
        return False
