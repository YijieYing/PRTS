import io
import json
import os
import sys
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import ear
import pulse
import test_ear


class NewEarTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_ear.EarTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.c, self.state, self.base = self.fixture.c, self.fixture.state, self.fixture.base
        self.c['ear'].update(source='new', devices=['phone'], min_chars=1)
        self.c['mapping'] = [{'name':'Canonical', 'aliases':['fixture']}]
        self.rows = self.fixture.root/'rows.json'
        command = self.fixture.stub('read_transcripts', """
with Path(os.environ['CALLS']+'.reads').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
for row in json.loads(Path(os.environ['ROWS']).read_text()): print(json.dumps(row))
""")
        env = patch.dict(os.environ, PULSE_EAR_COMMAND=command, ROWS=str(self.rows))
        env.start(); self.addCleanup(env.stop)
        clock = patch.object(ear.time, 'time', return_value=self.base+7200)
        clock.start(); self.addCleanup(clock.stop)

    def row(self, minute, device='phone', scope='one'):
        return dict(start=ear.utc(self.base+minute*60), end=ear.utc(self.base+minute*60+30),
                    text='设计一个学习工具', speaker='speaker0', speaker_scope=scope, device=device)

    def sync(self, rows):
        self.rows.write_text(json.dumps(rows))
        with redirect_stdout(io.StringIO()): ear.sync(self.c, self.state, no_notify=True)
        return list((self.state/'ear/results').glob('*.json'))

    def test_sentence_activity_includes_short_unclassified_speech(self):
        self.c['ear']['min_chars'] = 1000
        self.sync([self.row(119)])
        activity = ear.read(self.state/'ear/activity.json', {})
        self.assertTrue(activity['ok'])
        self.assertEqual(activity['latest_sentence'], self.base+119*60+30)
        self.assertEqual(self.fixture.calls().count('run'), 0)

    def test_alignment_gap_devices_and_scope(self):
        paths = self.sync([self.row(0), self.row(9,scope='two'), self.row(25), self.row(30), self.row(31,'other')])
        self.assertEqual(len(paths),3)
        records = sorted([json.loads(p.read_text()) for p in paths],key=lambda r:r['start'])
        self.assertEqual([r['start'] for r in records],[self.base,self.base+1500,self.base+1800])
        md = Path(records[0]['file']).read_text()
        self.assertIn('S01',md); self.assertIn('S02',md)
        self.assertEqual(records[0]['capture'],'phone:'+ear.utc(self.base))
        self.assertEqual(records[0]['agent_work'][0]['project'],'Canonical')

    def test_lookback_idempotence_and_gap_bridge(self):
        self.sync([self.row(0),self.row(20)])
        self.assertEqual(self.fixture.calls().count('run'),2)
        self.sync([self.row(0),self.row(20)])
        self.assertEqual(self.fixture.calls().count('run'),2)
        paths=self.sync([self.row(0),self.row(10),self.row(20)])
        self.assertEqual(len(paths),1)
        self.assertEqual(self.fixture.calls().count('run'),3)
        self.assertEqual(len(ear.day(self.state,self.base,self.base+7200)),1)
        self.assertEqual(len(ear.inbox(self.state/'ear')),1)
        cursor=ear.read(self.state/'ear/new-cursor.json',{})
        self.assertEqual(cursor['until'], self.base+7200)

    def test_unavailable_warns_without_cursor_and_recovers(self):
        with patch.dict(os.environ,PULSE_EAR_COMMAND='/nonexistent/read_transcripts'):
            err=io.StringIO()
            with redirect_stderr(err): ear.sync(self.c,self.state)
        self.assertIn('warning: Ear 数据缺失',err.getvalue())
        self.assertFalse((self.state/'ear/new-cursor.json').exists())
        self.assertFalse(ear.read(self.state/'ear/availability.json',{})['ok'])
        self.sync([])
        self.assertTrue(ear.read(self.state/'ear/availability.json',{})['ok'])

    def test_multiple_devices_lookback_and_daily_missing_warning(self):
        self.c['ear']['devices'] = ['phone', 'tablet']
        self.sync([self.row(0), self.row(1, 'tablet')])
        self.assertEqual(len(list((self.state/'ear/results').glob('*.json'))), 2)
        with patch.object(ear.time, 'time', return_value=self.base+48*3600):
            self.sync([self.row(0), self.row(1, 'tablet')])
        with patch.object(ear.time, 'time', return_value=self.base+49*3600):
            self.sync([])
        queries = [json.loads(line) for line in Path(os.environ['CALLS']+'.reads').read_text().splitlines()]
        self.assertEqual(queries[-1][queries[-1].index('--start')+1],ear.utc(self.base+24*3600))
        ear.save(self.state/'ear/availability.json', {'ok': False})
        data = dict(segments=[], outputs=[], warnings=[])
        with patch.object(pulse,'config',return_value=self.c), patch.object(pulse,'collect',return_value=data), \
             patch.object(pulse,'classify'), patch.object(sys,'argv',['pulse','day','2026-11-12']), \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pulse.main(),0)
        self.assertIn('Ear 数据缺失',out.getvalue())
        self.assertIn('## 人做了什么',out.getvalue())
        self.assertIn('## 时间线',out.getvalue())

    def test_default_new_missing_token(self):
        del self.c['ear']['source']
        self.c['ear']['token_file']='/nonexistent/token'
        env=dict(os.environ); env.pop('PULSE_EAR_COMMAND',None); env.pop('EAR_ADAPTER_STORAGE_TOKEN',None)
        with patch.dict(os.environ,env,clear=True), redirect_stderr(io.StringIO()) as err:
            ear.sync(self.c,self.state)
        self.assertIn('Ear 数据缺失',err.getvalue())


if __name__ == '__main__': unittest.main()
