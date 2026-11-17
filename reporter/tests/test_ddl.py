import datetime as dt
import json
import os
from unittest.mock import patch
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from reporter.lib.ddl import remind, main

class DDL(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.state=Path(self.tmp.name)
        self.calls=[]
        self.item=dict(id='X1',title='item',ddl='2026-11-19',status='💤',done=False,auto=None)
        self.project=dict(name='Test',roadmap=dict(items=[self.item]),meetings=[])
        self.groups=[dict(projects=[self.project])]
    def tick(self,time,quiet=False):
        remind(self.groups,dt.datetime.fromisoformat(time),quiet,self.state,lambda *args:self.calls.append(args))
    def test_phases_once(self):
        for date in ('12','17','19','20','21'):
            self.tick(f'2026-11-{date}T13:00:00+09:00');self.tick(f'2026-11-{date}T14:00:00+09:00')
        self.assertEqual(len(self.calls),4)
    def test_many_due_batched(self):
        self.project['roadmap']['items']=[dict(self.item,id=f'X{i}',ddl='2026-10-1%d'%i) for i in range(1,6)]+[self.item]
        self.tick('2026-11-17T13:00:00+09:00')
        self.assertEqual(len(self.calls),1);self.assertEqual(self.calls[0][0],'DDL 提醒 6 条')
        self.assertEqual(len(self.calls[0][1].splitlines()),6)
        self.tick('2026-11-17T14:00:00+09:00');self.assertEqual(len(self.calls),1)
    def test_quiet_delayed_and_completed(self):
        self.tick('2026-11-17T23:00:00+09:00',True);self.assertEqual(self.calls,[])
        self.tick('2026-11-18T01:00:00+09:00');self.assertEqual(len(self.calls),1)
        self.tick('2026-11-19T13:00:00+09:00',True);self.item['done']=True
        self.tick('2026-11-19T14:00:00+09:00');self.tick('2026-11-20T14:00:00+09:00')
        self.assertEqual(len(self.calls),1)
    def test_public_command_and_phone(self):
        self.item['ddl']=dt.date.today().isoformat()
        commands=[]
        def run(args):
            commands.append([str(a) for a in args])
            if str(args[0]).endswith('/status'): return json.dumps(dict(groups=self.groups))
            self.assertEqual(args[1],'phone')
            return ''
        with patch.dict(os.environ,PRTS_REPORTER_STATE=str(self.state)),patch('reporter.lib.ddl.run',side_effect=run):
            main(quiet=True);self.assertEqual(len(commands),1)
            main();main()
        self.assertEqual(sum(c[1]=='phone' for c in commands),1)

    def test_meeting(self):
        self.item.update(ddl=None,status='✅',done=True,auto=dict(state='accepted',at='2026-11-18T13:00:00+09:00'))
        self.project['meetings']=[dict(weekday=4,start='15:00',end='17:00')]
        self.tick('2026-11-19T11:59:00+09:00');self.assertEqual(self.calls,[])
        self.tick('2026-11-19T12:00:00+09:00',True);self.assertEqual(self.calls,[])
        self.tick('2026-11-19T13:00:00+09:00');self.tick('2026-11-19T14:00:00+09:00')
        self.assertEqual(len(self.calls),1);self.assertIn('X1 item',self.calls[0][1]);self.assertLessEqual(len(self.calls[0][1].splitlines()),8)

if __name__=='__main__': unittest.main(verbosity=2)
