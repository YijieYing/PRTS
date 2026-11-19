#!/usr/bin/env python3
"""Incremental, content-free token ledger for local Claude and Codex logs."""
import argparse, datetime as dt, hashlib, json, os, time
from pathlib import Path
from zoneinfo import ZoneInfo
try:
    from .projects import match as project_match
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from projects import match as project_match

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get('PRTS_INTERACTION_STATE', ROOT/'state')) / 'tokens'
TZ = ZoneInfo('Asia/Tokyo')
FIELDS = ('input','cache_write','cache_read','output','reasoning')

def _state(name): return STATE/name
def _load(name, default):
    try: return json.loads(_state(name).read_text())
    except (OSError, ValueError): return default
def _save(name, value):
    STATE.mkdir(parents=True, exist_ok=True); p=_state(name); t=p.with_suffix('.tmp'); t.write_text(json.dumps(value,ensure_ascii=False)); t.replace(p)
def _num(v): return int(v or 0) if isinstance(v,(int,float)) else 0
def _stamp(x, fallback):
    if not x: return fallback
    if isinstance(x,(int,float)): return dt.datetime.fromtimestamp(x/1000 if x>10**11 else x,dt.timezone.utc).isoformat()
    return str(x)
def _row_key(agent, ident, file, ordinal): return f'{agent}:{ident or hashlib.sha1((file+str(ordinal)).encode()).hexdigest()}'

def _registry():
    try:
        p=Path(os.environ.get('PRTS_INTERACTION_STATE',ROOT/'state'))/'registry.jsonl'
        rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except (OSError,ValueError): rows=[]
    tags={}; tasks={}; caller={}; name_tags={}
    for r in rows:
        if r.get('event')=='start':
            tid=r.get('thread'); name=r.get('name');
            if tid: tasks[tid]=name
            if r.get('tags') and name: tags[name]=r['tags']; name_tags[name]=r['tags']
            if r.get('caller'): caller[name]=r['caller']
        if r.get('event')=='thread' and r.get('thread') and r.get('name'):
            tasks[r['thread']]=r['name']; tags[r['thread']]=name_tags.get(r['name'],{})
    return tasks,tags

def _claude_files(): return sorted(Path(os.path.expanduser('~/.claude/projects')).glob('**/*.jsonl'))
def _codex_files(): return sorted(Path(os.path.expanduser('~/.codex/sessions')).glob('**/*.jsonl'))

def sync():
    STATE.mkdir(parents=True,exist_ok=True)
    index=_load('index.json',{}); seen=set(_load('seen.json',[])); rows=[]; files=0; bytes_read=0
    tasks,tags=_registry()
    paths=[('claude',p) for p in _claude_files()]+[('codex',p) for p in _codex_files()]
    for agent,p in paths:
        key=str(p); st=index.get(key,{}); stat=p.stat(); size=stat.st_size; mtime=stat.st_mtime
        off=st.get('offset',0)
        if size<off or mtime<st.get('mtime',0) or (st.get('inode') and st.get('inode') != stat.st_ino): off=0
        meta={}
        if agent=='codex':
            try:
                with p.open(errors='replace') as mf:
                    for line in mf:
                        x=json.loads(line)
                        if x.get('type')=='session_meta': meta=x.get('payload') or {}; break
            except Exception: pass
        with p.open('rb') as f:
            f.seek(off)
            for ordinal,raw in enumerate(f, start=0):
                bytes_read+=len(raw)
                try: rec=json.loads(raw)
                except ValueError: continue
                if agent=='claude':
                    msg=rec.get('message') or {}; usage=msg.get('usage')
                    if not isinstance(usage,dict): continue
                    ident=msg.get('id') or rec.get('uuid');
                    uid=_row_key(agent,ident,key,off+ordinal)
                    if uid in seen: continue
                    cwd=rec.get('cwd'); sid=p.stem
                    parent=rec.get('parentSessionId') or rec.get('parent_session_id')
                    vals={'input':_num(usage.get('input_tokens')),'cache_write':_num(usage.get('cache_creation_input_tokens')),'cache_read':_num(usage.get('cache_read_input_tokens')),'output':_num(usage.get('output_tokens')),'reasoning':_num((usage.get('output_tokens_details') or {}).get('thinking_tokens'))}
                    row={'time':_stamp(rec.get('timestamp'),dt.datetime.fromtimestamp(p.stat().st_mtime,dt.timezone.utc).isoformat()),'agent':agent,'model':msg.get('model'),'session':sid,'thread':sid,'parent_session':parent,'cwd':cwd,'project':project_match(cwd),'task':None,'title':None,'tags':tags.get(sid,{}),**vals,'_id':uid}
                else:
                    payload=rec.get('payload') or {}; info=payload.get('info') or {}
                    if rec.get('type')!='event_msg' or payload.get('type')!='token_count' or not isinstance(info.get('last_token_usage'),dict): continue
                    usage=info['last_token_usage']
                    # session id and metadata are in session_meta; derive from filename UUID suffix.
                    sid=p.stem.replace('rollout-','').split('-',1)[-1] if p.stem.startswith('rollout-') else p.stem
                    ident=f'{sid}:{rec.get("ordinal",off+ordinal)}'; uid=_row_key(agent,ident,key,ordinal)
                    if uid in seen: continue
                    sid=meta.get('id') or meta.get('session_id') or sid; cwd=meta.get('cwd')
                    row={'time':_stamp(rec.get('timestamp'),dt.datetime.fromtimestamp(p.stat().st_mtime,dt.timezone.utc).isoformat()),'agent':agent,'model':meta.get('model'),'session':sid,'thread':sid,'parent_session':meta.get('parent_thread_id') or meta.get('parent_session_id'),'cwd':cwd,'project':project_match(cwd),'task':tasks.get(sid),'title':meta.get('title') or meta.get('name'),'tags':tags.get(sid,{}),**{k:_num(usage.get(src)) for k,src in [('input','input_tokens'),('cache_write','cache_write_input_tokens'),('cache_read','cached_input_tokens'),('output','output_tokens'),('reasoning','reasoning_output_tokens')]},'_id':uid}
                seen.add(uid); rows.append(row)
            index[key]={'offset':f.tell(),'mtime':mtime,'inode':stat.st_ino}
    ledger=_state('ledger.jsonl')
    with ledger.open('a',encoding='utf-8') as f:
        for r in rows:
            r.pop('_id',None); f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    _save('index.json',index); _save('seen.json',sorted(seen))
    return {'rows':len(rows),'bytes':bytes_read,'files':len(paths)}

def read_rows():
    try: return [json.loads(x) for x in _state('ledger.jsonl').read_text().splitlines() if x.strip()]
    except OSError: return []
def _parse_date(s): return dt.datetime.fromisoformat(s).replace(tzinfo=TZ) if 'T' not in s else dt.datetime.fromisoformat(s).astimezone(TZ)
def summary(args):
    if not args.no_sync: sync()
    now=dt.datetime.now(TZ); start=now-dt.timedelta(days=7)
    if args.since: start=dt.datetime.fromisoformat(args.since).replace(tzinfo=TZ)
    end=now
    if args.until: end=dt.datetime.fromisoformat(args.until).replace(tzinfo=TZ)+dt.timedelta(days=1)
    rows=[]
    tags=_load('tags.json',{})
    for r in read_rows():
        t=dt.datetime.fromisoformat(r['time'].replace('Z','+00:00')).astimezone(TZ)
        if not(start<=t<end): continue
        r=dict(r); r['tags']={**tags.get(r.get('session',''),{}),**tags.get(r.get('thread',''),{})}; rows.append(r)
    wanted=dict(x.split('=',1) for x in (getattr(args,'tag',None) or []) if '=' in x)
    if wanted: rows=[r for r in rows if all(str(r['tags'].get(k))==v for k,v in wanted.items())]
    by=args.by or ['day']; groups={}
    for r in rows:
        t=dt.datetime.fromisoformat(r['time'].replace('Z','+00:00')).astimezone(TZ)
        vals={k:r.get(k,0) for k in FIELDS}; key=[]
        for b in by:
            if b=='day': key.append((t-dt.timedelta(hours=5)).date().isoformat() if args.logical_day else t.date().isoformat())
            elif b.startswith('tag:'): key.append(r['tags'].get(b[4:]))
            else: key.append(r.get('session') if b=='session' else r.get(b))
        key=tuple(key); g=groups.setdefault(key,{k:0 for k in FIELDS}|{'runs':set()})
        for k,v in vals.items(): g[k]+=v
        g['runs'].add(r.get('session'))
    out=[]
    for k,g in sorted(groups.items(),key=lambda x: tuple('' if v is None else str(v) for v in x[0])): out.append({'group':k[0] if len(k)==1 else k,**{x:g[x] for x in FIELDS},'total':sum(g[x] for x in FIELDS),'without_cache_read':g['input']+g['cache_write']+g['output']+g['reasoning'],'sessions':len(g['runs'])})
    return out

def main(argv=None):
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('sync')
    s=sub.add_parser('summary'); s.add_argument('--since'); s.add_argument('--until'); s.add_argument('--by',action='append'); s.add_argument('--tag',action='append'); s.add_argument('--logical-day',action='store_true'); s.add_argument('--json',action='store_true'); s.add_argument('--no-sync',action='store_true')
    t=sub.add_parser('tag'); t.add_argument('session'); t.add_argument('pairs',nargs='+')
    top=sub.add_parser('top'); top.add_argument('--since'); top.add_argument('-n',type=int,default=10); top.add_argument('--no-sync',action='store_true')
    a=p.parse_args(argv)
    if a.cmd=='sync': print(json.dumps(sync(),ensure_ascii=False)); return 0
    if a.cmd=='tag':
        tags=_load('tags.json',{}); d=tags.setdefault(a.session,{}); d.update(dict(x.split('=',1) for x in a.pairs if '=' in x)); _save('tags.json',tags); return 0
    if a.cmd=='summary':
        out=summary(a); print(json.dumps(out,ensure_ascii=False) if a.json else '\n'.join(f"{x['group']} input={x['input']} cache_write={x['cache_write']} cache_read={x['cache_read']} output={x['output']} reasoning={x['reasoning']} total={x['total']} without_cache_read={x['without_cache_read']} sessions={x['sessions']}" for x in out)); return 0
    if a.cmd=='top':
        if not a.no_sync: sync()
        cutoff=dt.datetime.fromisoformat(a.since).replace(tzinfo=TZ) if a.since else dt.datetime.now(TZ)-dt.timedelta(days=7)
        groups={}
        for r in read_rows():
            t=dt.datetime.fromisoformat(r['time'].replace('Z','+00:00')).astimezone(TZ)
            if t<cutoff: continue
            g=groups.setdefault(r.get('session'), {'title':r.get('title') or r.get('task') or r.get('session'),'agent':r.get('agent'),'total':0,'session':r.get('session')})
            g['total'] += sum(r.get(k,0) for k in FIELDS)
        for g in sorted(groups.values(),key=lambda x:x['total'],reverse=True)[:a.n]: print(f"{g['session']}\t{g['agent']}\t{g['total']}\t{g['title']}")
        return 0
if __name__=='__main__': main()
