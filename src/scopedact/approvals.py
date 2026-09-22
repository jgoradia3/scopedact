from __future__ import annotations

from .models import Approval, ApprovalStatus


class ApprovalRegistry:
    def __init__(self) -> None:
        self._approvals: dict[str, Approval] = {}

    def request(self, request_id: str) -> Approval:
        return self._approvals.setdefault(request_id, Approval(request_id))

    def approve(self, request_id: str, reviewer: str) -> Approval:
        approval = self.request(request_id)
        approval.status = ApprovalStatus.APPROVED
        approval.reviewer = reviewer
        return approval

    def reject(self, request_id: str, reviewer: str) -> Approval:
        approval = self.request(request_id)
        approval.status = ApprovalStatus.REJECTED
        approval.reviewer = reviewer
        return approval

    def get(self, request_id: str) -> Approval | None:
        return self._approvals.get(request_id)
