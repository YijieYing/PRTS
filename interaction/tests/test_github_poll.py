#!/usr/bin/env python3
"""Offline integration tests: disposable registry/state and fake git/gh."""
import concurrent.futures
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]

class GithubPoll(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / 'interaction', self.root / 'interaction',
                        ignore=shutil.ignore_patterns('state', '__pycache__'))
        self.state = self.root / 'state'
        self.stub = self.root / 'bin'; self.stub.mkdir()
        self.fixture = self.root / 'fixture.json'
        self.calls = self.root / 'calls.jsonl'
        self.env = dict(os.environ, PRTS_INTERACTION_STATE=str(self.state),
                        PATH=str(self.stub) + ':' + os.environ['PATH'],
                        FIXTURE=str(self.fixture), CALLS=str(self.calls))
        script = '''#!/usr/bin/env python3
import json, os, pathlib, sys
args=sys.argv[1:]
assert sys.stdin.read() == ''
with open(os.environ['CALLS'], 'a') as f: f.write(json.dumps([pathlib.Path(sys.argv[0]).name, args])+'\\n')
data=json.load(open(os.environ['FIXTURE']))
if pathlib.Path(sys.argv[0]).name == 'git':
    remote=data['remotes'].get(args[1])
    if remote is None: sys.exit(1)
    print(remote); sys.exit(0)
repo=args[args.index('--repo')+1]
if repo in data.get('fail', []): print('offline failure', file=sys.stderr); sys.exit(1)
prs=data['repos'][repo]
if args[1]=='list': print(json.dumps([{'number':int(n),'updatedAt':p['updatedAt']} for n,p in prs.items()]))
else: print(json.dumps(prs[args[2]]))
'''
        for name in ('git', 'gh'):
            p = self.stub / name; p.write_text(script); p.chmod(0o755)
        self.data = dict(remotes={'/repo':'git@github.com:owner/repo.git'},
                         repos={'owner/repo': {'123': self.detail()}}, fail=[])
        self.add_cwd('/repo')

    def detail(self, comments=0, ci='PENDING', updated='2026-11-14T00:00:00Z'):
        return dict(comments=[{}] * comments, statusCheckRollup=[{'state':ci}], updatedAt=updated)

    def add_cwd(self, cwd):
        subprocess.run([str(self.root / 'interaction/lib/registry'), 'append', json.dumps({'cwd':cwd})],
                       env=self.env, check=True, capture_output=True)

    def poll(self):
        self.fixture.write_text(json.dumps(self.data))
        result = subprocess.run([str(self.root / 'interaction/bin/github_poll')], env=self.env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def events(self):
        path = self.state / 'events/queue.jsonl'
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def test_baseline_unchanged_and_changes(self):
        self.poll()
        before = (self.state / 'github_poll.jsonl').read_bytes()
        self.poll()
        self.assertEqual(self.events(), [])
        self.assertEqual(before, (self.state / 'github_poll.jsonl').read_bytes())
        for detail, expected in [(self.detail(comments=1), '评论数'),
                                 (self.detail(comments=1, ci='FAILURE'), 'CI 从 pending 变成 failure'),
                                 (self.detail(comments=1, ci='FAILURE', updated='later'), '有更新')]:
            self.data['repos']['owner/repo']['123'] = detail
            count = len(self.events())
            self.poll(); self.poll()
            self.assertEqual(len(self.events()), count + 1)
            event = self.events()[-1]
            self.assertIn('owner/repo#123', event['text'])
            self.assertIn(expected, event['text'])
            self.assertEqual((event['level'], event['source'], event['status']), ('L1','github_poll','new'))

    def test_remotes_and_deduplication(self):
        for i, remote in enumerate(['https://github.com/owner/repo.git', 'ssh://git@github.com/owner/repo.git',
                                    'https://gitlab.com/o/r', '/local/repo', 'https://github.com.evil/o/r', None]):
            cwd = f'/repo{i}'; self.add_cwd(cwd); self.data['remotes'][cwd] = remote
        self.add_cwd('/repo')
        self.assertEqual(self.poll().stderr, '')
        calls = [json.loads(l) for l in self.calls.read_text().splitlines()]
        self.assertEqual(sum(name == 'gh' and args[1] == 'list' for name,args in calls), 1)

    def test_failed_repo_does_not_stop_other_repos(self):
        self.add_cwd('/bad'); self.data['remotes']['/bad']='https://github.com/aaa/bad.git'
        self.data['fail']=['aaa/bad']
        self.assertIn('offline failure', self.poll().stderr)
        self.data['repos']['owner/repo']['123'] = self.detail(comments=1)
        self.poll()
        self.assertEqual(len(self.events()), 1)

    def test_failed_observation_retries_and_bad_pr_is_isolated(self):
        self.poll()
        before = (self.state / 'github_poll.jsonl').read_bytes()
        self.data['fail'] = ['owner/repo']
        self.assertIn('offline failure', self.poll().stderr)
        self.assertEqual(before, (self.state / 'github_poll.jsonl').read_bytes())
        self.data['fail'] = []
        self.data['repos']['owner/repo']['122'] = {'updatedAt':'bad'}
        self.data['repos']['owner/repo']['123'] = self.detail(comments=1)
        self.assertIn('owner/repo#122', self.poll().stderr)
        self.assertEqual(len(self.events()), 1)

    def test_failed_event_retries_without_advancing_cursor(self):
        self.poll()
        before = (self.state / 'github_poll.jsonl').read_bytes()
        event = self.root / 'interaction/bin/event'
        original = event.read_text()
        event.write_text('#!/bin/sh\nexit 1\n')
        self.data['repos']['owner/repo']['123'] = self.detail(comments=1)
        self.assertIn('owner/repo#123', self.poll().stderr)
        self.assertEqual(before, (self.state / 'github_poll.jsonl').read_bytes())
        event.write_text(original)
        self.poll()
        self.assertEqual(len(self.events()), 1)

    def test_closed_pr_and_compaction(self):
        self.poll()
        self.data['repos']['owner/repo'] = {}
        self.calls.write_text('')
        self.poll()
        calls = [json.loads(l) for l in self.calls.read_text().splitlines()]
        self.assertFalse(any(name == 'gh' and args[1] == 'view' for name,args in calls))
        self.assertTrue(json.loads((self.state / 'github_poll.jsonl').read_text().splitlines()[-1])['deleted'])
        with (self.state / 'github_poll.jsonl').open('a') as f:
            f.write(' ' * (1024 * 1024) + '\n')
        self.poll()
        self.assertEqual((self.state / 'github_poll.jsonl').read_text(), '')
        self.assertEqual(self.events(), [])

    def test_concurrent_polls(self):
        self.poll()
        self.data['repos']['owner/repo']['123'] = self.detail(comments=1)
        self.fixture.write_text(json.dumps(self.data))
        def invoke(_):
            return subprocess.run([str(self.root / 'interaction/bin/github_poll')], env=self.env,
                                  capture_output=True, timeout=15).returncode
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(invoke, range(4))), [0]*4)
        self.assertEqual(len(self.events()), 1)

    def test_ci_and_timeout(self):
        module = runpy.run_path(str(ROOT / 'interaction/lib/github_poll.py'))
        ci = module['ci_state']
        self.assertEqual(ci([]), 'none')
        self.assertEqual(ci([{'status':'COMPLETED','conclusion':'SUCCESS'}, {'state':'PENDING'}]), 'pending')
        self.assertEqual(ci([{'status':'COMPLETED','conclusion':'CANCELLED'}]), 'failure')
        self.assertEqual(ci([{'status':'COMPLETED','conclusion':'SKIPPED'}]), 'success')
        self.assertEqual(ci([{'state':'unrecognized'}]), 'unknown')
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('gh', 30)) as run:
            self.assertEqual(module['poll']('owner/repo', self.state), [])
            self.assertEqual(run.call_args.kwargs['stdin'], subprocess.DEVNULL)
            self.assertEqual(run.call_args.kwargs['timeout'], 30)

if __name__ == '__main__':
    unittest.main(verbosity=2)
