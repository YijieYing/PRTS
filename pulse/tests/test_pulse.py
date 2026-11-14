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
import computer_history as history
from test_ear import EarTests
from test_focus import FocusTests

class PulseTests(unittest.TestCase):
    def test_codex_day_span_uses_one_observed_minute(self):
        rows=history.aggregate([dict(time=self.start+3605,kind='mouse.click',app='Codex',bundle='codex',title='Task',domain='')])
        segs=[]
        pulse.computer(segs,[dict(session='cx',title='Task',project='Octopus',start=self.start,end=self.end-1)],rows,[],self.start,self.end,self.c)
        self.assertEqual((segs[0]['start'],segs[0]['end']),(self.start+3600,self.start+3660))
        segs[0].update(category='chore',summary='短暂查看',learned=[],produced=[])
        other=dict(source='computer',session='other',start=self.start+7200,end=self.start+7500,
                   intervals=[[self.start+7200,self.start+7500]],project='Other',category='input',summary='阅读论文',messages=[])
        data=dict(segments=segs+[other],warnings=[])
        md=pulse.render(data,'2026-11-11',self.c)
        self.assertIn('**零碎** Octopus 1.0 分',md)
        self.assertNotIn('同时：',md)
        self.assertEqual(data['warnings'],[])

    def test_session_gap_and_actual_overlap(self):
        segs=pulse.segments([self.event(60),self.event(600)],self.start,self.end,self.c)
        self.assertEqual(len(segs),2)
        self.assertLess(segs[0]['end'],segs[1]['start'])
        a=dict(intervals=[[0,60],[10000,10060]])
        self.assertEqual(pulse.overlap(a,dict(intervals=[[5000,6000]])),0)

    def test_codex_title_shared_with_focus_adapter(self):
        path=self.root/'codex'/'2026'/'11'/'11'; path.mkdir(parents=True)
        rows=[dict(timestamp=datetime.fromtimestamp(t,pulse.ZoneInfo('Asia/Tokyo')).isoformat(),type=kind,payload=payload)
              for t,kind,payload in [(self.start-60,'event_msg',dict(type='user_message',message='研究活动分段')),
                                     (self.start+60,'event_msg',dict(type='user_message',message='继续'))]]
        (path/'uuid.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        users=[]
        _,activity=sources.codex(self.c['sources'],self.start,self.end,self.c['mapping'],set(),users=users)
        self.assertEqual(activity[0]['title'],'研究活动分段')
        self.assertEqual(users[0]['title'],activity[0]['title'])

    def test_render_disjoint_chatgpt_and_short_host(self):
        md=self.render_fixture([
            dict(minute=0,duration=600,source='chatgpt',summary='分次阅读',
                 intervals=[[self.start,self.start+300],[self.start+35700,self.start+36000]]),
            dict(minute=100,duration=1,source='codex',category='chore',summary='短暂查看'),
            dict(minute=100,duration=5,project='Other',summary='独立工作')])
        self.assertIn('05:00–05:05、14:55–15:00',md)
        self.assertNotIn('05:00–15:00',md)
        self.assertNotIn('同时：',md)
        self.assertIn('**零碎**',md)

    def test_computer_inactive_edges_do_not_extend_activity(self):
        rows=history.aggregate([dict(time=self.start+t,kind=kind,app='Editor',bundle='editor',title='Task',domain='')
                                for t,kind in [(5,'window.changed'),(65,'mouse.click'),(125,'window.changed')]])
        segs=[]
        pulse.computer(segs,[],rows,[],self.start,self.end,self.c)
        self.assertEqual((segs[0]['start'],segs[0]['end']),(self.start+60,self.start+120))

    def test_span_warning_before_render_repairs_bounds(self):
        import io
        s=dict(source='codex',session='bad',start=self.start,end=self.end-1,
               intervals=[[self.start+60,self.start+120]],project='Octopus',category='input')
        data=dict(segments=[s],warnings=[])
        stderr=io.StringIO()
        with patch('sys.stderr',stderr): pulse.render(data,'2026-11-11',self.c)
        self.assertEqual(len(data['warnings']),1)
        self.assertIn('活动跨度异常',stderr.getvalue())
        self.assertEqual(s['end']-s['start'],60)

    def test_display_intervals_merge_limit_and_evidence(self):
        intervals=[]
        cursor=self.start
        for i in range(9):
            intervals.append([cursor,cursor+60])
            cursor += 60 + (2+i%4)*60
        segment=dict(intervals=intervals)
        original=copy.deepcopy(segment)
        self.assertEqual(pulse.display_intervals(segment,self.c),[[intervals[0][0],intervals[-1][1]]])
        self.assertEqual(segment,original)
        md=self.render_fixture([dict(minute=0,duration=60,intervals=intervals,summary='九次活动')])
        self.assertIn('05:00–'+pulse.local(intervals[-1][1],self.c)+' ·',md)
        far=[[self.start,self.start+300],[self.start+14400,self.start+14700]]
        md=self.render_fixture([dict(minute=0,duration=245,intervals=far)])
        self.assertIn('05:00–05:05、09:00–09:05',md)
        far.append([self.start+28800,self.start+29100])
        md=self.render_fixture([dict(minute=0,duration=485,intervals=far)])
        self.assertIn('05:00–05:05、…、13:00–13:05（共 3 段）',md)
        self.assertEqual(pulse.display_intervals(dict(intervals=[[0,60],[960,1020]]),self.c),[[0,1020]])
        self.assertEqual(pulse.display_intervals(dict(intervals=[[0,60],[961,1020]]),self.c),[[0,60],[961,1020]])
        self.assertEqual(pulse.display_intervals(segment,dict(display_merge_minutes=0)),intervals)

    def test_classify_prompt_is_compacted_and_batched(self):
        minute={'type':'minute','time':0,'app':'WeChat','title':'Weixin','domain':'','counts':{'typing':2,'clicks':1},'active':True}
        seg={'id':'s1','source':'computer','messages':[],'intervals':[[0,60]],'computer_minutes':[minute]*300,
             'computer_summaries':[{'time':0,'title':'t','description':'d'*2000}]*20}
        packed=pulse.pack(seg)
        self.assertNotIn('computer_minutes',packed); self.assertEqual(packed['computer_windows'][0]['active_minutes'],300)
        self.assertEqual(len(packed['computer_summaries']),6); self.assertEqual(len(packed['computer_summaries'][0]['description']),400)
        items=[{'id':str(i),'x':'y'*100} for i in range(50)]
        groups=list(pulse.batches(items,1000))
        self.assertGreater(len(groups),1); self.assertEqual(sum(groups,[]),items)
        self.assertTrue(all(len(json.dumps(g))<=1000 or len(g)==1 for g in groups))

    def test_project_attribution_rules_candidates_and_batches(self):
        Path(self.c['sources']['projects']).write_text('[[project]]\nname="Octopus"\npath="/work/Octopus"\n')
        self.c['mapping'].append(dict(name='仅配置未命中',path='/unused'))
        data = dict(segments=[dict(id=str(i), source='computer', session=str(i),
                    title='窗口'+str(i), messages=[], project=project,
                    start=self.start+i*600, end=self.start+i*600+300,
                    intervals=[[self.start+i*600,self.start+i*600+300]])
                    for i, project in enumerate(['Infra','其他','未归属',None,'DsHarness'])], warnings=[])
        answers = ['Octopus','Infra',None,'编造的项目','Octopus']
        prompts = []
        def model(cmd, **kwargs):
            prompt = Path(cmd[1]).read_text(); prompts.append(prompt)
            rows = json.loads(prompt.split('活动 JSON：\n')[1])
            return subprocess.CompletedProcess(cmd, 0, json.dumps(dict(segments=[dict(
                id=r['id'], category='input', reason='阅读', summary='看课件', topic='', suggestion='',
                learned=[], produced=[], project=answers[int(r['id'])], project_hint='机械设计课')
                for r in rows])), '')
        with patch.object(pulse,'run',side_effect=model), patch.object(pulse,'PROMPT_BUDGET',100), patch('sys.stderr'):
            pulse.classify(data,self.state,self.c)
        self.assertEqual(len(prompts),5)
        candidates = [json.loads(p.split('项目候选 JSON：')[1].split('\n')[0]) for p in prompts]
        self.assertTrue(all(c==['DsHarness','Infra','Octopus'] for c in candidates))
        self.assertEqual([s['project'] for s in data['segments']],['Infra','Infra',None,None,'DsHarness'])
        self.assertEqual([s['project_source'] for s in data['segments']],['rule','model','none','none','rule'])
        self.assertEqual([s['project_hint'] for s in data['segments']],['','','机械设计课','机械设计课',''])
        self.assertEqual(len(data['warnings']),1); self.assertIn('编造的项目',data['warnings'][0])
        md=pulse.render(data,'2026-11-11',self.c)
        self.assertTrue(all(s['active_seconds']==300 for s in data['segments']))
        self.assertIn('**Infra** 10.0 分',md)
        self.assertIn('**不属于项目** 10.0 分',md)
        self.assertIn('可能的新项目：机械设计课（2 段，10.0 分）',md)
        self.assertEqual(pulse.schema()['properties']['segments']['items']['properties']['project']['type'],['string','null'])

    def test_project_hints_top_three_and_unmatched_beyond_limit(self):
        rows=[dict(minute=i*40,duration=i+4,project=None,project_source='none',project_hint=hint)
              for i,hint in enumerate(['甲','乙','丙','丁','丁'])]
        rows += [dict(minute=300+i*40,duration=4,project='P'+str(i)) for i in range(10)]
        section=self.human_section(self.render_fixture(rows))
        hint_line=section.split('可能的新项目：')[1]
        self.assertEqual(hint_line,'丁（2 段，15.0 分）；丙（1 段，6.0 分）；乙（1 段，5.0 分）')
        self.assertLessEqual(len(section),1200)
        self.assertGreater(section.index('**不属于项目**'),section.index('- 其他：'))
        self.assertEqual(len([line for line in section.splitlines() if line.startswith('- **')]),8)

    def test_project_cache_legacy_and_model_provenance(self):
        fresh=dict(source='computer',session='cache',start=self.start,end=self.start+300,
                   intervals=[[self.start,self.start+300]],messages=[],project='Octopus')
        old=dict(fresh,category='input',reason='阅读',topic='',suggestion='',learned=[],produced=[])
        del old['project']
        path=self.state/'cached.json'
        path.write_text(json.dumps(dict(segments=[old])))
        data=dict(segments=[copy.deepcopy(fresh)],warnings=[])
        pulse.reuse(data,path)
        self.assertEqual(data['segments'][0]['project'],'Octopus')
        self.assertEqual(data['segments'][0]['project_source'],'rule')
        self.assertIn('Octopus',pulse.render(data,'2026-11-11',self.c))
        old.update(project='Infra',project_source='model',project_hint='')
        path.write_text(json.dumps(dict(segments=[old])))
        fresh['project']='其他'
        data['segments']=[copy.deepcopy(fresh)]
        pulse.reuse(data,path)
        self.assertEqual(data['segments'][0]['project'],'Infra')
        self.assertEqual(data['segments'][0]['project_source'],'model')
        fresh['project']='Octopus'; data['segments']=[fresh]
        pulse.reuse(data,path)
        self.assertEqual(fresh['project'],'Octopus')

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.c=pulse.config(); self.start,self.end=pulse.day_window('2026-11-11',self.c)
        self.c['mapping']=[{'name':'Octopus','path':'/work/Octopus'}]
        for key in ('claude','titles','codex','computer_events','computer_summaries'):
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
print(json.dumps({'segments':[dict(id=r['id'],category='chore',reason='故障排查',summary='排查上传失败',topic='上传排查',suggestion='自动诊断上传失败并验证修复',learned=[],produced=[]) for r in rows]}))
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
        self.assertTrue((self.state/'computer/2026-11-11.jsonl').exists())
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
        self.assertIn('## 时间线',md); self.assertIn('## 可以交给 agent 的杂务',md); self.assertNotIn('| 类别 |',md)
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
        self.assertEqual(timing['segments'][0]['summary'],'排查上传失败')
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
        self.assertIn('输入 <0.1 分',md)
        self.assertNotIn('输入 0.0 分',md)

    def render_fixture(self, rows, outputs=None, warnings=None):
        segs=[]
        for i, row in enumerate(rows):
            row = dict(row)
            start, duration = row.pop('minute'), row.pop('duration')
            s=dict(start=self.start+start*60, end=self.start+(start+duration)*60,
                   intervals=[[self.start+start*60,self.start+(start+duration)*60]],
                   project='Octopus', category='output', reason='回退理由', learned=[], produced=[],
                   suggestion='', session=str(i), source='computer', messages=[])
            s.update(row); segs.append(s)
        return pulse.render(dict(segments=segs,outputs=outputs or [],warnings=warnings or []),'2026-11-11',self.c)

    def human_section(self, md):
        return md.split('## 人做了什么\n',1)[1].split('## 时间线',1)[0].strip()

    def test_human_projects_rank_limit_and_remainder(self):
        md=self.render_fixture([dict(minute=i*40,duration=i+3,project=f'P{i}',summary=f'活动{i}')
                                for i in range(10)])
        section=self.human_section(md)
        projects=[line.split('**')[1] for line in section.splitlines() if line.startswith('- **')]
        self.assertEqual(projects,[f'P{i}' for i in range(9,1,-1)])
        self.assertIn('- 其他：7.0 分',section)
        self.assertLess(md.index('## 人做了什么'),md.index('## 时间线'))
        self.assertTrue(md.splitlines()[1].startswith('输入 '))
        head=[line for line in md.splitlines()[2:] if line.strip() and not line.startswith('## ')][:8]
        self.assertTrue(head[0].startswith('- **P9**'))

    def test_human_unmatched_projects_merge_last(self):
        md=self.render_fixture([dict(minute=0,duration=30,project='其他',summary='看课件。'),
                                dict(minute=40,duration=20,project='未归属',summary='写报告。'),
                                dict(minute=80,duration=5,project='P1',summary='读论文')])
        rows=[line for line in self.human_section(md).splitlines() if line.startswith('- **')]
        self.assertEqual([r.split('**')[1] for r in rows],['P1','不属于项目'])
        self.assertIn('50.0 分',rows[1]); self.assertNotIn('。；',rows[1])

    def test_project_aliases_merge_names(self):
        self.c['mapping']=[{'name':'总控','path':'/work/PRTS','aliases':['PRTS','总控（主）']}]
        md=self.render_fixture([dict(minute=0,duration=10,project='PRTS',summary='甲'),
                                dict(minute=40,duration=10,project='总控（主）',summary='乙'),
                                dict(minute=80,duration=10,project='总控',summary='丙')])
        rows=[line for line in self.human_section(md).splitlines() if line.startswith('- **')]
        self.assertEqual(len(rows),1); self.assertTrue(rows[0].startswith('- **总控** 30.0 分'))

    def test_human_categories_summaries_and_children(self):
        md=self.render_fixture([
            dict(minute=0,duration=4,category='input',summary='阅读论文',learned=['甲','甲','乙','丙']),
            dict(minute=40,duration=5,summary='设计实验',produced=['一','一','二','三']),
            dict(minute=80,duration=6,category='chore',summary='阅读论文'),
            dict(minute=120,duration=7,category='unclassified',summary='不能选这句'),
            dict(minute=160,duration=9,category='other',source='claude',summary='不计其他'),
            dict(minute=200,duration=1,summary='不计零碎'),
            dict(minute=240,duration=0,intervals=[],learned=['不计无活动'])])
        section=self.human_section(md)
        self.assertIn('22.0 分（输入 4.0 · 输出 5.0 · 杂务 6.0 · 未分类 7.0）',section)
        self.assertIn('：阅读论文；设计实验',section)
        for text in ('不能选这句','不计其他','不计零碎','不计无活动','丙','三'):
            self.assertNotIn(text,section)
        for label in ('学到','产出'):
            self.assertEqual(section.count('  - '+label+'：'),2)
        self.assertEqual(section.count('学到：甲'),1)

    def test_human_ear_and_attached_projects(self):
        md=self.render_fixture([
            dict(minute=0,duration=10,source='claude',project='电脑',summary='电脑活动'),
            dict(minute=1,duration=4,source='ear',project=None,value='high',title='录音',summary='线下讨论'),
            dict(minute=2,duration=4,project='图表',summary='读图'),
            dict(minute=40,duration=1,source='ear',project='',value='medium',title='短录音',summary='短讨论'),
            dict(minute=80,duration=5,source='ear',project='低值',value='low',title='背景',summary='低值录音')])
        section=self.human_section(md)
        self.assertIn('**线下**',section)
        self.assertIn('**图表**',section)
        self.assertIn('短讨论',section)
        self.assertNotIn('低值',section)

    def test_human_empty_and_unclassified(self):
        for rows in ([], [dict(minute=0,duration=1)],
                     [dict(minute=0,duration=10,category='other')],
                     [dict(minute=0,duration=0,intervals=[],produced=['无活动'])]):
            self.assertNotIn('## 人做了什么',self.render_fixture(rows))
        section=self.human_section(self.render_fixture([
            dict(minute=0,duration=5,category='unclassified',summary='未知活动')]))
        self.assertIn('5.0 分',section)
        self.assertNotIn('未知活动',section)
        self.assertNotIn('回退理由',section)

    def test_human_budget_preserves_totals_and_summaries(self):
        rows=[dict(minute=i*40,duration=4,project=f'P{i}',summary='甲'*100,
                   learned=['学'*80,'读'*80],produced=['写'*80,'画'*80]) for i in range(8)]
        rows += [dict(minute=400+i*40,duration=5,project=f'P{i}',summary='乙'*100) for i in range(8)]
        md=self.render_fixture(rows)
        section=self.human_section(md)
        self.assertLessEqual(len(section),1200)
        self.assertEqual(section.count('- **'),8)
        self.assertEqual(section.count('9.0 分'),8)
        self.assertNotIn('  - 学到',section)
        self.assertNotIn('  - 产出',section)
        self.assertIn('乙',section)
        self.assertLessEqual(len(md),4000)
        self.assertIn('篇幅受限',md)
        # Whole-report pressure must not shrink the already bounded overview.
        longer=self.render_fixture(rows,warnings=['缺口'+str(i)+'长'*200 for i in range(6)])
        self.assertLessEqual(len(longer),4000)
        self.assertEqual(self.human_section(longer).split('- 其他：')[0].strip(),section)

    def test_render_merge_boundaries_and_summary(self):
        md=self.render_fixture([
            dict(minute=0,duration=4,summary='短段'),
            dict(minute=34,duration=6,summary='设计实验'),
            dict(minute=71,duration=4),
            dict(minute=76,duration=4,category='input'),
            dict(minute=81,duration=4,project='Other')])
        self.assertIn('05:00–05:04、05:34–05:40',md)
        timeline=md.split('## 时间线',1)[1]
        self.assertIn('设计实验',timeline); self.assertNotIn('短段',timeline)
        self.assertEqual(timeline.count('** '),4)
        self.assertIn('回退理由',md)

    def test_render_fragments_after_merge(self):
        md=self.render_fixture([
            dict(minute=0,duration=1,app='微信'),
            dict(minute=40,duration=1,app='微信'),
            dict(minute=80,duration=1,learned=['理解一个概念']),
            dict(minute=120,duration=1,produced=['写出提纲']),
            dict(minute=160,duration=2),dict(minute=162,duration=2)])
        self.assertIn('**零碎** 微信 2.0 分',md)
        self.assertIn('理解一个概念',md); self.assertIn('写出提纲',md)
        self.assertIn('07:40–07:44',md)
        self.assertNotIn('05:00–05:01',md)

    def test_render_attaches_latest_final_and_git(self):
        def output(minute,text,project='Octopus',**kw):
            return dict(time=self.start+minute*60,text=text,source='codex',session='agent',project=project,**kw)
        outputs=[output(1,'早期结论',final=True),output(2,'最终结论',final=True),
                 output(3,'还在运行',final=False),dict(output(90,'无法挂段','Unknown'),session='unrelated')]
        md=self.render_fixture([dict(minute=0,duration=10)],outputs)
        self.assertIn('最终结论（agent 自述，未核实）',md)
        self.assertIn('无法挂段',md)  # Agent work no longer needs a user segment.
        self.assertNotIn('agent 同时在做',md)
        for absent in ('早期结论','还在运行'): self.assertNotIn(absent,md)
        git=output(20,'提交结果'); git.update(source='git',verified=True)
        md=self.render_fixture([dict(minute=0,duration=10)],[git,output(5,'跨项目同时发生','Other')])
        self.assertIn('提交结果（git 提交，已核实存在）',md)
        self.assertIn('跨项目同时发生',md)
        long=output(1,'字'*100,final=True)
        md=self.render_fixture([dict(minute=0,duration=10)],[long])
        self.assertIn('字'*79+'…',md); self.assertNotIn('字'*80,md)

    def test_render_limits_and_removal_priority(self):
        rows=[dict(minute=i*40,duration=4,project=str(i),summary='设计'+ '长'*200,
                   learned=['学'*200]*3,produced=['写'*200]*3) for i in range(30)]
        outputs=[dict(time=self.start+60,text='结论'*100,source='codex',session='x',project='0')]
        md=self.render_fixture(rows+[dict(minute=1400,duration=1,app='碎片')],outputs)
        self.assertLessEqual(len(md),4000)
        self.assertNotIn('agent 同时在做',md); self.assertNotIn('**零碎**',md)
        self.assertIn('篇幅受限',md); self.assertIn('## 可以交给 agent 的杂务',md)

    def test_render_real_scale_limit_and_priority(self):
        # 45 segments now also include a protected project overview.
        rows=[dict(minute=i*6,duration=4,project=f'项目{i}',summary='检查实验结果并整理观察记录') for i in range(45)]
        outputs=[dict(time=self.start+(i*6+1)*60,text='结论'*40,source='codex',session=str(i),project=f'项目{i}') for i in range(45)]
        md=self.render_fixture(rows+[dict(minute=400,duration=1,app='碎片')],outputs)
        self.assertLessEqual(len(md),4000)
        self.assertGreater(len(md.encode('utf-8')),len(md))
        self.assertNotIn('agent 同时在做',md)
        self.assertIn('## 人做了什么',md)
        self.assertIn('项目0',md.split('## 时间线')[0])
        self.assertIn('**零碎** 碎片',md)
        self.assertEqual(md.split('## 时间线')[1].count('** '),46)
        # 60 rich segments overflow even after agent and fragments removal.
        rows=[dict(minute=i*6,duration=4,project=str(i),summary='写'*100,
                   learned=['学'*100,'读'*100],produced=['造'*100,'改'*100]) for i in range(60)]
        md=self.render_fixture(rows+[dict(minute=400,duration=1,app='碎片')],outputs,
                               warnings=['缺口'+str(i)+'说明'*200 for i in range(50)])
        self.assertLessEqual(len(md),4000)
        self.assertIn('## 附：数据缺口',md); self.assertIn('其余数据缺口见同日 JSON',md)
        self.assertNotIn('agent 同时在做',md); self.assertNotIn('**零碎**',md)
        self.assertIn('篇幅受限',md)

    def test_render_system_noise_and_ranked_fragments(self):
        rows=[dict(minute=i*40,duration=10,app=name,summary='系统噪声')
              for i,name in enumerate(self.c['sources']['system_apps'])]
        # Other computer activities have no concrete learning/output: even a
        # 20-minute segment belongs in fragments. Non-computer Other stays.
        rows += [dict(minute=400+i*40,duration=i+1,app=f'应用{i}',category='other',summary='窗口切换')
                 for i in range(8)]
        rows += [dict(minute=800,duration=20,app='浏览器',category='other',summary='长跨度切换'),
                 dict(minute=900,duration=4,category='other',source='claude',summary='对话记录')]
        md=self.render_fixture(rows)
        self.assertNotIn('系统噪声',md); self.assertNotIn('窗口切换',md); self.assertNotIn('长跨度切换',md)
        for name in self.c['sources']['system_apps']: self.assertNotIn(name,md)
        self.assertIn('对话记录',md)
        fragment=next(line for line in md.splitlines() if line.startswith('**零碎**'))
        self.assertEqual(fragment,'**零碎** 浏览器 20.0 分、应用7 8.0 分、应用6 7.0 分、应用5 6.0 分、应用4 5.0 分、应用3 4.0 分、其他 6.0 分')

    def test_render_conversation_primary_and_one_suggestion(self):
        md=self.render_fixture([
            dict(minute=40,duration=10,source='codex',category='chore',summary='检查运行',topic='诊断',suggestion='第一条'),
            dict(minute=41,duration=4,summary='阅读论文'),
            dict(minute=42,duration=4,summary='整理笔记'),
            dict(minute=43,duration=1,intervals=[],summary='无操作窗口',category='unclassified'),
            dict(minute=51,duration=5,source='codex',category='chore',summary='追查运行',topic='诊断',suggestion='重复主题'),
            dict(minute=57,duration=5,source='codex',category='chore',summary='修复服务',topic='修复',suggestion='第二主题'),
            dict(minute=0,duration=10,source='claude',summary='设计实验'),
            dict(minute=1,duration=4,summary='查看图表')])
        self.assertLess(md.index('05:00–05:10'),md.index('05:40–05:50、…、05:57–06:02（共 3 段）'))
        self.assertEqual(md.count('  - 同时：'),2)
        self.assertIn('同时：阅读论文；整理笔记',md)
        self.assertNotIn('05:41–05:45',md); self.assertNotIn('05:42–05:46',md)
        self.assertEqual(md.count('  - 可以交给 agent：'),1)
        self.assertIn('  - 可以交给 agent：第一条',md)
        self.assertNotIn('重复主题',md); self.assertNotIn('无操作窗口',md)
        self.assertIn('06:02',md)

    def test_system_events_follow_observed_foreground(self):
        self.history_fixture([
            (0,'mouse.click','Dock','unowned'),
            (5,'window.changed','WPS','Octopus slides'),
            (10,'keyboard.text_input','Simplified Chinese Input Method','候选'),
            (20,'window.changed','Terminal','Octopus shell'),
            (25,'keyboard.submit','TextInputSwitcher','候选'),
            (145,'keyboard.text_input','Simplified Chinese Input Method','stale'),
            (200,'mouse.click','Dock','stale')])
        rows,_=history.load(self.c['sources'],self.start,self.end,self.state,set())
        self.assertEqual({r['app'] for r in rows},{'WPS','Terminal'})
        wps=next(r for r in rows if r['app']=='WPS')
        terminal=next(r for r in rows if r['app']=='Terminal')
        self.assertEqual(wps['title'],'Octopus slides'); self.assertEqual(wps['counts']['typing'],1)
        self.assertEqual(terminal['counts']['submits'],1); self.assertEqual(terminal['counts']['typing'],0)
        data=pulse.collect(self.start,self.end,self.c)
        self.assertEqual(pulse.allocate(data['segments']),60)
        self.assertFalse(any(history.system_app(s,self.c['sources']) for s in data['segments']))

    def test_system_archive_without_order_is_dropped(self):
        directory,_=self.history_fixture([(5,'mouse.click','Dock','system')])
        raw=[history.event(json.loads(line)) for line in (directory/'events.jsonl').read_text().splitlines()]
        archive=self.state/'computer'; archive.mkdir()
        (archive/'old.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in history.aggregate(raw)))
        # Neither current raw system-only events nor old unordered system
        # minutes may reappear as an activity after filtering.
        self.assertEqual(history.load(self.c['sources'],self.start,self.end,self.state,set())[0],[])
        (directory/'events.jsonl').unlink()
        self.assertEqual(history.load(self.c['sources'],self.start,self.end,self.state,set())[0],[])

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


    def history_fixture(self, entries=None):
        entries=entries or [(0,'window.changed','WPS','Octopus slides'),(5,'keyboard.text_input','WPS','Octopus slides'),
                            (10,'keyboard.submit','WPS','Octopus slides'),(15,'keyboard.shortcut','WPS','Octopus slides'),
                            (20,'mouse.click','WPS','Octopus slides'),(65,'window.changed','Finder','files')]
        directory=Path(self.c['sources']['computer_events'])/'2026-11-10T20-00-00Z'; directory.mkdir(exist_ok=True)
        rows=[]
        for i,(offset,kind,app,title) in enumerate(entries):
            rows.append(dict(id=i,timestamp=datetime.fromtimestamp(self.start+offset,pulse.ZoneInfo('UTC')).isoformat().replace('+00:00','Z'),
                             kind=kind,app=dict(name=app,bundleIdentifier=app),window=dict(title=title,url='https://example.test/SECRET?q=SECRET'),
                             ax=dict(text='SECRET'),keyboard=dict(text='SECRET'),selection=dict(text='SECRET')))
        (directory/'events.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        path=Path(self.c['sources']['computer_summaries'])/'2026-11-10T20-00-00-test-10min-memory-summary.md'
        path.write_text('---\ntitle: Slides\ndescription: >\n  Editing slides\n  for meeting\napplications: [WPS]\n---\n## Memory summary\nIgnored\n## Recording summary\n### Work\nUpdated slides.\n## Other\nIgnored too\n')
        return directory,path

    def test_computer_parse_minutes_and_summary(self):
        self.history_fixture()
        warnings=set(); rows,summaries=history.load(self.c['sources'],self.start,self.end,self.state,warnings)
        self.assertEqual(len(rows),2); self.assertEqual([r['active'] for r in rows],[True,False])
        self.assertEqual(rows[0]['counts'],dict(clicks=1,typing=1,submits=1,shortcuts=1,selections=0))
        self.assertEqual(rows[0]['domain'],'example.test'); self.assertEqual(rows[0]['time'],self.start)
        self.assertNotIn('SECRET',json.dumps(rows)); self.assertNotIn('Ignored',json.dumps(summaries))
        self.assertEqual(summaries[0]['description'],'Editing slides for meeting')
        self.assertEqual(summaries[0]['recording'],'### Work\nUpdated slides.')
        self.assertEqual(datetime.fromtimestamp(rows[0]['time'],pulse.ZoneInfo('Asia/Tokyo')).hour,5)
        self.assertEqual(history.aggregate([history.event(dict(timestamp='2026-11-10T19:59:59Z',kind='selection.changed'))])[0]['time'],self.start-60)
        previous,_=history.load(self.c['sources'],self.start-86400,self.start,self.state,set()); self.assertEqual(previous,[])

    def test_computer_summary_period_and_replay(self):
        directory,path=self.history_fixture()
        six=path.with_name(path.name.replace('-10min-','-6h-')); six.write_text(path.read_text())
        rows,summaries=history.load(self.c['sources'],self.start,self.start+300,self.state,set())
        self.assertEqual(summaries,[])
        rows,summaries=history.load(self.c['sources'],self.start,self.end,self.state,set())
        self.assertEqual({s['period'] for s in summaries},{'6h','10min'})
        self.assertEqual(next(s for s in summaries if s['period']=='6h')['end'],self.start+21600)
        history.archive(self.c['sources'],self.start,self.end,self.state,'2026-11-11',set())
        (directory/'events.jsonl').unlink(); path.unlink(); six.unlink()
        rows,summaries=history.load(self.c['sources'],self.start,self.start+30,self.state,set())
        self.assertEqual(len(rows),1); self.assertEqual(summaries,[])

    def test_computer_alignment_gaps_and_held(self):
        self.history_fixture([(5,'mouse.click','Claude','Upload'),(65,'keyboard.text_input','WPS','Octopus slides'),
                              (1265,'mouse.click','WPS','Octopus slides'),(2525,'mouse.click','WPS','Octopus slides')])
        rows,summaries=history.load(self.c['sources'],self.start,self.end,self.state,set())
        segs=pulse.segments([self.event(0),self.event(10,'tool','')],self.start,self.start+3600,self.c)
        pulse.computer(segs,[],rows,summaries,self.start,self.end,self.c)
        claude=next(s for s in segs if s['source']=='claude')
        self.assertEqual(claude['computer_minutes'][0]['app'],'Claude')
        self.assertEqual(len(claude['held_activity']),3)
        new=[s for s in segs if s['source']=='computer']; self.assertEqual(len(new),2)
        self.assertEqual(new[0]['project'],'Octopus'); self.assertEqual(new[0]['computer_summaries'][0]['title'],'Slides')
        self.assertEqual(new[0]['user_seconds'],120)
        self.assertFalse(any(a<=self.start+65<b for a,b in claude['intervals']))

    def test_computer_ambiguous_and_unaligned(self):
        self.history_fixture([(5,'mouse.click','Claude','Claude'),(65,'mouse.click','Codex','Codex')])
        rows,summaries=history.load(self.c['sources'],self.start,self.end,self.state,set())
        segs=pulse.segments([self.event(0),self.event(10)],self.start,self.end,self.c)
        duplicate=copy.deepcopy(segs[0]); duplicate['session']='second'; segs.append(duplicate)
        pulse.computer(segs,[],rows,summaries,self.start,self.end,self.c)
        self.assertEqual(len([s for s in segs if s['source']=='computer']),2)
        self.assertFalse(any(s.get('computer_minutes') for s in segs if s['source']=='claude'))

    def test_computer_codex_and_chatgpt(self):
        rows=history.aggregate([dict(time=self.start+5,kind='mouse.click',app='Codex',bundle='codex',title='Task',domain=''),
                                dict(time=self.start+65,kind='keyboard.submit',app='Google Chrome',bundle='chrome',title='Concept',domain='chatgpt.com')])
        chat=dict(source='chatgpt',session='chat',title='Concept',project='Other',start=self.start+60,end=self.start+120,
                  intervals=[[self.start+60,self.start+120]],held_candidates=[],messages=[],confidence='低')
        segs=[chat]; activity=[dict(session='cx',project='Octopus',start=self.start,end=self.start+30)]
        pulse.computer(segs,activity,rows,[],self.start,self.end,self.c)
        self.assertEqual([s['source'] for s in segs],['codex','chatgpt']); self.assertEqual(pulse.allocate(segs),120)

    def test_computer_archive_restore_and_raw_priority(self):
        directory,path=self.history_fixture()
        archive=history.archive(self.c['sources'],self.start,self.end,self.state,'2026-11-11',set())
        original=archive.read_text(); self.assertNotIn('SECRET',original)
        raw,summary=history.load(self.c['sources'],self.start,self.end,self.state,set())
        (directory/'events.jsonl').unlink(); path.unlink()
        restored,restored_summary=history.load(self.c['sources'],self.start,self.end,self.state,set())
        self.assertEqual(restored,raw); self.assertEqual(restored_summary,summary)
        self.history_fixture([(5,'mouse.click','Terminal','Octopus')])
        fresh,_=history.load(self.c['sources'],self.start,self.end,self.state,set())
        self.assertEqual(fresh[0]['app'],'Terminal'); self.assertEqual(fresh[1]['app'],'Finder')
        history.archive(self.c['sources'],self.start,self.end,self.state,'2026-11-11',set())
        once=archive.read_text(); history.archive(self.c['sources'],self.start,self.end,self.state,'2026-11-11',set())
        self.assertEqual(archive.read_text(),once)

    def test_computer_missing_and_now(self):
        warnings=set(); self.assertEqual(history.load({},self.start,self.end,self.state,warnings),([],[]))
        self.assertTrue(any('Computer History' in w for w in warnings))
        current=datetime.now().timestamp()
        self.history_fixture([(current-self.start-10,'keyboard.text_input','Unity','Octopus')])
        with patch.object(pulse,'run',side_effect=OSError): value=pulse.now(self.c)
        self.assertEqual(value['app'],'Unity'); self.assertTrue(value['typing']); self.assertEqual(value['window_title'],'Octopus')
        self.assertEqual(value['domain'],'example.test'); self.assertIsNotNone(value['computer_at'])

    def test_computer_manual_chore_check(self):
        self.history_fixture([(i*60+5,'keyboard.shortcut','Terminal','Octopus build failure') for i in range(61)])
        data=pulse.collect(self.start,self.start+5400,self.c)
        with patch.dict(os.environ,PULSE_RUN=self.llm()):
            notices=pulse.check(data,self.start+5400,self.c,self.state,True)
        self.assertTrue(notices); self.assertEqual(data['check']['chore_active_seconds'],3660)

    def test_computer_mixed_estimate_and_measured(self):
        self.history_fixture([(605,'mouse.click','Claude','Upload')])
        rows,summaries=history.load(self.c['sources'],self.start,self.end,self.state,set())
        segs=pulse.segments([self.event(0),self.event(20)],self.start,self.end,self.c)
        pulse.computer(segs,[],rows,summaries,self.start,self.end,self.c)
        self.assertEqual(len(segs),1)
        self.assertEqual(pulse.allocate(segs),1200)

    def test_computer_same_minute_no_double_count(self):
        self.history_fixture([(5,'mouse.click','WPS','slides'),(20,'mouse.click','Terminal','shell')])
        data=pulse.collect(self.start,self.end,self.c)
        self.assertEqual(pulse.allocate(data['segments']),60)

    def test_now(self):
        idle=subprocess.CompletedProcess([],0,'"HIDIdleTime" = 601000000000','')
        app=subprocess.CompletedProcess([],0,'Terminal\n','')
        with patch.object(pulse,'run',side_effect=[idle,app]):
            value=pulse.now(self.c)
        self.assertEqual(value['status'],'away'); self.assertEqual(value['app'],'Terminal'); self.assertIsInstance(value['quiet'],bool)
        with patch.object(pulse,'run',side_effect=OSError): self.assertEqual(pulse.now(self.c)['status'],'unknown')

if __name__=='__main__': unittest.main()
