from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from .grants import GrantRegistry
from .models import ActionRequest, Decision, GrantStatus, Permission, utc_now


class AuthorizationEvaluator:
    def __init__(
        self,
        registry: GrantRegistry,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.registry = registry
        self.clock = clock

    def evaluate(self, request: ActionRequest) -> Decision:
        grant = self.registry.get(request.task_id)
        if grant is None:
            return Decision(False, "GRANT_NOT_FOUND", "No task grant exists.")
        if grant.principal != request.actor:
            return Decision(False, "ACTOR_MISMATCH", "Grant belongs to another principal.")
        if grant.status is not GrantStatus.ACTIVE:
            return Decision(False, "GRANT_INACTIVE", "Task grant is not active.")
        if self.registry.is_revoked(grant.task_id):
            return Decision(False, "GRANT_REVOKED", "Task grant has been revoked.")
        if self.clock() >= grant.expires_at:
            return Decision(False, "GRANT_EXPIRED", "Task grant has expired.")
        # A descendant remains bounded by every current ancestor grant.
        node = grant
        seen = {grant.task_id}
        while node.parent_task_id:
            if node.parent_task_id in seen:
                return Decision(False, "INVALID_DELEGATION_CHAIN", "Delegation cycle detected.")
            seen.add(node.parent_task_id)
            parent = self.registry.get(node.parent_task_id)
            if parent is None:
                return Decision(False, "INVALID_DELEGATION_CHAIN", "Ancestor is missing.")
            if (parent.status is not GrantStatus.ACTIVE or self.registry.is_revoked(parent.task_id)
                    or self.clock() >= parent.expires_at):
                return Decision(False, "ANCESTOR_INACTIVE", "Ancestor authority is no longer active.")
            if (node.initiator != parent.initiator or not node.permissions <= parent.permissions
                    or node.expires_at > parent.expires_at):
                return Decision(False, "INVALID_DELEGATION_CHAIN", "Ancestor bounds exceeded.")
            node = parent
        requested = Permission(request.action, request.resource)
        if requested not in grant.permissions:
            return Decision(False, "PERMISSION_NOT_GRANTED", "Action-resource pair is outside the task grant.")
        return Decision(True, "PERMISSION_GRANTED", "Action-resource pair is explicitly granted.")

