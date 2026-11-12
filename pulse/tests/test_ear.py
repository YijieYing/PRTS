"""Synthetic legacy payloads only; no personal files or services used."""
from contextlib import redirect_stdout, closing
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
import ear
import pulse


class EarTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.db=self.root/'ear.sqlite3'; self.state=self.root/'state'; self.state.mkdir()
        self.c=pulse.config(); self.c['ear']=dict(database=str(self.db),start_from='2026-11-12T12:00:00+09:00',min_chars=300)
        self.base=ear.stamp('2026-11-12T12:00:00+09:00')
        with closing(sqlite3.connect(self.db)) as db, db:
            for table,cols in dict(captures='capture_id,started_at',pipeline_runs='pipeline_run_id,capture_id,status,created_at',
                                   audio_chunks='audio_chunk_id,capture_id',speech_segments='audio_chunk_id',
                                   speaker_resolutions='diarization_scope_id',speaker_identities='person_id',
                                   audio_events='audio_chunk_id',sensor_observations='capture_id').items():
                db.execute(f'CREATE TABLE {table} ({cols},payload TEXT)')
        self.answer=dict(kind='monologue',user_speaking=.9,value='high',title='设计离线学习工具',summary=['设计输入。','确定输出。','安排后续验证。'],
                         corrections=[{'from':'错字','to':'正字'}],learned=[],produced=['提出设计'],todos=['学习数学'],
                         agent_work=[{'project':'fixture','what':'实现采集'}],category='output',continues=False)
        self.run=self.stub('run',"""prompt=Path(sys.argv[1]).read_text()
assert '判断标准是**用户的脑子在做什么**' in prompt
assert '只总结用户自己的想法和收获，不转述别人的原话' in prompt
assert '用户本人是主要说话人' in prompt
assert '反例一：别人介绍职业教育方案' in prompt
assert '反例二：从 Scala 课程聊到 C++' in prompt
assert '用户在听、在学的对话、会议、课为 normal' in prompt
assert '--output-schema' in sys.argv
with Path(os.environ['CALLS']).open('a') as f: f.write('run\\n')
print(Path(os.environ['ANSWER']).read_text())
""")
        self.notify=self.stub('notify',"with Path(os.environ['CALLS']).open('a') as f: f.write('notify\\n')\n")
        self.answer_file=self.root/'answer.json'; self.answer_file.write_text(json.dumps(self.answer))
        self.env=patch.dict(os.environ,{'PULSE_RUN':self.run,'PULSE_NOTIFY':self.notify,'CALLS':str(self.root/'calls'),
                                      'ANSWER':str(self.answer_file),'PULSE_STATE':str(self.state),'PULSE_EAR_DB':str(self.db)})
        self.env.start()
        self.vocab=patch.object(ear,'vocabulary',return_value='测试项目'); self.vocab.start()
    def tearDown(self):
        self.vocab.stop(); self.env.stop(); self.tmp.cleanup()
    def stub(self,name,code):
        p=self.root/name
        p.write_text('#!/usr/bin/env python3\nimport os,sys,json\nfrom pathlib import Path\nassert sys.stdin.read()==""\n'+code)
        p.chmod(0o755); return str(p)
    def insert(self,table,row):
        with closing(sqlite3.connect(self.db)) as db, db:
            cols=[r[1] for r in db.execute('pragma table_info('+table+')')]
            db.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in cols)+')',
                       [json.dumps(row) if col=='payload' else row.get(col) for col in cols])
    def capture(self,cid='one',offset=0,text='设计一个学习工具。'*60,status='succeeded'):
        def iso(t): return datetime.fromtimestamp(t,timezone.utc).isoformat()
        start=self.base+offset
        self.insert('captures',dict(capture_id=cid,started_at=iso(start),ended_at=iso(start+1200)))
        self.insert('pipeline_runs',dict(pipeline_run_id='run-'+cid,capture_id=cid,status=status,created_at=iso(start+1200)))
        self.insert('audio_chunks',dict(audio_chunk_id=cid,capture_id=cid,started_at=iso(start),ended_at=iso(start+1200)))
        self.insert('speech_segments',dict(audio_chunk_id=cid,start_offset_ms=3000,end_offset_ms=10000,text=text,diarization_scope_id=cid,local_speaker_id='S01'))
        self.insert('audio_events',dict(audio_chunk_id=cid,start_offset_ms=0,end_offset_ms=120000,label='风声',confidence=.8))
        self.insert('sensor_observations',dict(capture_id=cid,observed_at=iso(start),location={'latitude':1,'longitude':2}))
    def sync(self,no_notify=False):
        with redirect_stdout(io.StringIO()): ear.sync(self.c,self.state,no_notify)
    def calls(self): return (self.root/'calls').read_text().splitlines() if (self.root/'calls').exists() else []
    def test_readonly_and_render(self):
        self.capture()
        self.insert('speaker_identities',dict(person_id='p',display_name='测试者'))
        self.insert('speaker_resolutions',dict(diarization_scope_id='one',local_speaker_id='S01',person_id='p'))
        with ear.database(self.db) as db:
            with self.assertRaises(sqlite3.OperationalError): db.execute('DELETE FROM captures')
            md,chars=ear.evidence(db,ear.captures(db,self.c['ear']['start_from'])[0])
        self.assertIn('[12:00:03] 测试者:',md); self.assertIn('[12:01] 风声',md)
        self.assertIn('latitude',md); self.assertGreater(chars,300)
        with self.assertRaises(sqlite3.OperationalError):
            with ear.database(self.root/'missing'): pass
        self.assertFalse((self.root/'missing').exists())
    def test_cursor_threshold_start_latest_and_idempotence(self):
        self.capture('old',-3600); self.capture('short',text='几句话'); self.capture('pending',status='running')
        self.sync(); self.sync()
        self.assertEqual(self.calls(),[])
        self.assertEqual(ear.read(self.state/'ear/cursor.json',[]),['short'])
        self.assertEqual(ear.read(self.state/'ear/results/short.json',{})['value'],'low')
        self.insert('pipeline_runs',dict(pipeline_run_id='new',capture_id='pending',status='succeeded',created_at='2026-11-12T05:00:00Z'))
        self.sync(True); self.assertEqual(self.calls(),['run'])
    def test_high_continuation_and_notify_once(self):
        self.capture(); self.sync()
        self.answer['continues']=True; self.answer_file.write_text(json.dumps(self.answer))
        self.capture('two',1200); self.sync(); self.sync()
        self.assertEqual(self.calls(),['run','notify','run'])
        rows=ear.inbox(self.state/'ear'); self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['group'],rows[1]['group'])
    def test_no_notify_and_retry(self):
        self.capture()
        with patch.dict(os.environ,{'PULSE_RUN':self.stub('bad','sys.exit(1)')}):
            with self.assertRaises(RuntimeError): self.sync()
        self.assertFalse((self.state/'ear/cursor.json').exists())
        self.sync(True); self.sync()
        self.assertEqual(self.calls(),['run']); self.assertEqual(len(ear.inbox(self.state/'ear')),1)
    def test_notification_retry_reuses_classification(self):
        self.capture()
        with patch.dict(os.environ,{'PULSE_NOTIFY':self.stub('bad','sys.exit(1)')}):
            with self.assertRaises(RuntimeError): self.sync()
        self.sync()
        self.assertEqual(self.calls(),['run','notify']); self.assertEqual(len(ear.inbox(self.state/'ear')),1)
    def test_wait_blocks_groups_and_hands_once(self):
        command=[sys.executable,str(pulse.MODULE/'bin/pulse'),'ear','wait','--poll','0.02']
        proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            time.sleep(.15); self.assertIsNone(proc.poll())
            self.capture(); self.sync(True)
            out,err=proc.communicate(timeout=5)
            self.assertEqual(proc.returncode,0,err); self.assertEqual(json.loads(out)['captures'],['one'])
        finally:
            if proc.poll() is None: proc.kill(); proc.communicate()
        self.capture('two',1200); self.sync(True)
        self.answer['continues']=True; self.answer_file.write_text(json.dumps(self.answer))
        self.capture('three',2400); self.sync(True)
        p=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5)
        self.assertEqual(json.loads(p.stdout)['captures'],['two','three'])
        p=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            time.sleep(.15); self.assertIsNone(p.poll())
        finally: p.kill(); p.communicate()
    def test_concurrent_sync_lock(self):
        self.capture()
        cfg=self.root/'config.json'; cfg.write_text(json.dumps(self.c))
        code=("import sys,json; from pathlib import Path; sys.path.insert(0,sys.argv[1]); import ear; "
              "ear.vocabulary=lambda:'fixture'; ear.sync(json.loads(Path(sys.argv[2]).read_text()),Path(sys.argv[3]))")
        command=[sys.executable,'-c',code,str(pulse.MODULE/'lib'),str(cfg),str(self.state)]
        procs=[subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
        try:
            for proc in procs:
                out,err=proc.communicate(timeout=10)
                self.assertEqual(proc.returncode,0,err)
            self.assertEqual(self.calls(),['run','notify'])
            self.assertEqual(len(ear.inbox(self.state/'ear')),1)
        finally:
            for proc in procs:
                if proc.poll() is None: proc.kill(); proc.communicate()
    def test_overlapping_continuation(self):
        self.capture(); self.sync(True)
        self.answer['continues']=True; self.answer_file.write_text(json.dumps(self.answer))
        self.capture('overlap',600); self.sync(True)
        rows=ear.inbox(self.state/'ear')
        self.assertEqual(rows[0]['group'],rows[1]['group'])
    def test_day_never_reclassifies_ear(self):
        self.capture(); self.sync(True)
        data=dict(segments=[],outputs=[],warnings=[])
        def classify(data,state): self.assertEqual(data['segments'],[])
        with patch.object(pulse,'config',return_value=self.c), patch.object(pulse,'collect',return_value=data), \
             patch.object(pulse,'classify',side_effect=classify) as model, \
             patch.object(sys,'argv',['pulse','day','2026-11-12']), redirect_stdout(io.StringIO()):
            self.assertEqual(pulse.main(),0)
        model.assert_called_once()
        self.assertEqual(data['segments'][0]['source'],'ear')
        self.assertEqual(data['segments'][0]['category'],'output')

    def test_retriage_since_no_side_effects_and_failure(self):
        self.capture(); self.capture('two',1200); self.sync()
        state=self.state/'ear'
        saved={name:(state/name).read_bytes() for name in ('inbox.jsonl','notifications.json','cursor.json')}
        before=ear.read(state/'results/one.json',{})
        self.capture('new',2400)  # Retriage does not consume new captures.
        self.answer.update(value='normal',category='input',title='学习语言区别')
        self.answer_file.write_text(json.dumps(self.answer))
        since=ear.local(self.base+1200).isoformat()
        with redirect_stdout(io.StringIO()): ear.sync(self.c,self.state,retriage=True,since=since)
        self.assertEqual(ear.read(state/'results/one.json',{}),before)
        self.assertEqual(ear.read(state/'results/two.json',{})['value'],'normal')
        self.assertFalse((state/'results/new.json').exists())
        for name,data in saved.items(): self.assertEqual((state/name).read_bytes(),data)
        normal=(state/'results/two.json').read_bytes()
        with patch.dict(os.environ,{'PULSE_RUN':self.stub('fail','sys.exit(1)')}):
            with self.assertRaises(RuntimeError): ear.sync(self.c,self.state,retriage=True,since=since)
        self.assertEqual((state/'results/two.json').read_bytes(),normal)
        self.assertEqual(self.calls().count('notify'),2)
        out=io.StringIO()
        with redirect_stdout(out): ear.wait(self.state,.01)
        self.assertEqual(json.loads(out.getvalue())['captures'],['one'])
        self.assertEqual(ear.day(self.state,self.base,self.base+3600)[1]['category'],'input')
        # Remaining high after another retriage also never repeats a notification.
        self.answer.update(value='high'); self.answer_file.write_text(json.dumps(self.answer))
        with redirect_stdout(io.StringIO()): ear.sync(self.c,self.state,retriage=True,since=since)
        self.assertEqual(self.calls().count('notify'),2)
        for kwargs in ({'retriage':True},{'since':since},{'retriage':True,'since':'2026-11-12'}):
            with self.assertRaises(ValueError): ear.sync(self.c,self.state,**kwargs)

    def test_push_daily_cap_and_midnight(self):
        self.c['ear']['max_push_per_day']=4
        with patch.object(ear.time,'time',return_value=ear.stamp('2026-11-13T23:59:00+09:00')):
            for i in range(6): self.capture(str(i),i*1200)
            self.sync(); self.sync()
        self.assertEqual(self.calls().count('notify'),4)
        self.assertEqual(len(ear.inbox(self.state/'ear')),6)
        self.capture('next',7200)
        with patch.object(ear.time,'time',return_value=ear.stamp('2026-11-14T00:00:00+09:00')): self.sync()
        self.assertEqual(self.calls().count('notify'),5)
        self.c['ear']['max_push_per_day']=0
        self.capture('disabled',8400); self.sync()
        self.assertEqual(self.calls().count('notify'),5)
        self.assertEqual(len(ear.inbox(self.state/'ear')),8)

    def test_suppressed_does_not_consume_budget_and_legacy_notices(self):
        self.c['ear']['max_push_per_day']=1
        self.capture(); self.sync(True)
        self.capture('two',1200); self.sync()
        self.assertEqual(self.calls().count('notify'),1)
        state=self.state/'ear'
        ear.save(state/'notifications.json',{'legacy':'sent','one':'suppressed','two':'sent'})
        self.capture('three',2400); self.sync()
        self.assertEqual(self.calls().count('notify'),1)
        self.assertEqual(ear.read(state/'notifications.json',{})['three']['status'],'limited')

    def test_wait_merges_time_gap_and_ack_cli(self):
        for cid,offset in [('one',0),('two',3600),('three',7201)]: self.capture(cid,offset)
        self.sync(True)  # All independent groups; exact 40 minute gap merges.
        out=io.StringIO()
        with redirect_stdout(out): ear.wait(self.state,.01)
        value=json.loads(out.getvalue())
        self.assertEqual(value['captures'],['one','two'])
        self.assertEqual(value['summary'],self.answer['summary'][:2]*2)
        self.assertEqual(value['start'],ear.local(self.base).isoformat())
        self.assertEqual(value['end'],ear.local(self.base+4800).isoformat())
        command=[sys.executable,str(pulse.MODULE/'bin/pulse'),'ear','ack','--before']
        boundary=ear.local(self.base+7201).isoformat()
        result=subprocess.run(command+[boundary],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(result.stdout,'')
        self.assertNotIn('three',ear.read(self.state/'ear/handed.json',[]))
        for _ in range(2):
            result=subprocess.run(command+[ear.local(self.base+7202).isoformat()],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(result.stdout,'')
        self.assertEqual(ear.read(self.state/'ear/handed.json',[]),['one','two','three'])
        with self.assertRaises(ValueError): ear.ack(self.state,'2026-11-13')

    def test_wait_configurable_gap(self):
        self.capture(); self.capture('two',1800); self.sync(True)
        out=io.StringIO()
        with redirect_stdout(out): ear.wait(self.state,.01,gap_minutes=5)
        self.assertEqual(json.loads(out.getvalue())['captures'],['one'])

    def test_invalid_schema(self):
        for patch_value in ({'continues':'yes'},{'user_speaking':2},{'summary':['one']},{'agent_work':[{}]}):
            with self.assertRaises(ValueError): ear.validate(self.answer | patch_value)
    def test_day_overlap_low_and_agent_section(self):
        self.capture(); self.sync(True)
        rows=ear.day(self.state,self.base,self.base+3600)
        desktop=dict(source='computer',session='desktop',title='课件',project='课堂',start=self.base,end=self.base+700,
                     intervals=[[self.base,self.base+700]],held_candidates=[],messages=[],category='input',summary='学习一个概念',learned=['概念'],produced=[])
        output=dict(source='codex',session='agent',project='工程',time=self.base,text='完成脚本',final=True)
        data=dict(segments=[desktop]+rows,outputs=[output],warnings=[])
        md=pulse.render(data,'2026-11-12',self.c)
        self.assertIn('录音：设计离线学习工具',md)
        self.assertNotIn('· 输出 ·',md)
        self.assertNotIn('agent 同时在做',md)
        self.assertNotIn('完成脚本',md.split('## agent 做了什么')[0])
        desktop['end']=self.base+600; desktop['intervals']=[[self.base,self.base+600]]
        md=pulse.render(data,'2026-11-12',self.c)
        self.assertNotIn('录音：',md); self.assertIn('· 输出 ·',md)
        rows[0]['value']='low'
        md=pulse.render(data,'2026-11-12',self.c)
        self.assertNotIn('设计离线学习工具',md); self.assertIn('录音（低价值）',md)
    def test_overlap_survives_desktop_fragment_and_absorption(self):
        self.capture(); self.sync(True)
        rows=ear.day(self.state,self.base,self.base+3600)
        desktop=dict(source='computer',session='desk',title='桌面',project='桌面',start=self.base,end=self.base+1200,
                     intervals=[[self.base,self.base+1200]],held_candidates=[],messages=[],category='other',summary='浏览',learned=[],produced=[])
        data=dict(segments=[desktop]+rows,outputs=[],warnings=[])
        self.assertIn('录音：设计离线学习工具',pulse.render(data,'2026-11-12',self.c))
        dialogue=dict(desktop,source='claude',session='chat',project='对话',category='input',end=self.base+120,
                      intervals=[[self.base,self.base+120]],learned=['理解概念'])
        data['segments'].append(dialogue)
        md=pulse.render(data,'2026-11-12',self.c)
        self.assertIn('录音：设计离线学习工具',md)
        self.assertNotIn('· 输出 ·',md)

    def test_no_database_day_uses_saved_results(self):
        self.capture(); self.sync(True); self.db.unlink()
        self.assertEqual(len(ear.day(self.state,self.base,self.base+3600)),1)
        self.assertEqual(ear.day(self.root/'empty',self.base,self.base+3600),[])

if __name__=='__main__': unittest.main()
