"""Read-only weekly usage audit for user-facing PRTS functions."""
import argparse, datetime as dt, json, os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TZ = dt.timezone(dt.timedelta(hours=9))

def _state(name, fallback):
    return Path(os.environ.get(name, fallback))

def _rows(path):
    try:
        return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    except (OSError, ValueError): return []

def _time(v):
    if isinstance(v,(int,float)): return float(v)
    if not v: return None
    try: return dt.datetime.fromisoformat(str(v).replace('Z','+00:00')).timestamp()
    except ValueError: return None

def _weeks(n, now=None):
    now = now or dt.datetime.now(TZ)
    monday = (now - dt.timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    # Include the current (possibly partial) Monday–Sunday week.
    return [(monday-dt.timedelta(days=7*(n-i-1)), monday-dt.timedelta(days=7*(n-i-2))) for i in range(n)]

def _count(times, windows):
    return [sum(a.timestamp() <= t < b.timestamp() for t in times if t is not None) for a,b in windows]

def _feature(name, signal, reason, times, windows, no_signal=None, measurable=True):
    counts=_count(times,windows)
    unused=0
    for x in reversed(counts):
        if x: break
        unused += 1
    return dict(name=name, signal=signal, reason=reason, weekly=counts,
                consecutive_unused_weeks=unused,
                # Zero counts from a feature we cannot observe are not evidence of disuse.
                candidate=measurable and unused>=2,
                no_signal=no_signal, measurable=measurable)

def audit(weeks=4, now=None):
    windows=_weeks(weeks,now); start=windows[0][0]; end=windows[-1][1]
    pulse=_state('PULSE_STATE',str(ROOT.parent/'pulse/state'))
    reporter=_state('PRTS_REPORTER_STATE',str(ROOT.parent/'reporter/state'))
    interaction=_state('PRTS_INTERACTION_STATE',str(ROOT/'state'))
    def in_window(v):
        t=_time(v); return t is not None and start.timestamp() <= t < end.timestamp()
    inbox=[r for r in _rows(pulse/'ear/inbox.jsonl') if r.get('value')=='high' and in_window(r.get('start',r.get('time')))]
    handed=set()
    try: handed=set(json.loads((pulse/'ear/handed.json').read_text()))
    except (OSError,ValueError): pass
    ear_times=[_time(r.get('start',r.get('time'))) for r in inbox if r.get('capture') in handed]
    out=[]
    out.append(_feature('Ear → 总控 inbox high 推送','inbox high + ear/handed.json',
                        '只把已被总控领取的 high 计为用户/总控实际处理；系统产生转写不算使用',ear_times,windows,
                        '没有 inbox/handed 可用信号' if not (pulse/'ear/inbox.jsonl').exists() else None))
    qs=_rows(reporter/'questions.jsonl'); qids={}
    for r in qs:
        qids.setdefault(r.get('qid'),[]).append(r)
    qtimes=[]
    for rows in qids.values():
        outcomes=[r.get('outcome') for r in rows if r.get('event')=='closed']
        delivered=any(r.get('event')=='delivered' for r in rows)
        if delivered and any(x in ('answered','delegated','expired_seen','expired_unseen') for x in outcomes):
            t=next((_time(r.get('t')) for r in rows if r.get('event')=='created'),None)
            if t is not None and start.timestamp()<=t<end.timestamp(): qtimes.append(t)
    out.append(_feature('每小时 remind 的问题推送','questions.jsonl: delivered → answered/delegated/expired',
                        '只计有结果的提问，提醒程序自身运行不算用户使用',qtimes,windows,
                        'questions.jsonl 不存在'))
    checks=[]
    for p in (pulse/'checks').glob('*.json') if (pulse/'checks').exists() else []:
        try:
            r=json.loads(p.read_text());
            if r.get('reminded') and in_window(r.get('time')): checks.append(_time(r.get('time')))
        except (OSError,ValueError): pass
    out.append(_feature('杂务提醒','pulse checks: reminded=true；回答/下降无法从现有数据稳定关联',
                        '只计实际提醒，不把 check 定时运行算使用；后续回答关联信号缺失',checks,windows,
                        '没有可把提醒与用户回答或杂务下降关联的持久信号'))
    focus=[]
    for p in (pulse/'focus').glob('log.jsonl') if (pulse/'focus').exists() else []:
        for r in _rows(p):
            if r.get('event')!='ignored' and in_window(r.get('start')): focus.append(_time(r.get('start')))
    out.append(_feature('专注时段','pulse/state/focus/log.jsonl 的 start（含 source=dnd）',
                        '开启时段是用户动作；check/到期结束不重复计数',focus,windows,
                        'focus 日志不存在' if not (pulse/'focus/log.jsonl').exists() else None))
    receipts={}
    try: receipts=json.loads((reporter/'recap-sent.json').read_text())
    except (OSError,ValueError): pass
    recap=[_time(k+'T12:00:00+09:00') for k,v in receipts.items() if v.get('note') is True and v.get('sent') is True and in_window(k+'T12:00:00+09:00')]
    out.append(_feature('每日回顾','reporter/recap-sent.json: note=true and sent=true',
                        '备忘录写入成功才计；日报生成或 alert 单独成功不算',recap,windows,
                        '只有系统写入备忘录的记录，没有你是否读了日报的信号',
                        measurable=False))
    ddl=[]; data={}
    try: data=json.loads((reporter/'ddl-sent.json').read_text()); ddl=[_time(v) for v in data.get('sent',{}).values() if in_window(v)]
    except (OSError,ValueError): pass
    out.append(_feature('DDL / 组会提醒','reporter/ddl-sent.json sent',
                        '发送是可观测使用；roadmap 状态变化只作为后续核对，不能伪造用户确认',ddl,windows,
                        '只有系统发送记录，没有你是否看了或照做的信号',
                        measurable=False))
    todo=[]
    try:
        cmd=[str(ROOT.parent/'reporter/bin/todo'),'list','--all']; r=subprocess.run(cmd,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5)
        # The audit itself invoked this read-only command; that invocation is
        # never evidence of a user's use. The API has no item timestamps, so
        # weekly additions/completions remain an explicit signal gap.
        if r.returncode != 0: todo=[]
    except (OSError,subprocess.TimeoutExpired): pass
    out.append(_feature('todo（Apple 提醒事项 PRTS）','reporter/bin/todo list --all',
                        '当前接口只返回快照，没有每条新增/完成时间；仅报告当前可见信号',todo,windows,
                        'todo 输出没有时间戳，无法计算每周新增/完成，需最小埋点建议：保存只读快照差分',
                        measurable=False))
    order_path=Path(os.environ.get('AGENT_CONSOLE_HOME',str(Path.home()/'.agentconsole')))/'order.json'
    order_times=[order_path.stat().st_mtime] if order_path.exists() and start.timestamp()<=order_path.stat().st_mtime<end.timestamp() else []
    out.append(_feature('AgentConsole','order.json mtime（手动排序）；server access log/状态动作未持久化',
                        '排序写入可证实用户动作；浏览器 GET 和状态操作没有稳定本地审计日志',order_times,windows,
                        '缺少 server access log，无法统计浏览请求与改状态动作',
                        measurable=False))
    out.append(_feature('token 统计','无可区分“用户调用 tokens”与日报调用的现有日志',
                        'tokens ledger 只记录被统计的 agent 用量，不能反推用户是否主动运行命令',[],windows,
                        '没有区分人工调用/日报调用的信号；最小埋点建议：tokens 命令写调用来源和时间',
                        measurable=False))
    return dict(weeks=weeks, generated_at=dt.datetime.now(TZ).isoformat(), features=out)

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--weeks',type=int,default=4); p.add_argument('--json',action='store_true'); a=p.parse_args(argv)
    if a.weeks<1: p.error('--weeks must be positive')
    data=audit(a.weeks)
    if a.json: print(json.dumps(data,ensure_ascii=False,indent=2)); return 0
    print(f'PRTS 功能使用盘点（最近 {a.weeks} 周）')
    for f in data['features']:
        mark='候选' if f['candidate'] else ('（测不到，不判）' if not f.get('measurable',True) else '')
        suffix=('；无信号：'+f['no_signal']) if f.get('no_signal') else ''
        print(f"{f['name']}："+' / '.join(map(str,f['weekly']))+f"；连续未用 {f['consecutive_unused_weeks']} 周 {mark}"+suffix)
    return 0
