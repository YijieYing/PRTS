#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import shutil
import time

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
        self.age_git(self.path('merged'), 8)
        self.assertIn('rule=B', self.clean('--dry')); self.assertTrue(self.path('merged').exists())
        (self.path('merged') / 'untracked').write_text('x')
        self.assertIn('有改动', self.clean()); (self.path('merged') / 'untracked').unlink()
        self.age_git(self.path('merged'), 8)
        self.assertFalse('SKIP' in self.clean()); self.assertFalse(self.path('merged').exists())
        self.assertIn('refs/heads/merged', self.git('show-ref'))
        self.dispatch('pending', '--dry')
        (self.path('pending') / 'file').write_text('pending')
        self.git('commit', '-am', 'pending', cwd=self.path('pending'))
        self.assertIn('未满足规则 A/B', self.clean()); self.assertTrue(self.path('pending').exists())
        self.git('push', 'origin', 'pending')
        self.assertIn('未满足规则 A/B', self.clean())

    def test_squash_and_old_pr(self):
        self.dispatch('squash', '--dry'); path = self.path('squash')
        (path / 'file').write_text('changed'); self.git('commit', '-am', 'feature', cwd=path)
        oid = self.git('rev-parse', 'squash')
        self.git('push', '-u', 'origin', 'squash', cwd=path)
        self.git('merge', '--squash', 'squash'); self.git('commit', '-m', 'squashed'); self.git('push')
        self.env['FAKE_PR'] = json.dumps([dict(headRefOid='0' * 40)])
        self.assertIn('未满足规则 A/B', self.clean())
        self.env['FAKE_PR'] = json.dumps([dict(headRefOid=oid)])
        self.age_git(path, 8)
        self.clean()
        self.assertFalse(path.exists())
        self.assertIn('refs/heads/squash', self.git('show-ref'))

    def test_squash_branch_delete_refusal_is_reported(self):
        self.dispatch('retained', '--dry'); path = self.path('retained')
        (path / 'file').write_text('changed'); self.git('commit', '-am', 'feature', cwd=path)
        oid = self.git('rev-parse', 'retained')
        self.env['FAKE_PR'] = json.dumps([dict(headRefOid=oid)])
        output = self.clean()
        self.assertFalse(path.exists())
        self.assertFalse(path.exists())
        self.assertEqual(self.git('rev-parse', 'retained'), oid)

    def test_all_and_existing_external_worktree(self):
        external = self.home / 'external'
        self.git('worktree', 'add', '-b', 'external', external)
        self.dispatch('external', '--dry')
        self.assertIn(str(external), (self.state / 'tasks/task/run.log').read_text())
        self.assertNotIn(str(external), self.clean('--dry'))
        self.assertIn(str(external), self.clean('--all', '--dry'))
        self.age_git(external, 8)
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

    def age_git(self, path, days=2, seconds=None):
        gd = Path(self.git('rev-parse', '--git-dir', cwd=path))
        if not gd.is_absolute(): gd = path / gd
        stamp = __import__('time').time() - (days * 86400 if seconds is None else seconds)
        for name in ('HEAD', 'index', 'logs/HEAD'):
            p = gd / name
            if p.exists(): os.utime(p, (stamp, stamp))
        if gd.exists(): os.utime(gd, (stamp, stamp))

    def test_auto_idle_threshold_and_now(self):
        self.dispatch('threshold', '--dry'); path = self.path('threshold')
        (path / 'file').write_text('threshold'); self.git('commit', '-am', 'threshold', cwd=path)
        self.git('merge', '--ff-only', 'threshold'); self.git('push', 'origin', 'main')
        self.age_git(path, seconds=29 * 60)
        out = self.auto().stdout
        self.assertIn('闲置不足 30 分钟', out); self.assertTrue(path.exists())
        self.age_git(path, seconds=31 * 60)
        out = self.auto().stdout
        self.assertIn('可删除', out); self.assertFalse(path.exists())

        self.dispatch('now', '--dry'); now_path = self.path('now')
        (now_path / 'file').write_text('now'); self.git('commit', '-am', 'now', cwd=now_path)
        self.git('merge', '--ff-only', 'now'); self.git('push', 'origin', 'main')
        self.assertTrue(now_path.exists())
        self.auto('--now')
        self.assertFalse(now_path.exists())

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

    def test_auto_rule_a_new_local_commit_is_skipped(self):
        self.dispatch('new-after-delete', '--dry'); path = self.path('new-after-delete')
        self.git('push', '-u', 'origin', 'new-after-delete', cwd=path); self.auto()
        self.git('push', 'origin', '--delete', 'new-after-delete')
        (path / 'file').write_text('unseen'); self.git('commit', '-am', 'unseen', cwd=path); self.age_git(path, 2)
        self.assertIn('远程已删，但本地有远程没见过的提交', self.auto().stdout); self.assertTrue(path.exists())

    def test_auto_rule_b_merged_and_fresh_idle_window(self):
        self.dispatch('merged-auto', '--dry'); path = self.path('merged-auto')
        (path / 'file').write_text('merged'); self.git('commit', '-am', 'merged', cwd=path)
        self.git('merge', '--ff-only', 'merged-auto'); self.git('push', 'origin', 'main'); self.age_git(path, 2)
        out = self.auto().stdout; self.assertFalse(path.exists(), out)
        self.dispatch('fresh-two', '--dry'); fresh = self.path('fresh-two'); self.age_git(fresh, 2)
        self.assertTrue(fresh.exists()); self.git('worktree', 'prune'); self.age_git(fresh, 8); out = self.auto().stdout; self.assertIn('rule=B', out)

    def test_auto_dirty_young_and_live_dispatch_are_skipped(self):
        self.dispatch('dirty-auto', '--dry'); dirty = self.path('dirty-auto'); self.age_git(dirty, 2)
        (dirty / 'untracked').write_text('x'); self.assertIn('有改动', self.auto().stdout); self.assertTrue(dirty.exists())
        self.dispatch('young-auto', '--dry'); young = self.path('young-auto'); self.assertIn('闲置不足 30 分钟', self.auto().stdout)
        self.dispatch('live-auto', '--dry'); live = self.path('live-auto'); self.age_git(live, 2)
        with (self.state / 'registry.jsonl').open('a') as f: f.write(json.dumps({'name':'live','event':'start','pid':os.getpid(),'cwd':str(live),'worktree':{'path':str(live)}})+'\n')
        self.assertIn('有活着的派发', self.auto().stdout); self.assertTrue(live.exists())

    def test_auto_upstream_alias_is_not_rule_a(self):
        self.dispatch('alias-upstream', '--dry'); path = self.path('alias-upstream')
        self.git('branch', '--set-upstream-to=origin/main', 'alias-upstream', cwd=path)
        self.assertIn('rule=B', self.auto().stdout)

    def test_auto_protected_main_detached_and_locked(self):
        self.dispatch('detached-auto', '--dry'); detached = self.path('detached-auto')
        self.git('checkout', '--detach', cwd=detached); out = self.auto().stdout
        self.assertIn('detached HEAD，保留', out)
        self.git('worktree', 'lock', str(detached)); out = self.auto().stdout
        self.assertIn('worktree 已锁定', out)

    def test_auto_pending_branch_removed_after_14_days(self):
        self.dispatch('pending-14', '--dry'); path = self.path('pending-14'); self.git('push', '-u', 'origin', 'pending-14', cwd=path); self.auto(); self.git('push', 'origin', '--delete', 'pending-14'); self.age_git(path, 2); self.auto()
        state_path = self.state / 'worktrees' / 'auto-state.json'; state = json.loads(state_path.read_text())
        for p in state['pending_branches']:
            p['removed_at'] = '2000-01-01T00:00:00'
        state_path.write_text(json.dumps(state)); self.auto(); self.assertNotIn('refs/heads/pending-14', self.git('show-ref'))

    def test_auto_lsof_child_directory_skips(self):
        self.dispatch('child-cwd', '--dry'); path = self.path('child-cwd'); self.age_git(path, 2)
        (self.home / 'bin' / 'lsof').write_text(f'#!/bin/sh\nprintf "n{path}/interaction\\n"\n')
        (self.home / 'bin' / 'lsof').chmod(0o755)
        self.assertIn('可能正在使用', self.auto().stdout); self.assertTrue(path.exists())

    def test_auto_prunes_missing_registration_and_trashes_old_debris(self):
        self.dispatch('missing-auto', '--dry'); missing = self.path('missing-auto'); shutil = __import__('shutil'); shutil.rmtree(missing)
        old = self.root / 'repo' / '.ci.log'; old.write_text('old'); os.utime(old, (1, 1)); new = self.root / 'repo' / 'new.ci.log'; new.write_text('new')
        self.auto(); self.assertNotIn(str(missing), self.git('worktree', 'list')); self.assertTrue((self.home / '.Trash' / '.ci.log').exists()); self.assertTrue(new.exists())

    def test_repo_limits_processing_to_requested_repository(self):
        other = self.home / 'other'; other.mkdir()
        self.run_cmd('git', 'init', '-b', 'main', cwd=other)
        self.run_cmd('git', 'config', 'user.name', 'Test', cwd=other)
        self.run_cmd('git', 'config', 'user.email', 'test@example.test', cwd=other)
        (other / 'file').write_text('initial'); self.run_cmd('git', 'add', '.', cwd=other); self.run_cmd('git', 'commit', '-m', 'initial', cwd=other)
        path = self.home / 'other-worktree'
        self.run_cmd('git', 'worktree', 'add', '-b', 'other-feature', path, cwd=other)
        (path / 'file').write_text('merged'); self.run_cmd('git', 'commit', '-am', 'merged', cwd=path)
        self.run_cmd('git', 'merge', '--ff-only', 'other-feature', cwd=other); self.age_git(path, 8)
        self.assertTrue(path.exists())
        self.auto('--repo', self.repo)
        self.assertTrue(path.exists())

    def test_clean_skips_worktree_with_child_cwd(self):
        self.dispatch('clean-lsof', '--dry'); path = self.path('clean-lsof'); self.age_git(path, 8)
        fake_lsof = self.home / 'bin' / 'lsof'
        fake_lsof.write_text(f'#!/bin/sh\nprintf "n{path}/child\n"\n'); fake_lsof.chmod(0o755)
        out = self.clean()
        self.assertIn('可能正在使用', out); self.assertTrue(path.exists())

    def test_auto_lock_is_nonblocking_and_dry_does_not_lock(self):
        self.dispatch('locked-auto', '--dry'); path = self.path('locked-auto'); self.age_git(path, 8)
        lock = self.state / 'worktrees' / 'auto.lock'; lock.parent.mkdir(parents=True, exist_ok=True)
        code = 'import fcntl,time; f=open(%r,"a+"); fcntl.flock(f.fileno(), fcntl.LOCK_EX); time.sleep(2)' % str(lock)
        holder = subprocess.Popen([__import__('sys').executable, '-c', code])
        time.sleep(0.2)
        try:
            self.assertNotIn('另一个 auto 正在运行', self.auto('--dry').stdout)
            out = self.auto().stdout
        finally:
            holder.wait()
        self.assertIn('另一个 auto 正在运行', out); self.assertTrue(path.exists())

    def test_repo_without_worktrees_does_not_fetch(self):
        real_git = shutil.which('git')
        count = self.home / 'git-calls'; wrapper = self.home / 'bin' / 'git'
        wrapper.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{count}"\nexec "{real_git}" "$@"\n'); wrapper.chmod(0o755)
        empty = self.home / 'empty'; empty.mkdir()
        self.run_cmd('git', 'init', '-b', 'main', cwd=empty)
        self.run_cmd('git', 'config', 'user.name', 'Test', cwd=empty)
        self.run_cmd('git', 'config', 'user.email', 'test@example.test', cwd=empty)
        (empty / 'file').write_text('initial'); self.run_cmd('git', 'add', '.', cwd=empty); self.run_cmd('git', 'commit', '-m', 'initial', cwd=empty)
        count.write_text('')
        self.auto('--repo', empty)
        self.assertNotIn(' fetch ', count.read_text())

    def test_stale_event_only_on_list_change(self):
        def make_stale(branch):
            self.dispatch(branch, '--dry'); path = self.path(branch)
            (path / 'file').write_text(branch); self.git('commit', '-am', branch, cwd=path)
            self.git('push', '-u', 'origin', branch, cwd=path); self.age_git(path, 8)
            return path
        make_stale('stale-one'); first_out = self.auto().stdout
        queue = self.state / 'events' / 'queue.jsonl'
        self.assertTrue(queue.exists(), first_out)
        rows = [json.loads(line) for line in queue.read_text().splitlines() if json.loads(line).get('source') == 'worktrees_stale']
        self.assertEqual(len(rows), 1); self.assertEqual(rows[0]['level'], 'L1')
        self.auto()
        rows2 = [json.loads(line) for line in queue.read_text().splitlines() if json.loads(line).get('source') == 'worktrees_stale']
        self.assertEqual(len(rows2), 1)
        make_stale('stale-two'); self.auto()
        rows3 = [json.loads(line) for line in queue.read_text().splitlines() if json.loads(line).get('source') == 'worktrees_stale']
        self.assertEqual(len(rows3), 2)


if __name__ == '__main__': unittest.main()
