from __future__ import annotations


class PendingApprovalError(Exception):
    def __init__(self, approval_id: str = "", reason: str = ""):
        self.approval_id = str(approval_id or "")
        self.reason = str(reason or "")
        super().__init__(f"Approval required ({self.approval_id}): {self.reason}".strip())


def extract_pending_approval(error: BaseException) -> PendingApprovalError | None:
    approval_id = getattr(error, "approval_id", "")
    reason = getattr(error, "reason", "")
    if not approval_id and not reason:
        return None
    return PendingApprovalError(str(approval_id or ""), str(reason or ""))
