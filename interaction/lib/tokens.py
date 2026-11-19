#!/usr/bin/env python3
"""Incremental token ledger. input is non-cached input; output includes reasoning."""
import argparse, datetime as dt, hashlib, json, os, sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo
try:
    from .projects import match as project_match
except ImportError:
    import sys; sys.path.insert(0, str(Path(__file__).resolve().parent)); from projects import match as project_match

ROOT=Path(__file__).resolve().parents[1]
STATE=Path(os.environ.get('PRTS_INTERACTION_STATE',ROOT/'state'))/'tokens'
TZ=ZoneInfo('Asia/Tokyo'); FIELDS=('input','cache_write','cache_read','output','reasoning')
TOTAL_FIELDS=('input_tokens','cached_input_tokens','cache_write_input_tokens','output_tokens','reasoning_output_tokens')
def _path(n): return STATE/n
def _load(n,d):
    try: return json.loads(_path(n).read_text())
    except (OSError,ValueError): return d
def _save(n,v):
    STATE.mkdir(parents=True,exist_ok=True); p=_path(n); t=p.with_suffix('.tmp'); t.write_text(json.dumps(v,ensure_ascii=False,separators=(',',':'))); t.replace(p)
def _num(v): return int(v or 0) if isinstance(v,(int,float)) else 0
def _stamp(v,fallback):
    if not v: return fallback
    if isinstance(v,(int,float)): return dt.datetime.fromtimestamp(v/1000 if v>10**11 else v,dt.timezone.utc).isoformat()
    return str(v)

def _registry():
    p=Path(os.environ.get('PRTS_INTERACTION_STATE',ROOT/'state'))/'registry.jsonl'
    try: rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except (OSError,ValueError): rows=[]
    task_by_thread={}; tags_by_task={}; caller_task={}; starts={}
    for r in rows:
        name=r.get('name')
        if r.get('event')=='start' and name:
            starts[name]=r
            if r.get('tags'): tags_by_task[name]=r['tags']
            if r.get('caller',{}).get('id'): caller_task[r['caller']['id']]=name
            if r.get('thread'): task_by_thread[r['thread']]=name
        if r.get('event')=='thread' and r.get('thread') and name: task_by_thread[r['thread']]=name
    for name,r in starts.items():
        if r.get('thread'): task_by_thread[r['thread']]=name
    return task_by_thread,tags_by_task,caller_task
def _claude_files(): return sorted(Path(os.path.expanduser('~/.claude/projects')).glob('**/*.jsonl'))
def _codex_files(): return sorted(Path(os.path.expanduser('~/.codex/sessions')).glob('**/*.jsonl'))
def _claude_ids(p):
    sid=p.stem; parent=None
    if 'subagents' in p.parts:
        i=p.parts.index('subagents'); parent=p.parts[i-1] if i else None
    return sid,parent
def _claude_values(u): return {'input':_num(u.get('input_tokens')),'cache_write':_num(u.get('cache_creation_input_tokens')),'cache_read':_num(u.get('cache_read_input_tokens')),'output':_num(u.get('output_tokens')),'reasoning':_num((u.get('output_tokens_details') or {}).get('thinking_tokens'))}
def _codex_values(u):
    cached=_num(u.get('cached_input_tokens'))
    return {'input':max(0,_num(u.get('input_tokens'))-cached),'cache_write':_num(u.get('cache_write_input_tokens')),'cache_read':cached,'output':_num(u.get('output_tokens')),'reasoning':_num(u.get('reasoning_output_tokens'))}
def _sig(t): return tuple(_num(t.get(k)) for k in TOTAL_FIELDS)
def _delta(total,previous,last):
    cur=_sig(total)
    if previous is None: return (dict(total) if any(cur) else dict(last)),'initial'
    old=_sig(previous)
    if cur==old: return None,'repeat'
    if any(a<b for a,b in zip(cur,old)): return dict(last),'reset'
    return {k:_num(total.get(k))-_num(previous.get(k)) for k in TOTAL_FIELDS},'delta'

def sync(rebuild=False):
    STATE.mkdir(parents=True,exist_ok=True)
    if rebuild:
        for n in ('index.json','seen.json','ledger.jsonl'): _path(n).unlink(missing_ok=True)
    index=_load('index.json',{}); seen=set(_load('seen.json',[])); rows=[]; bytes_read=0
    task_by_thread,tags_by_task,caller_task=_registry(); codex_models={}
    db=Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'state_5.sqlite'
    try:
        with sqlite3.connect(f'file:{db}?mode=ro',uri=True) as con:
            codex_models={row[0]:row[1] for row in con.execute('select id,model from threads') if row[1]}
    except (OSError,sqlite3.Error): pass
    paths=[('claude',p) for p in _claude_files()]+[('codex',p) for p in _codex_files()]
    for agent,p in paths:
        key=str(p); st=index.get(key,{}); stat=p.stat(); off=st.get('offset',0)
        if off>stat.st_size or stat.st_mtime<st.get('mtime',0) or (st.get('inode') and st['inode']!=stat.st_ino): off=0
        meta={}; title=st.get('title',''); cwd=''
        if agent=='codex':
            try:
                with p.open(errors='replace') as mf:
                    for line in mf:
                        try: x=json.loads(line)
                        except ValueError: continue
                        if x.get('type')=='session_meta': meta=x.get('payload') or {}; break
            except OSError: pass
            cwd=meta.get('cwd') or ''
        sid,parent=_claude_ids(p) if agent=='claude' else (meta.get('id') or meta.get('session_id') or p.stem,None)
        previous=st.get('codex_total') if agent=='codex' else None; total_seen=set(st.get('codex_seen_totals',[])) if agent=='codex' else set()
        with p.open('rb') as f:
            f.seek(off)
            while True:
                rawpos=f.tell(); raw=f.readline()
                if not raw: break
                bytes_read+=len(raw)
                try: rec=json.loads(raw)
                except ValueError: continue
                stamp=_stamp(rec.get('timestamp'),dt.datetime.fromtimestamp(stat.st_mtime,dt.timezone.utc).isoformat())
                if agent=='codex' and not title:
                    pl=rec.get('payload') or {}; text=''
                    if pl.get('type')=='message' and pl.get('role')=='user':
                        content=pl.get('content')
                        if isinstance(content,str): text=content
                        elif isinstance(content,list): text=' '.join(x.get('text','') for x in content if isinstance(x,dict))
                    if text: title=text.strip().replace('\n',' ')[:40]
                if agent=='claude':
                    msg=rec.get('message') or {}; usage=msg.get('usage')
                    if not title and rec.get('type')=='user' and isinstance(msg.get('content'),str): title=msg['content'].strip().replace('\n',' ')[:40]
                    if not isinstance(usage,dict): continue
                    ident=msg.get('id') or rec.get('uuid') or hashlib.sha1(raw).hexdigest(); uid='claude:'+ident
                    if uid in seen: continue
                    cwd=cwd or rec.get('cwd') or ''
                    task=caller_task.get(sid) or caller_task.get(parent or '')
                    row={'time':stamp,'agent':'claude','model':msg.get('model'),'session':sid,'thread':sid,'parent_session':parent,'cwd':cwd,'project':project_match(cwd),'task':task,'title':title,'tags':tags_by_task.get(task,{}),**_claude_values(usage)}
                    seen.add(uid)
                else:
                    payload=rec.get('payload') or {}; info=payload.get('info') or {}; last=info.get('last_token_usage'); total=info.get('total_token_usage')
                    if rec.get('type')!='event_msg' or payload.get('type')!='token_count' or not isinstance(last,dict): continue
                    if not isinstance(total,dict): total=last
                    delta,mode=_delta(total,previous,last)
                    if delta is None: continue
                    sig=':'.join(str(x) for x in _sig(total))
                    if sig in total_seen or 'codex-total:'+sig in seen:
                        previous=total; continue
                    total_seen.add(sig); seen.add('codex-total:'+sig); previous=total
                    task=task_by_thread.get(sid)
                    row={'time':stamp,'agent':'codex','model':meta.get('model') or codex_models.get(sid),'session':sid,'thread':sid,'parent_session':meta.get('parent_thread_id') or meta.get('parent_session_id'),'cwd':cwd,'project':project_match(cwd),'task':task,'title':meta.get('title') or meta.get('name') or task or title,'tags':tags_by_task.get(task,{}),**_codex_values(delta)}
                    seen.add('codex:'+sid+':'+sig)
                rows.append(row)
            off=f.tell()
        state={'offset':off,'mtime':stat.st_mtime,'inode':stat.st_ino}
        if agent=='codex': state.update(codex_total=previous,codex_seen_totals=sorted(total_seen))
        if title: state['title']=title
        index[key]=state
    with _path('ledger.jsonl').open('a',encoding='utf-8') as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    _save('index.json',index); _save('seen.json',sorted(seen)); return {'rows':len(rows),'bytes':bytes_read,'files':len(paths)}

def read_rows():
    try: return [json.loads(x) for x in _path('ledger.jsonl').read_text().splitlines() if x.strip()]
    except OSError: return []
def _filtered(a):
    if not a.no_sync: sync()
    now=dt.datetime.now(TZ); since=getattr(a,'since',None); until=getattr(a,'until',None)
    shift=dt.timedelta(hours=5) if getattr(a,'logical_day',False) else dt.timedelta(0)
    start=dt.datetime.fromisoformat(since).replace(tzinfo=TZ)+shift if since else now-dt.timedelta(days=7)
    end=dt.datetime.fromisoformat(until).replace(tzinfo=TZ)+dt.timedelta(days=1)+shift if until else now
    tags=_load('tags.json',{}); wanted=dict(x.split('=',1) for x in (getattr(a,'tag',None) or []) if '=' in x); out=[]
    for row in read_rows():
        try: t=dt.datetime.fromisoformat(row['time'].replace('Z','+00:00')).astimezone(TZ)
        except (KeyError,ValueError): continue
        if not(start<=t<end): continue
        r=dict(row); r['tags']={**r.get('tags',{}),**tags.get(r.get('session',''),{}),**tags.get(r.get('thread',''),{})}
        if wanted and not all(str(r['tags'].get(k))==v for k,v in wanted.items()): continue
        out.append(r)
    return out
def _dim(r,d,logical):
    if d=='day':
        t=dt.datetime.fromisoformat(r['time'].replace('Z','+00:00')).astimezone(TZ); return (t-dt.timedelta(hours=5)).date().isoformat() if logical else t.date().isoformat()
    if d.startswith('tag:'): return r.get('tags',{}).get(d[4:])
    return r.get('session') if d=='session' else r.get(d)
def summary(a):
    groups={}
    for r in _filtered(a):
        key=tuple(_dim(r,d,a.logical_day) for d in (a.by or ['day'])); g=groups.setdefault(key,{k:0 for k in FIELDS}|{'runs':0,'sessions':set()})
        for k in FIELDS: g[k]+=_num(r.get(k))
        g['runs']+=1; g['sessions'].add(r.get('session'))
    out=[]
    for key,g in sorted(groups.items(),key=lambda x:tuple('' if v is None else str(v) for v in x[0])):
        total=g['input']+g['cache_write']+g['cache_read']+g['output']; item={'group':key[0] if len(key)==1 else key,**{k:g[k] for k in FIELDS},'total':total,'without_cache_read':g['input']+g['cache_write']+g['output'],'sessions':len(g['sessions']),'runs':g['runs']}
        item['mean']={k:(item[k]/g['runs'] if g['runs'] else 0) for k in FIELDS}; item['mean']['total']=total/g['runs'] if g['runs'] else 0; out.append(item)
    return out
def _fmt(n):
    n=float(n)
    return f'{n/1_000_000:.2f}M' if abs(n)>=1_000_000 else f'{n/1_000:.1f}K' if abs(n)>=1_000 else f'{int(n):,}'
def _table(items):
    heads=['group','input','cache_write','cache_read','output','reasoning','total','without_cache_read','runs','mean_total']; vals=[]
    for x in items:
        g='|'.join(map(str,x['group'])) if isinstance(x['group'],tuple) else str(x['group']); vals.append([g]+[_fmt(x[k]) for k in heads[1:8]]+[str(x['runs']),_fmt(x['mean']['total'])])
    widths=[max([len(h)]+[len(v[i]) for v in vals]) for i,h in enumerate(heads)]; lines=['  '.join(h.ljust(widths[i]) for i,h in enumerate(heads)),'  '.join('-'*w for w in widths)]
    lines += ['  '.join(v[i].ljust(widths[i]) if i==0 else v[i].rjust(widths[i]) for i in range(len(heads))) for v in vals]; return '\n'.join(lines)
def main(argv=None):
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True); sy=sub.add_parser('sync'); sy.add_argument('--rebuild',action='store_true'); s=sub.add_parser('summary'); s.add_argument('--since'); s.add_argument('--until'); s.add_argument('--by',action='append'); s.add_argument('--tag',action='append'); s.add_argument('--logical-day',action='store_true'); s.add_argument('--json',action='store_true'); s.add_argument('--no-sync',action='store_true'); t=sub.add_parser('tag'); t.add_argument('session'); t.add_argument('pairs',nargs='+'); top=sub.add_parser('top'); top.add_argument('--since'); top.add_argument('-n',type=int,default=10); top.add_argument('--no-sync',action='store_true'); a=p.parse_args(argv)
    if a.cmd=='sync': print(json.dumps(sync(a.rebuild),ensure_ascii=False)); return 0
    if a.cmd=='tag':
        tags=_load('tags.json',{}); tags.setdefault(a.session,{}).update(dict(x.split('=',1) for x in a.pairs if '=' in x)); _save('tags.json',tags); return 0
    if a.cmd=='summary':
        out=summary(a); print(json.dumps(out,ensure_ascii=False) if a.json else _table(out)); return 0
    groups={}
    for r in _filtered(a):
        g=groups.setdefault(r.get('session'),{'session':r.get('session'),'agent':r.get('agent'),'title':r.get('title') or r.get('task') or r.get('session'),'total':0}); g['total']+=sum(_num(r.get(k)) for k in FIELDS[:4])
    for g in sorted(groups.values(),key=lambda x:x['total'],reverse=True)[:a.n]: print(f"{g['session']}\t{g['agent']}\t{_fmt(g['total'])}\t{g['title']}")
    return 0
if __name__=='__main__': raise SystemExit(main())
