"""Native wiring tests use an explicitly fake model, never claim live AI validation."""
from pathlib import Path
import tempfile
import time
import unittest
from scopedact.incident_lab.native import NativeLab
from scopedact.incident_lab.services import LOGS, CONFIG
from scopedact.pilot.client import Client
from scopedact.pilot.common import OPERATOR

class NativeReviewTests(unittest.TestCase):
    def test_real_services_deny_and_pause_with_fake_model(self):
        class Model:
            name = "test-double"
            def chat(self, messages, tools):
                return {'role':'assistant','content':'','tool_calls':[
                    {'function':{'name':'read_document','arguments':{'resource':resource}}}
                    for resource in (LOGS, CONFIG, LOGS)]}
        with tempfile.TemporaryDirectory() as tmp:
            lab = NativeLab(tmp, 0, model_factory=Model)
            try:
                self.assertTrue(all(s.server_address[0]=='127.0.0.1' for s in lab.servers))
                operator = Client(lab.url, OPERATOR, lab.keys['operator'])
                code, started = operator.post('/v1/lab/start', {'evaluation_role':'support-intern'})
                self.assertEqual(code, 200, started)
                for _ in range(100):
                    code, status = operator.post('/v1/lab/status', {})
                    if status.get('status') != 'running': break
                    time.sleep(.05)
                self.assertEqual(status['status'], 'paused_on_denial', status)
                self.assertEqual(len(status['actions']), 2)
                self.assertTrue(status['actions'][0]['executed'])
                self.assertEqual(status['actions'][1]['decision'], 'PERMISSION_NOT_GRANTED')
                self.assertFalse(status['actions'][1]['executed'])
                self.assertEqual(operator.post('/v1/lab/end', {})[0], 200)
                self.assertIn('/#access=', lab.link())
                with self.assertRaisesRegex(ValueError, 'already in use'):
                    NativeLab(tmp, 0)
            finally:
                lab.close()
            second = NativeLab(tmp, 0, model_factory=Model)
            try:
                self.assertEqual(second.keys, lab.keys)
                self.assertTrue((Path(tmp)/'gateway.db').exists())
            finally:
                second.close()

if __name__ == '__main__': unittest.main()
