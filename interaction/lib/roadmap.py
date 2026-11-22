"""Canonical roadmap parsing and serialized, file-scoped completion writes."""
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
from .projects import mapping, canonical

STATES = ('💤', '📝', '🔨', '🔍', '✅', '❌')

def state():
    return Path(os.environ.get('PRTS_INTERACTION_STATE', Path(__file__).resolve().parents[1]/'state'))

def records():
    try:
        result = []
        for line in (state()/'roadmap-status.jsonl').read_text().splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict) and all(k in row for k in ('project','id','state','at')): result.append(row)
            except ValueError: continue
        return result
    except FileNotFoundError:
        return []

def rows(content):
    header, header_cells = None, []
    fence = None
    for n, raw in enumerate(content.splitlines(keepends=True)):
        stripped = raw.lstrip()
        if stripped.startswith(('```', '~~~')):
            marker = stripped[:3]
            fence = marker if fence is None else (None if marker == fence else fence)
            continue
        if fence: continue
        task = re.match(r'^\s*[-*+]\s+\[([ xX])\]\s+(.+)', raw)
        if task:
            yield n, None, None, dict(id=None, title=' '.join(task[2].split()), status=None,
                start=None, ddl=None, evidence=None, done=task[1] != ' ', auto=None)
            continue
        if not stripped.startswith('|'):
            header = None
            continue
        parts = re.split(r'(?<!\\)\|', raw)
        cells = [c.strip() for c in parts[1:-1]]
        aliases = {'#':'id', '编号':'id', 'ID':'id', '状态':'status', '事项':'title', '标题':'title', '开始':'start', 'DDL':'ddl', '完成证据':'evidence'}
        candidate = {aliases[c]:i for i,c in enumerate(cells) if c in aliases}
        if all(k in candidate for k in ('id','status','title')):
            header, header_cells = candidate, cells
            continue
        if not header or max(header.values()) >= len(cells): continue
        get = lambda k: cells[header[k]] or None if k in header else None
        ident = get('id')
        if not ident or not re.fullmatch(r'[A-Za-z]+\d+', ident): continue
        item = {k:get(k) for k in ('id','title','status','start','ddl','evidence')}
        item['title'] = ' '.join(item['title'].replace('**','').split()) if item['title'] else None
        for k in ('start','ddl'):
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', item[k] or ''): raise ValueError()
                dt.date.fromisoformat(item[k])
            except ValueError: item[k] = None
        if '类型' in header_cells: item['kind'] = cells[header_cells.index('类型')] or None   # optional column
        item.update(done=any(s in (item['status'] or '') for s in ('✅','❌')), auto=None)
        yield n, header, parts, item

def read(project):
    path = project.get('roadmap')
    result = dict(path=str(Path(path).expanduser()) if path else None, open=[], error=None, items=[], next_ddl=None)
    if not path: return result
    try:
        parsed = list(rows(Path(result['path']).read_text()))
        history = {(r['project'],r['id']):r for r in records()}
    except (OSError, UnicodeError, ValueError) as exc:
        result['error'] = str(exc)
        return result
    if not parsed: result['error'] = 'No supported roadmap table rows or Markdown checklist items found'
    for _, _, _, item in parsed:
        prefix = project.get('roadmap_prefix','')
        if prefix and not (item['id'] or '').startswith(prefix): continue
        old = history.get((project.get('name'),item['id']))
        if old: item['auto'] = {k:old.get(k) for k in ('state','url','at')}
        if (item['id'] is None and not item['done']) or (item['id'] and '✅' not in (item['status'] or '')):
            if len(result['open']) < 5: result['open'].append({k:item[k] for k in ('id','title','status')})
        if len(result['items']) < 60: result['items'].append(item)
        if not item['done'] and item['ddl']:
            result['next_ddl'] = min(result['next_ddl'] or item['ddl'], item['ddl'])
    return result

def project(name):
    name = canonical(name)
    found = [p for p in mapping() if p['name'] == name]
    if not found: raise ValueError('unknown project: '+name)
    result = dict(found[0])
    for p in found:
        for k,v in p.items():
            if not result.get(k): result[k] = v
    if not result.get('roadmap'): raise ValueError('project has no roadmap: '+name)
    return result

def locate(name, ident):
    p = project(name)
    path = Path(p['roadmap']).expanduser().resolve()
    content = path.read_bytes().decode('utf-8')
    found = [r for r in rows(content) if r[3]['id'] == ident and ident.startswith(p.get('roadmap_prefix',''))]
    if len(found) != 1: raise ValueError('unknown or ambiguous roadmap ID: '+ident)
    return p, path, content, found[0]

def git(path, *args):
    return subprocess.run(['git','-C',str(path),*args], stdin=subprocess.DEVNULL,
        capture_output=True,text=True,check=True).stdout.strip()

def mark(name, ident, status, evidence=None, auto=None, url=None):
    if status not in STATES: raise ValueError('invalid roadmap status: '+status)
    state().mkdir(parents=True, exist_ok=True)
    with (state()/'roadmap.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        p,path,content,(n,header,parts,item) = locate(name,ident)
        history = [r for r in records() if r['project']==p['name'] and r['id']==ident]
        if auto and (item['done'] or any(r['state'] in ('merged','accepted') for r in history)): return False
        if auto == 'pr_open' and history and history[-1]['state']=='pr_open' and history[-1].get('url')==url: return False
        if auto != 'pr_open':
            def replace(index, value):
                old = parts[index+1]
                parts[index+1] = old[:len(old)-len(old.lstrip())] + value + old[len(old.rstrip()):]
            replace(header['status'],status)
            if evidence is not None:
                evidence = ' '.join(evidence.split()).replace('|',r'\|')
                if 'evidence' in header: replace(header['evidence'], evidence)
                else:
                    index = len(parts)-3
                    replace(index, parts[index+1].strip() + ('；' if parts[index+1].strip() else '') + evidence)
            lines = content.splitlines(keepends=True)
            lines[n] = '|'.join(parts)
            updated = ''.join(lines)
            try: repo = Path(git(path.parent,'rev-parse','--show-toplevel'))
            except subprocess.CalledProcessError: repo = None   # e.g. ~/outreach: plain files, nothing to commit
            relative = repo and str(path.relative_to(repo))
            if updated != content:
                path.write_bytes(updated.encode('utf-8'))
            # Also retry a prior failed commit before recording completion.
            if repo and git(repo,'status','--porcelain','--',relative):
                try:
                    git(repo,'commit','--only','-m',f'roadmap: {p["name"]} {ident} {status}','--',relative)
                except subprocess.CalledProcessError:
                    path.write_bytes(content.encode('utf-8'))
                    raise
        if auto:
            row = dict(project=p['name'],id=ident,state=auto,url=url,at=dt.datetime.now(dt.timezone.utc).isoformat())
            with (state()/'roadmap-status.jsonl').open('a+') as f:
                f.seek(0)
                existing = f.read()
                if existing and not existing.endswith('\n'): f.write('\n')
                f.write(json.dumps(row,ensure_ascii=False)+'\n')
                f.flush()
                os.fsync(f.fileno())
        return True

def observe(name, detail):
    if not name: return
    p = project(name)
    text = ' '.join(str(detail.get(k) or '') for k in ('title','headRefName','body'))
    status = detail.get('state')
    if status not in ('OPEN','MERGED'): return
    for _, _, _, item in rows(Path(p['roadmap']).expanduser().read_text()):
        ident = item['id']
        if not ident or not ident.startswith(p.get('roadmap_prefix','')): continue
        if ident and re.search(r'(?<!\w)'+re.escape(ident)+r'(?!\w)', text):
            mark(name,ident,'✅',detail.get('url'),auto='merged' if status=='MERGED' else 'pr_open',url=detail.get('url'))

def meetings(project):
    result = []
    for value in project.get('meetings',[]):
        m = re.fullmatch(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([0-2]\d:[0-5]\d)-([0-2]\d:[0-5]\d)',value)
        if m and m[2] < '24:00' and m[3] < '24:00':
            result.append(dict(weekday=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].index(m[1])+1,start=m[2],end=m[3]))
    return result


def completed(project, since):
    """Find transitions to complete in committed history, including manual edits."""
    if not project.get('roadmap'): return []
    path = Path(project['roadmap']).expanduser().resolve()
    try:
        repo = Path(git(path.parent, 'rev-parse', '--show-toplevel'))
        relative = str(path.relative_to(repo))
        commits = git(repo, 'log', '--since='+since, '--format=%H', '--', relative).splitlines()
        found = set()
        for commit in commits:
            after = git(repo, 'show', commit+':'+relative)
            try: before = git(repo, 'show', commit+'^:'+relative)
            except subprocess.CalledProcessError: before = ''
            old = {r[3]['id']:r[3] for r in rows(before)}
            for _,_,_,item in rows(after):
                ident = item['id']
                if ident and item['status']=='✅' and old.get(ident,{}).get('status')!='✅': found.add(ident)
        return [i for i in read(project)['items'] if i['id'] in found and i['status']=='✅']
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
