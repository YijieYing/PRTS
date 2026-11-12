"""Compatibility dependency on undocumented OpenAI Skysight internal formats.

All event/summary parsing lives here. Only allowlisted metadata is retained;
AX, keyboard payloads, selection text and URL paths/queries are never used.
No activity is extrapolated across missing minutes. Sources are read-only.
"""
from datetime import datetime
import fcntl
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

COUNTS = {'mouse.click': 'clicks', 'keyboard.text_input': 'typing',
          'keyboard.submit': 'submits', 'keyboard.shortcut': 'shortcuts',
          'selection.changed': 'selections'}


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def event(row):
    """Return only permitted fields, never inspect payloads of input events."""
    t = timestamp(row['timestamp'])
    app, window = row.get('app') or {}, row.get('window') or {}
    return dict(time=t, kind=row.get('kind',''), app=app.get('name',''),
                bundle=app.get('bundleIdentifier',''), title=window.get('title',''),
                domain=urlparse(window.get('url') or '').hostname or '')


def aggregate(events):
    buckets = {}
    for e in sorted(events, key=lambda e:e['time']):
        minute = int(e['time']//60)*60
        key = (minute,e['bundle'],e['app'],e['title'],e['domain'])
        if key not in buckets:
            buckets[key] = dict(type='minute', time=minute, app=e['app'], bundle=e['bundle'],
                                title=e['title'], domain=e['domain'], counts={v:0 for v in COUNTS.values()},
                                active=False, last=e['time'], last_typing=None)
        m = buckets[key]
        m['last'] = e['time']
        if e['kind'] in COUNTS:
            m['counts'][COUNTS[e['kind']]] += 1
            m['active'] = True
        if e['kind']=='keyboard.text_input': m['last_typing']=e['time']
    return list(buckets.values())


def summary(path):
    match = re.match(r'(\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d)(?:Z)?-.*-(10min|6h)-',path.name)
    if not match: return None
    t = datetime.strptime(match[1],'%Y-%m-%dT%H-%M-%S').replace(tzinfo=ZoneInfo('UTC')).timestamp()
    text = path.read_text()
    header = re.match(r'\A---\s*\n(.*?)\n---\s*\n',text,re.S)
    fields = {}
    # Deliberately small YAML subset: top-level scalars, quoted and block forms.
    if header:
        lines=header[1].splitlines()
        for i,line in enumerate(lines):
            m=re.match(r'^(title|description):\s*(.*)$',line)
            if not m: continue
            value=m[2]
            if value in ('>', '|', '>-', '|-'):
                block=[]
                for following in lines[i+1:]:
                    if following and not following.startswith((' ', '\t')): break
                    block.append(following.strip())
                value=('\n' if value.startswith('|') else ' ').join(block)
            elif value.startswith('"'):
                try: value=json.loads(value)
                except ValueError: value=value.strip('"')
            elif value.startswith("'"): value=value.strip("'").replace("''", "'")
            fields[m[1]]=value
    recording=re.search(r'^## Recording summary\s*\n(.*?)(?=^## |\Z)',text,re.M|re.S)
    return dict(type='summary', id=path.name, time=t, end=t+(600 if match[2]=='10min' else 21600),
                period=match[2], title=fields.get('title',''), description=fields.get('description',''),
                recording=recording[1].strip() if recording else '')


def key(row):
    return ('summary',row['id']) if row['type']=='summary' else ('minute',row['time'],row['bundle'],row['app'],row['title'],row['domain'])


def load(config, start, end, state, warnings):
    saved, raw = {}, {}
    for path in (Path(state)/'computer').glob('*.jsonl'):
        try:
            for line in path.read_text().splitlines():
                row=json.loads(line)
                if row['type']=='minute' and start <= row['last'] < end: saved[key(row)]=row
                elif row['type']=='summary' and row['end']<=end and row['end']>start: saved[key(row)]=row
        except (OSError,ValueError,KeyError,TypeError): warnings.add('Computer History 部分存档无法读取')
    events, seen = [], set()
    root=config.get('computer_events')
    for path in sorted(Path(root).expanduser().glob('*/events.jsonl')) if root else []:
        try:
            with path.open() as f:
                for line in f:
                    try:
                        row=json.loads(line); e=event(row)
                        identity=(row.get('id'),e['time'])
                        if identity in seen and row.get('id') is not None: continue
                        seen.add(identity)
                        if start <= e['time'] < end: events.append(e)
                    except (ValueError,KeyError,TypeError,AttributeError): warnings.add('Computer History 部分事件无法解析')
        except OSError: warnings.add('Computer History 事件无法读取')
    # A raw minute replaces its entire archived minute, including removed contexts.
    minutes=aggregate(events)
    present={r['time'] for r in minutes}
    saved={k:r for k,r in saved.items() if r['type']!='minute' or r['time'] not in present}
    for r in minutes: raw[key(r)]=r
    root=config.get('computer_summaries')
    for path in sorted(Path(root).expanduser().glob('*.md')) if root else []:
        try:
            r=summary(path)
            if r and r['end'] <= end and r['end']>start: raw[key(r)]=r
        except (OSError,ValueError,TypeError): warnings.add('Computer History 部分摘要无法读取')
    rows=list((saved|raw).values())
    minutes=sorted((r for r in rows if r['type']=='minute'),key=lambda r:(r['time'],r['last']))
    summaries=sorted((r for r in rows if r['type']=='summary'),key=lambda r:r['time'])
    if minutes and not events: warnings.add('Computer History 原始事件不存在或本时段为空；已从分钟存档恢复')
    if not minutes: warnings.add('Computer History 数据源不存在或本时段为空；未计入电脑活动')
    return minutes,summaries


def archive(config, start, end, state, date, warnings):
    directory=Path(state)/'computer'; directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (directory/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        minutes,summaries=load(config,start,end,state,warnings)
        path=directory/(date+'.jsonl')
        # Keep later observations when replaying an earlier --at.
        rows={}
        if path.exists():
            for line in path.read_text().splitlines():
                r=json.loads(line); rows[key(r)]=r
        present={r['time'] for r in minutes}
        rows={k:r for k,r in rows.items() if r['type']!='minute' or r['time'] not in present or r['last']>=end}
        future={r['time'] for r in rows.values() if r['type']=='minute' and r['last']>=end}
        rows.update({key(r):r for r in minutes+summaries if r['type']!='minute' or r['time'] not in future})
        with tempfile.NamedTemporaryFile(mode='w',dir=directory,delete=False) as f:
            for r in sorted(rows.values(),key=lambda r:(r['time'],str(key(r)))):
                f.write(json.dumps(r,ensure_ascii=False)+'\n')
        Path(f.name).replace(path)
        return path


def project(row, mapping):
    text=(row['title']+' '+row['domain']).casefold()
    for item in mapping:
        path=str(Path(item['path']).expanduser()).rstrip('/')
        if path==str(Path.home()): continue
        terms=[path,item['name'],Path(path).name]
        if any(len(term)>2 and re.search(r'(?<![\w])'+re.escape(term.casefold())+r'(?![\w])',text) for term in terms): return item['name']
    return '其他'


def source(row):
    app=(row['app']+' '+row['bundle']).lower()
    if 'claude' in app: return 'claude'
    if 'codex' in app: return 'codex'
    if 'chrome' in app and row['domain'] in ('chatgpt.com','www.chatgpt.com'): return 'chatgpt'
    return None
