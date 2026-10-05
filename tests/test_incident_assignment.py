"""Incident policy resolution: trusted context, authority ceilings, no prompt grants."""
import unittest
from copy import deepcopy
from scopedact.incident_lab.assignment import resolve, INCIDENT, CATALOG, ROLE_CEILING
from scopedact.incident_lab.services import CONFIG, SECRET, LOGS
from scopedact.models import Permission
from scopedact.pilot.common import OPERATOR

class IncidentPolicyTests(unittest.TestCase):
    def test_scope_intersects_context_role_and_upstream(self):
        narrowed={Permission('read',CONFIG),Permission('read',LOGS),Permission('read',SECRET)}
        result=resolve('INC-2048',OPERATOR,narrowed)
        self.assertEqual({(p['action'],p['resource']) for p in result['permissions']},{('read',CONFIG),('read',LOGS)})
        self.assertTrue(result['excluded'])
        altered=deepcopy(CATALOG);altered[CONFIG]['environment']='production'
        result=resolve('INC-2048',OPERATOR,narrowed,catalog=altered)
        self.assertEqual([p['resource'] for p in result['permissions']],[LOGS])
    def test_unknown_incident_role_and_empty_authority_fail_closed(self):
        for incident,actor,authority in [('INC-other',OPERATOR,ROLE_CEILING),('INC-2048','agent:other',ROLE_CEILING),('INC-2048',OPERATOR,set())]:
            with self.assertRaises(ValueError):resolve(incident,actor,authority)
    def test_policy_snapshot_explains_exact_permissions(self):
        result=resolve(INCIDENT['id'],OPERATOR,ROLE_CEILING)
        self.assertEqual({Permission(p['action'],p['resource']) for p in result['permissions']},ROLE_CEILING)
        self.assertTrue(all(p['reason'] and p['rule'] for p in result['permissions']))
        self.assertEqual([p['resource'] for p in result['permissions'] if p['approval_required']],[CONFIG])

    def test_intern_cannot_obtain_configuration_or_write_permissions(self):
        result=resolve(INCIDENT['id'],OPERATOR,ROLE_CEILING,evaluation_role='support-intern')
        self.assertTrue(result['permissions'])
        self.assertTrue(all(p['action']=='read' and p['resource']!=CONFIG for p in result['permissions']))
        with self.assertRaises(ValueError):resolve(INCIDENT['id'],OPERATOR,ROLE_CEILING,evaluation_role='admin')
