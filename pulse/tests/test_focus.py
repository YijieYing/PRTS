"""Isolated focus fixtures; no real history, model or notification channels."""
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
import focus
import pulse
import sources

class FocusTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.state=Path(self.tmp.name)
        (self.state/'focus').mkdir()
        self.c=pulse.config(); self.c.pop('study',None); self.t=1800000000
        self.current=dict(goal='学 agent',note='',on=['study'],off=['Ear'],start=self.t,until=self.t+7200,rows=[],reminders=[])
        self.rows=[]; self.users=[]
        self.patches=[patch.object(focus.computer_history,'archive'),patch.object(focus.computer_history,'load',side_effect=lambda *a:(self.rows,[])),patch.object(focus,'sessions',side_effect=lambda *a:self.users)]
        for p in self.patches: p.start()
        self.runner=self.stub('model',"rows=json.loads(Path(sys.argv[1]).read_text().split('活动 JSON：\\n')[1]); print(json.dumps({'items':[{'id':r['id'],'category':'off','reason':'偏离'} for r in rows]}))")
        self.notify=self.stub('notify','assert sys.argv[1]=="alert"')
        self.env=patch.dict(os.environ,{'PULSE_RUN':str(self.runner),'PULSE_NOTIFY':str(self.notify)}); self.env.start()
    def tearDown(self):
        self.env.stop()
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()
    def stub(self,name,body):
        p=self.state/name
        p.write_text('#!/usr/bin/env python3\nimport sys,json\nfrom pathlib import Path\nassert sys.stdin.read()==""\nPath(__file__+".calls").open("a").write("1\\n")\n'+body+'\n'); p.chmod(0o755); return p
    def calls(self,p):
        file=Path(str(p)+'.calls'); return len(file.read_text().splitlines()) if file.exists() else 0
    def minutes(self,a,b,title='Ear',app='Editor',active=True):
        self.rows += [dict(time=self.t+i*60,last=self.t+i*60+50,title=title,app=app,domain='',bundle=app,active=active,counts={'typing':3}) for i in range(a,b)]
    def check(self,m,dry=False): return focus.check(self.current,self.t+m*60,self.c,self.state,dry)
    def test_empty_silent(self):
        out=io.StringIO()
        with redirect_stdout(out): focus.command(argparse.Namespace(focus_command='check',at=None,dry=False),self.c,self.state)
        self.assertEqual(out.getvalue(),''); self.assertEqual(self.calls(self.runner),0)
    def test_away_rules_and_priority(self):
        self.minutes(0,3,'study'); self.minutes(3,6,'study Ear'); self.minutes(6,8,'Ear',active=False)
        r=self.check(8,True)
        self.assertEqual(r['counts'],dict(on=3,off=3,unknown=0,away=2)); self.assertEqual(self.calls(self.runner),0)
    def test_session_and_short_control(self):
        self.minutes(0,4,'Claude','Claude')
        self.users=[dict(time=self.t-60,source='claude',session='s',title='调试',cwd='/work/Ear')]
        self.assertEqual(self.check(4,True)['counts']['off'],4)
        self.minutes(4,6,'Claude','Claude')
        self.users.append(dict(time=self.t+240,source='claude',session='control',title='Ear',cwd=str(focus.ROOT)))
        self.assertEqual(self.check(6,True)['counts']['unknown'],2)
    def test_cache_and_goal_scope(self):
        self.minutes(0,4,'other')
        self.check(4,True); self.check(4,True)
        self.assertEqual(self.calls(self.runner),1)
        self.current['goal']='different'; self.check(4,True)
        self.assertEqual(self.calls(self.runner),2)
    def test_failure_unknown(self):
        self.runner.write_text('#!/bin/sh\nexit 1\n'); self.minutes(0,4,'other')
        self.assertEqual(self.check(4,True)['counts']['unknown'],4)
    def test_threshold_cooldown_recovery(self):
        self.minutes(0,9); self.assertFalse(self.check(9)['would_remind'])
        self.minutes(9,10); self.assertTrue(self.check(10)['reminded'])
        self.minutes(10,12); self.assertFalse(self.check(12)['would_remind'])
        self.minutes(12,18,'study'); self.check(18)
        self.minutes(18,28); self.assertTrue(self.check(28)['reminded'])
        self.assertEqual(self.calls(self.notify),2)
    def test_cooldown_expires_and_system_apps(self):
        self.minutes(0,10); self.assertTrue(self.check(10)['reminded'])
        self.minutes(10,29); self.assertFalse(self.check(29)['would_remind'])
        self.minutes(29,30); self.assertTrue(self.check(30)['reminded'])
        self.minutes(30,32,app='Dock')
        self.assertEqual(self.check(32,True)['counts']['away'],2)

    def test_window_threshold(self):
        self.minutes(0,6); self.minutes(6,8,'study'); self.minutes(8,14)
        self.assertTrue(self.check(14)['reminded'])
    def test_dry_and_expiry(self):
        self.minutes(0,12); self.assertTrue(self.check(12,True)['would_remind'])
        self.assertEqual(self.calls(self.notify),0)
        self.current['until']=self.t+900; self.check(16)
        self.assertFalse((self.state/'focus/current.json').exists())
        record=json.loads((self.state/'focus/log.jsonl').read_text()); self.assertEqual(record['end_reason'],'expired')
        self.assertEqual(record['counts']['away'],3)
        section=focus.day(self.state,self.t,self.t+86400,self.c)
        self.assertIn('## 专注',section); self.assertIn('off 12',section)
        self.assertEqual(focus.day(self.state,self.t-1000,self.t,self.c),'')
    def test_switch_and_duplicate_minutes(self):
        self.minutes(0,1); self.minutes(0,1,'study'); self.minutes(1,3,'study')
        r=self.check(3,True); self.assertEqual(sum(r['counts'].values()),3)
        self.assertEqual(r['counts']['off'],0)
    def test_commands_and_day_render(self):
        args=argparse.Namespace(focus_command='set',goal='study',until='01:00',on=['study'],off=['Ear'],note='')
        with redirect_stdout(io.StringIO()):
            focus.command(args,self.c,self.state)
        current=focus.read(self.state/'focus/current.json',None)
        self.assertGreater(current['until'],current['start'])
        self.assertLessEqual(current['until']-current['start'],86400)
        with redirect_stdout(io.StringIO()):
            focus.command(argparse.Namespace(focus_command='status'),self.c,self.state)
            focus.command(argparse.Namespace(focus_command='stop'),self.c,self.state)
        self.assertFalse((self.state/'focus/current.json').exists())
        self.assertEqual(self.calls(self.notify),0)
        section=focus.day(self.state,current['start']-60,current['until']+60,self.c)
        data={'segments':[], 'outputs':[], 'warnings':[], 'focus':section}
        self.assertIn('## 专注',pulse.render(data,'2026-11-13',self.c))

    def test_codex_user_metadata(self):
        root=self.state/'codex/2026/11/13'; root.mkdir(parents=True)
        rows=[{'type':'session_meta','payload':{'id':'c','cwd':'/work/Ear'}}, {'type':'event_msg','timestamp':'2026-11-13T12:00:00+09:00','payload':{'type':'user_message','message':'修录音'}}]
        (root/'one.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
        users=[]; sources.codex({'codex':str(self.state/'codex')},0,9999999999,[],set(),users)
        self.assertEqual(users[0]['title'],'修录音'); self.assertEqual(users[0]['cwd'],'/work/Ear')

    def test_start_dnd_creates_source_and_stop_reason(self):
        rows=[dict(time=self.t-60,last=self.t-1,title='unregistered',app='Editor',bundle='Editor',domain='',active=True,counts={'typing':1})]
        with patch.object(focus.computer_history,'load',return_value=(rows,[])):
            with redirect_stdout(io.StringIO()):
                focus.command(argparse.Namespace(focus_command='start-dnd',dry=False),self.c,self.state)
        current=focus.read(self.state/'focus/current.json',None)
        self.assertEqual(current['source'],'dnd'); self.assertEqual(current['goal'],'专注（勿扰模式）')
        with redirect_stdout(io.StringIO()) as out:
            focus.command(argparse.Namespace(focus_command='stop',reason='dnd-off'),self.c,self.state)
        self.assertEqual(json.loads((self.state/'focus/log.jsonl').read_text())['end_reason'],'dnd-off')

    def test_start_dnd_does_not_replace_manual(self):
        focus.write(self.state/'focus/current.json',self.current)
        with redirect_stdout(io.StringIO()):
            focus.command(argparse.Namespace(focus_command='start-dnd',dry=False),self.c,self.state)
        self.assertEqual(focus.read(self.state/'focus/current.json',None)['goal'],'学 agent')
        self.assertEqual(len((self.state/'focus/dnd.log').read_text().splitlines()),1)

if __name__=='__main__': unittest.main()
