#!/usr/bin/env python3
"""Isolated R18 CLI contract, routing, concurrency and dispatch completion fixtures."""
import concurrent.futures
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from interaction.lib.schema import validate, object_schema
UUID = '12345678-1234-1234-1234-123456789abc'

class Threads(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT/'interaction', self.root/'interaction', ignore=shutil.ignore_patterns('state','__pycache__'))
        self.i = self.root/'interaction'; self.state = self.root/'state'
        self.projects = self.root/'projects.toml'
        self.projects.write_text('[[project]]\nname="Canonical"\npath="/repo"\naliases=["alias"]\n')
        self.bin = self.root/'bin'; self.bin.mkdir()
        stub = self.bin/'codex'
        stub.write_text("""#!/usr/bin/env python3
import os,sys,json
assert sys.stdin.read() == ''
with open(os.environ['CALLS'],'a') as f: f.write(json.dumps(sys.argv[1:])+'\n')
if sys.argv[1] == 'queue': sys.exit(int(os.environ.get('QUEUE_RC','0')))
print('session id: 12345678-1234-1234-1234-123456789abc')
if '-o' in sys.argv:
    open(sys.argv[sys.argv.index('-o')+1],'w').write('Created https://github.com/owner/repo/pull/7')
""")
        # A literal newline must be escaped in generated Python.
        stub.write_text(stub.read_text().replace("+'\n')", "+'\\n')"))
        stub.chmod(0o755)
        self.env = dict(os.environ, PRTS_INTERACTION_STATE=str(self.state),
                        PRTS_PROJECTS=str(self.projects), PATH=str(self.bin)+':'+os.environ['PATH'],
                        CALLS=str(self.root/'calls'))
    def call(self, cmd, *args, ok=True):
        result = subprocess.run([str(self.i/cmd), *args], env=self.env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=15)
        if ok: self.assertEqual(result.returncode, 0, result.stderr)
        return result
    def sub(self, *args):
        return json.loads(self.call('bin/subscribe','add', *args).stdout)
    def emit(self, ident='event', **fields):
        args = ['add','L1','fixture','hello','--id',ident]
        for k,v in fields.items(): args += ['--'+k, v]
        return self.call('bin/event', *args)
    def rows(self):
        return [json.loads(l) for l in (self.state/'events/queue.jsonl').read_text().splitlines()]
    def test_subscription_lifecycle_concurrency(self):
        s = self.sub('--project','alias','--to','codex:'+UUID)
        self.assertEqual(s['project'],'Canonical')
        self.call('bin/subscribe','pause',s['id'])
        self.emit(project='alias')
        self.assertEqual(self.rows()[-1]['status'],'new')
        self.assertFalse((self.root/'calls').exists())
        self.call('bin/subscribe','resume',s['id'])
        self.emit('next', thread='project:alias')
        self.assertEqual(self.rows()[-1]['status'],'routed')
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            result = list(pool.map(lambda _: self.sub('--project','alias','--to','codex:'+UUID), range(12)))
        self.assertEqual({r['id'] for r in result},{s['id']})
        self.assertEqual(len(self.call('bin/subscribe','list').stdout.splitlines()),1)
        self.call('bin/subscribe','remove',s['id'])
        self.assertEqual(self.call('bin/subscribe','list').stdout,'')
    def test_routes_dedupe_and_failure(self):
        self.sub('--thread','ear:first','--to','codex:'+UUID)
        self.emit(thread='ear:first',project='alias',kind='ear_agent_work')
        self.emit(thread='ear:first',project='alias')
        self.assertEqual(len((self.root/'calls').read_text().splitlines()),1)
        self.assertEqual(self.rows()[-1]['project'],'Canonical')
        self.assertEqual(self.rows()[0]['kind'],'routed')
        self.env['QUEUE_RC']='7'
        self.emit('failed',thread='ear:first')
        self.assertEqual(self.rows()[-1]['kind'],'route_pending')
        self.assertEqual(self.rows()[-1]['level'],'L1')
        self.emit('failed',thread='ear:first')
        self.assertEqual(len((self.root/'calls').read_text().splitlines()),2)
    def test_interrupted_attempt_is_pending_without_resending(self):
        sub = self.sub('--project','alias','--to','codex:'+UUID)
        (self.state/'routes.jsonl').write_text(json.dumps(dict(event_id='event',subscription=sub['id'],
            to=sub['to'],t='2026-11-15T00:00:00Z',status='attempting'))+'\n')
        self.emit(project='alias')
        self.assertFalse((self.root/'calls').exists())
        self.assertEqual(self.rows()[-1]['kind'],'route_pending')

    def test_claude(self):
        self.sub('--project','alias','--to','claude:local_fixture')
        self.emit(project='alias'); self.emit(project='alias')
        self.assertEqual(len((self.state/'outbox/local_fixture.jsonl').read_text().splitlines()),1)
        self.assertEqual(self.rows()[-1]['kind'],'route_pending')
    def test_order(self):
        env = patch.dict(os.environ,self.env); env.start(); self.addCleanup(env.stop)
        classify = runpy.run_path(str(self.i/'bin/event'))['classify']
        self.sub('--project','alias','--to','codex:'+UUID)
        self.assertEqual(classify(dict(kind='host_down',project='Canonical'))[0],'L2')
        self.assertEqual(classify(dict(kind='state',project='Canonical'))[0],'routed')
        self.assertEqual(classify(dict(kind='state'))[0],'L0')
        self.assertEqual(classify(dict(kind='unknown',level='L1'))[0],'L1')
        (self.i/'config/filter.toml').write_text('allowed_sources=["fixture"]')
        from interaction.lib import run_model
        with patch.object(run_model, 'classify_with_model', return_value=dict(level='L0', project=None, reason='noise')) as model:
            self.assertEqual(classify(dict(kind='unknown',project='Canonical',source='fixture'))[0], 'routed')
            self.assertEqual(classify(dict(kind='state',source='fixture'))[0], 'L0')
            model.assert_not_called()
            event = dict(kind='unknown',source='fixture')
            self.assertEqual(classify(event), ('L0','noise'))
            self.assertIsNone(event['project'])
            model.assert_called_once()

    def test_status_review_schema_and_auto(self):
        self.assertEqual(json.loads(self.call('bin/status','threads','--json').stdout)['threads'],[])
        self.state.mkdir(exist_ok=True)
        start = dict(name='task',event='start',t='2026-11-15T00:00:00+00:00',cwd='/repo',
                     worktree=dict(repo='/repo',path='/worktree'))
        (self.state/'registry.jsonl').write_text(json.dumps(start)+'\n')
        task = self.state/'tasks/task'; task.mkdir(parents=True)
        log = task/'run.log'; output=task/'last.md'; prompt=task/'prompt.md'; prompt.write_text('fixture')
        self.call('lib/codex','--cwd',str(self.root),'--prompt',str(prompt),'--name','task',
                  '--log',str(log),'--output',str(output),'--worktree',json.dumps(start['worktree']), 'exec')
        subs = [json.loads(l) for l in self.call('bin/subscribe','list').stdout.splitlines()]
        self.assertEqual(subs[0]['thread_key'],'gh:owner/repo#7')
        self.call('bin/review','task')
        value = json.loads(self.call('bin/status','threads','--json').stdout)
        string={'type':'string'}; nullable={'type':['string','null']}
        schema=object_schema(dict(generated_at=string,threads={'type':'array','items':object_schema(dict(
            key=string,kind={'type':'string','enum':['project','gh','ear','other']},project=nullable,title=string,
            subscribers={'type':'array','items':object_schema(dict(id=string,to=string,paused={'type':'boolean'}))},
            last_event_at=nullable,last_event=nullable,
            counts=object_schema({k:{'type':'number','minimum':0} for k in ('events','routed','pending')}),
            tasks={'type':'array','items':object_schema(dict(name=string,status={'type':'string','enum':['running','done','failed']},
                started_at=string,report=nullable,reviewed={'type':'boolean'}))}))}))
        self.assertIn('groups', value)
        validate({k: value[k] for k in ('generated_at', 'threads')},schema)
        self.assertTrue(all(t['tasks'][0]['reviewed'] for t in value['threads']))
        self.call('bin/review','task','--undo')
        self.assertFalse(json.loads(self.call('bin/status','threads','--json').stdout)['threads'][0]['tasks'][0]['reviewed'])

if __name__ == '__main__': unittest.main(verbosity=2)
