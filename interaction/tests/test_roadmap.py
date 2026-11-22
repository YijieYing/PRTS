#!/usr/bin/env python3
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from interaction.lib import roadmap as r
from interaction.lib.groups import groups
from interaction.lib import github_poll
ROOT=Path(__file__).resolve().parents[2]

class Roadmap(unittest.TestCase):
    def cmd(self,*args,ok=True):
        result=subprocess.run(list(map(str,args)),cwd=self.repo,stdin=subprocess.DEVNULL,capture_output=True,text=True)
        if ok: self.assertEqual(result.returncode,0,result.stderr)
        return result
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name);self.file=self.repo/'roadmap.md';self.state=self.repo/'state'
        self.config=self.repo/'projects.toml'
        self.config.write_text(f'[[project]]\nname="Test"\npath="{self.repo}"\ngroup="G"\nroadmap="{self.file}"\nmeetings=["Thu 15:00-17:00"]\n')
        self.env=patch.dict(os.environ,PRTS_PROJECTS=str(self.config),PRTS_INTERACTION_STATE=str(self.state),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1')
        self.env.start();self.addCleanup(self.env.stop)
        self.file.write_text('| DDL | 事项 | 编号 | 完成证据 | 状态 | 开始 |\n|---|---|---|---|---|---|\n| 2020-01-01 | **one** | X1 | old | 💤 | 2019-01-01 |\n| 2030-01-01 | two | X2 | | 🔍 | |\n| 2018-01-01 | done | X3 | proof | ❌ | |\n')
        self.cmd('git','init');self.cmd('git','config','user.name','Fixture');self.cmd('git','config','user.email','fixture@example.test')
        self.cmd('git','add','roadmap.md');self.cmd('git','commit','-m','initial')
    def test_parse_groups(self):
        value=r.read(r.project('Test'))
        self.assertEqual(value['next_ddl'],'2020-01-01');self.assertEqual(len(value['items']),3)
        self.assertEqual(value['items'][0]['title'],'one');self.assertTrue(value['items'][2]['done'])
        with patch('interaction.lib.groups.scan',return_value=[]):
            gs=groups({},[],[],dt.datetime.now(dt.timezone.utc).isoformat())
        self.assertEqual(gs[0]['next_ddl'],'2020-01-01')
        self.assertEqual(gs[0]['projects'][0]['meetings'],[dict(weekday=4,start='15:00',end='17:00')])
        self.file.write_text('| # | 状态 | 事项 | 要点 |\n|---|---|---|---|\n| R1 | 💤 | old | detail |\n| M1 | ✅ | console | done |\n- [ ] task\n')
        value=r.read(dict(roadmap=str(self.file),roadmap_prefix='R'))
        self.assertEqual([i['id'] for i in value['items']],['R1']);self.assertIsNone(value['items'][0]['ddl'])
        self.assertIsNone(value['next_ddl'])
    def test_group_minimum_and_manual_history(self):
        second=self.repo/'second.md'
        second.write_text('| 编号 | 状态 | 事项 | DDL |\n|---|---|---|---|\n| Y1 | 💤 | earlier | 2010-01-01 |\n')
        with self.config.open('a') as f:
            f.write(f'[[project]]\nname="Second"\npath="/second"\ngroup="G"\nroadmap="{second}"\n')
        with patch('interaction.lib.groups.scan',return_value=[]):
            gs=groups({},[],[],dt.datetime.now(dt.timezone.utc).isoformat())
        self.assertEqual(gs[0]['next_ddl'],'2010-01-01')
        r.mark('Test','X1','✅','manual')
        self.assertEqual([i['id'] for i in r.completed(r.project('Test'),'2000-01-01')],['X1'])

    def test_commit_failure_restores_row(self):
        hook=self.repo/'.git/hooks/pre-commit';hook.write_text('#!/bin/sh\nexit 1\n');hook.chmod(0o755)
        before=self.file.read_bytes()
        with self.assertRaises(subprocess.CalledProcessError): r.mark('Test','X1','✅','failed',auto='accepted')
        self.assertEqual(self.file.read_bytes(),before);self.assertEqual(r.records(),[])
        hook.unlink();self.assertTrue(r.mark('Test','X1','✅','retry',auto='accepted'))

    def test_mark_scoped_and_errors(self):
        before=self.file.read_text();other=self.repo/'other';other.write_text('staged')
        self.cmd('git','add','other')
        r.mark('Test','X1','✅','task | evidence')
        expected=before.replace('| old | 💤 |','| task \\| evidence | ✅ |')
        self.assertEqual(self.file.read_text(),expected)
        self.assertEqual(self.cmd('git','show','--format=','--name-only','HEAD').stdout.strip(),'roadmap.md')
        self.assertIn('other',self.cmd('git','diff','--cached','--name-only').stdout)
        for ident,status in [('X99','✅'),('X1','bad')]:
            self.assertNotEqual(self.cmd(ROOT/'interaction/bin/roadmap','mark','Test',ident,status,ok=False).returncode,0)
    def test_plain_folder_and_kind(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'table.md'
            f.write_text('| 编号 | 状态 | DDL | 类型 | 事项 | 完成证据 |\n|---|---|---|---|---|---|\n| S01 | 💤 | 2030-01-01 | 检查 | look | |\n')
            self.config.write_text(f'[[project]]\nname="Test"\npath="{d}"\nroadmap="{f}"\nroadmap_prefix="S"\n')
            self.assertEqual(r.read(r.project('Test'))['items'][0]['kind'],'检查')
            r.mark('Test','S01','✅','done')
            self.assertIn('| S01 | ✅ |',f.read_text())
    def test_legacy_evidence_and_done_guard(self):
        self.file.write_text('| # | 状态 | 事项 | 要点 |\n|---|---|---|---|\n| X1 | 💤 | one | notes |\n')
        r.mark('Test','X1','✅','proof')
        self.assertIn('| one | notes；proof |',self.file.read_text())
        self.assertFalse(r.mark('Test','X1','✅','replace',auto='accepted'))
    def test_dispatch_review(self):
        prompt=self.repo/'prompt';prompt.write_text('fixture')
        self.assertNotEqual(self.cmd(ROOT/'interaction/bin/dispatch','task',self.repo,prompt,'--roadmap','Test:X99','--dry',ok=False).returncode,0)
        self.cmd(ROOT/'interaction/bin/dispatch','task',self.repo,prompt,'--roadmap','Test:X1','--dry')
        # Execute the actual launcher with a fake executable, without a model call.
        stub=self.repo/'codex';stub.write_text('#!/bin/sh\necho fixture\n');stub.chmod(0o755)
        self.cmd(ROOT/'interaction/lib/codex','--cwd',self.repo,'--prompt',prompt,'--name','task','--log',self.repo/'run.log','--roadmap','Test:X1','--binary',stub,'--start','exec')
        row=json.loads((self.state/'registry.jsonl').read_text().splitlines()[0]);self.assertEqual(row['roadmap'],'Test:X1')
        self.cmd(ROOT/'interaction/lib/codex','--cwd',self.repo,'--prompt',prompt,'--name','task','--log',self.repo/'resume.log','--target','fixture-thread','--binary',stub,'--start','resume')
        starts=[json.loads(s) for s in (self.state/'registry.jsonl').read_text().splitlines() if json.loads(s)['event']=='start']
        self.assertEqual(starts[-1]['roadmap'],'Test:X1')
        self.cmd(ROOT/'interaction/bin/review','task');head=self.cmd('git','rev-parse','HEAD').stdout
        self.cmd(ROOT/'interaction/bin/review','task');self.assertEqual(self.cmd('git','rev-parse','HEAD').stdout,head)
        self.assertEqual(r.read(r.project('Test'))['items'][0]['evidence'],'task')
        self.assertEqual(len(r.records()),1)
    def test_poll_open_merged(self):
        detail=dict(title='X1 and Y1 but not prefixX2',body='',headRefName='feature',state='OPEN',url='https://example.test/pr/1',comments=[],reviews=[],statusCheckRollup=[],updatedAt='2026-11-17')
        def run(args,**kwargs):
            if args[0]=='gh' and args[1:3]==['api','user']: return '{"login":"me"}'
            if args[1:3]==['pr','list']: return json.dumps([dict(detail,number=1)])
            if args[1:3]==['pr','view']: return json.dumps(detail)
            if args[1]=='api': return '[[]]'
            raise AssertionError(args)
        before=self.file.read_bytes()
        with patch.dict(github_poll.REPO_PROJECTS,{'repo':'Test'}),patch.object(github_poll,'run',side_effect=run):
            github_poll.poll('repo',self.state);github_poll.poll('repo',self.state)
            self.assertEqual(self.file.read_bytes(),before);self.assertEqual(len(r.records()),1)
            self.assertEqual(r.read(r.project('Test'))['items'][0]['auto']['state'],'pr_open')
            detail['state']='MERGED';github_poll.poll('repo',self.state);head=self.cmd('git','rev-parse','HEAD').stdout
            github_poll.poll('repo',self.state);self.assertEqual(self.cmd('git','rev-parse','HEAD').stdout,head)
        self.assertEqual(len(r.records()),2);self.assertEqual(r.read(r.project('Test'))['items'][1]['status'],'🔍')

if __name__=='__main__': unittest.main(verbosity=2)
