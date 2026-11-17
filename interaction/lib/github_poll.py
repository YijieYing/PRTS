"""Observe other users feedback and CI transitions, then classify events."""
import hashlib
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

I = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(I.parent))
from interaction.lib.projects import match as project_match
from interaction.lib.roadmap import observe, project as roadmap_project

REPO_PROJECTS = {}
registry = runpy.run_path(str(I / 'lib/registry'))
TIMEOUT = 30
COMPACT_BYTES = 1024 * 1024
PR_LIMIT = 10000


def run(args, **kwargs):
    return subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=TIMEOUT, check=True, **kwargs).stdout


def error(context, exc):
    detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
    print(f'github_poll: {context}: {detail}', file=sys.stderr)


def repositories():
    result = set()
    history = registry['rows']()
    origins = {r.get('cwd'): (r.get('worktree') or {}).get('repo') for r in history if r.get('worktree')}
    cwds = {r.get('cwd') for r in history if isinstance(r.get('cwd'), str) and r['cwd']}
    for cwd in sorted(cwds):
        try:
            remote = run(['git', '-C', cwd, 'remote', 'get-url', 'origin']).strip()
        except (OSError, subprocess.SubprocessError):
            continue  # Deleted directories and non-repositories are ordinary registry history.
        match = re.fullmatch(r'(?:git@github\.com:|(?:https?|ssh|git)://(?:git@)?github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?/?', remote, re.I)
        if match:
            result.add(match[1].lower())
            project = project_match(origins.get(cwd) or cwd)
            if project: REPO_PROJECTS[match[1].lower()] = project
    return sorted(result)


def ci_state(checks):
    if not isinstance(checks, list):
        raise ValueError('statusCheckRollup must be a list')
    if not checks:
        return 'none'
    states = []
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError('invalid check')
        if 'status' in check:
            value = check.get('conclusion') if check['status'] == 'COMPLETED' else 'PENDING'
        else:
            value = check.get('state')
        states.append(str(value or 'UNKNOWN').upper())
    if any(s in {'FAILURE', 'ERROR', 'TIMED_OUT', 'CANCELLED', 'ACTION_REQUIRED', 'STARTUP_FAILURE'} for s in states):
        return 'failure'
    if any(s in {'PENDING', 'EXPECTED', 'QUEUED', 'IN_PROGRESS', 'WAITING', 'REQUESTED'} for s in states):
        return 'pending'
    if all(s in {'SUCCESS', 'NEUTRAL', 'SKIPPED'} for s in states):
        return 'success'
    return 'unknown'


def read_cursors(path):
    latest = {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
                key = row['key']
                if row.get('deleted'):
                    latest.pop(key, None)
                else:
                    latest[key] = row
            except (ValueError, KeyError, TypeError):
                continue  # Incomplete trailing records can be retried on the next poll.
    return latest


def append(path, row):
    with path.open('a', encoding='utf-8') as stream:
        # Repair a torn trailing line before appending another JSON record.
        if path.stat().st_size:
            with path.open('rb') as check:
                check.seek(-1, 2)
                if check.read(1) != b'\n':
                    stream.write('\n')
        stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def poll(repo: str, state_dir: Path) -> list[dict]:
    """Serialize compare/delivery/checkpoint, returning successfully queued events."""
    events = []
    state_dir = Path(state_dir).resolve()
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        with (state_dir / '.github_poll.lock').open('a') as lock:
            # Skip overlapping runs instead of waiting indefinitely for another poller.
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return events
            user_path = state_dir / 'github_user.json'
            if user_path.exists():
                login = json.loads(user_path.read_text())['login']
            else:
                login = json.loads(run(['gh', 'api', 'user']))['login']
                user_path.write_text(json.dumps({'login': login}))
            path = state_dir / 'github_poll.jsonl'
            latest = read_cursors(path)
            roadmap_name = REPO_PROJECTS.get(repo)
            if roadmap_name:
                try: roadmap_project(roadmap_name)
                except ValueError: roadmap_name = None
            prs = json.loads(run(['gh', 'pr', 'list', '--repo', repo, '--state', 'all' if roadmap_name else 'open',
                                 '--json', 'number,updatedAt,state,title,body,headRefName,url' if roadmap_name else 'number,updatedAt', '--limit', str(PR_LIMIT)]))
            if not isinstance(prs, list) or len(prs) >= PR_LIMIT:
                raise ValueError('invalid or truncated PR list')
            numbers = {pr['number'] for pr in prs}
            if any(type(n) is not int or n <= 0 for n in numbers):
                raise ValueError('invalid PR number')
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            listed = {pr['number']: pr for pr in prs}
            closed_numbers = set()
            for number in sorted(numbers):
                key = f'{repo}#{number}'
                try:
                    if roadmap_name and listed[number].get('state') in ('CLOSED', 'MERGED'):
                        observe(roadmap_name, listed[number])
                        closed_numbers.add(number)
                        continue
                    detail = json.loads(run(['gh', 'pr', 'view', str(number), '--repo', repo,
                                             '--json', 'comments,reviews,statusCheckRollup,updatedAt,title,body,headRefName,state,url']))
                    if roadmap_name:
                        observe(roadmap_name, detail)
                    if detail.get('state') in ('CLOSED', 'MERGED'):
                        closed_numbers.add(number)
                        continue
                    if not isinstance(detail['comments'], list) or not isinstance(detail['updatedAt'], str):
                        raise ValueError('invalid PR details')
                    inline_pages = json.loads(run(['gh', 'api', '--paginate', '--slurp',
                        f'repos/{repo}/pulls/{number}/comments']))
                    inline = [comment for page in inline_pages for comment in page]
                    def others(items):
                        return sum(1 for item in items if
                            (item.get('author') or item.get('user') or {}).get('login') not in (None, login))
                    row = dict(key=key, updated_at=detail['updatedAt'], comments=others(detail['comments']),
                               reviews=others(detail['reviews']), inline=others(inline),
                               ci=ci_state(detail['statusCheckRollup']))
                    old = latest.get(key)
                    fields = ('comments', 'reviews', 'inline', 'ci')
                    if old and all(old.get(f) == row[f] for f in fields):
                        continue
                    if old and all(f in old for f in fields):
                        changes = []
                        if old['comments'] != row['comments']:
                            changes.append(f"评论数从 {old['comments']} 变成 {row['comments']}")
                        for field, label in (('reviews', '评审数'), ('inline', '行内意见数')):
                            if old[field] != row[field]:
                                changes.append(f"{label}从 {old[field]} 变成 {row[field]}")
                        if old['ci'] != row['ci']:
                            changes.append(f"CI 从 {old['ci']} 变成 {row['ci']}")
                        text = key + ' ' + '；'.join(changes or ['有更新'])
                        env = dict(os.environ, PRTS_INTERACTION_STATE=str(state_dir))
                        event_id = 'gh:' + hashlib.sha256(json.dumps([key, old, row], sort_keys=True).encode()).hexdigest()
                        command = [str(I / 'bin/event'), 'add', 'L1', 'github_poll', text,
                                   '--thread', 'gh:'+key, '--kind', 'github_poll', '--id', event_id]
                        if REPO_PROJECTS.get(repo): command += ['--project', REPO_PROJECTS[repo]]
                        run(command, env=env)
                        events.append(dict(level='L1', source='github_poll', text=text))
                    row['t'] = now
                    append(path, row)  # Never advance a cursor if event delivery failed.
                    latest[key] = row
                except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
                    error(key, exc)
            # Tombstones remove feedback cursors for PRs no longer in the query.
            active = {f'{repo}#{n}' for n in numbers - closed_numbers}
            for key in list(latest):
                if key.startswith(repo + '#') and key not in active:
                    append(path, dict(key=key, deleted=True, t=now))
                    del latest[key]
            if path.exists() and path.stat().st_size > COMPACT_BYTES:
                tmp = path.with_suffix('.tmp')
                tmp.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in latest.values()))
                tmp.replace(path)  # Stable separate lock also covers replacement.
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        error(repo, exc)
    return events


def main():
    for repo in repositories():
        poll(repo, registry['state']())
    return 0
