"""Worktree creation, inventory and conservative cleanup."""
import argparse
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import datetime as dt
import shutil
import time
import fcntl

IDLE_SECONDS = 1800
STALE_SECONDS = 7 * 86400

registry = runpy.run_path(str(Path(__file__).with_name('registry')))


def run(args, cwd=None, check=True, timeout=60):
    p = subprocess.run(args, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode:
        raise ValueError(p.stderr.strip() or p.stdout.strip() or 'command failed: ' + ' '.join(args))
    return p


def git(repo, *args, check=True, timeout=60):
    return run(['git', '-C', str(repo), *args], check=check, timeout=timeout)


def root():
    return Path(os.environ.get('PRTS_WORKTREE_ROOT', Path.home() / '.worktrees')).expanduser().resolve()


def entries(repo):
    data = git(repo, 'worktree', 'list', '--porcelain', '-z').stdout
    result = []
    for record in data.split('\0\0'):
        row = dict(field.split(' ', 1) if ' ' in field else (field, True)
                   for field in record.split('\0') if field)
        if 'worktree' in row:
            result.append(row)
    return result


def repository(repo):
    return Path(entries(repo)[0]['worktree']).resolve()


def default_ref(repo):
    if not git(repo, 'remote', 'get-url', 'origin', check=False).returncode:
        ref = git(repo, 'symbolic-ref', '--quiet', 'refs/remotes/origin/HEAD', check=False)
        if ref.returncode:
            remote = git(repo, 'ls-remote', '--symref', 'origin', 'HEAD').stdout
            for line in remote.splitlines():
                if line.startswith('ref: refs/heads/'):
                    return 'refs/remotes/origin/' + line.split()[1].removeprefix('refs/heads/')
            raise ValueError('cannot determine origin default branch')
        return ref.stdout.strip()
    if git(repo, 'remote').stdout.strip():
        raise ValueError('repository has remotes but no origin; specify --base')
    return 'HEAD'


def merged_into_default(repo, head, ref):
    """Ancestor of the default branch on origin, or of the local branch with the same name
    (locally merged but not pushed yet, e.g. PRTS main; 11-26)."""
    refs = [ref]
    if ref.startswith('refs/remotes/origin/'):
        local = 'refs/heads/' + ref.removeprefix('refs/remotes/origin/')
        if git(repo, 'show-ref', '--verify', '--quiet', local, check=False).returncode == 0: refs.append(local)
    return any(git(repo, 'merge-base', '--is-ancestor', head, r, check=False).returncode == 0 for r in refs)


def prepare(repo, branch, base=None):
    source = repo
    repo = repository(repo)
    if branch.startswith('-') or git(repo, 'check-ref-format', 'refs/heads/' + branch, check=False).returncode:
        raise ValueError('invalid branch name: ' + branch)
    for row in entries(repo):
        if row.get('branch') == 'refs/heads/' + branch:
            path = Path(row['worktree']).resolve()
            if not path.is_dir() or repository(path) != repo:
                raise ValueError('registered worktree is unavailable: ' + str(path))
            return dict(path=str(path), branch=branch, repo=str(repo))
    path = root() / repo.name / branch.replace('/', '-')
    if path.exists() or path.is_symlink():
        raise ValueError('worktree path occupied: ' + str(path))
    exists = git(repo, 'show-ref', '--verify', '--quiet', 'refs/heads/' + branch, check=False).returncode == 0
    if not exists:
        if base is None:
            if git(repo, 'remote', 'get-url', 'origin', check=False).returncode == 0:
                git(repo, 'fetch', 'origin')
            base = default_ref(repo)
            if base == 'HEAD':
                base = git(source, 'rev-parse', 'HEAD').stdout.strip()
        # Resolve before creating any directory or branch (also prevents option injection).
        base = git(repo, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}').stdout.strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, 'worktree', 'add', *([] if exists else ['-b', branch]), str(path), *([branch] if exists else [base]))
    return dict(path=str(path.resolve()), branch=branch, repo=str(repo))


def inventory(all_repos=False):
    candidates = [Path.cwd()]
    if root().exists():
        candidates.extend(p.parent for p in root().glob('*/*/.git'))
    rows = registry['rows']()
    for r in rows:
        if r.get('cwd'): candidates.append(Path(r['cwd']))
        if r.get('worktree', {}).get('repo'): candidates.append(Path(r['worktree']['repo']))
    repos = set()
    for p in candidates:
        try: repos.add(repository(p))
        except (ValueError, OSError): pass
    for repo in sorted(repos):
        for row in entries(repo):
            path = Path(row['worktree']).resolve()
            if not all_repos and not path.is_relative_to(root()): continue
            tasks = sorted({r['name'] for r in rows if r.get('name') and
                            (r.get('worktree', {}).get('path') == str(path) or r.get('cwd') == str(path))})
            yield repo, row, path, tasks

def scan_repositories():
    """Find repositories for automatic cleanup, including shallow user roots."""
    bases = os.environ.get('PRTS_WORKTREE_SCAN')
    if bases is None:
        bases = ':'.join(str(Path.home() / x) for x in ('Projects', 'research', 'PRTS', 'outreach'))
    found = set()
    for base in [x for x in bases.split(':') if x]:
        b = Path(base).expanduser()
        if not b.exists(): continue
        for p in [b] + [x for x in b.glob('*') if x.is_dir()] + [x for x in b.glob('*/*') if x.is_dir()] + [x for x in b.glob('*/*/*') if x.is_dir()]:
            if (p / '.git').is_dir() and not any(str(p).startswith(str(Path.home()/x)) for x in ('.claude', '.codex')):
                try: found.add(repository(p))
                except (OSError, ValueError): pass
    for repo, _, _, _ in inventory(True): found.add(repo)
    return sorted(found)

def _auto_state():
    p = registry['state']() / 'worktrees' / 'auto-state.json'
    if not p.exists(): return {}, p
    try: return json.loads(p.read_text()), p
    except (OSError, ValueError): return {}, p

def _save_auto(state, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')

def _age(path):
    try: return time.time() - path.stat().st_mtime
    except OSError: return float('inf')

def _idle(path):
    return _git_idle(path, IDLE_SECONDS)

def _git_idle(path, seconds):
    gd = git(path, 'rev-parse', '--git-dir', check=False).stdout.strip()
    if not gd: return False
    gd = Path(gd); gd = gd if gd.is_absolute() else path / gd
    return all(_age(gd / x) >= seconds for x in ('HEAD', 'index', 'logs/HEAD'))

def _alive_registry(path):
    target = str(path.resolve())
    starts = {}
    for r in registry['rows']():
        name = r.get('name')
        if r.get('event') == 'start': starts[name] = r
        elif r.get('event') == 'exit': starts.pop(name, None)
    for r in starts.values():
        wt = r.get('worktree') or {}
        if r.get('cwd') == target or wt.get('path') == target:
            pid = r.get('pid')
            try: os.kill(int(pid), 0)
            except (OSError, TypeError, ValueError): continue
            return True
    return False

def _cwd_snapshot():
    try:
        p = subprocess.run(['lsof', '-a', '-d', 'cwd', '-Fn'], capture_output=True, text=True, timeout=5)
        if p.returncode == 1: return set(), True
        if p.returncode != 0: return set(), True
        return {line[1:] for line in p.stdout.splitlines() if line.startswith('n')}, False
    except (OSError, subprocess.TimeoutExpired): return set(), True

def _in_use(path, cwds, unavailable=False):
    if unavailable: return True
    target = str(path.resolve())
    return any(cwd == target or cwd.startswith(target + os.sep) for cwd in cwds)

def _event(action, repo, path='', branch='', rule='', reason=''):
    row = dict(t=dt.datetime.now(dt.timezone.utc).isoformat(), action=action, repo=str(repo), path=str(path), branch=branch, rule=rule, reason=reason)
    p = registry['state']() / 'worktrees'; p.mkdir(parents=True, exist_ok=True)
    with (p / 'auto.jsonl').open('a') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')

def _merged_prs(repo, cache):
    key = str(repo)
    if key in cache: return cache[key]
    result = {}
    try:
        p = run(['gh', 'pr', 'list', '--state', 'merged', '--json', 'headRefName,headRefOid', '--limit', '1000'], cwd=repo, check=False, timeout=15)
        if p.returncode == 0:
            for row in json.loads(p.stdout):
                result.setdefault(row.get('headRefName'), set()).add(row.get('headRefOid'))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        result = {}
    cache[key] = result
    return result


def _repo_selection(all_repos=False, requested=None):
    if requested:
        result = []
        for item in requested:
            result.append(repository(Path(item).expanduser()))
        return sorted(set(result))
    if all_repos is not None:
        found = {repo for repo, _, _, _ in inventory(all_repos)}
        return sorted(found)
    return scan_repositories()


def auto(dry=False, daily=False, now=False, all_repos=None, requested=None, verbose=False):
    state, state_path = _auto_state(); today = dt.datetime.now().date().isoformat()
    if daily and state.get('last_daily') == today: return 0
    lock_handle = None
    if not dry:
        lock_path = registry['state']() / 'worktrees' / 'auto.lock'
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_handle = lock_path.open('a+')
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('另一个 auto 正在运行')
            return 0
    state.setdefault('seen', {}); state.setdefault('pending_branches', [])
    changed = False; deleted = 0; failed = False
    try:
        repos = _repo_selection(all_repos, requested)
    except (ValueError, OSError):
        repos = []
    cwds, lsof_unavailable = _cwd_snapshot()
    merged_cache = {}
    stale = []
    for repo in repos:
        rows = entries(repo)
        non_main = [r for r in rows if Path(r['worktree']).resolve() != repo]
        if not non_main:
            if verbose:
                print(f'{repo}\tbranch=main\trepo={repo}\trule=-\treason=无非主检出 worktree，跳过')
            continue
        stale_idle = {str(Path(r['worktree']).resolve()): _git_idle(Path(r['worktree']).resolve(), STALE_SECONDS)
                      for r in non_main}
        if not dry: git(repo, 'worktree', 'prune', check=False)
        fetch_ok = True
        fetch_reason = ''
        if git(repo, 'remote', 'get-url', 'origin', check=False).returncode == 0 and not dry:
            try: fetch_ok = git(repo, 'fetch', '--prune', 'origin', check=False, timeout=30).returncode == 0
            except subprocess.TimeoutExpired: fetch_ok = False
            if not fetch_ok: fetch_reason = 'fetch origin 失败，本次不使用规则 A'
        rows = entries(repo); repo_key = str(repo); previous = state['seen'].setdefault(repo_key, {})
        current = {}
        present_branches = set()
        for row in rows:
            path = Path(row['worktree']).resolve(); branch = row.get('branch','').removeprefix('refs/heads/'); rule='-'; reasons=[]
            idle_now = _idle(path)
            protected = path == repo or 'locked' in row or not branch
            if branch: present_branches.add(branch)
            if path == repo: reasons = ['主检出，保留']
            elif 'locked' in row: reasons = ['worktree 已锁定']
            elif not branch: reasons = ['detached HEAD，保留']
            head = row.get('HEAD','')
            remote_ref = 'refs/remotes/origin/' + branch if branch else ''
            remote_exists = bool(remote_ref and git(repo, 'show-ref', '--verify', '--quiet', remote_ref, check=False).returncode == 0)
            if remote_exists: current[branch] = git(repo, 'rev-parse', remote_ref).stdout.strip()
            gone = fetch_ok and branch and not remote_exists and ((branch in previous) or (git(path, 'config', '--get', 'branch.'+branch+'.merge', check=False).stdout.strip() == 'refs/heads/'+branch and '[gone]' in git(path, 'for-each-ref', '--format=%(upstream:track)', 'refs/heads/'+branch, check=False).stdout))
            merged = False
            if branch and not protected and not gone:
                try:
                    ref = default_ref(repo)
                    merged = merged_into_default(repo, head, ref)
                    if not merged and ref.startswith('refs/remotes/origin/'):
                        prs = _merged_prs(repo, merged_cache)
                        merged = head in prs.get(branch, set()) or head in prs.get(None, set())
                except (ValueError, OSError, subprocess.TimeoutExpired):
                    pass
            if gone: rule='A'
            elif merged: rule='B'
            if rule == 'B' and not protected:
                base = default_ref(repo)
                mb = git(repo, 'merge-base', head, base, check=False).stdout.strip()
                reflog = git(repo, 'reflog', 'show', '--format=%gs', branch, check=False).stdout
                own_history = any(x.startswith(('commit:', 'rebase', 'cherry-pick')) for x in reflog.splitlines())
                if mb and git(repo, 'rev-list', '--count', mb+'..'+head, check=False).stdout.strip() == '0' and not own_history and not _git_idle(path, 7*86400): reasons.append('刚建且闲置不足 7 天')
            if not protected and fetch_reason: reasons.append(fetch_reason)
            dirty = bool(git(path, 'status', '--porcelain', '--untracked-files=all', check=False).stdout.strip())
            if not protected and dirty: reasons.append('有改动或无法读取工作区')
            if not protected and rule == 'A':
                contained = (branch in previous and git(repo, 'merge-base', '--is-ancestor', head, previous[branch], check=False).returncode == 0) or git(repo, 'for-each-ref', '--contains', head, '--format=%(refname)', 'refs/remotes/').stdout.strip()
                if not contained: reasons.append('远程已删，但本地有远程没见过的提交')
            elif not protected and rule not in ('B',): reasons.append('未满足规则 A/B')
            if not protected and _in_use(path, cwds, lsof_unavailable): reasons.append('可能正在使用')
            if not protected and _alive_registry(path): reasons.append('有活着的派发')
            if not protected and not now and not idle_now: reasons.append('闲置不足 30 分钟')
            if not protected and rule not in ('A', 'B') and stale_idle.get(str(path), False):
                stale.append(str(path))
            if path == repo and not verbose:
                continue
            print(f'{path}\tbranch={branch or "(detached)"}\trepo={repo}\trule={rule}\treason={"；".join(reasons) or "可删除"}')
            if reasons or protected or dry: continue
            try:
                git(repo, 'worktree', 'remove', str(path)); deleted += 1; changed = True
                state['pending_branches'].append(dict(repo=repo_key, branch=branch, sha=head, removed_at=dt.datetime.now().isoformat(), rule=rule)); _event('worktree_removed', repo, path, branch, rule, '；'.join(reasons) or '安全检查通过')
            except (ValueError, subprocess.TimeoutExpired) as e:
                _event('remove_failed', repo, path, branch, rule, str(e)); print('  ERROR '+str(e)); failed=True
        if fetch_ok:
            retained = {b: sha for b, sha in previous.items() if b in present_branches and b not in current}
            retained.update(current)
            state['seen'][repo_key] = retained
    # Branch retention and old debris are deliberately skipped in dry runs.
    if not dry:
        kept=[]
        all_wt = {str(repo): entries(Path(repo)) for repo in {p.get('repo') for p in state['pending_branches']} if repo and Path(repo).exists()}
        for p in state['pending_branches']:
            exists = git(p['repo'], 'show-ref', '--verify', '--quiet', 'refs/heads/'+p['branch'], check=False).returncode == 0
            sha_same = exists and git(p['repo'], 'rev-parse', p['branch'], check=False).stdout.strip() == p['sha']
            if not exists:
                _event('branch_dropped', p['repo'], '', p['branch'], p['rule'], '分支已不存在'); continue
            if not sha_same:
                _event('branch_dropped', p['repo'], '', p['branch'], p['rule'], '分支 sha 变了'); continue
            try: old = (dt.datetime.now() - dt.datetime.fromisoformat(p.get('removed_at',''))).total_seconds() >= 14*86400
            except (ValueError, TypeError): old = False
            if not old: kept.append(p); continue
            if any(r.get('branch') == 'refs/heads/'+p['branch'] for r in all_wt.get(p['repo'], [])): kept.append(p); continue
            cmd = '-d' if p['rule']=='B' else '-D'; git(p['repo'], 'branch', cmd, '--', p['branch'], check=False); _event('branch_removed', p['repo'], '', p['branch'], p['rule'], '保留期满')
        state['pending_branches'] = kept
        trash = Path.home()/'.Trash'; trash.mkdir(parents=True, exist_ok=True)
        for base in [root()]:
            if not base.exists(): continue
            for f in base.glob('*/*'):
                if f.is_file() and (f.name.endswith(('.ci.log','.fails','.pytest'))) and _age(f) >= 7*86400:
                    dest=trash/f.name
                    if dest.exists(): dest=trash/(f.name+'.'+str(int(time.time())))
                    shutil.move(str(f), str(dest)); _event('debris_trashed', '', f, '', '-', '超过 7 天')
        old_stale = state.get('stale_paths', [])
        if stale != old_stale and stale:
            text = f"{len(stale)} 个 worktree 闲置超过 7 天且未合并：" + '、'.join(stale)
            subprocess.run([str(Path(__file__).parents[1]/'bin/event'),'add','L1','worktrees_stale',text], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=False)
            state['stale_date'] = today
        state['stale_paths'] = stale
        state['last_daily'] = today if daily else state.get('last_daily'); _save_auto(state, state_path)
        if deleted:
            subprocess.run([str(Path(__file__).parents[1]/'bin/event'),'add','L0','worktrees_auto',f'删除 {deleted} 个 worktree'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=False)
    return 1 if failed else 0


def inspect(repo, row, path):
    branch = row.get('branch', '').removeprefix('refs/heads/')
    status = git(path, 'status', '--porcelain', '--untracked-files=all', check=False)
    dirty = bool(status.stdout.strip()) or status.returncode != 0
    merged = False
    reason = ''
    try:
        ref = default_ref(repo)
        merged = merged_into_default(repo, row['HEAD'], ref)
        if not merged and branch and ref.startswith('refs/remotes/origin/'):
            # Any merged PR whose head is exactly this commit counts: repos often merge into a
            # branch other than the default (EchoAsRecord: default main, PRs into dev; 11-15).
            try:
                pr = run(['gh', 'pr', 'list', '--head', branch,
                          '--state', 'merged', '--json', 'headRefOid', '--limit', '1000'], cwd=repo, check=False)
                merged = pr.returncode == 0 and any(p.get('headRefOid') == row['HEAD'] for p in json.loads(pr.stdout))
            except (OSError, ValueError, subprocess.TimeoutExpired): pass
    except ValueError as e:
        reason = str(e)
    if dirty: reason = '有改动或无法读取工作区'
    elif path == repo: reason = '主检出，保留'
    elif 'locked' in row: reason = 'worktree 已锁定'
    elif not branch: reason = 'detached HEAD，保留'
    elif not merged:
        pushed = git(repo, 'for-each-ref', '--contains', row['HEAD'], '--format=%(refname)', 'refs/remotes/').stdout.strip()
        reason = reason or ('未合并' if pushed else '未合并、未推送（无远程引用包含当前提交）')
    return branch, dirty, merged, reason


def main():
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['list', 'clean', 'prepare', 'auto'])
    p.add_argument('--dry', action='store_true')
    p.add_argument('--daily', action='store_true')
    p.add_argument('--all', action='store_true')
    p.add_argument('--repo', action='append'); p.add_argument('--branch'); p.add_argument('--base')
    p.add_argument('--now', action='store_true'); p.add_argument('--verbose', action='store_true')
    a = p.parse_args()
    if a.command == 'prepare':
        repo_arg = a.repo[-1] if isinstance(a.repo, list) else a.repo
        print(json.dumps(prepare(repo_arg, a.branch, a.base)))
        return
    if a.command == 'auto':
        raise SystemExit(auto(a.dry, a.daily, a.now, None, a.repo, a.verbose))
    if a.command == 'clean':
        raise SystemExit(auto(a.dry, False, True, a.all, a.repo, a.verbose))
    failed = False
    for repo, row, path, tasks in inventory(a.all):
        branch, dirty, merged, reason = inspect(repo, row, path)
        print(f'{path}\tbranch={branch or "(detached)"}\trepo={repo}\tdirty={dirty}\tmerged={merged}\ttasks={",".join(tasks) or "-"}')
        if a.command == 'list': continue
        if reason:
            print('  SKIP ' + reason); continue
        if a.dry:
            print('  DRY git worktree remove; git branch -d ' + branch); continue
        try:
            git(repo, 'worktree', 'remove', str(path))
            print('  REMOVED worktree')
            deleted = git(repo, 'branch', '-d', '--', branch, check=False)
            if deleted.returncode:
                print('  KEEP branch (-d refused): ' + deleted.stderr.strip())
            else: print('  DELETED branch ' + branch)
        except ValueError as e:
            print('  ERROR ' + str(e)); failed = True
    if failed: sys.exit(1)


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        sys.exit('worktrees: ' + str(e))
