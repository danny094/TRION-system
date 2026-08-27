from __future__ import annotations

from typing import Any, Dict, List, Optional

from commander_runtime_connection_inference import infer_access_link_meta, infer_service_name
from utils.service_endpoint_resolver import resolve_public_endpoint_host


def extract_port_details(attrs: Dict[str, Any]) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    ports_obj = (((attrs or {}).get("NetworkSettings") or {}).get("Ports") or {})
    config = (attrs or {}).get("Config") or {}
    labels = config.get("Labels") or {}
    blueprint_id = str(labels.get("trion.blueprint") or "").strip().lower()
    image_ref = str(config.get("Image") or "").strip().lower()
    for container_port, bindings in dict(ports_obj).items():
        if not bindings:
            continue
        for binding in bindings:
            result.append(
                {
                    "container_port": str(container_port or ""),
                    "host_ip": str((binding or {}).get("HostIp") or "0.0.0.0"),
                    "host_port": str((binding or {}).get("HostPort") or ""),
                    "service_name": infer_service_name(
                        str(container_port or ""),
                        blueprint_id=blueprint_id,
                        image_ref=image_ref,
                    ),
                    **infer_access_link_meta(
                        str(container_port or ""),
                        blueprint_id=blueprint_id,
                        image_ref=image_ref,
                    ),
                }
            )
    return sorted(result, key=lambda item: (item.get("host_port", ""), item.get("container_port", "")))


def build_connection_info(ip_address: Optional[str], ports: List[Dict[str, str]]) -> Dict[str, Any]:
    import os

    configured_public_host = str(os.environ.get("TRION_PUBLIC_HOST", "")).strip()
    public_host = configured_public_host
    endpoints: List[str] = []
    access_links: List[Dict[str, str]] = []
    seen_links: set[tuple[str, str, str, str]] = set()
    for port in list(ports or []):
        host_port = str(port.get("host_port") or "").strip()
        container_port = str(port.get("container_port") or "").strip()
        if not host_port:
            continue
        proto = "tcp"
        if "/" in container_port:
            _, proto = container_port.rsplit("/", 1)
        endpoint_host = resolve_public_endpoint_host(
            configured_public_host=configured_public_host,
            host_ip=str(port.get("host_ip") or "").strip(),
        )
        if endpoint_host:
            endpoints.append(f"{endpoint_host}:{host_port}/{proto}")
        access_scheme = str(port.get("access_scheme") or "").strip()
        if access_scheme:
            access_path = str(port.get("access_path") or "/").strip() or "/"
            link_key = (host_port, access_scheme, access_path, str(port.get("access_label") or "").strip())
            if link_key not in seen_links:
                seen_links.add(link_key)
                link_url = ""
                if endpoint_host:
                    link_url = f"{access_scheme}://{endpoint_host}:{host_port}{access_path}"
                access_links.append(
                    {
                        "host_ip": str(port.get("host_ip") or "0.0.0.0"),
                        "host_port": host_port,
                        "container_port": container_port,
                        "service_name": str(port.get("service_name") or "").strip(),
                        "label": str(port.get("access_label") or "Open").strip(),
                        "scheme": access_scheme,
                        "path": access_path,
                        "kind": str(port.get("access_kind") or "").strip(),
                        "url": link_url,
                    }
                )
    connection: Dict[str, Any] = {
        "ip_address": ip_address,
        "public_host": public_host,
        "published_endpoints": endpoints,
    }
    if access_links:
        connection["access_links"] = access_links
    return connection
