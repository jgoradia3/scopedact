"""Copy-paste integration: protect ordinary Python functions with ScopedAct."""
from scopedact import CallableTool, ScopedAct


records = {"invoice:123": {"amount": 245.75, "status": "pending"}}


def read_invoice(resource: str):
    return dict(records[resource])


def delete_invoice(resource: str):
    return records.pop(resource)


tool = CallableTool(
    "tool:billing",
    {"read": read_invoice, "delete": delete_invoice},
)
guard = ScopedAct(tool, audit_path="audit/quickstart.jsonl")
guard.issue_task(
    task_id="task:reconcile-123",
    initiator="human:operator",
    actor="agent:billing",
    permissions=[("read", "invoice:123")],
)

allowed = guard.invoke(
    task_id="task:reconcile-123",
    actor="agent:billing",
    action="read",
    resource="invoice:123",
)
denied = guard.invoke(
    task_id="task:reconcile-123",
    actor="agent:billing",
    action="delete",
    resource="invoice:123",
)

print("read:", allowed.reason_code, "executed=", allowed.executed)
print("delete:", denied.reason_code, "executed=", denied.executed)
assert allowed.executed is True
assert denied.executed is False
assert "invoice:123" in records
