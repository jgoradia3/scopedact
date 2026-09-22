from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from .agents import OpenAICompatibleProposer, ScriptedProposer
from .audit import AuditLogger
from .evaluator import AuthorizationEvaluator
from .grants import SQLiteGrantRegistry
from .lifecycle import GrantIssuer, LifecycleGateway, LifecycleOperator, LifecycleStore, run_id
from .lifecycle_config import LifecycleConfig
from .models import ActionRequest
from .policy import ActionPolicy, PolicySet
from .service import InvoiceService

@dataclass(frozen=True)
class AgentWorkflowResult:
    task_id: str
    source: str
    steps: tuple[tuple[str,str,bool], ...]

def run_agent_workflow(database: str|Path, config_path: str|Path, audit_output: str|Path|None=None, *, live=False, model="gpt-4.1-mini", proposer=None):
    """Run predefined workflow stages; a model may propose, but never authorize, each action."""
    config=LifecycleConfig.load(config_path); store=LifecycleStore(database); registry=SQLiteGrantRegistry(database)
    try:
        store.add_authority(config.initiator,config.upstream_authority); task_id=run_id("task-workflow")
        GrantIssuer(store,registry).issue(task_id=task_id,initiator=config.initiator,actor=config.actor,permissions=set(config.task_permissions),lifetime=timedelta(minutes=config.grant_lifetime_minutes))
        gateway=LifecycleGateway(AuthorizationEvaluator(registry),InvoiceService(),store,AuditLogger(audit_output,truncate=False),PolicySet({a:ActionPolicy(True) for a in config.approval_required_actions}))
        operator=LifecycleOperator(store,registry); steps=[]; history=""
        planned=[("Read the invoice","read","invoice:123"),("Read the purchase order","read","purchase-order:456"),("Compare the records","compare","comparison:123-456"),("Request payment approval","approve_payment","invoice:123")]
        live_proposer=proposer or (OpenAICompatibleProposer(model=model) if live else None)
        for label,action,resource in planned:
            body={"request_id":run_id("req-workflow"),"task_id":task_id,"actor":config.actor,"parent_actor":config.initiator,"tool":config.tool,"action":action,"resource":resource}
            current=live_proposer or ScriptedProposer(body)
            request=current.propose(label,{"allowed_proposal":str(body),"prior_outcomes":history})
            result=gateway.invoke(request); steps.append((label,result.decision.reason_code,result.decision.allowed))
            if result.decision.reason_code=="APPROVAL_REQUIRED":
                operator.approve(request.request_id,"human:workflow-reviewer"); result=gateway.invoke(request); steps.append((label+" after approval",result.decision.reason_code,result.decision.allowed))
            history += f"{label}:{result.decision.reason_code};"
        operator.close_task(task_id)
        return AgentWorkflowResult(task_id,"live-model" if live else "deterministic",tuple(steps))
    finally: store.close(); registry.close()
