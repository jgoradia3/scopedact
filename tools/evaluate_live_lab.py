"""Deterministic Docker evaluation, explicitly not an autonomous model run.

Run only after initializing services and injecting the fault. This test operator
approves its own test proposal. It does not constitute independent human review.
"""
import json
from pathlib import Path
from uuid import uuid4
from scopedact.pilot.client import Client
from scopedact.pilot.common import AGENT, CHILD, OPERATOR, canonical, secret_file
from scopedact.incident_lab.services import CONFIG, LOGS, CHECK, HISTORY, SECRET, READABLE

root=Path('.scopedact-lab')
def client(role,actor):return Client('http://127.0.0.1:8891',actor,secret_file(root/'secrets'/f'{role}.key'))
operator,agent,child=client('operator',OPERATOR),client('agent',AGENT),client('child',CHILD)
def post(c,path,body):
    status,result=c.post(path,body)
    assert status==200,(status,result)
    return result
permissions=[{'action':'read','resource':r} for r in READABLE]+[{'action':'update','resource':CONFIG}]
task=post(operator,'/v1/tasks',{'summary':'Scripted live-service control evaluation','permissions':permissions})['task_id']
def request(resource,**kw):return {'task_id':task,'request_id':'request:'+uuid4().hex,'action':'read','resource':resource,**kw}
def read(resource):
    r=post(agent,'/v1/actions',request(resource));assert r['executed'];return r['value']
assert not json.loads(read(CHECK)['text'])['passed']
current=read(CONFIG)
history=json.loads(read(HISTORY)['text'])
baseline=next(r for r in history if r['reason']=='initial deployment')
p=request(CONFIG,action='update',input={'expected_version':current['version'],'text':canonical({'expected_issuer':baseline['expected_issuer']})})
assert post(agent,'/v1/actions',p)['decision']=='APPROVAL_REQUIRED'
assert post(agent,'/v1/actions',request(SECRET))['decision']=='PERMISSION_NOT_GRANTED'
review=post(operator,'/v1/review',{'request_id':p['request_id']})
post(operator,'/v1/decision',{'request_id':p['request_id'],'digest':review['digest'],'approve':True})
assert post(agent,'/v1/actions',p)['executed']
assert json.loads(read(CHECK)['text'])['passed']
assert not post(agent,'/v1/actions',p)['executed']
helper=post(agent,'/v1/delegations',{'parent_task_id':task,'permissions':[{'action':'read','resource':LOGS}],'lifetime_seconds':120})['task_id']
assert post(child,'/v1/actions',request(LOGS,task_id=helper))['executed']
post(operator,'/v1/task-control',{'task_id':task,'operation':'revoke'})
assert post(child,'/v1/actions',request(LOGS,task_id=helper))['decision']=='ANCESTOR_INACTIVE'
evidence=post(operator,'/v1/map',{'task_id':task})
assert evidence['integrity']['valid']
assert evidence['verifications'][-1]['details']['passed']
print(json.dumps({'evaluation':'scripted, automated approvals','task_id':task,'counts':evidence['counts'],
                  'verification':evidence['verifications'][-1]['details'],'event_chain_valid':True},indent=2))
