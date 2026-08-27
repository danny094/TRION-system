from __future__ import annotations

from typing import Dict


def infer_service_name(container_port: str, blueprint_id: str = "", image_ref: str = "") -> str:
    raw_port = str(container_port or "").strip().lower()
    if not raw_port:
        return ""
    if "/" in raw_port:
        port_text, proto = raw_port.rsplit("/", 1)
    else:
        port_text, proto = raw_port, "tcp"
    try:
        port_num = int(port_text)
    except Exception:
        return ""

    lower_bp = str(blueprint_id or "").strip().lower()
    lower_image = str(image_ref or "").strip().lower()
    if (
        lower_bp in {"gaming-station", "steam-headless", "gaming_station"}
        or "steam-headless" in lower_image
        or "sunshine" in lower_image
    ):
        sunshine_names = {
            (8083, "tcp"): "Desktop GUI (noVNC)",
            (47984, "tcp"): "Sunshine HTTPS",
            (47989, "tcp"): "Sunshine HTTP",
            (47990, "tcp"): "Sunshine Web UI",
            (48010, "tcp"): "Sunshine RTSP",
            (47998, "udp"): "Sunshine Video",
            (47999, "udp"): "Sunshine Control",
            (48000, "udp"): "Sunshine Audio",
            (48002, "udp"): "Sunshine Mic",
        }
        if (port_num, proto) in sunshine_names:
            return sunshine_names[(port_num, proto)]
        if proto == "udp" and 48100 <= port_num <= 48110:
            return "Game Stream UDP"

    well_known = {
        (22, "tcp"): "SSH",
        (53, "tcp"): "DNS",
        (53, "udp"): "DNS",
        (80, "tcp"): "HTTP",
        (81, "tcp"): "Web UI",
        (110, "tcp"): "POP3",
        (123, "udp"): "NTP",
        (143, "tcp"): "IMAP",
        (443, "tcp"): "HTTPS",
        (445, "tcp"): "SMB",
        (465, "tcp"): "SMTP TLS",
        (587, "tcp"): "SMTP",
        (993, "tcp"): "IMAPS",
        (995, "tcp"): "POP3S",
        (1433, "tcp"): "SQL Server",
        (1521, "tcp"): "Oracle DB",
        (1883, "tcp"): "MQTT",
        (2375, "tcp"): "Docker API",
        (3000, "tcp"): "Web App",
        (3306, "tcp"): "MySQL",
        (3389, "tcp"): "RDP",
        (3478, "udp"): "STUN/TURN",
        (5000, "tcp"): "Registry/API",
        (5432, "tcp"): "PostgreSQL",
        (5672, "tcp"): "RabbitMQ",
        (5900, "tcp"): "VNC",
        (6080, "tcp"): "noVNC",
        (6379, "tcp"): "Redis",
        (7860, "tcp"): "Gradio",
        (8000, "tcp"): "HTTP API",
        (8006, "tcp"): "Web UI",
        (8080, "tcp"): "Web UI",
        (8081, "tcp"): "Admin UI",
        (8123, "tcp"): "Home Assistant",
        (8443, "tcp"): "HTTPS Admin",
        (8501, "tcp"): "Streamlit",
        (9000, "tcp"): "Web Console",
        (9090, "tcp"): "Metrics UI",
        (9443, "tcp"): "HTTPS UI",
        (11434, "tcp"): "Ollama API",
        (27017, "tcp"): "MongoDB",
    }
    return well_known.get((port_num, proto), "")


def infer_access_link_meta(container_port: str, blueprint_id: str = "", image_ref: str = "") -> Dict[str, str]:
    raw_port = str(container_port or "").strip().lower()
    if not raw_port:
        return {}
    if "/" in raw_port:
        port_text, proto = raw_port.rsplit("/", 1)
    else:
        port_text, proto = raw_port, "tcp"
    try:
        port_num = int(port_text)
    except Exception:
        return {}

    lower_bp = str(blueprint_id or "").strip().lower()
    lower_image = str(image_ref or "").strip().lower()
    if proto == "tcp" and (
        lower_bp in {"gaming-station", "steam-headless", "gaming_station"}
        or "steam-headless" in lower_image
        or "sunshine" in lower_image
    ):
        if port_num == 8083:
            return {
                "access_label": "Open Desktop GUI",
                "access_scheme": "http",
                "access_path": "/web/",
                "access_kind": "desktop_gui",
            }
        if port_num == 47990:
            return {
                "access_label": "Open Sunshine",
                "access_scheme": "https",
                "access_path": "/welcome",
                "access_kind": "web_ui",
            }
        if port_num == 47989:
            return {
                "access_label": "Open Sunshine HTTP",
                "access_scheme": "http",
                "access_path": "/",
                "access_kind": "web_ui",
            }
    return {}
