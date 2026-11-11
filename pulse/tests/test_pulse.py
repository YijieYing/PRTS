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
        self.assertEqual(len(events),7); self.assertEqual([e['text'] for e in events if e['role']=='tool'],['']); self.assertEqual(events[0]['title'],'Upload'); self.assertEqual(events[0]['project'],'Octopus')
    def test_day_cut_and_cap(self):
        self.assertEqual(datetime.fromtimestamp(self.start,pulse.ZoneInfo('Asia/Tokyo')).hour,5)
        events=[self.event(t,text='') for t in (-10,0,10,50,60)]
        segs=pulse.segments(events,self.start,self.end,self.c)
        self.assertEqual(len(segs),2); self.assertEqual([s['user_seconds']/60 for s in segs],[30,10])
        self.assertEqual(segs[0]['start'],self.start)
        self.assertEqual(pulse.day_window('2026-11-12',self.c)[0],self.end)
    def test_chrome(self):
        with closing(sqlite3.connect(self.c['sources']['chrome'])) as db:
            db.executescript('CREATE TABLE urls(id INTEGER,url TEXT,title TEXT); CREATE TABLE visits(url INTEGER, visit_time TEXT, visit_duration TEXT);')
            rows=[(1,'https://chatgpt.com/g/g-p-123/project','ChatGPT - DigitalFly'),(2,'https://chatgpt.com/g/g-p-123/c/abc','概念和定义'),(3,'https://other.test/private','SECRET'),(4,'https://evil.test/?chatgpt.com','SECRET')]
            db.executemany('INSERT INTO urls VALUES(?,?,?)',rows)
            for ident in range(1,5):
                db.execute('INSERT INTO visits VALUES(?,?,?)',(ident,str(int((self.start+11644473600)*1e6)),'600000000'))
            db.execute('INSERT INTO visits VALUES(?,?,?)',(2,str(int((self.start+600+11644473600)*1e6)),'0'))
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
        text='\n'.join(f'{k} = {json.dumps(self.c[k])}' for k in ('timezone','day_start_hour','gap_minutes','cap_minutes','chatgpt_cap_minutes','held_cap_minutes'))+'\n'
        for section in ('check','user','sources','timing'):
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
            self.assertFalse(pulse.check(data,self.start+5400,self.c,self.state,True))
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
    def test_read_write_paste_and_caps(self):
        self.assertEqual(pulse.writing_seconds('字'*40,self.c),60)
        self.assertEqual(pulse.writing_seconds('<pasted_content>'+'字'*400+'</pasted_content>',self.c),60)
        self.assertEqual(pulse.writing_seconds('字'*200+'\n'+'字'*200,self.c),60)
        self.assertEqual(pulse.writing_seconds('字'*10000,self.c),900)
        self.assertEqual(pulse.reading_seconds('字'*400,self.c),60)
        self.assertEqual(pulse.reading_seconds('字'*10000,self.c),900)
        events=[self.event(10,text='字'*40),self.event(12,'assistant','字'*400)|{'final':True}]
        segs=pulse.segments(events,self.start,self.end,self.c)
        self.assertEqual(segs[0]['user_seconds'],120)
        segs[0]['category']='chore'; pulse.allocate(segs)
        self.assertEqual(segs[0]['held_seconds'],120)
        previous=[self.event(0,'assistant','字'*400),self.event(10,text='字'*40)]
        self.assertEqual(pulse.segments(previous,self.start,self.end,self.c)[0]['user_seconds'],120)

    def test_max_gap_not_sum(self):
        segs=pulse.segments([self.event(10,text='字'*40),self.event(25,text='字'*40)],self.start,self.end,self.c)
        self.assertEqual(segs[0]['estimates'][0]['active_seconds'],900)
        self.assertEqual(segs[0]['user_seconds'],960)

    def test_held_cap_completion_next_user_and_overlap(self):
        events=[self.event(10,text=''),self.event(80,'tool',''),self.event(85,'assistant','')|{'final':True}]
        segs=pulse.segments(events,self.start,self.end,self.c)
        self.assertEqual(segs[0]['held_candidates'],[[self.start+600,self.start+4200]])
        segs[0]['category']='chore'
        other=dict(intervals=[[self.start+1800,self.start+2400]],category='input')
        pulse.allocate(segs+[other])
        self.assertEqual(segs[0]['held_seconds'],3000)
        self.assertEqual(other['active_seconds'],600)
        events=[self.event(10,text=''),self.event(12,'tool',''),self.event(14,'assistant','')|{'final':True},self.event(16,'tool',''),self.event(20,text='')]
        segs=pulse.segments(events,self.start,self.end,self.c)
        self.assertEqual(segs[0]['held_evidence'][0]['end'],self.start+14*60)
        events=[self.event(10,text=''),self.event(19,'tool',''),self.event(20,text=''),self.event(25,'assistant','')|{'final':True}]
        segs=pulse.segments(events,self.start,self.end,self.c)
        self.assertEqual(segs[0]['held_evidence'][0]['end'],self.start+20*60)

    def test_held_threshold_sparse_user(self):
        segs=pulse.segments([self.event(0,text=''),self.event(31,'tool','')],self.start,self.start+5400,self.c)
        data=dict(segments=segs,start=self.start,end=self.start+5400)
        with patch.dict(os.environ,PULSE_RUN=self.llm()):
            self.assertTrue(pulse.check(data,self.start+5400,self.c,self.state,True))
        self.assertEqual(data['check']['chore_active_seconds'],0)
        self.assertEqual(data['check']['chore_held_seconds'],3600)
        self.assertEqual(len((self.state/'calls').read_text().splitlines()),1)
        # Exactly 30 minutes is not continuous >30, and is below the new 60-minute total.
        data['segments'][0]['held_candidates']=[[self.start,self.start+1800]]
        with patch.dict(os.environ,PULSE_RUN=self.llm()): self.assertFalse(pulse.check(data,self.start+5400,self.c,self.state,True))

    def test_ratio_uses_window_not_active(self):
        rows=[self.event(0,text=''),self.event(30,'assistant','')|{'final':True},self.event(40,text=''),self.event(70,'assistant','')|{'final':True}]
        data=dict(segments=pulse.segments(rows,self.start,self.start+7260,self.c),start=self.start,end=self.start+7260)
        # Disable continuous branch to isolate inclusive 60-minute and 50% boundaries.
        self.c['check']['continuous_minutes']=100
        with patch.dict(os.environ,PULSE_RUN=self.llm()):
            self.assertFalse(pulse.check(data,self.start+7260,self.c,self.state,True))
        data['end']=self.start+7200
        with patch.dict(os.environ,PULSE_RUN=self.llm()):
            self.assertTrue(pulse.check(data,self.start+7200,self.c,self.state,True))

    def test_home_mapping_excluded(self):
        mapping=[dict(name='PRTS',path=str(Path.home()),exact=True)]
        self.assertEqual(sources.project(str(Path.home()),mapping),'未归属')
        mapping=[dict(name='PRTS',path=str(Path.home()))]+self.c['mapping']
        self.assertEqual(sources.project('/work/Octopus/child',mapping),'Octopus')
        self.assertNotEqual(sources.project(str(Path.home()/'unknown'),mapping),'PRTS')

    def test_chrome_duration_next_page_cap_and_url_merge(self):
        db=sqlite3.connect(self.c['sources']['chrome'])
        with closing(db):
            db.executescript('CREATE TABLE urls(id INTEGER,url TEXT,title TEXT); CREATE TABLE visits(url INTEGER,visit_time TEXT,visit_duration TEXT);')
            db.executemany('INSERT INTO urls VALUES(?,?,?)',[(1,'https://chatgpt.com/g/g-p-test/c/a','概念'),(2,'https://chatgpt.com/g/g-p-test/project','ChatGPT - Test'),(3,'https://evil.test/?chatgpt.com','SECRET')])
            for ident,minute,duration in [(1,0,148),(3,5,1),(2,10,1),(1,60,148),(1,180,0)]:
                db.execute('INSERT INTO visits VALUES(?,?,?)',(ident,str(int((self.start+minute*60+11644473600)*1e6)),str(int(duration*60e6))))
            db.commit()
        events=sources.chrome(self.c['sources'],self.start,self.end,set())
        segs=pulse.segments(events,self.start,self.end,self.c)
        self.assertEqual(len(segs),1)
        self.assertEqual(segs[0]['user_seconds'],55*60)
        self.assertEqual(segs[0]['confidence'],'低')
        self.assertEqual(segs[0]['project'],'Test')
        self.assertEqual(segs[0]['intervals'][0],[self.start,self.start+600])

    def test_no_classify_preserves_report_and_labels_by_uuid(self):
        self.fixture()
        with patch.object(pulse,'config',return_value=self.c), patch.dict(os.environ,PULSE_RUN=self.llm()), patch.object(sys,'argv',['pulse','day','2026-11-11']), patch('builtins.print'):
            self.assertEqual(pulse.main(),0)
        path=self.state/'days/2026-11-11.json'; original=path.read_bytes()
        with patch.object(pulse,'config',return_value=self.c), patch.object(pulse,'classify',side_effect=AssertionError('must not call')), patch.object(sys,'argv',['pulse','day','2026-11-11','--no-classify']), patch('builtins.print'):
            self.assertEqual(pulse.main(),0)
        self.assertEqual(path.read_bytes(),original)
        timing=json.loads((self.state/'days/2026-11-11.timing.json').read_text())
        self.assertEqual(timing['classification_status'],'cached')
        data=copy.deepcopy(timing); data['segments'][0]['id']='999'
        pulse.reuse(data,path); self.assertEqual(data['segments'][0]['category'],'chore')
        for m in data['segments'][0]['messages']:m['uuid']='new'
        pulse.reuse(data,path); self.assertEqual(data['segments'][0]['category'],'unclassified')

    def test_no_classify_failure_preserves_original(self):
        self.fixture()
        days=self.state/'days'; days.mkdir()
        original=days/'2026-11-11.json'; original.write_text('preserve original')
        broken=self.root/'broken.json'; broken.write_text('{')
        with patch.object(pulse,'config',return_value=self.c), patch.object(sys,'argv',['pulse','day','2026-11-11','--no-classify','--classification-file',str(broken)]), patch('builtins.print'):
            self.assertEqual(pulse.main(),1)
        self.assertEqual(original.read_text(),'preserve original')
        self.assertEqual(json.loads((days/'2026-11-11.timing.json').read_text())['classification_status'],'failed')

    def test_table_percentages_and_tiny_minutes(self):
        segs=pulse.segments([self.event(0,text=''),self.event(10,text='')],self.start,self.end,self.c)
        for s in segs:s.update(category='input',reason='x',learned=[],produced=[],topic='',suggestion='')
        segs[0]['intervals']=[[self.start,self.start+0.5]]
        md=pulse.render(dict(segments=segs,outputs=[],warnings=[]),'2026-11-11',self.c)
        self.assertIn('<0.1（100.0%）',md)
        self.assertNotIn('0.0（100.0%）',md)

    def test_replay_excludes_future_tools_and_final(self):
        directory,rows=self.fixture((0,))
        for minute,kind in ((20,'tool'),(40,'assistant')):
            rows.append(dict(type='user' if kind=='tool' else kind,sessionId='s',uuid=kind,
                             timestamp=datetime.fromtimestamp(self.start+minute*60,pulse.ZoneInfo('Asia/Tokyo')).isoformat(),cwd='/work/Octopus',
                             message={'content':[{'type':'tool_result','content':'SECRET'}] if kind=='tool' else 'done','stop_reason':'end_turn'}))
        (directory/'one.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        data=pulse.collect(self.start,self.start+30*60,self.c)
        self.assertEqual(data['segments'][0]['held_candidates'],[[self.start,self.start+30*60]])
        self.assertNotIn('SECRET',json.dumps(data))
        self.assertTrue(all(e['time']<self.start+30*60 for h in data['segments'][0]['held_evidence'] for e in h['events']))

    def test_now(self):
        idle=subprocess.CompletedProcess([],0,'"HIDIdleTime" = 601000000000','')
        app=subprocess.CompletedProcess([],0,'Terminal\n','')
        with patch.object(pulse,'run',side_effect=[idle,app]):
            value=pulse.now(self.c)
        self.assertEqual(value['status'],'away'); self.assertEqual(value['app'],'Terminal'); self.assertIsInstance(value['quiet'],bool)
        with patch.object(pulse,'run',side_effect=OSError): self.assertEqual(pulse.now(self.c)['status'],'unknown')

if __name__=='__main__': unittest.main()
