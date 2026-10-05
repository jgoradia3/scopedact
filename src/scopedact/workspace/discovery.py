"""Permission-filtered name discovery and operator selection; never reads document bodies."""
import json
from ..models import ActionRequest
from ..pilot.common import request_id
from ..pilot.delegation import PilotEvaluator
from ..pilot.gateway import APIError, fields


def searches(store, task_id):
    result = []
    for row in store.connection.execute("SELECT request_id,details FROM lifecycle_events WHERE task_id=? AND event_type='document_search' ORDER BY event_id", (task_id,)):
        item = json.loads(row['details']); item['request_id'] = row['request_id']; item['task_id'] = task_id
        choice = store.connection.execute("SELECT details FROM lifecycle_events WHERE request_id=? AND event_type='document_selected'", (row['request_id'],)).fetchone()
        item['selected'] = json.loads(choice[0])['resource'] if choice else None
        result.append(item)
    return result


def readable(store, registry, actor, task_id, resource):
    grant = registry.get(task_id); task = store.get_task(task_id)
    if not grant or not task or task.status.value != 'active': return False
    parent = registry.get(grant.parent_task_id) if grant.parent_task_id else None
    return PilotEvaluator(registry, store).evaluate(ActionRequest(task_id=task_id, request_id='request:discovery-check',
        actor=actor, parent_actor=parent.principal if parent else grant.initiator,
        tool='tool:managed-workspace', action='read', resource=resource)).allowed


def search(body, actor, store, registry, documents):
    fields(body, {'task_id','request_id','query'})
    request_id(body['request_id'])
    query = body['query']
    if not isinstance(query,str) or not 1 <= len(query.strip()) <= 80: raise APIError(400,'query must contain 1–80 characters')
    grant = registry.get(body['task_id'])
    if not grant or grant.principal != actor: raise APIError(403,'task not available to this agent')
    matches = [d['resource'] for d in documents.catalog() if query.casefold() in d['resource'][4:].casefold()
               and readable(store,registry,actor,body['task_id'],d['resource'])]
    old = store.connection.execute("SELECT task_id,details FROM lifecycle_events WHERE request_id=? AND event_type='document_search'", (body['request_id'],)).fetchone()
    if old:
        prior=json.loads(old['details'])
        if old['task_id']!=body['task_id'] or prior['actor']!=actor or prior['query']!=query: raise APIError(409,'search request mismatch')
        matches=[r for r in prior['candidates'] if r in matches]
    else:
        store.event('document_search',body['task_id'],body['request_id'],{'actor':actor,'query':query,'candidates':matches})
    choice=store.connection.execute("SELECT details FROM lifecycle_events WHERE request_id=? AND event_type='document_selected'", (body['request_id'],)).fetchone()
    selected=json.loads(choice[0])['resource'] if choice else None
    if (old and not matches) or (selected and selected not in matches): return {'status':'unavailable','candidates':[],'selected':None}
    # Never silently pick another result after a previously ambiguous search loses access.
    original=json.loads(old['details'])['candidates'] if old else matches
    state='selected' if selected else 'needs_choice' if len(original)>1 else 'one_match' if matches else 'no_matches'
    return {'status':state,'candidates':matches,'selected':selected or (matches[0] if state=='one_match' else None)}


def choose(body,store,registry):
    fields(body,{'task_id','request_id','resource'})
    item=next((s for s in searches(store,body['task_id']) if s['request_id']==body['request_id']),None)
    if not item or body['resource'] not in item['candidates']: raise APIError(400,'select a result from this search')
    if item['selected']: raise APIError(409,'selection already recorded')
    if not readable(store,registry,item['actor'],body['task_id'],body['resource']): raise APIError(409,'document is no longer permitted')
    store.event('document_selected',body['task_id'],body['request_id'],{'resource':body['resource'],'actor':item['actor']})
    return {'selected':body['resource']}
