"""Worktree creation, inventory and conservative cleanup."""
import argparse
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

registry = runpy.run_path(str(Path(__file__).with_name('registry')))


def run(args, cwd=None, check=True):
    p = subprocess.run(args, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    if check and p.returncode:
        raise ValueError(p.stderr.strip() or p.stdout.strip() or 'command failed: ' + ' '.join(args))
    return p


def git(repo, *args, check=True):
    return run(['git', '-C', str(repo), *args], check=check)


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
        if r.get('worktree'): candidates.append(Path(r['worktree']['repo']))
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


def inspect(repo, row, path):
    branch = row.get('branch', '').removeprefix('refs/heads/')
    status = git(path, 'status', '--porcelain', '--untracked-files=all', check=False)
    dirty = bool(status.stdout.strip()) or status.returncode != 0
    merged = False
    reason = ''
    try:
        ref = default_ref(repo)
        merged = git(repo, 'merge-base', '--is-ancestor', row['HEAD'], ref, check=False).returncode == 0
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
    p.add_argument('command', choices=['list', 'clean', 'prepare'])
    p.add_argument('--dry', action='store_true')
    p.add_argument('--all', action='store_true')
    p.add_argument('--repo'); p.add_argument('--branch'); p.add_argument('--base')
    a = p.parse_args()
    if a.command == 'prepare':
        print(json.dumps(prepare(a.repo, a.branch, a.base)))
        return
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
