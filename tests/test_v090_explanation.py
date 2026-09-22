import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scopedact.dashboard import render_dashboard
from scopedact.tour import run_tour

class ExplanationReleaseTests(unittest.TestCase):
    def setUp(self):self.temp=TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_tour_explains_proposal_decision_and_execution(self):
        text=run_tour(self.root/"tour.db",self.root/"tour.jsonl")
        self.assertIn("PROPOSAL:",text);self.assertIn("DECISION:",text);self.assertIn("EXECUTED:",text);self.assertIn("TOUR RESULT: PASS",text)
    def test_tour_states_real_world_boundary(self):
        text=run_tour(self.root/"boundary.db",self.root/"boundary.jsonl")
        self.assertIn("WHAT THIS DOES NOT PROVE",text);self.assertIn("not a production identity provider",text)
    def test_dashboard_explains_processed_versus_executed(self):
        page=render_dashboard({"tasks":[],"attempts":[],"approvals":[],"events":[],"grants":[]},"token","nonce")
        self.assertIn("How to read this console",page);self.assertIn("Executed: Yes",page);self.assertIn("tool was not called",page)

if __name__=="__main__":unittest.main()
