from __future__ import annotations
from contextlib import closing

import hashlib, hmac, json, os, secrets, sqlite3, threading, time
import urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .audit import AuditLogger
from .evaluator import AuthorizationEvaluator
from .grants import SQLiteGrantRegistry
from .lifecycle import LifecycleGateway, LifecycleStore, run_id
from .lifecycle_config import LifecycleConfig
from .models import ActionRequest
from .mvp import initialize_demo_task
from .policy import ActionPolicy, PolicySet
from .service import InvoiceService

DEFAULT_LAB_KEY="local-evaluation-only-change-me"

def _canonical(method:str,path:str,timestamp:str,nonce:str,body:bytes)->bytes:
    return b"\n".join([method.upper().encode(),path.encode(),timestamp.encode(),nonce.encode(),hashlib.sha256(body).hexdigest().encode()])

def sign_headers(method:str,path:str,body:bytes,client_id:str,key:str,*,timestamp:str|None=None,nonce:str|None=None)->dict[str,str]:
    stamp=timestamp or str(int(time.time())); value=nonce or secrets.token_hex(16)
    signature=hmac.new(key.encode(),_canonical(method,path,stamp,value,body),hashlib.sha256).hexdigest()
    return {"Content-Type":"application/json","X-ScopedAct-Client":client_id,"X-ScopedAct-Timestamp":stamp,"X-ScopedAct-Nonce":value,"X-ScopedAct-Signature":signature}

class ApiAuthenticator:
    def __init__(self,database:str|Path,clients:dict[str,str],window_seconds:int=60):
        self.database=str(database);self.clients=clients;self.window_seconds=window_seconds
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("CREATE TABLE IF NOT EXISTS api_nonces(client_id TEXT NOT NULL, nonce TEXT NOT NULL, timestamp INTEGER NOT NULL, PRIMARY KEY(client_id,nonce))")
    def verify(self,method,path,body,headers)->str:
        client=headers.get("X-ScopedAct-Client","");stamp=headers.get("X-ScopedAct-Timestamp","");nonce=headers.get("X-ScopedAct-Nonce","");signature=headers.get("X-ScopedAct-Signature","")
        if client not in self.clients:raise PermissionError("unknown API client")
        try:seconds=int(stamp)
        except ValueError as error:raise PermissionError("invalid request timestamp") from error
        if abs(int(time.time())-seconds)>self.window_seconds:raise PermissionError("request timestamp outside allowed window")
        expected=hmac.new(self.clients[client].encode(),_canonical(method,path,stamp,nonce,body),hashlib.sha256).hexdigest()
        if not nonce or not hmac.compare_digest(signature,expected):raise PermissionError("invalid request signature")
        connection=sqlite3.connect(self.database)
        try:
            with connection:connection.execute("INSERT INTO api_nonces VALUES (?,?,?)",(client,nonce,seconds))
        except sqlite3.IntegrityError as error:raise PermissionError("API nonce replay detected") from error
        finally:connection.close()
        return client

class HttpProtectedTool:
    tool_name="tool:invoice-service"
    def __init__(self,url:str,internal_key:str):self.url=url;self.internal_key=internal_key
    def execute(self,action:str,resource:str)->Any:
        body=json.dumps({"action":action,"resource":resource},sort_keys=True).encode();request=urllib.request.Request(self.url+"/execute",data=body,headers={"Content-Type":"application/json","X-ScopedAct-Internal-Key":self.internal_key},method="POST")
        with urllib.request.urlopen(request,timeout=5) as response:return json.loads(response.read())["value"]

def _json_response(handler,status:int,value:dict):
    body=json.dumps(value,sort_keys=True,default=str).encode();handler.send_response(status);handler.send_header("Content-Type","application/json");handler.send_header("Content-Length",str(len(body)));handler.send_header("Cache-Control","no-store");handler.send_header("X-Content-Type-Options","nosniff");handler.end_headers();handler.wfile.write(body)

def build_tool_server(host:str,port:int,internal_key:str):
    service=InvoiceService()
    class ToolHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=="/health":_json_response(self,200,{"status":"healthy","service":"synthetic-invoice"})
            else:self.send_error(404)
        def do_POST(self):
            if self.path!="/execute":self.send_error(404);return
            if not hmac.compare_digest(self.headers.get("X-ScopedAct-Internal-Key",""),internal_key):_json_response(self,401,{"error":"gateway authentication required"});return
            try:
                size=int(self.headers.get("Content-Length","0"));payload=json.loads(self.rfile.read(size));value=service.execute(payload["action"],payload["resource"]);_json_response(self,200,{"value":value})
            except (ValueError,KeyError,json.JSONDecodeError) as error:_json_response(self,400,{"error":str(error)})
        def log_message(self,format,*args):return
    return ThreadingHTTPServer((host,port),ToolHandler)

def build_gateway_server(host:str,port:int,*,database:str|Path,config_path:str|Path,tool_url:str,internal_key:str,client_keys:dict[str,str]):
    database=str(database);config=LifecycleConfig.load(config_path);auth=ApiAuthenticator(database,client_keys)
    class GatewayHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=="/health":_json_response(self,200,{"status":"healthy","service":"scopedact-gateway"})
            else:self.send_error(404)
        def do_POST(self):
            path=urlparse(self.path).path
            if path not in {"/v1/tasks","/v1/actions"}:self.send_error(404);return
            try:
                if self.headers.get_content_type()!="application/json":raise ValueError("JSON body required")
                size=int(self.headers.get("Content-Length","0"))
                if size<2 or size>8192:raise ValueError("invalid body size")
                body=self.rfile.read(size);client=auth.verify("POST",path,body,self.headers);payload=json.loads(body)
                if client!=config.actor:raise PermissionError("client is not the configured task actor")
                if path=="/v1/tasks":
                    if payload!={"template":"default"}:raise ValueError("only the reviewed default task template is available")
                    task_id=initialize_demo_task(database,config_path);_json_response(self,201,{"task_id":task_id,"status":"active"});return
                if set(payload)!={"task_id","request_id","action","resource"}:raise ValueError("action request has invalid fields")
                store=LifecycleStore(database);registry=SQLiteGrantRegistry(database)
                try:
                    task=store.get_task(payload["task_id"])
                    if task is None:raise ValueError("unknown task")
                    request=ActionRequest(request_id=payload["request_id"],task_id=payload["task_id"],actor=client,parent_actor=task.initiator,tool=config.tool,action=payload["action"],resource=payload["resource"])
                    policy=PolicySet({x:ActionPolicy(True) for x in config.approval_required_actions});gateway=LifecycleGateway(AuthorizationEvaluator(registry),HttpProtectedTool(tool_url,internal_key),store,AuditLogger(str(Path(database).with_suffix(".jsonl")),truncate=False),policy);result=gateway.invoke(request)
                    _json_response(self,200,{"decision":result.decision.reason_code,"executed":result.decision.allowed,"value":result.value})
                finally:store.close(); registry.close()
            except PermissionError as error:_json_response(self,401,{"error":str(error)})
            except (ValueError,KeyError,json.JSONDecodeError) as error:_json_response(self,400,{"error":str(error)})
        def log_message(self,format,*args):return
    return ThreadingHTTPServer((host,port),GatewayHandler)

def request_gateway(base_url:str,path:str,payload:dict,client_id:str,key:str,*,timestamp=None,nonce=None):
    body=json.dumps(payload,sort_keys=True,separators=(",", ":")).encode();headers=sign_headers("POST",path,body,client_id,key,timestamp=timestamp,nonce=nonce);request=urllib.request.Request(base_url+path,data=body,headers=headers,method="POST")
    try:
        with urllib.request.urlopen(request,timeout=5) as response:return response.status,json.loads(response.read())
    except urllib.error.HTTPError as error:return error.code,json.loads(error.read())

def serve_lab(*,database="audit/lab.db",config_path="config/lifecycle.json",host="127.0.0.1",gateway_port=8770,tool_port=8780,dashboard_port=8765,client_key=None):
    if host not in {"127.0.0.1","localhost","::1"}:raise ValueError("lab services must bind to loopback")
    key=client_key or os.environ.get("SCOPEDACT_LAB_CLIENT_KEY",DEFAULT_LAB_KEY);internal=secrets.token_urlsafe(32);config=LifecycleConfig.load(config_path)
    tool=build_tool_server(host,tool_port,internal);gateway=build_gateway_server(host,gateway_port,database=database,config_path=config_path,tool_url=f"http://{host}:{tool_port}",internal_key=internal,client_keys={config.actor:key})
    for server in (tool,gateway):threading.Thread(target=server.serve_forever,daemon=True).start()
    print(f"ScopedAct gateway: http://{host}:{gateway_port}");print(f"Protected tool:    http://{host}:{tool_port} (gateway credential required)");print(f"Operator console:  http://{host}:{dashboard_port}");print("NEXT (new terminal): scopedact lab-agent")
    from .dashboard import serve_dashboard
    try:serve_dashboard(database,host,dashboard_port,config_path)
    finally:
        gateway.shutdown();tool.shutdown();gateway.server_close();tool.server_close()

def run_lab_agent(*,base_url="http://127.0.0.1:8770",client_id="agent:procurement",key=None,task_id=None,resume_request_id=None):
    key=key or os.environ.get("SCOPEDACT_LAB_CLIENT_KEY",DEFAULT_LAB_KEY)
    if resume_request_id:
        if not task_id:raise ValueError("--task-id is required with --resume-request-id")
        status,result=request_gateway(base_url,"/v1/actions",{"task_id":task_id,"request_id":resume_request_id,"action":"approve_payment","resource":"invoice:123"},client_id,key);return task_id,[("payment_after_approval",status,result)]
    if task_id is None:
        status,result=request_gateway(base_url,"/v1/tasks",{"template":"default"},client_id,key)
        if status!=201:raise RuntimeError(result)
        task_id=result["task_id"]
    steps=[]
    for label,action,resource in [("read_invoice","read","invoice:123"),("read_purchase_order","read","purchase-order:456"),("compare_records","compare","comparison:123-456"),("request_payment","approve_payment","invoice:123")]:
        request_id=run_id("req-lab");status,result=request_gateway(base_url,"/v1/actions",{"task_id":task_id,"request_id":request_id,"action":action,"resource":resource},client_id,key);steps.append((label,status,{**result,"request_id":request_id}))
    return task_id,steps
