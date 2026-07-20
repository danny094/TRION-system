import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def env_or_dotenv(name: str, default: str = "") -> str:
    import os

    value = str(os.getenv(name, "")).strip()
    if value:
        return value

    env_path = ROOT / ".env"
    if not env_path.exists():
        return default

    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, raw_value = line.partition("=")
            if key.strip() != name:
                continue
            value = raw_value.strip().strip("'\"")
            return value or default
    except Exception:
        return default
    return default
