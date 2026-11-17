"""DDL and meeting notifications, using interaction's public status command."""
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def run(args):
    return subprocess.run([str(x) for x in args], stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, check=True, timeout=120).stdout

def due(groups, now):
    today = now.date()
    result = {}
    for group in groups:
        for project in group['projects']:
            name = project['name']
            items = project['roadmap']['items']
            for item in items:
                if item['done'] or not item['ddl']: continue
                days = (dt.date.fromisoformat(item['ddl'])-today).days
                phase = str(days) if days in (7,2,0) else ('overdue' if days < 0 else None)
                if phase is not None:
                    key = json.dumps(['ddl',name,item['id'] or item['title'],item['ddl'],phase],ensure_ascii=False)
                    when = '已过期' if days < 0 else ('今天到期' if days == 0 else f'{days} 天后到期')
                    result[key] = dict(title=f'{name} · {item["id"] or "DDL"} {when}',text=f'{item["title"]}\nDDL：{item["ddl"]}',project=name,id=item['id'],ddl=item['ddl'],kind='ddl')
            for meeting in project.get('meetings',[]):
                if today.isoweekday()!=meeting['weekday'] or now.hour < 12: continue
                key = json.dumps(['meeting',name,today.isoformat(),meeting['start'],meeting['end']],ensure_ascii=False)
                recent=list(project.get('completed',[])); waiting=[]
                for item in items:
                    auto=item.get('auto') or {}
                    if item['status']=='🔍' or (auto.get('state')=='pr_open' and not item['done']): waiting.append(item)
                    if item['status']=='✅' and auto.get('at') and auto.get('state') in ('accepted','merged'):
                        at=dt.datetime.fromisoformat(auto['at']).astimezone(now.tzinfo)
                        if now-dt.timedelta(days=7)<=at<=now and not any(i['id']==item['id'] for i in recent): recent.append(item)
                lines=[f'{name} 组会 {meeting["start"]}-{meeting["end"]}',
                       '最近 7 天完成：'+('；'.join(f'{i["id"]} {i["title"]}' for i in recent) or '无已记录条目'),
                       '待验收：'+('；'.join(f'{i["id"]} {i["title"]}' for i in waiting) or '无')]
                result[key]=dict(title=lines[0],text='\n'.join(lines),project=name,kind='meeting',date=today.isoformat())
    return result

def remind(groups, now, quiet, state_dir, notify):
    state_dir.mkdir(parents=True,exist_ok=True)
    with (state_dir/'ddl.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=state_dir/'ddl-sent.json'
        data=json.loads(path.read_text()) if path.exists() else dict(sent={},pending={})
        data['pending'].update({k:v for k,v in due(groups,now).items() if k not in data['sent']})
        active={(p['name'],i['id'],i['ddl']) for g in groups for p in g['projects'] for i in p['roadmap']['items'] if not i['done']}
        ddl_batch=[]
        for key,value in list(data['pending'].items()):
            if value['kind']=='ddl' and (value['project'],value['id'],value['ddl']) not in active:
                del data['pending'][key]; continue
            if quiet: continue
            if value['kind']=='ddl':
                ddl_batch.append((key,value)); continue
            notify(value['title'],value['text'])
            data['sent'][key]=now.isoformat()
            del data['pending'][key]
            temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False));temp.replace(path)
        # Several DDL items due in one run go out as one push (e.g. a stale imported roadmap with many overdue rows).
        if len(ddl_batch)==1:
            notify(ddl_batch[0][1]['title'],ddl_batch[0][1]['text'])
        elif ddl_batch:
            lines=[f"{v['title']}：{v['text'].splitlines()[0]}" for _,v in ddl_batch]
            notify(f'DDL 提醒 {len(ddl_batch)} 条','\n'.join(lines[:12]+([f'……另 {len(lines)-12} 条'] if len(lines)>12 else [])))
        for key,_ in ddl_batch:
            data['sent'][key]=now.isoformat(); del data['pending'][key]
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False));temp.replace(path)

def main(quiet=False):
    groups=json.loads(run([ROOT/'interaction/bin/status','threads','--json']))['groups']
    now=dt.datetime.now().astimezone()
    if any(m['weekday']==now.isoweekday() for g in groups for p in g['projects'] for m in p.get('meetings',[])) and now.hour>=12:
        completed=json.loads(run([ROOT/'interaction/bin/roadmap','list','--json','--completed-since',(now-dt.timedelta(days=7)).isoformat()]))
        by_name={p['name']:p['completed'] for p in completed}
        for g in groups:
            for p in g['projects']: p['completed']=by_name.get(p['name'],[])
    state_dir=Path(os.environ.get('PRTS_REPORTER_STATE',ROOT/'reporter/state'))
    remind(groups,now,quiet,state_dir,
           lambda title,text: run([ROOT/'reporter/bin/notify','phone','--title',title,'--text',text]))
