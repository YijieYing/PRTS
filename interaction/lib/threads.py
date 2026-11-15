"""Read-only projection for AgentConsole; all fields form the CLI contract."""
from .projects import canonical, match
from .groups import groups
from .subscriptions import latest, read, registry, now

def snapshot():
    root = registry['state']()
    threads = {}
    def get(key, project=None):
        if key not in threads:
            kind = key.split(':', 1)[0]
            threads[key] = dict(key=key, kind=kind if kind in ('project', 'gh', 'ear') else 'other',
                project=project, title=key.split(':', 1)[-1], subscribers=[],
                last_event_at=None, last_event=None, counts=dict(events=0, routed=0, pending=0), tasks=[])
        if project: threads[key]['project'] = project
        return threads[key]
    subscriptions = latest()
    for sub in subscriptions:
        key = sub.get('thread_key') or 'project:'+sub['project']
        project = sub.get('project') or (key[8:] if key.startswith('project:') else None)
        get(key, project)['subscribers'].append({k: sub[k] for k in ('id', 'to', 'paused')})
    events = read(root/'events/queue.jsonl')
    for e in events:
        if e.get('parent_id'): continue
        project = canonical(e.get('project'))
        keys = {k for k in (e.get('thread_key'), 'project:'+project if project else None) if k}
        for key in keys:
            thread = get(key, project)
            thread['counts']['events'] += 1
            thread['counts']['pending'] += int(e.get('status') == 'new')
            thread['counts']['routed'] += int(e.get('status') == 'routed')
            if e.get('t', '') >= (thread['last_event_at'] or ''):
                thread['last_event_at'] = e.get('t')
                thread['last_event'] = ' '.join(e.get('text', '').split())[:240] or None
    tasks = {}
    rows = registry['rows']()
    for r in rows:
        name = r.get('name')
        if not name: continue
        if r.get('event') == 'start':
            tasks[name] = dict(r, status='running', reviewed=False)
        elif name in tasks:
            task = tasks[name]
            if r.get('event') == 'thread': task['thread'] = r.get('thread')
            if r.get('event') in ('exit', 'gave_up'):
                task['status'] = 'done' if r.get('event') == 'exit' and r.get('rc') == 0 else 'failed'
            if r.get('event') == 'reviewed': task['reviewed'] = r['reviewed']
    for name, task in tasks.items():
        project = match((task.get('worktree') or {}).get('repo') or task.get('cwd'))
        keys = {'project:'+project} if project else set()
        for sub in subscriptions:
            if sub.get('task') == name or (task.get('thread') and sub['to'] == 'codex:'+task['thread']):
                keys.add(sub.get('thread_key') or 'project:'+sub['project'])
        for e in events:
            if e.get('task') == name or (task.get('thread') and e.get('thread_uuid') == task['thread']):
                if e.get('thread_key'): keys.add(e['thread_key'])
        report = root/'tasks'/name/'last.md'
        view = dict(name=name, status=task['status'], started_at=task['t'],
                    report=str(report.resolve()) if report.is_file() else None, reviewed=task['reviewed'])
        for key in keys: get(key, project)['tasks'].append(view)
    generated_at = now()
    return dict(generated_at=generated_at, threads=[threads[k] for k in sorted(threads)],
                groups=groups(threads, subscriptions, rows, generated_at))
