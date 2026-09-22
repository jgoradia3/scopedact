from __future__ import annotations

import argparse
from pathlib import Path
import json
import os

from . import __version__
from .scenarios import SCENARIOS, run_all, run_scenario


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="scopedact", description="Task-scoped authorization for AI-agent tool actions")
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a usable local ScopedAct project")
    init.add_argument("--project", type=Path, default=Path(".scopedact"))
    doctor = commands.add_parser("doctor", help="Validate project configuration and local prerequisites")
    doctor.add_argument("--project", type=Path, default=Path(".scopedact"))
    serve = commands.add_parser("serve", help="Start the authority gateway, protected workspace tool, and console")
    serve.add_argument("--project", type=Path, default=Path(".scopedact"))
    create_task = commands.add_parser("create-task", help="Create an agent task from the reviewed project policy")
    create_task.add_argument("--project", type=Path, default=Path(".scopedact"))
    invoke = commands.add_parser("invoke", help="Submit a signed tool-action proposal through ScopedAct")
    invoke.add_argument("--project", type=Path, default=Path(".scopedact"))
    invoke.add_argument("--task-id", required=True)
    invoke.add_argument("--action", required=True)
    invoke.add_argument("--resource", required=True)
    invoke.add_argument("--input")
    invoke.add_argument("--request-id")
    commands.add_parser("list", help="List deterministic scenarios")
    demo = commands.add_parser("demo", help="Run every scenario")
    demo.add_argument("--output", type=Path, default=Path("audit/demo.jsonl"))
    run = commands.add_parser("run", help="Run one scenario")
    run.add_argument("scenario", choices=sorted(SCENARIOS))
    run.add_argument("--output", type=Path)
    agent = commands.add_parser("agent-demo", help="Run an offline or optional live-model proposal")
    agent.add_argument("--live", action="store_true", help="Use OPENAI_API_KEY and a live model")
    agent.add_argument("--model", default="gpt-4.1-mini")
    agent.add_argument("--output", type=Path, default=Path("audit/agent-demo.jsonl"))
    aws = commands.add_parser("aws-iam-demo", help="Read one explicitly granted IAM role")
    aws.add_argument("--role-name", required=True)
    aws.add_argument("--profile")
    aws.add_argument("--output", type=Path, default=Path("audit/aws-iam-demo.jsonl"))
    lifecycle = commands.add_parser("lifecycle-demo", help="Run the durable authority-lifecycle MVP")
    lifecycle.add_argument("--database", type=Path, default=Path("audit/lifecycle.db"))
    lifecycle.add_argument("--output", type=Path, default=Path("audit/lifecycle.jsonl"))
    lifecycle_aws = commands.add_parser("lifecycle-aws-demo", help="Run one read-only AWS role lookup through lifecycle controls")
    lifecycle_aws.add_argument("--role-name", required=True)
    lifecycle_aws.add_argument("--profile")
    lifecycle_aws.add_argument("--database", type=Path, default=Path("audit/lifecycle.db"))
    lifecycle_aws.add_argument("--output", type=Path, default=Path("audit/lifecycle-aws.jsonl"))
    init_demo = commands.add_parser("init-demo", help="Create an active hands-on procurement task")
    init_demo.add_argument("--database", type=Path, default=Path("audit/lifecycle.db"))
    init_demo.add_argument("--config", type=Path)
    init_demo.add_argument("--authority-bundle", type=Path)
    workflow = commands.add_parser("workflow-demo", help="Run a multi-step deterministic or optional model-proposed workflow")
    workflow.add_argument("--database", type=Path, default=Path("audit/workflow.db"))
    workflow.add_argument("--config", type=Path, default=Path("config/lifecycle.json"))
    workflow.add_argument("--output", type=Path, default=Path("audit/workflow.jsonl"))
    workflow.add_argument("--live", action="store_true")
    workflow.add_argument("--model", default="gpt-4.1-mini")
    verify = commands.add_parser("verify-events", help="Verify the local lifecycle event hash chain")
    verify.add_argument("--database", type=Path)
    verify.add_argument("--project", type=Path, default=Path(".scopedact"))
    preflight = commands.add_parser("aws-preflight", help="Show the active AWS identity and record connector health")
    preflight.add_argument("--profile")
    preflight.add_argument("--database", type=Path, default=Path("audit/lifecycle.db"))
    dry = commands.add_parser("aws-dry-run", help="Print the exact read-only AWS command without executing it")
    dry.add_argument("--role-name", required=True); dry.add_argument("--profile")
    auth_create=commands.add_parser("authority-create",help="Create a signed, time-bounded authority bundle")
    auth_create.add_argument("--config",type=Path,default=Path("config/lifecycle.json"));auth_create.add_argument("--output",type=Path,default=Path("audit/authority.json"));auth_create.add_argument("--key-id",default="local:v1");auth_create.add_argument("--lifetime",type=int,default=60)
    auth_verify=commands.add_parser("authority-verify",help="Verify a signed authority bundle")
    auth_verify.add_argument("--config",type=Path,default=Path("config/lifecycle.json"));auth_verify.add_argument("--bundle",type=Path,default=Path("audit/authority.json"))
    anchor=commands.add_parser("anchor-events",help="Write a separately retained signed event-chain anchor")
    anchor.add_argument("--database",type=Path,default=Path("audit/lifecycle.db"));anchor.add_argument("--output",type=Path,default=Path("audit/lifecycle.anchor.json"))
    verify_anchor=commands.add_parser("verify-anchor",help="Verify lifecycle state against a signed anchor")
    verify_anchor.add_argument("--database",type=Path,default=Path("audit/lifecycle.db"));verify_anchor.add_argument("--anchor",type=Path,default=Path("audit/lifecycle.anchor.json"))
    commands.add_parser("connectors",help="List built-in connector contracts")
    lab=commands.add_parser("lab",help="Run the localhost gateway, protected tool, and operator console")
    lab.add_argument("--database",type=Path,default=Path("audit/lab.db"));lab.add_argument("--config",type=Path,default=Path("config/lifecycle.json"));lab.add_argument("--gateway-port",type=int,default=8770);lab.add_argument("--tool-port",type=int,default=8780);lab.add_argument("--dashboard-port",type=int,default=8765)
    lab_agent=commands.add_parser("lab-agent",help="Run a separate signed agent client against the lab gateway")
    lab_agent.add_argument("--gateway",default="http://127.0.0.1:8770");lab_agent.add_argument("--task-id");lab_agent.add_argument("--resume-request-id")
    tour=commands.add_parser("tour",help="Run a narrated explanation of proposals, decisions, and execution")
    tour.add_argument("--database",type=Path,default=Path("audit/tour.db"));tour.add_argument("--output",type=Path,default=Path("audit/tour.jsonl"))
    action_request = commands.add_parser("request", help="Propose one action for a hands-on demo task")
    action_request.add_argument("--task-id", required=True)
    action_request.add_argument("--action", required=True)
    action_request.add_argument("--resource", required=True)
    action_request.add_argument("--request-id")
    action_request.add_argument("--database", type=Path, default=Path("audit/lifecycle.db"))
    action_request.add_argument("--output", type=Path, default=Path("audit/hands-on.jsonl"))
    dashboard = commands.add_parser("dashboard", help="Serve the local interactive operator console")
    dashboard.add_argument("--database", type=Path, default=Path("audit/lifecycle.db"))
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8765)
    dashboard.add_argument("--config",type=Path,default=Path("config/lifecycle.json"))
    status = commands.add_parser("status", help="Print durable lifecycle state as JSON")
    status.add_argument("--database", type=Path)
    status.add_argument("--project", type=Path, default=Path(".scopedact"))
    task = commands.add_parser("task", help="Pause, resume, revoke, or close a lifecycle task")
    task.add_argument("action", choices=["pause", "resume", "revoke", "close"])
    task.add_argument("task_id")
    task.add_argument("--database", type=Path)
    task.add_argument("--project", type=Path, default=Path(".scopedact"))
    approval = commands.add_parser("approval", help="Approve or reject a pending request")
    approval.add_argument("action", choices=["approve", "reject"])
    approval.add_argument("request_id")
    approval.add_argument("--reviewer", required=True)
    approval.add_argument("--database", type=Path)
    approval.add_argument("--project", type=Path, default=Path(".scopedact"))
    return root


def render(results) -> int:
    print(f"{'SCENARIO':<24} {'RESULT':<7} OBSERVED")
    print("-" * 72)
    for item in results:
        print(f"{item.name:<24} {'PASS' if item.passed else 'FAIL':<7} {item.observed}")
    passed = sum(item.passed for item in results)
    print(f"\n{passed}/{len(results)} predefined deterministic scenarios passed.")
    return 0 if passed == len(results) else 1


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "init":
        from .application import initialize_application
        project = initialize_application(args.project)
        print(f"CREATED: {project.directory}")
        print(f"POLICY:  {project.lifecycle_config}")
        print(f"FILES:   {project.workspace}")
        print("NEXT:    scopedact doctor && scopedact serve")
        return 0
    if args.command == "doctor":
        from .application import diagnose_application
        result = diagnose_application(args.project)
        for item in result["checks"]:
            print(f"{'PASS' if item['healthy'] else 'FAIL':<5} {item['name']:<22} {item['path']}")
        print(f"RESULT: {'READY' if result['healthy'] else 'ACTION_REQUIRED'}")
        return 0 if result["healthy"] else 1
    if args.command == "serve":
        from .application import serve_application
        serve_application(args.project)
        return 0
    if args.command == "create-task":
        from .application import create_application_task
        try: result = create_application_task(args.project)
        except OSError as error:
            print("ERROR: cannot reach the ScopedAct gateway. Start 'scopedact serve' first.")
            return 2
        print(f"TASK:   {result['task_id']}")
        print(f"STATUS: {result['status']}")
        print("NEXT: copy the task ID into a 'scopedact invoke' command")
        return 0
    if args.command == "invoke":
        from .application import invoke_application
        try: result = invoke_application(directory=args.project, task_id=args.task_id, action=args.action, resource=args.resource, input_value=args.input, request_id=args.request_id)
        except OSError:
            print("ERROR: cannot reach the ScopedAct gateway. Start 'scopedact serve' first.")
            return 2
        print(f"REQUEST:  {result.get('request_id', args.request_id or 'not-created')}")
        print(f"DECISION: {result.get('decision', result.get('error'))}")
        print(f"EXECUTED: {result.get('executed', False)}")
        if result.get("value") is not None: print("RESULT:   " + json.dumps(result["value"], sort_keys=True))
        if result.get("decision") == "APPROVAL_REQUIRED": print("NEXT: approve in http://127.0.0.1:8765, then repeat this command with --request-id " + result["request_id"])
        return 0 if result.get("executed") or result.get("decision") == "APPROVAL_REQUIRED" else 1
    if args.command == "list":
        for name in SCENARIOS:
            print(name)
        return 0
    if args.command == "run":
        return render([run_scenario(args.scenario, args.output)])
    if args.command == "agent-demo":
        from .integrations import run_agent_demo
        result, proposal = run_agent_demo(live=args.live, model=args.model, output=args.output)
        print("PROPOSAL")
        for key, value in proposal.items():
            print(f"  {key}: {value}")
        print(f"DECISION: {result.decision.reason_code}")
        print(f"EXECUTED: {result.decision.allowed}")
        if result.value is not None:
            print(f"RESULT: {result.value}")
        return 0 if result.decision.allowed else 1
    if args.command == "aws-iam-demo":
        from .integrations import run_aws_iam_demo
        result = run_aws_iam_demo(args.role_name, profile=args.profile, output=args.output)
        print(f"DECISION: {result.decision.reason_code}")
        print(f"EXECUTED: {result.decision.allowed}")
        if result.value is not None:
            print(f"RESULT: {result.value}")
        return 0 if result.decision.allowed else 1
    if args.command == "lifecycle-demo":
        from .mvp import run_lifecycle_demo
        result = run_lifecycle_demo(args.database, args.output)
        print(f"{'STEP':<27} {'DECISION':<30} EXECUTED")
        print("-" * 72)
        for step in result.steps:
            print(f"{step.label:<27} {step.decision:<30} {step.executed}")
        print(f"\nTASK: {result.task_id}")
        print(f"DATABASE: {result.database}")
        print(f"RESULT: {'PASS' if result.passed else 'FAIL'}")
        print("NEXT: python3 -m scopedact dashboard --database " + result.database)
        return 0 if result.passed else 1
    if args.command == "lifecycle-aws-demo":
        from .mvp import run_lifecycle_aws_demo
        task_id, result = run_lifecycle_aws_demo(
            args.role_name, database=args.database, profile=args.profile, audit_output=args.output
        )
        print(f"TASK: {task_id}")
        print(f"DECISION: {result.decision.reason_code}")
        print(f"EXECUTED: {result.decision.allowed}")
        if result.value is not None:
            print(f"RESULT: {result.value}")
        return 0 if result.decision.allowed else 1
    if args.command == "init-demo":
        from .mvp import initialize_demo_task
        source=None
        if args.authority_bundle:
            from .authority_source import SignedBundleAuthoritySource
            source=SignedBundleAuthoritySource(args.authority_bundle,os.environ.get("SCOPEDACT_AUTHORITY_KEY",""))
        task_id = initialize_demo_task(args.database, args.config, source)
        print(f"TASK: {task_id}")
        print("STATUS: active")
        print("DATABASE: " + str(args.database))
        return 0
    if args.command in {"authority-create","authority-verify"}:
        from .authority_source import SignedBundleAuthoritySource,create_signed_bundle
        from .lifecycle_config import LifecycleConfig
        secret=os.environ.get("SCOPEDACT_AUTHORITY_KEY","")
        config=LifecycleConfig.load(args.config)
        if args.command=="authority-create":
            document=create_signed_bundle(principal=config.initiator,permissions=config.upstream_authority,secret=secret,key_id=args.key_id,lifetime_minutes=args.lifetime)
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(document,indent=2,sort_keys=True)+"\n");print(f"AUTHORITY_BUNDLE: {args.output}");return 0
        record=SignedBundleAuthoritySource(args.bundle,secret).resolve(config.initiator);print(json.dumps({"valid":True,"principal":record.principal,"source":record.source,"key_id":record.key_id,"expires_at":record.expires_at.isoformat(),"permissions":len(record.permissions)},indent=2));return 0
    if args.command in {"anchor-events","verify-anchor"}:
        from .evidence import create_anchor,verify_anchor
        secret=os.environ.get("SCOPEDACT_ANCHOR_KEY","")
        if args.command=="anchor-events": result=create_anchor(args.database,args.output,secret);print(f"ANCHOR: {args.output}\nEVENTS: {result['events']}\nHEAD: {result['head']}");return 0
        result=verify_anchor(args.database,args.anchor,secret);print(json.dumps(result,indent=2,sort_keys=True));return 0 if result["valid"] else 1
    if args.command=="connectors":
        from .aws_iam import AwsIamReadOnlyTool
        from .connectors import ConnectorRegistry
        registry=ConnectorRegistry();registry.register(AwsIamReadOnlyTool())
        for item in registry.describe():print(f"{item.name:<16} {item.tool:<28} {','.join(item.actions)}")
        return 0
    if args.command=="lab":
        from .lab import serve_lab
        serve_lab(database=args.database,config_path=args.config,gateway_port=args.gateway_port,tool_port=args.tool_port,dashboard_port=args.dashboard_port);return 0
    if args.command=="lab-agent":
        from .lab import run_lab_agent
        task_id,steps=run_lab_agent(base_url=args.gateway,task_id=args.task_id,resume_request_id=args.resume_request_id)
        print(f"TASK: {task_id}\n")
        pending=None
        for label,status,result in steps:
            decision=result.get('decision',result.get('error'));executed=result.get('executed',False)
            print(f"AGENT PROPOSAL:  {label}")
            print(f"SCOPEDACT:       {decision}")
            print(f"TOOL EXECUTED:   {'YES' if executed else 'NO'}")
            print(f"API TRANSPORT:   HTTP {status} (the gateway processed the message)\n")
            if result.get("decision")=="APPROVAL_REQUIRED":pending=result["request_id"]
        if pending:
            print("\nAPPROVAL REQUIRED")
            print("1. Approve the pending request at http://127.0.0.1:8765")
            print(f"2. Resume: scopedact lab-agent --task-id '{task_id}' --resume-request-id '{pending}'")
        return 0
    if args.command=="tour":
        from .tour import run_tour
        print(run_tour(args.database,args.output));return 0
    if args.command == "workflow-demo":
        from .workflow import run_agent_workflow
        result=run_agent_workflow(args.database,args.config,args.output,live=args.live,model=args.model)
        print(f"MODE: {result.source}\nTASK: {result.task_id}")
        for label,decision,executed in result.steps: print(f"{label:<32} {decision:<28} {executed}")
        print("RESULT: PASS" if all(d in {"PERMISSION_GRANTED","APPROVAL_REQUIRED"} for _,d,_ in result.steps) else "RESULT: REVIEW")
        return 0
    if args.command == "verify-events":
        from .lifecycle import LifecycleStore
        if args.database is None:
            from .application import ApplicationProject
            args.database=ApplicationProject.load(args.project).database
        store=LifecycleStore(args.database)
        try: result=store.verify_event_chain()
        finally: store.close()
        print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["valid"] else 1
    if args.command in {"aws-preflight","aws-dry-run"}:
        from .aws_iam import AwsIamReadOnlyTool
        tool=AwsIamReadOnlyTool(profile=args.profile)
        if args.command=="aws-dry-run":
            print(json.dumps({"executes":False,"command":tool.command_for("get_role",f"iam-role:{args.role_name}")},indent=2)); return 0
        from .lifecycle import LifecycleStore
        store=LifecycleStore(args.database)
        try:
            try: identity=tool.preflight(); store.record_connector_status("aws-iam","healthy",identity)
            except Exception as error: store.record_connector_status("aws-iam","error",{"error":str(error)}); raise
        finally: store.close()
        print(json.dumps(identity,indent=2,sort_keys=True)); return 0
    if args.command == "request":
        from .mvp import invoke_demo_request
        request, result = invoke_demo_request(
            args.database, task_id=args.task_id, action=args.action,
            resource=args.resource, request_id=args.request_id, audit_output=args.output,
        )
        print(f"REQUEST: {request.request_id}")
        print(f"DECISION: {result.decision.reason_code}")
        print(f"EXECUTED: {result.decision.allowed}")
        if result.value is not None:
            print(f"RESULT: {result.value}")
        return 0 if result.decision.allowed or result.decision.reason_code == "APPROVAL_REQUIRED" else 1
    if args.command == "dashboard":
        from .dashboard import serve_dashboard
        serve_dashboard(args.database, args.host, args.port, args.config)
        return 0
    if args.command == "status":
        from .lifecycle import LifecycleStore
        if args.database is None:
            from .application import ApplicationProject
            args.database=ApplicationProject.load(args.project).database
        store = LifecycleStore(args.database)
        try:
            print(json.dumps(store.snapshot(), indent=2, sort_keys=True))
        finally:
            store.close()
        return 0
    if args.command in {"task", "approval"}:
        from .grants import SQLiteGrantRegistry
        from .lifecycle import LifecycleOperator, LifecycleStore
        if args.database is None:
            from .application import ApplicationProject
            args.database=ApplicationProject.load(args.project).database
        store = LifecycleStore(args.database)
        registry = SQLiteGrantRegistry(args.database)
        operator = LifecycleOperator(store, registry)
        try:
            if args.command == "task":
                method = operator.close_task if args.action == "close" else getattr(operator, args.action)
                method(args.task_id)
                print(f"TASK {args.task_id}: {args.action.upper()} completed")
            else:
                getattr(operator, args.action)(args.request_id, args.reviewer)
                print(f"REQUEST {args.request_id}: {args.action.upper()} completed")
        finally:
            store.close(); registry.close()
        return 0
    return render(run_all(args.output))
