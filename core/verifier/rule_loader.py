import csv
from pathlib import Path
from typing import Dict, List


_RULE_CACHE: dict[str, List[Dict[str, str]]] = {}
_RULE_MTIMES: dict[str, float] = {}


def load_security_rules() -> List[Dict[str, str]]:
    return _load_csv(_security_rules_path())


def load_anti_pattern_rules() -> List[Dict[str, str]]:
    return _load_csv(_anti_patterns_path())


def load_plan_rules() -> List[Dict[str, str]]:
    return _load_csv(_plan_rules_path())


def load_approval_rules() -> List[Dict[str, str]]:
    return _load_csv(_approval_rules_path())


def _load_csv(path: Path) -> List[Dict[str, str]]:
    cache_key = str(path)
    mtime = _mtime(path)
    if _RULE_CACHE.get(cache_key) is not None and _RULE_MTIMES.get(cache_key) == mtime:
        return _RULE_CACHE[cache_key]
    rows = _read_csv(path)
    _RULE_CACHE[cache_key] = rows
    _RULE_MTIMES[cache_key] = mtime
    return rows


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [
            {str(key or "").strip(): str(value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return -1.0


def _security_rules_path() -> Path:
    return _repo_root() / "intelligence_modules" / "cim_skill_rag" / "security_policies.csv"


def _anti_patterns_path() -> Path:
    return _repo_root() / "intelligence_modules" / "procedural_rag" / "anti_patterns.csv"


def _plan_rules_path() -> Path:
    return _repo_root() / "intelligence_modules" / "cim_skill_rag" / "verifier_plan_rules.csv"


def _approval_rules_path() -> Path:
    return _repo_root() / "intelligence_modules" / "cim_skill_rag" / "verifier_approval_rules.csv"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
