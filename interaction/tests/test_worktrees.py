#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

BIN = Path(__file__).resolve().parents[1] / 'bin'


class Worktrees(unittest.TestCase):
    def run_cmd(self, *args, cwd=None, ok=True):
        p = subprocess.run(list(map(str, args)), cwd=cwd or self.repo, env=self.env,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True)
        if ok: self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    def git(self, *args, cwd=None):
        return self.run_cmd('git', *args, cwd=cwd).stdout.strip()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.repo = self.home / 'repo'; self.repo.mkdir()
        self.root = self.home / 'worktrees'
        self.state = self.home / 'state'
        fake = self.home / 'bin'; fake.mkdir()
        (fake / 'codex').write_text('#!/bin/sh\necho launched\n')
        (fake / 'gh').write_text('#!/bin/sh\nprintf "%s\\n" "${FAKE_PR:-[]}"\n')
        for p in fake.iterdir(): p.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(fake) + ':' + os.environ['PATH'],
                        PRTS_WORKTREE_ROOT=str(self.root), PRTS_INTERACTION_STATE=str(self.state),
                        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
        self.git('init', '-b', 'main'); self.git('config', 'user.name', 'Test'); self.git('config', 'user.email', 'test@example.test')
        (self.repo / 'file').write_text('initial'); self.git('add', '.'); self.git('commit', '-m', 'initial')
        self.remote = self.home / 'remote.git'
        self.git('init', '--bare', '-b', 'main', self.remote)
        self.git('remote', 'add', 'origin', str(self.remote)); self.git('push', '-u', 'origin', 'main')
        self.prompt = self.home / 'prompt'; self.prompt.write_text('test')

    def dispatch(self, branch, *args, ok=True):
        return self.run_cmd(BIN / 'dispatch', 'task', self.repo, self.prompt, '--worktree', branch, *args, ok=ok)

    def path(self, branch): return self.root / 'repo' / branch.replace('/', '-')

    def clean(self, *args): return self.run_cmd(BIN / 'worktrees', 'clean', *args).stdout

    def test_create_reuse_registry_and_failure(self):
        self.dispatch('feature/test')
        path = self.path('feature/test')
        self.assertTrue(path.is_dir())
        rows = [json.loads(x) for x in (self.state / 'registry.jsonl').read_text().splitlines()]
        start = next(r for r in rows if r['event'] == 'start')
        self.assertEqual(start['worktree'], dict(path=str(path), branch='feature/test', repo=str(self.repo)))
        self.assertEqual(start['cwd'], str(path))
        self.dispatch('feature/test', '--dry')
        before = (self.state / 'registry.jsonl').read_text()
        self.assertNotEqual(self.dispatch('bad..branch', ok=False).returncode, 0)
        conflict = self.path('conflict'); conflict.mkdir()
        self.assertNotEqual(self.dispatch('conflict', ok=False).returncode, 0)
        self.assertEqual(before, (self.state / 'registry.jsonl').read_text())
        self.git('branch', 'existing')
        self.dispatch('existing', '--dry')
        self.assertTrue(self.path('existing').is_dir())

    def test_clean_merged_dry_dirty_unmerged(self):
        self.dispatch('merged', '--dry')
        self.assertIn('DRY', self.clean('--dry')); self.assertTrue(self.path('merged').exists())
        (self.path('merged') / 'untracked').write_text('x')
        self.assertIn('有改动', self.clean()); (self.path('merged') / 'untracked').unlink()
        self.assertIn('REMOVED', self.clean()); self.assertFalse(self.path('merged').exists())
        self.assertNotIn('refs/heads/merged', self.git('show-ref'))
        self.dispatch('pending', '--dry')
        (self.path('pending') / 'file').write_text('pending')
        self.git('commit', '-am', 'pending', cwd=self.path('pending'))
        self.assertIn('未推送', self.clean()); self.assertTrue(self.path('pending').exists())
        self.git('push', 'origin', 'pending')
        self.assertIn('未合并', self.clean())

    def test_squash_and_old_pr(self):
        self.dispatch('squash', '--dry'); path = self.path('squash')
        (path / 'file').write_text('changed'); self.git('commit', '-am', 'feature', cwd=path)
        oid = self.git('rev-parse', 'squash')
        self.git('push', '-u', 'origin', 'squash', cwd=path)
        self.git('merge', '--squash', 'squash'); self.git('commit', '-m', 'squashed'); self.git('push')
        self.env['FAKE_PR'] = json.dumps([dict(headRefOid='0' * 40)])
        self.assertIn('未合并', self.clean())
        self.env['FAKE_PR'] = json.dumps([dict(headRefOid=oid)])
        self.assertIn('REMOVED', self.clean()); self.assertFalse(path.exists())
        self.assertNotIn('refs/heads/squash', self.git('show-ref'))

    def test_squash_branch_delete_refusal_is_reported(self):
        self.dispatch('retained', '--dry'); path = self.path('retained')
        (path / 'file').write_text('changed'); self.git('commit', '-am', 'feature', cwd=path)
        oid = self.git('rev-parse', 'retained')
        self.env['FAKE_PR'] = json.dumps([dict(headRefOid=oid)])
        output = self.clean()
        self.assertIn('KEEP branch (-d refused)', output)
        self.assertFalse(path.exists())
        self.assertEqual(self.git('rev-parse', 'retained'), oid)

    def test_all_and_existing_external_worktree(self):
        external = self.home / 'external'
        self.git('worktree', 'add', '-b', 'external', external)
        self.dispatch('external', '--dry')
        self.assertIn(str(external), (self.state / 'tasks/task/run.log').read_text())
        self.assertNotIn(str(external), self.clean('--dry'))
        self.assertIn(str(external), self.clean('--all', '--dry'))
        self.clean('--all'); self.assertFalse(external.exists()); self.assertTrue(self.repo.exists())

    def test_local_and_explicit_base(self):
        self.git('remote', 'remove', 'origin')
        self.dispatch('local', '--dry')
        self.dispatch('explicit', '--base', 'main', '--dry')
        (self.path('local') / 'file').write_text('local change')
        self.git('commit', '-am', 'local change', cwd=self.path('local'))
        self.run_cmd(BIN / 'dispatch', 'nested', self.path('local'), self.prompt,
                     '--worktree', 'nested', '--dry')
        self.assertEqual(self.git('rev-parse', 'nested'), self.git('rev-parse', 'local'))
        self.assertEqual(self.git('rev-parse', 'explicit'), self.git('rev-parse', 'main'))

    def age_git(self, path, days=2):
        gd = Path(self.git('rev-parse', '--git-dir', cwd=path))
        if not gd.is_absolute(): gd = path / gd
        stamp = __import__('time').time() - days * 86400
        for name in ('HEAD', 'index', 'logs/HEAD'):
            p = gd / name
            if p.exists(): os.utime(p, (stamp, stamp))

    def auto(self, *args, ok=True):
        return self.run_cmd(BIN / 'worktrees', 'auto', *args, ok=ok)

    def test_auto_rule_a_remote_deleted_and_pending_branch(self):
        self.dispatch('gone', '--dry')
        path = self.path('gone'); (path / 'file').write_text('work'); self.git('commit', '-am', 'work', cwd=path)
        self.git('push', '-u', 'origin', 'gone', cwd=path)
        self.auto()
        self.git('push', 'origin', '--delete', 'gone')
        self.age_git(path, 2)
        out = self.auto().stdout
        self.assertIn('rule=A', out); self.assertFalse(path.exists())
        state = json.loads((self.state / 'worktrees' / 'auto-state.json').read_text())
        self.assertTrue(any(p['branch'] == 'gone' for p in state['pending_branches']))

    def test_auto_dry_and_daily_do_not_write(self):
        self.dispatch('preview', '--dry')
        path = self.path('preview'); self.age_git(path, 2)
        before = (self.state / 'worktrees' / 'auto-state.json').exists()
        self.auto('--dry'); self.assertEqual(before, (self.state / 'worktrees' / 'auto-state.json').exists())
        self.auto('--daily'); self.assertEqual(self.auto('--daily').returncode, 0)


if __name__ == '__main__': unittest.main()
