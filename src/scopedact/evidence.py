from __future__ import annotations

import hashlib, hmac, json
from datetime import datetime, timezone
from pathlib import Path
from .lifecycle import LifecycleStore

def _canonical(body): return json.dumps(body,sort_keys=True,separators=(",", ":")).encode()

def create_anchor(database: str|Path, output: str|Path, secret: str) -> dict:
    if not secret: raise ValueError("anchor signing secret must not be empty")
    store=LifecycleStore(database)
    try: state=store.verify_event_chain()
    finally: store.close()
    if not state["valid"]: raise ValueError("cannot anchor an invalid event chain")
    body={"schema":"scopedact-anchor/v1","events":state["events"],"head":state["head"],"anchored_at":datetime.now(timezone.utc).isoformat()}
    document={**body,"signature":hmac.new(secret.encode(),_canonical(body),hashlib.sha256).hexdigest()}
    path=Path(output); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(document,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return document

def verify_anchor(database: str|Path, anchor: str|Path, secret: str) -> dict:
    document=json.loads(Path(anchor).read_text(encoding="utf-8")); signature=document.pop("signature","")
    signed=hmac.new(secret.encode(),_canonical(document),hashlib.sha256).hexdigest()
    if not secret or not hmac.compare_digest(signature,signed): return {"valid":False,"reason":"ANCHOR_SIGNATURE_INVALID"}
    if document.get("schema")!="scopedact-anchor/v1": return {"valid":False,"reason":"ANCHOR_SCHEMA_INVALID"}
    store=LifecycleStore(database)
    try: state=store.verify_event_chain()
    finally: store.close()
    if not state["valid"]: return {"valid":False,"reason":"EVENT_CHAIN_INVALID"}
    if state["events"]!=document["events"] or state["head"]!=document["head"]: return {"valid":False,"reason":"ANCHOR_MISMATCH","events":state["events"]}
    return {"valid":True,"reason":"ANCHOR_MATCH","events":state["events"],"head":state["head"]}
