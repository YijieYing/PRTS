"""Project groups, roadmap items and registry-backed teams for status."""
import datetime as dt
from pathlib import Path
import re

from .projects import mapping, match


def timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.replace(tzinfo=dt.timezone.utc) if parsed.tzinfo is None else parsed
    except (TypeError, ValueError, AttributeError):
        return None


def line(value):
    return ' '.join(value.split()) or None


def roadmap(project):
    path = project.get('roadmap')
    result = dict(path=str(Path(path).expanduser()) if path else None, open=[], error=None)
    if not path:
        return result
    try:
        content = Path(result['path']).read_text()
    except (OSError, UnicodeError) as exc:
        result['error'] = str(exc)
        return result
    recognized = False
    fence = None
    prefix = project.get('roadmap_prefix', '')
    for raw in content.splitlines():
        stripped = raw.lstrip()
        if stripped.startswith(('```', '~~~')):
            marker = stripped[:3]
            if fence is None: fence = marker
            elif marker == fence: fence = None
            continue
        if fence: continue
        item = None
        task = re.match(r'^\s*[-*+]\s+\[([ xX])\]\s+(.+)', raw)
        cells = [c.strip() for c in re.split(r'(?<!\\)\|', raw.strip().strip('|'))]
        if task:
            recognized = True
            if task[1] == ' ' and not prefix:
                item = dict(id=None, title=line(task[2]), status=None)
        elif raw.lstrip().startswith('|') and len(cells) >= 3 and re.fullmatch(r'[A-Za-z]+\d+', cells[0]):
            recognized = True
            if '✅' not in cells[1] and cells[0].startswith(prefix):
                item = dict(id=cells[0], title=line(cells[2].replace('**', '')), status=cells[1] or None)
        if item and len(result['open']) < 5:
            result['open'].append(item)
    if not recognized:
        result['error'] = 'No supported roadmap table rows or Markdown checklist items found'
    return result


def activity(rows, items):
    """Use every dispatch run, never carry an earlier run's caller/thread forward."""
    runs, current = [], {}
    for row in rows:
        name, event = row.get('name'), row.get('event')
        if event == 'start':
            run = dict(row, last_active=row.get('t'))
            current[name] = run
            runs.append(run)
        elif name in current:
            run = current[name]
            if event == 'caller': run['caller'] = row.get('caller')
            if event == 'thread': run['thread'] = row.get('thread')
            if event in ('thread', 'exit', 'gave_up') and timestamp(row.get('t')):
                if not timestamp(run['last_active']) or timestamp(row['t']) > timestamp(run['last_active']):
                    run['last_active'] = row['t']
    result = {}
    for run in runs:
        project = match((run.get('worktree') or {}).get('repo') or run.get('cwd'), items)
        targets = []
        if run.get('thread'): targets.append(('codex', run['thread'], run['last_active']))
        caller = run.get('caller') or {}
        if caller.get('kind') in ('claude', 'codex') and caller.get('id'):
            # Caller activity is the dispatch itself, not the child's subsequent exit.
            targets.append((caller['kind'], caller['id'], run.get('t')))
        for kind, ident, active in targets:
            member = dict(kind=kind, id=kind+':'+ident, title=line(run.get('name', '')),
                          subscribed=False, last_active=active if timestamp(active) else None)
            members = result.setdefault(project, {})
            old = members.get(member['id'])
            if old is None or (timestamp(active) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)) > (timestamp(old['last_active']) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)):
                members[member['id']] = member
    return result


def groups(threads, subscriptions, rows, generated_at):
    items = mapping()
    projects, grouped = {}, {}
    for item in items:
        project = projects.setdefault(item['name'], dict(item, paths=[]))
        if item['path'] not in project['paths']: project['paths'].append(item['path'])
        for key in ('group', 'roadmap', 'roadmap_prefix'):
            if not project.get(key) and item.get(key): project[key] = item[key]
        if item.get('group'): grouped.setdefault(item['group'], [])
    teams = activity(rows, items)
    current = timestamp(generated_at)
    cutoff = current - dt.timedelta(days=14)
    for name, project in projects.items():
        key = 'project:'+name
        thread = threads.get(key, {})
        members = teams.get(name, {})
        subscribers = {}
        for sub in subscriptions:
            if sub.get('paused') or (sub.get('thread_key') or 'project:'+str(sub.get('project'))) != key:
                continue
            target = sub['to']
            kind = target.split(':', 1)[0]
            subscribers[target] = dict(members.get(target) or dict(kind=kind, id=target, title=None, last_active=None), subscribed=True)
        recent = [m for ident, m in members.items() if ident not in subscribers and
                  timestamp(m['last_active']) and cutoff <= timestamp(m['last_active']) <= current]
        minimum = dt.datetime.min.replace(tzinfo=dt.timezone.utc)
        order = lambda m: (-(timestamp(m['last_active']) or minimum).timestamp(), m['id'])
        team = sorted([*subscribers.values(), *sorted(recent, key=order)[:10]], key=order)
        tasks = thread.get('tasks', [])
        view = dict(name=name, thread=key, paths=project['paths'], roadmap=roadmap(project), team=team,
                    tasks_running=sum(t['status'] == 'running' for t in tasks),
                    tasks_unreviewed=sum(t['status'] != 'running' and not t['reviewed'] for t in tasks),
                    last_event_at=thread.get('last_event_at'))
        grouped.setdefault(project.get('group') or '未分组', []).append(view)
    names = [n for n in grouped if n != '未分组'] + (['未分组'] if '未分组' in grouped else [])
    return [dict(name=n, projects=grouped[n]) for n in names]
