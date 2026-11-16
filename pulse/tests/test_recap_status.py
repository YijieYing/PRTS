"""Activity-boundary fixtures; source readers replaced, stdin never inherited."""
from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'lib'))
import pulse


class Status(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name); (self.state/'ear').mkdir()
        self.c = dict(timezone='Asia/Tokyo',day_start_hour=5,sources={},mapping=[],
                      user=dict(quiet_start='05:00',quiet_end='12:00'))
        self.computer = []; self.claude = []; self.chrome = []; self.codex = []
        for target, effect in [
            ('computer_history.load', lambda *a: (self.computer, [])),
            ('sources.claude', lambda *a: self.claude.copy()),
            ('sources.chrome', lambda *a: self.chrome.copy()),
            ('sources.codex', lambda *a, users: users.extend(self.codex))]:
            mock = patch('pulse.'+target, side_effect=effect); mock.start(); self.addCleanup(mock.stop)

    def status(self, at='2026-11-17T03:00:00+09:00', sentence_age=5400, ok=True):
        now = datetime.fromisoformat(at)
        (self.state/'ear/activity.json').write_text(json.dumps(dict(
            ok=ok,checked=now.timestamp(),latest_sentence=now.timestamp()-sentence_age)))
        return pulse.recap_status(self.c,self.state,now)

    def test_idle_90_and_day_boundary(self):
        s=self.status(); self.assertTrue(s['idle']); self.assertTrue(s['eligible'])
        self.assertEqual(s['day'],'2026-11-16')
        self.assertFalse(self.status('2026-11-16T22:59:00+09:00')['eligible'])
        self.assertTrue(self.status('2026-11-16T23:00:00+09:00')['eligible'])
        s=self.status('2026-11-17T05:00:00+09:00')
        self.assertEqual(s['previous'],'2026-11-16'); self.assertFalse(s['eligible'])

    def test_each_activity_blocks(self):
        self.computer=[dict(active=True)]; self.assertFalse(self.status()['idle']); self.computer=[]
        for source in ('claude','codex','chrome'):
            setattr(self,source,[dict(role='user')])
            self.assertFalse(self.status()['idle'],source)
            setattr(self,source,[])
        self.assertFalse(self.status(sentence_age=5399)['idle'])
        self.assertFalse(self.status(ok=False)['idle'])

    def test_agent_output_and_passive_windows_do_not_block(self):
        self.claude=[dict(role='assistant')]; self.computer=[dict(active=False)]
        self.assertTrue(self.status()['idle'])
