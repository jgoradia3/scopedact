"""Deterministic separately authenticated parent/child workflow; no live model."""
from uuid import uuid4
from .client import Client
from .common import AGENT, CHILD, OPERATOR


def evaluate_delegation(base, parent_key, child_key, operator_key):
    parent=Client(base,AGENT,parent_key)
    child=Client(base,CHILD,child_key)
    operator=Client(base,OPERATOR,operator_key)
    checks=[]
    def check(name,condition):
        checks.append({'name':name,'passed':bool(condition)})
        if not condition:raise AssertionError(name)
    status,root=operator.post('/v1/tasks',{'resource':'ticket:T-100'})
    check('operator assigns parent task',status==200)
    task=root['task_id']
    delegation={'parent_task_id':task,'permissions':[{'action':'read','resource':'ticket:T-100'}],'lifetime_seconds':300}
    status,assigned=parent.post('/v1/delegations',delegation)
    check('parent delegates read-only child grant',status==200 and assigned['actor']==CHILD)
    child_task=assigned['task_id']
    def action(client,task_id,verb,resource='ticket:T-100',value=None):
        body={'task_id':task_id,'request_id':'request:'+uuid4().hex,'action':verb,'resource':resource}
        if value is not None:body['input']=value
        return client.post('/v1/actions',body)[1]
    read=action(child,child_task,'read')
    check('child reads assigned ticket',read.get('executed') is True)
    denied=action(child,child_task,'read','ticket:T-200')
    check('child cannot read another ticket',denied.get('decision')=='PERMISSION_NOT_GRANTED')
    denied=action(child,child_task,'update',value={'text':'Unauthorized child update','expected_version':1})
    check('child cannot update',denied.get('decision')=='PERMISSION_NOT_GRANTED')
    denied=action(child,task,'read')
    check('child cannot use parent grant',denied.get('decision')=='ACTOR_MISMATCH')
    status,_=parent.post('/v1/delegations',{**delegation,'permissions':[{'action':'delete','resource':'ticket:T-100'}]})
    check('delegation cannot add privilege',status==409)
    status,_=parent.post('/v1/delegations',{**delegation,'permissions':[{'action':'read','resource':'ticket:T-200'}]})
    check('delegation cannot add resource',status==409)
    status,_=parent.post('/v1/delegations',{**delegation,'lifetime_seconds':900})
    check('child cannot outlive parent',status==409)
    status,_=child.post('/v1/delegations',delegation)
    check('child cannot create further delegation',status==403)
    status,_=child.post('/v1/decision',{})
    check('child cannot approve',status==403)
    operator.post('/v1/task-control',{'task_id':task,'operation':'pause'})
    check('parent pause blocks child',action(child,child_task,'read').get('decision')=='ANCESTOR_TASK_NOT_ACTIVE')
    operator.post('/v1/task-control',{'task_id':task,'operation':'resume'})
    check('parent resume restores valid child scope',action(child,child_task,'read').get('executed') is True)
    check('parent performs next legitimate step',action(parent,task,'read').get('executed') is True)
    operator.post('/v1/task-control',{'task_id':task,'operation':'revoke'})
    check('revocation blocks next child step',action(child,child_task,'read').get('decision')=='ANCESTOR_INACTIVE')
    check('revocation blocks next parent step',action(parent,task,'read').get('decision')=='TASK_NOT_ACTIVE')
    status,_=parent.post('/v1/delegations',delegation)
    check('revoked parent cannot delegate',status==409)
    _,lineage=operator.post('/v1/lineage',{'task_id':task})
    reads=[event for event in lineage['actions'] if event['actor']==CHILD and event['executed']]
    check('lineage reconstructs human parent child tool',bool(reads) and reads[0]['initiator']==OPERATOR
          and [n['actor'] for n in reads[0]['authority_chain']]==[AGENT,CHILD]
          and reads[0]['parent_actor']==AGENT and reads[0]['delegation_id']==assigned['delegation_id'])
    _,evidence=operator.post('/v1/evidence',{})
    check('delegated event chain verifies',evidence['integrity']['valid'])
    return {'schema_version':1,'checks':checks,'passed':len(checks),'total':len(checks),
            'task_id':task,'child_task_id':child_task,'lineage':lineage,
            'limitations':['Scripted proposals, no live model.','Role keys identify possession, not corporate identities.',
                           'One-parent, one-child-hop pilot; no novel graph mechanism.',
                           'Revocation denies subsequent actions; it does not cancel in-flight work.']}
