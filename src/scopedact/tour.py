from __future__ import annotations

from pathlib import Path
from .mvp import run_lifecycle_demo

INTRO="""SCOPEDACT GUIDED TOUR

WHAT ARE WE BUILDING?
ScopedAct is a security checkpoint between an AI agent and the tools it wants to use.
The agent proposes an action. ScopedAct decides. Only an allowed action reaches the tool.

THE SIMULATED BUSINESS TASK
An AI procurement agent must read invoice 123, read purchase order 456, compare them,
and request payment. Invoice data and payment are synthetic; the authorization controls are real code.

THREE DISTINCT EVENTS
1. PROPOSAL  - the agent asks to perform an action.
2. DECISION  - ScopedAct checks identity, task state, exact permission, replay, and approval.
3. EXECUTION - the protected tool is called only when the decision permits it.
"""

def run_tour(database:str|Path="audit/tour.db",output:str|Path="audit/tour.jsonl")->str:
    result=run_lifecycle_demo(database,output);by_name={x.label:x for x in result.steps}
    lines=[INTRO,"LIVE WALKTHROUGH"]
    examples=[("Agent proposes: read invoice:123","read_invoice","Exact permission exists, so the synthetic invoice tool is called."),("Agent proposes: delete invoice:123","unauthorized_delete","Delete was never granted, so the tool is not called."),("Agent proposes: approve_payment invoice:123","payment_before_approval","Permission exists but human approval is required; nothing executes yet."),("Reviewer approves; agent resubmits the same lifecycle request","payment_after_approval","Approval now exists, so the payment simulation executes."),("Operator closes the task; agent proposes another read","request_after_close","Closed tasks cannot act, even if the old grant listed the action.")]
    for proposal,key,meaning in examples:
        step=by_name[key];lines += [f"\nPROPOSAL:  {proposal}",f"DECISION:  {step.decision}",f"EXECUTED:  {'YES' if step.executed else 'NO'}",f"WHY:       {meaning}"]
    lines += ["\nWHAT THIS PROVES","ScopedAct can enforce task-bounded authority, manual oversight, lifecycle shutdown, and durable evidence outside an agent's reasoning.","","WHAT THIS DOES NOT PROVE","It is not a production identity provider, autonomous general-purpose agent, real payment system, or enterprise deployment.","",f"TOUR RESULT: {'PASS' if result.passed else 'FAIL'}",f"DATABASE: {result.database}"]
    return "\n".join(lines)
