#!/usr/bin/env python3
"""All fixtures and subprocess state live in one disposable tree; transports are stubs."""
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class Modules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for module in ('interaction', 'reporter'):
            for part in ('bin', 'lib'):
                shutil.copytree(ROOT / module / part, self.root / module / part, ignore=shutil.ignore_patterns('__pycache__'))
        self.home = self.root / 'home'; self.home.mkdir()
        self.state = self.root / 'interaction-data'
        self.env = dict(os.environ, HOME=str(self.home), CODEX_HOME=str(self.home / '.codex'),
                        PRTS_INTERACTION_STATE=str(self.state), PRTS_REPORTER_STATE=str(self.root / 'reporter-data'),
                        CODEX_GAP='0', CODEX_TRIES='2')
        for key in ('CLAUDE_CODE_SESSION_ID', 'CODEX_THREAD_ID'):
            self.env.pop(key, None)
        self.stub = self.root / 'stubs'; self.stub.mkdir()
        self.env['PATH'] = str(self.stub) + ':' + os.environ['PATH']
        self.calls = self.root / 'calls'
        self.env['TEST_CALLS'] = str(self.calls)
        script = '''#!/usr/bin/env python3
import json,os,pathlib,sys
with open(os.environ['TEST_CALLS'],'a') as f: f.write(json.dumps({'bin':pathlib.Path(sys.argv[0]).name,'args':sys.argv[1:],'stdin':sys.stdin.read()})+'\\n')
if os.environ.get('TEST_CAPACITY')=='1': print('at capacity'); sys.exit(1)
'''
        for name in ('codex', 'osascript'):
            f = self.stub / name; f.write_text(script); f.chmod(0o755)
        # Never enter the real CodexBridge checkout or invoke WeChat.
        f = self.root / 'reporter/lib/channels/wechat'; f.write_text(script); f.chmod(0o755)
        self.repo = self.root / 'repo'; self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.prompt = self.root / 'prompt'; self.prompt.write_text('你好 "quote" $(touch INJECTED)\n')

    def run_cmd(self, cmd, *args, input='', rc=0, env=None):  # never inherit our stdin: the stubs read it
        r = subprocess.run([str(self.root / cmd), *map(str, args)], input=input, text=True,
                           capture_output=True, cwd=self.root, env=env or self.env)
        self.assertEqual(r.returncode, rc, r.stdout + r.stderr)
        return r.stdout

    def registry(self, **row):
        self.run_cmd('interaction/lib/registry', 'append', json.dumps(row))

    def rows(self, cmd='interaction/bin/event', *args):
        return [json.loads(l) for l in self.run_cmd(cmd, *args).splitlines()]

    def test_registry(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda i: self.registry(name='名字"', event='start', cwd='/a"b', index=i), range(24)))
        rows = self.rows('interaction/lib/registry', 'list')
        self.assertEqual(len(rows), 24)
        self.assertEqual({r['index'] for r in rows}, set(range(24)))
        self.assertTrue(all(r['t'] and r['name'] == '名字"' for r in rows))
        self.assertEqual(len(self.rows('interaction/bin/status', '名字"')), 24)

    def test_event_add_list_ack(self):
        ident = self.run_cmd('interaction/bin/event', 'add', 'L1', 'test', '多行\n"内容"').strip()
        self.run_cmd('interaction/bin/event', 'add', 'L0', 'test', 'quiet')  # L0 is recorded, not queued for review
        self.assertEqual(len(self.rows('interaction/bin/event', 'list', '--new')), 1)
        self.run_cmd('interaction/bin/event', 'ack', ident)
        self.run_cmd('interaction/bin/event', 'ack', ident)
        self.assertEqual(len(self.rows('interaction/bin/event', 'list', '--new')), 0)
        self.assertEqual(len(self.rows('interaction/bin/event', 'list')), 2)
        self.run_cmd('interaction/bin/event', 'ack', 'missing', rc=2)
        self.assertFalse(self.calls.exists())

    def test_agentconsole(self):
        self.registry(name='job', event='start', cwd='/quote"[x]')
        events = [({'event':'state','to':'dormant','cwd':'/quote"[x]','title':'任务'}, 'L1'),
                  ({'event':'state','to':'dormant','cwd':'/unknown'}, 'L0'),
                  ({'event':'state','to':'working','cwd':'/quote"[x]'}, 'L0'),
                  ({'event':'idle_long','pid':42}, 'L1'),
                  ({'event':'stale','host':'lain','count':2,'days':7}, 'L1'),
                  ({'event':'host_down','host':'lain'}, 'L2')]
        for e, _ in events:
            self.run_cmd('interaction/bin/event', 'from-agentconsole', input=json.dumps(e))
        rows = self.rows('interaction/bin/event', 'list')
        self.assertEqual([r['level'] for r in rows], [level for _, level in events])
        self.assertIn('派发任务结束', rows[0]['text'])
        calls = [json.loads(l) for l in self.calls.read_text().splitlines()]
        self.assertEqual([r['bin'] for r in calls], ['wechat','osascript'])
        self.assertFalse((self.home / 'PRTS/human/inbox.md').exists())

    def test_alert_failure_retains_event(self):
        self.run_cmd('interaction/bin/event', 'add', 'L2', 'test', 'urgent', env=dict(self.env, TEST_CAPACITY='1'), rc=1)
        self.assertEqual(self.rows('interaction/bin/event', 'list', '--new')[0]['text'], 'urgent')

    def test_daily_rejection(self):
        config = self.root / 'reporter/config'; config.mkdir()
        daily = self.root / 'daily'; daily.mkdir()
        (daily / 'latest-wechat.txt').write_text('invalid report')
        (config / 'config.toml').write_text('aquant_daily_dir = ' + json.dumps(str(daily)))
        import sys
        r = subprocess.run([sys.executable, str(self.root / 'reporter/lib/aquant_daily.py')], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stderr)
        row = self.rows('interaction/bin/event', 'list')[0]
        self.assertEqual((row['level'], row['source']), ('L1', 'aquant_daily'))
        self.assertFalse(self.calls.exists())

    def test_notify(self):
        for args in [('log','--text','hello'), ('log','--title','标题','--file',self.prompt)]:
            self.run_cmd('reporter/bin/notify', *args)
        log = self.root / 'reporter-data/out/notifications.jsonl'
        rows = [json.loads(l) for l in log.read_text().splitlines()]
        self.assertEqual(rows[1]['text'], self.prompt.read_text())
        self.assertFalse(self.calls.exists())
        self.run_cmd('reporter/bin/notify', '--text', 'legacy')
        self.run_cmd('reporter/bin/notify', 'outbox')
        self.assertEqual(len(self.calls.read_text().splitlines()), 2)

    def test_dispatch_dry_and_resume(self):
        env = dict(self.env, DISPATCH_DRY='1')
        self.run_cmd('interaction/bin/dispatch', 'dry', self.repo, self.prompt, '--model', 'test', env=env)
        log = (self.state / 'tasks/dry/run.log').read_text()
        self.assertIn('workspace-write', log)
        self.assertIn(str(self.repo / '.git'), log)
        self.assertIn('< /dev/null', log)
        self.assertFalse(self.calls.exists())
        self.assertFalse((self.state / 'registry.jsonl').exists())
        self.run_cmd('interaction/bin/dispatch', 'dry', self.repo, env=env)
        self.run_cmd('interaction/bin/resume', 'resume', 'uuid', self.repo, self.prompt, '2', '0')
        call = json.loads(self.calls.read_text().splitlines()[0])
        self.assertEqual(call['stdin'], '')
        self.assertEqual(call['args'][-1], self.prompt.read_text())
        self.assertFalse((self.root / 'INJECTED').exists())
        env = dict(self.env, TEST_CAPACITY='1')
        self.run_cmd('interaction/bin/resume', 'full', 'uuid', self.repo, self.prompt, '2', '0', env=env, rc=75)
        self.assertEqual([r['event'] for r in self.rows('interaction/bin/status', 'full')], ['start','thread','capacity','capacity','gave_up'])
        # wait: returns the latest run's rc and prints its report; a new start resets an earlier exit
        out = self.run_cmd('interaction/bin/wait', 'full', '1', rc=75)
        self.assertIn('full finished, rc=75', out)
        self.run_cmd('interaction/bin/wait', 'nosuch', '1', rc=2)

    def test_dispatch_real_stub(self):
        self.run_cmd('interaction/bin/dispatch', 'short', self.repo, self.prompt)
        rows = self.rows('interaction/bin/status', 'short')
        self.assertEqual([r['event'] for r in rows], ['start','exit'])
        self.assertEqual(rows[-1]['rc'], 0)

    def test_caller_and_thread(self):
        thread = '12345678-1234-1234-1234-123456789abc'
        stub = self.stub / 'codex'
        stub.write_text(stub.read_text() + "\nimport time\nprint('session id: " + thread + "', flush=True)\n"
                        + "print('activity\\n' * 10, flush=True)\ntime.sleep(float(os.environ.get('TEST_SLEEP', '0')))\n")
        for kind, caller_env in [('claude', {'CLAUDE_CODE_SESSION_ID': 'claude-parent', 'CODEX_THREAD_ID': 'codex-parent'}),
                                 ('codex', {'CODEX_THREAD_ID': 'codex-parent'}), ('none', {})]:
            for mode in ('dispatch', 'resume'):
                name = mode + '-' + kind
                env = dict(self.env, **caller_env)
                args = (name, self.repo, self.prompt) if mode == 'dispatch' else (name, thread, self.repo, self.prompt)
                self.run_cmd('interaction/bin/' + mode, *args, env=env)
                rows = self.rows('interaction/bin/status', name)
                start = next(r for r in rows if r['event'] == 'start')
                if kind == 'none':
                    self.assertNotIn('caller', start)
                else:
                    self.assertEqual(start['caller'], {'kind': kind, 'id': kind + '-parent'})
                self.assertEqual([r['thread'] for r in rows if r['event'] == 'thread'], [thread])
        # Exercise the still-running confirmation branch as well as fast exits.
        self.run_cmd('interaction/bin/dispatch', 'running', self.repo, self.prompt,
                     env=dict(self.env, TEST_SLEEP='3', CODEX_THREAD_ID='codex-parent'))
        links = self.rows('interaction/bin/status', 'links')
        self.assertEqual(len(links), 5)
        self.assertEqual(next(r for r in links if r['task'] == 'dispatch-claude'),
                         {'child': thread, 'parent': 'claude-parent', 'parent_kind': 'claude', 'task': 'dispatch-claude'})
        self.assertTrue(all(r['child'] == thread for r in links))
        self.assertTrue(all(json.loads(l)['stdin'] == '' for l in self.calls.read_text().splitlines()))
        # A new run cannot inherit a previous caller or thread; legacy rows are not guessed.
        self.registry(name='running', event='start')
        self.registry(name='legacy', event='thread', thread=thread)
        self.registry(name='incomplete', event='start', caller={'kind': 'codex', 'id': 'parent'})
        self.assertEqual(len(self.rows('interaction/bin/status', 'links')), 4)

    def test_wake_private_commands(self):
        self.run_cmd('interaction/bin/wake', '_claim', 'fake', rc=2)
        self.assertFalse(self.state.exists())

if __name__ == '__main__': unittest.main(verbosity=2)
