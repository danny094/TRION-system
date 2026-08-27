import csv
import logging
import re
from pathlib import Path


logger = logging.getLogger("intelligence_modules.cim_policy.cim_policy_engine")
POLICY_DIR = Path(__file__).parent
POLICY_CSV = POLICY_DIR / "cim_policy.csv"


class CIMPolicyLoadingMixin:
    def _load_policies(self):
        """Lädt und kompiliert alle Policies aus CSV."""
        if not self.policy_file.exists():
            logger.warning(f"[CIM] Policy file not found: {self.policy_file}")
            return

        try:
            with open(self.policy_file, "r", encoding="utf-8") as policy_stream:
                reader = csv.DictReader(policy_stream)
                for row in reader:
                    row["check_skill_exists"] = row.get("check_skill_exists", "").lower() == "true"
                    row["allows_chaining"] = row.get("allows_chaining", "").lower() == "true"
                    row["requires_confirmation"] = row.get("requires_confirmation", "").lower() == "true"
                    row["intent_confidence"] = float(row.get("intent_confidence", 0.5))
                    pattern_id = row["pattern_id"]
                    regex_string = row.get("trigger_regex", "")
                    if regex_string:
                        try:
                            self.compiled_patterns[pattern_id] = re.compile(
                                regex_string, re.IGNORECASE | re.UNICODE
                            )
                        except re.error as error:
                            logger.error(f"[CIM] Invalid regex for {pattern_id}: {error}")
                            continue
                    self.policies.append(row)

            priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
            self.policies.sort(
                key=lambda item: priority_order.get(item.get("priority", "normal"), 2)
            )
            logger.info(f"[CIM] Loaded {len(self.policies)} policies")
        except Exception as error:
            logger.error(f"[CIM] Error loading policies: {error}")
