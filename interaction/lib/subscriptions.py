"""Append-only subscription registry, with a stable lock."""
import datetime as dt
import fcntl
import json
import os
import re
import runpy
import uuid
from contextlib import contextmanager
from pathlib import Path
from .projects import canonical, match

I = Path(__file__).resolve().parents[1]
registry = runpy.run_path(str(I / 'lib/registry'))

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def read(path):
    if not path.exists(): return []
    result = []
    for line in path.read_text().splitlines():
        try: result.append(json.loads(line))
        except ValueError: continue
    return result

def append(path, row):
    with path.open('a') as f:
        if path.stat().st_size:
            with path.open('rb') as check:
                check.seek(-1, 2)
                if check.read(1) != b'\n': f.write('\n')
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())

@contextmanager
def locked(name):
    root = registry['state']()
    root.mkdir(parents=True, exist_ok=True)
    with (root / name).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield root

def latest():
    rows = {}
    for r in read(registry['state']() / 'subscriptions.jsonl'): rows[r['id']] = r
    return [r for r in rows.values() if not r.get('removed')]

def change(action, ident=None, *, project=None, thread=None, to=None, task=None):
    with locked('.subscriptions.lock') as root:
        rows = latest()
        if action == 'add':
            if to.startswith('codex:'):
                uuid.UUID(to[6:])
            elif not re.fullmatch(r'claude:local_[A-Za-z0-9_-]+', to):
                raise ValueError('target must be codex:UUID or claude:local_id')
            project = canonical(project)
            if thread and thread.startswith('project:'):
                thread = 'project:' + str(canonical(thread[8:]))
            if not project and not thread: raise ValueError('project or thread required')
            for r in rows:
                if (r.get('project'), r.get('thread_key'), r['to']) == (project, thread, to):
                    return r
            row = dict(id='sub_' + uuid.uuid4().hex, project=project, thread_key=thread,
                       to=to, paused=False, removed=False, task=task)
        else:
            row = next((dict(r) for r in rows if r['id'] == ident), None)
            if row is None: raise ValueError('unknown subscription')
            if action == 'remove': row['removed'] = True
            else: row['paused'] = action == 'pause'
        row['t'] = now()
        append(root / 'subscriptions.jsonl', row)
        return row

def matching(e):
    return [s for s in latest() if not s['paused'] and
            ((s.get('thread_key') and s['thread_key'] == e.get('thread_key')) or
             (not s.get('thread_key') and s.get('project') and s['project'] == e.get('project')))]

def auto(name, log, output, worktree):
    """Only successful worktree dispatch completion calls this."""
    text = '\n'.join(Path(p).read_text(errors='replace') for p in (log, output) if p and Path(p).exists())
    session = re.search(r'^session id: ([0-9a-fA-F-]{36})\s*$', text, re.M)
    if not session: return
    for repo, number in sorted(set(re.findall(r'https://github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)\b', text))):
        change('add', thread=f'gh:{repo.lower()}#{number}', to='codex:'+session[1], task=name)
