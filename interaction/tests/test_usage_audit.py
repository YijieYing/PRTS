import json, os, tempfile, unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lib.usage_audit import audit

class UsageAuditTests(unittest.TestCase):
    def test_weekly_counts_and_candidates_are_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); pulse=root/'pulse'; reporter=root/'reporter'; interaction=root/'interaction'
            (pulse/'ear').mkdir(parents=True); (reporter).mkdir(); interaction.mkdir()
            now=datetime(2026,11,20,tzinfo=timezone(timedelta(hours=9)))
            t=(now-timedelta(days=2)).timestamp()
            (pulse/'ear/inbox.jsonl').write_text(json.dumps({'value':'high','capture':'c','start':t})+'\n')
            (pulse/'ear/handed.json').write_text(json.dumps(['c']))
            (pulse/'focus').mkdir(); (pulse/'focus/log.jsonl').write_text(json.dumps({'start':t})+'\n')
            env={'PULSE_STATE':str(pulse),'PRTS_REPORTER_STATE':str(reporter),'PRTS_INTERACTION_STATE':str(interaction)}
            with patch.dict(os.environ,env):
                result=audit(3,now)
            ear=next(x for x in result['features'] if x['name'].startswith('Ear'))
            self.assertEqual(ear['weekly'][-1],1); self.assertEqual(ear['consecutive_unused_weeks'],0)
            self.assertFalse((pulse/'focus/log.jsonl').read_text()== '')

if __name__=='__main__': unittest.main()
