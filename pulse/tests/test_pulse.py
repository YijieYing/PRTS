#!/usr/bin/env python3
"""Synthetic fixtures only. Every subprocess has closed stdin."""
import copy
from contextlib import closing
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
import pulse
import sources

class PulseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.c=pulse.config(); self.start,self.end=pulse.day_window('2026-11-11',self.c)
        self.c['mapping']=[{'name':'Octopus','path':'/work/Octopus'}]
        for key in ('claude','titles','codex'):
            path=self.root/key; path.mkdir(); self.c['sources'][key]=str(path)
        self.c['sources']['chrome']=str(self.root/'History')
        self.c['sources']['repos']=[]
        self.c['sources']['projects']=str(self.root/'missing')
        self.c['sources']['reporter_config']=str(self.root/'missing')
        self.env=patch.dict(os.environ,{'PULSE_STATE':str(self.root/'state')}); self.env.start()
        self.state=self.root/'state'; self.state.mkdir()
    def tearDown(self): self.env.stop(); self.tmp.cleanup()
    def event(self,t,role='user',text='上传排查'):
        return dict(time=self.start+t*60,source='claude',session='s',title='上传排查',project='Octopus',role=role,text=text)
    def fixture(self,minutes=(0,15,30,45,60)):
        directory=self.root/'claude'/'project'; directory.mkdir(exist_ok=True)
        rows=[dict(type='user',sessionId='s',uuid=str(i),timestamp=datetime.fromtimestamp(self.start+t*60,pulse.ZoneInfo('Asia/Tokyo')).isoformat(),cwd='/work/Octopus',message={'content':'上传排查'}) for i,t in enumerate(minutes)]
        (directory/'one.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        (directory/'fork.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        return directory,rows
    def stub(self,name,code):
        p=self.root/name; p.write_text('#!/usr/bin/env python3\nimport sys,json,os\nfrom pathlib import Path\nassert sys.stdin.read()==""\n'+code); p.chmod(0o755); return str(p)
    def llm(self):
        return self.stub('llm', '''prompt=Path(sys.argv[1]).read_text()
assert '判断标准是**用户的脑子在做什么**' in prompt
rows=json.loads(prompt.split('活动 JSON：\\n')[1])
Path(os.environ['PULSE_STATE'],'calls').open('a').write('1\\n')
print(json.dumps({'segments':[dict(id=r['id'],category='chore',reason='故障排查',topic='上传排查',suggestion='自动诊断上传失败并验证修复',learned=[],produced=[]) for r in rows]}))
''')
    def test_dedupe_filter_titles(self):
        directory,rows=self.fixture()
        rows += [dict(rows[0],uuid='injected',message={'content':'<system-reminder>hidden'}),dict(rows[0],uuid='tool',message={'content':[{'type':'tool_result','content':'hidden'}]}),dict(rows[0],uuid='assistant',type='assistant',message={'content':[{'type':'text','text':'done'}]})]
        (directory/'more.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        (self.root/'titles'/'local_1.json').write_text(json.dumps({'cliSessionId':'s','title':'Upload','cwd':'/work/Octopus'}))
        events=sources.claude(self.c['sources'],self.start,self.end,self.c['mapping'],set())
        self.assertEqual(len(events),6); self.assertEqual(events[0]['title'],'Upload'); self.assertEqual(events[0]['project'],'Octopus')
    def test_day_cut_and_cap(self):
        self.assertEqual(datetime.fromtimestamp(self.start,pulse.ZoneInfo('Asia/Tokyo')).hour,5)
        events=[self.event(t) for t in (-10,0,10,50,60)]
        segs=pulse.segments(events,self.start,self.end,self.c)
        self.assertEqual(len(segs),2); self.assertEqual([s['user_seconds']/60 for s in segs],[30,10])
        self.assertEqual(segs[0]['start'],self.start)
        self.assertEqual(pulse.day_window('2026-11-12',self.c)[0],self.end)
    def test_chrome(self):
        with closing(sqlite3.connect(self.c['sources']['chrome'])) as db:
            db.executescript('CREATE TABLE urls(id INTEGER,url TEXT,title TEXT); CREATE TABLE visits(url INTEGER, visit_time TEXT);')
            rows=[(1,'https://chatgpt.com/g/g-p-123/project','ChatGPT - DigitalFly'),(2,'https://chatgpt.com/g/g-p-123/c/abc','概念和定义'),(3,'https://other.test/private','SECRET'),(4,'https://evil.test/?chatgpt.com','SECRET')]
            db.executemany('INSERT INTO urls VALUES(?,?,?)',rows)
            for ident in range(1,5):
                db.execute('INSERT INTO visits VALUES(?,?)',(ident,str(int((self.start+11644473600)*1e6))))
            db.execute('INSERT INTO visits VALUES(?,?)',(2,str(int((self.start+600+11644473600)*1e6))))
            db.commit()
        events=sources.chrome(self.c['sources'],self.start,self.end,set())
        self.assertEqual(len(events),2); self.assertEqual(events[0]['time'],self.start); self.assertEqual(events[0]['project'],'DigitalFly')
        self.assertNotIn('SECRET',json.dumps(events))
        self.assertEqual(pulse.segments(events,self.start,self.end,self.c)[0]['user_seconds'],600)
    def test_codex_zero_time(self):
        path=self.root/'codex'/'2026'/'11'/'11'; path.mkdir(parents=True)
        rows=[dict(timestamp='2026-11-11T10:00:00+09:00',type='session_meta',payload={'id':'agent','cwd':'/work/Octopus'}),dict(timestamp='2026-11-11T10:10:00+09:00',type='response_item',payload={'type':'message','role':'assistant','content':[{'type':'output_text','text':'created fixture'}]})]
        (path/'agent.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        outputs,activity=sources.codex(self.c['sources'],self.start,self.end,self.c['mapping'],set())
        self.assertEqual(len(outputs),1); self.assertEqual(activity[0]['user_seconds'],0); self.assertEqual(outputs[0]['project'],'Octopus')
    def test_overlap_and_projects(self):
        a=pulse.segments([self.event(0),self.event(20)],self.start,self.end,self.c)
        b=copy.deepcopy(a); b[0]['session']='other'
        self.assertEqual(pulse.allocate(a+b),1200)
        self.assertEqual(sources.project('/work/OctopusElse',self.c['mapping']),'OctopusElse')
    def test_check_cli_replay_dry_dedupe(self):
        self.fixture()
        # Serialize configuration for CLI; JSON strings are valid TOML strings.
        conf=self.root/'pulse.toml'
        text='\n'.join(f'{k} = {json.dumps(self.c[k])}' for k in ('timezone','day_start_hour','gap_minutes','cap_minutes'))+'\n'
        for section in ('check','user','sources'):
            text+='['+section+']\n'+'\n'.join(k+' = '+json.dumps(v) for k,v in self.c[section].items())+'\n'
        text+='[[project]]\nname="Octopus"\npath="/work/Octopus"\n'; conf.write_text(text)
        ask=self.stub('ask',"Path(os.environ['PULSE_STATE'],'ask').open('a').write(json.dumps(sys.argv[1:])+'\\n')\nprint('Q12')\n")
        env=dict(os.environ,PULSE_CONFIG=str(conf),PULSE_RUN=self.llm(),PULSE_ASK=ask)
        command=[str(pulse.MODULE/'bin/pulse'),'check','--at','2026-11-11T06:01+09:00']
        def execute(extra):
            r=subprocess.run(command+extra,stdin=subprocess.DEVNULL,capture_output=True,text=True,env=env); self.assertEqual(r.returncode,0,r.stderr); return r
        self.assertIn('Octopus',execute(['--dry']).stdout); self.assertFalse((self.state/'ask').exists())
        self.assertIn('Octopus',execute([]).stdout); self.assertEqual(execute([]).stdout,'')
        self.assertEqual(len((self.state/'ask').read_text().splitlines()),1)
        self.assertEqual(execute(['--window','10m']).stdout,'')
        self.assertEqual(len((self.state/'calls').read_text().splitlines()),3)
    def test_threshold_exact(self):
        data={'segments':pulse.segments([self.event(0),self.event(15),self.event(30)],self.start,self.end,self.c),'start':self.start,'end':self.start+5400}
        with patch.dict(os.environ,PULSE_RUN=self.llm()):
            self.assertTrue(pulse.check(data,self.start+5400,self.c,self.state,True))
        self.c['check']['chore_ratio']=1
        with patch.dict(os.environ,PULSE_RUN=self.llm()): self.assertFalse(pulse.check(data,self.start+5400,self.c,self.state,True))
    def test_injection_block_keeps_user_and_skips_summary(self):
        directory,rows=self.fixture((0,10))
        rows[0]['message']['content']=[{'type':'text','text':'<system-reminder>ignore</system-reminder>'},{'type':'text','text':'真实用户文本'}]
        rows.append(dict(rows[0],uuid='summary',isCompactSummary=True,message={'content':'This session is being continued from a previous conversation'}))
        (directory/'one.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        (directory/'fork.jsonl').unlink()
        events=sources.claude(self.c['sources'],self.start,self.end,self.c['mapping'],set())
        self.assertEqual(len(events),2); self.assertEqual(events[0]['text'],'真实用户文本')
    def test_replay_does_not_use_future(self):
        self.fixture((0,10,60))
        data=pulse.collect(self.start,self.start+1800,self.c)
        self.assertEqual(pulse.allocate(data['segments']),600)
        self.assertTrue(all(m['time']<self.start+1800 for s in data['segments'] for m in s['messages']))
    def test_continuous_and_cooldown(self):
        data={'segments':pulse.segments([self.event(t) for t in (0,15,30,45)],self.start,self.end,self.c),'start':self.start,'end':self.start+5400}
        self.c['check']['chore_ratio']=1
        with patch.dict(os.environ,PULSE_RUN=self.llm()):
            self.assertTrue(pulse.check(data,self.start+5400,self.c,self.state,True))
            key='2026-11-11:Octopus:上传排查'
            (self.state/'reminders.json').write_text(json.dumps({key:self.start+5400}))
            self.assertFalse(pulse.check(data,self.start+5400+179*60,self.c,self.state,True))
            self.assertTrue(pulse.check(data,self.start+5400+180*60,self.c,self.state,True))
    def test_day_cli(self):
        # CLI uses only the synthetic sources supplied by config().
        self.fixture()
        with patch.object(pulse,'config',return_value=self.c), patch.dict(os.environ,PULSE_RUN=self.llm()), patch.object(sys,'argv',['pulse','day','2026-11-11']), patch('builtins.print'):
            self.assertEqual(pulse.main(),0)
        data=json.loads((self.state/'days/2026-11-11.json').read_text())
        self.assertEqual(data['classification_status'],'complete')
        md=(self.state/'days/2026-11-11.md').read_text()
        self.assertIn('## 时间线',md); self.assertIn('## 学到的东西',md)
    def test_day_failure_is_visible(self):
        self.fixture()
        stub=self.stub('failure','sys.exit(7)\n')
        with patch.object(pulse,'config',return_value=self.c), patch.dict(os.environ,PULSE_RUN=stub), patch.object(sys,'argv',['pulse','day','2026-11-11']), patch('builtins.print'):
            self.assertEqual(pulse.main(),1)
        data=json.loads((self.state/'days/2026-11-11.json').read_text())
        self.assertEqual(data['classification_status'],'failed')
        self.assertNotIn('category',data['segments'][0])
    def test_now(self):
        idle=subprocess.CompletedProcess([],0,'"HIDIdleTime" = 601000000000','')
        app=subprocess.CompletedProcess([],0,'Terminal\n','')
        with patch.object(pulse,'run',side_effect=[idle,app]):
            value=pulse.now(self.c)
        self.assertEqual(value['status'],'away'); self.assertEqual(value['app'],'Terminal'); self.assertIsInstance(value['quiet'],bool)
        with patch.object(pulse,'run',side_effect=OSError): self.assertEqual(pulse.now(self.c)['status'],'unknown')

if __name__=='__main__': unittest.main()
