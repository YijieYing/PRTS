"""Fixed study periods, independently accounted from focus sessions."""
from contextlib import contextmanager
import fcntl
import json
import math
import re
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import computer_history
import focus

ROOT = Path(__file__).resolve().parents[2]
DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


def _path(state, date):
    return state / 'study' / 'days' / f'{date}.json'


def _read(path, default):
    try:
        return json.loads(path.read_text()) if path.exists() else default
    except (OSError, ValueError, TypeError):
        return default


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False))
    temp.replace(path)


def _append(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + '\n')


@contextmanager
def _lock(state):
    path = state / 'study' / '.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def _date(at, config):
    return datetime.fromtimestamp(at, ZoneInfo(config['timezone'])).date().isoformat()


def _stamp(date, hm, config):
    hour, minute = map(int, hm.split(':'))
    local = datetime.fromisoformat(date).replace(
        hour=hour, minute=minute, second=0, microsecond=0,
        tzinfo=ZoneInfo(config['timezone']))
    return local.timestamp()


def validate(config):
    items = config.get('study', [])
    seen = set()
    errors = []
    for item in items:
        ident = item.get('id')
        if not ident or ident in seen:
            errors.append(f'重复或缺少 study id: {ident}')
        seen.add(ident)
        if item.get('mode') not in ('offline', 'any'):
            errors.append(f'{ident}: 未知 mode')
        if any(day not in DAYS for day in item.get('days', [])):
            errors.append(f'{ident}: 未知星期')
        try:
            _stamp('2026-01-01', item['start'], config)
            if int(item['minutes']) <= 0:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            errors.append(f'{ident}: start/minutes 无效')
    for index, item in enumerate(items):
        for other in items[index + 1:]:
            overlap = set(item.get('days', [])) & set(other.get('days', []))
            if overlap and _overlap(item, other):
                errors.append(f"学习时段重叠: {item.get('id')} / {other.get('id')}")
    if errors:
        raise ValueError('；'.join(errors))
    return items


def _overlap(first, second):
    def minutes(item):
        hour, minute = map(int, item['start'].split(':'))
        return hour * 60 + minute
    left = minutes(first)
    right = minutes(second)
    return left < right + int(second['minutes']) and right < left + int(first['minutes'])


def _notify(title, text):
    command = os.environ.get('PULSE_NOTIFY', str(ROOT / 'reporter/bin/notify'))
    try:
        result = subprocess.run(
            [command, 'alert', '--title', title, '--text', text],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _logs(state, ident, date):
    path = state / 'study' / 'log.jsonl'
    rows = []
    for line in path.read_text().splitlines() if path.exists() else []:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get('id') == ident and row.get('date') == date:
            rows.append(row)
    return rows


def _scheduled(config, date):
    weekday = DAYS[datetime.fromisoformat(date).weekday()]
    return [item for item in config['study'] if weekday in item.get('days', [])]


def _slot(kind, start, minutes):
    return {'kind': kind, 'start': start, 'until': start + minutes * 60,
            'on': 0, 'off': 0, 'unknown': 0, 'sent': [], 'closed': False}


def _load_day(state, date, config):
    """The day's ledger, with an entry and a main slot for every scheduled item."""
    day = _read(_path(state, date), {'date': date, 'items': {}})
    for item in _scheduled(config, date):
        start = _stamp(date, item['start'], config)
        day['items'].setdefault(item['id'], {
            'title': item['title'], 'minutes': int(item['minutes']), 'status': 'pending',
            'slots': [_slot('main', start, int(item['minutes']))]})
    return day


def _measure(slot, item, at, config, state):
    """Recompute the slot's minute ledger from Computer History; no minute counted twice."""
    warnings = set()
    start, end = slot['start'], min(at, slot['until'])
    try:
        source, _ = computer_history.load(config['sources'], start, end, state, warnings)
    except Exception as error:   # unreadable history is unknown, never "off the screen"
        warnings.add(f'Computer History 读取失败：{error}')
        source = None
    buckets = {}
    for row in source or []:
        if row.get('active') and not computer_history.system_app(row, config['sources']):
            buckets.setdefault(int(row['time'] // 60) * 60, []).append(row)
    rows = []
    for minute in range(math.ceil(start / 60) * 60, int(end // 60) * 60, 60):
        label, context = '离屏', None
        if source is None:
            category = 'unknown'
        elif minute not in buckets:
            category = 'on'
        else:
            row = max(buckets[minute], key=lambda r: (sum(r.get('counts', {}).values()), r.get('last', 0)))
            label = row.get('title') or row.get('domain') or row['app']
            context = (row['app'], row.get('title', ''), row.get('domain', ''), '', '')
            category = _category(item, context, buckets, minute)
        rows.append({'time': minute, 'category': category, 'label': label, 'context': context})
    pending = {row['context'] for row in rows if row['category'] is None}
    if pending:
        (state / 'focus').mkdir(parents=True, exist_ok=True)
        current = {'goal': item['title'], 'note': '固定学习时段', 'on': item.get('on', []), 'off': []}
        found = focus.classify(pending, current, state / 'focus', warnings)
        for row in rows:
            row['category'] = row['category'] or found[row['context']]['category']
    for kind in ('on', 'off', 'unknown'):
        slot[kind] = sum(row['category'] == kind for row in rows)
    return rows


def _category(item, context, buckets, minute):
    text = ' '.join(context).casefold()
    words = [str(Path(item['dir']).expanduser())] + item.get('on', [])
    if any(word.casefold() in text for word in words):
        return 'on'
    if minute - 60 not in buckets and minute + 60 not in buckets:
        return 'unknown'   # a single glance
    return 'off' if item['mode'] == 'offline' else None


def _status(entry, logs, at, config):
    if entry.get('skip_reason'):
        return 'skip'
    need = entry['minutes'] * float(config.get('study_settings', {}).get('done_ratio', .6))
    started = any(slot['start'] <= at for slot in entry['slots'])
    enough = (sum(slot['on'] for slot in entry['slots']) >= need
              or sum(row.get('minutes') or 0 for row in logs) >= need)
    if logs and enough:
        return 'done'
    if any(slot['start'] <= at < slot['until'] for slot in entry['slots']):
        return 'active'
    if not started:
        return 'partial' if logs else 'pending'
    return 'partial' if logs or enough else 'missed'


def tick(config, state, at=None, dry=False):
    if not config.get('study'):
        return {'disabled': True}
    at = at if at is not None else datetime.now().timestamp()
    try:
        validate(config)
    except (ValueError, KeyError, TypeError) as error:
        warning = 'study 配置无效：' + str(error)
        if not dry:
            (state / 'focus').mkdir(parents=True, exist_ok=True)
            _append(state / 'focus' / 'checks.jsonl', {'time': at, 'warning': warning})
        return {'warning': warning}
    if dry:
        return {'dry': True}
    today = _date(at, config)
    yesterday = (datetime.fromisoformat(today) - timedelta(days=1)).date().isoformat()
    result = {}
    with _lock(state):
        for date in (yesterday, today):   # yesterday: a make-up that runs past midnight
            if date == yesterday and not _path(state, date).exists():
                continue
            day = _load_day(state, date, config)
            _tick_day(day, date, at, config, state)
            if day['items']:
                _write(_path(state, date), day)
            result[date] = {key: entry['status'] for key, entry in day['items'].items()}
    return result


def _tick_day(day, date, at, config, state):
    items = [item for item in _scheduled(config, date) if item['id'] in day['items']]
    for item in items:
        entry = day['items'][item['id']]
        for slot in entry['slots']:
            if not slot['closed']:
                _tick_slot(entry, slot, item, date, at, config, state)
        entry['status'] = _status(entry, _logs(state, item['id'], date), at, config)
    _plan_makeup(day, items, date, at, config)


def _plan_makeup(day, items, date, at, config):
    makeup = config.get('study_settings', {}).get('makeup_start', '')
    lead = int(config.get('study_settings', {}).get('lead_minutes', 10)) * 60
    if not makeup or day.get('makeup_planned'):
        return
    cursor = _stamp(date, makeup, config)
    entries = [day['items'][item['id']] for item in items]
    if at < cursor - lead or not all(slot['closed'] for entry in entries for slot in entry['slots']):
        return
    day['makeup_planned'] = True
    if at >= cursor + 30 * 60:
        return   # the machine was asleep at the time; too late to start
    for entry in entries:
        if entry['status'] in ('partial', 'missed'):
            entry['slots'].append(_slot('makeup', cursor, entry['minutes']))
            cursor = entry['slots'][-1]['until']


def _tick_slot(entry, slot, item, date, at, config, state):
    settings = config.get('study_settings', {})
    logs = _logs(state, item['id'], date)
    rows = _measure(slot, item, at, config, state) if at > slot['start'] else []
    entry['status'] = _status(entry, logs, at, config)
    ended = at >= slot['until']
    if entry['status'] == 'skip' or entry['status'] == 'done' and 'start' not in slot['sent']:
        slot['closed'] = ended   # nothing to ask for
        return
    if not ended:
        lead = int(settings.get('lead_minutes', 10)) * 60
        if at >= slot['start']:
            _once(slot, 'start', *_invite(item, slot, config, state, pitch='lead' not in slot['sent']))
            _mark_focus(item, slot, state, at)
            if entry['status'] != 'done':
                _nag(slot, item, rows, at, int(settings.get('nag_minutes', 5)) * 60)
        elif at >= slot['start'] - lead:
            title, text = _invite(item, slot, config, state, pitch=True)
            _once(slot, 'lead', f"{int((slot['start'] - at) // 60)} 分钟后" + title.removeprefix('现在'), text)
        return
    slot['closed'] = True
    _unmark_focus(item, slot, rows, state)
    if at <= slot['until'] + 30 * 60:
        _once(slot, 'end', *_summary(entry, slot, item, logs))


def _once(slot, kind, title, text):
    if kind not in slot['sent']:
        slot['sent'].append(kind)   # an attempt counts even if a channel fails
        _notify(title, text)


def _invite(item, slot, config, state=None, pitch=False):
    clock = datetime.fromtimestamp(slot['start'], ZoneInfo(config['timezone'])).strftime('%H:%M')
    what = '合上电脑，拿出纸质材料。' if item['mode'] == 'offline' else '打开学习材料。'
    again = '（补）' if slot['kind'] == 'makeup' else ''
    title, text = f"现在：{item['title']}{again}", f"{clock} 起 {int(item['minutes'])} 分钟。{what}"
    paper = _paper(item, state, _date(slot['start'], config), config) if state else None
    if paper:
        title = f"现在读：{paper['id']} {paper['name']}{again}"
        text = f"{paper['night']}。{text}" + (f"\n\n为什么读：{paper['why']}\n\n{paper['pace']}" if pitch else '')
    return title, text


def _queue(path):
    """Papers from a queue.md: `## P1 · name` headings with 状态/晚数/为什么读 lines."""
    papers = []
    for line in Path(path).expanduser().read_text().splitlines():
        heading = re.match(r'^## (\w+) · (.+)$', line)
        field = re.match(r'^- (状态|晚数|为什么读)：(.+)$', line)
        if heading:
            papers.append({'id': heading[1], 'name': heading[2].strip(), 'status': '待读', 'nights': 1, 'why': ''})
        elif field and papers:
            key = {'状态': 'status', '晚数': 'nights', '为什么读': 'why'}[field[1]]
            papers[-1][key] = int(re.sub(r'\D', '', field[2]) or 1) if key == 'nights' else field[2].strip()
    return papers


def _paper(item, state, date, config):
    """Tonight's paper and how the reader stands against the plan; None without a queue."""
    if not item.get('queue'):
        return None
    try:
        papers = _queue(item['queue'])
    except OSError:
        return None
    left = [index for index, paper in enumerate(papers) if paper['status'] != '读完']
    if not left:
        return None
    index = left[0]
    paper = papers[index]
    spent = len({row['date'] for row in _all_logs(state, item['id']) if row['title'].startswith(paper['id'])})
    evenings = sum(1 for path in (state / 'study' / 'days').glob('*.json')
                   if path.stem < date and _read(path, {}).get('items', {}).get(item['id'], {}).get('status') not in (None, 'skip'))
    planned, total = 0, 0
    for planned, other in enumerate(papers):
        total += other['nights']
        if total > evenings:
            break
    gap = index - planned
    pace = '进度：按计划正好。' if gap == 0 else f"进度：比计划{'提前' if gap > 0 else '落后'} {abs(gap)} 篇（计划今晚读 {papers[planned]['id']}）。"
    night = f"第 {spent + 1} 晚，预计 {paper['nights']} 晚" if spent < paper['nights'] else f"第 {spent + 1} 晚（预计 {paper['nights']} 晚，可以慢慢来）"
    return dict(paper, night=night, pace=pace)


def _all_logs(state, ident):
    path = state / 'study' / 'log.jsonl'
    rows = []
    for line in path.read_text().splitlines() if path.exists() else []:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get('id') == ident:
            rows.append(row)
    return rows


def _nag(slot, item, rows, at, cooldown):
    recent = [row for row in rows if row['time'] >= at - 600]
    off = [row['label'] for row in recent if row['category'] == 'off']
    if len(off) < 5 or 'off' not in [row['category'] for row in rows[-2:]] or at - slot.get('last_nag', 0) < cooldown:
        return
    slot['last_nag'] = at
    place = max(set(off), key=off.count)[:60]
    _notify(f"该{item['title']}了，你还在：{place}", f"最近 10 分钟有 {len(off)} 分钟在别处。")


def _summary(entry, slot, item, logs):
    names = {'done': '完成', 'partial': '完成一半', 'missed': '没做'}
    counted = '离屏' if item['mode'] == 'offline' else '离屏或在学'
    text = f"{counted} {slot['on']} 分，偏离 {slot['off']} 分。"
    if not logs:
        text += f"还没有记录：告诉任意 session 今天学了什么，或 pulse study log {item['id']} \"标题\" --note \"一句话\"。"
    return f"{item['title']}：{names.get(entry['status'], entry['status'])}", text


def _mark_focus(item, slot, state, at):
    """Occupy the focus slot so 勿扰 cannot start its own; a manual focus is left alone."""
    directory = state / 'focus'
    directory.mkdir(parents=True, exist_ok=True)
    current = focus.read(directory / 'current.json', None)
    if current and current.get('source') == 'dnd':
        focus.finish(directory, current, at, 'study')
        current = None
    if not current:
        focus.write(directory / 'current.json', {
            'goal': item['title'], 'note': '', 'on': [], 'off': [], 'source': 'study',
            'study_id': item['id'], 'start': slot['start'], 'until': slot['until'],
            'rows': [], 'counts': focus.counts([]), 'reminders': []})


def _unmark_focus(item, slot, rows, state):
    directory = state / 'focus'
    current = focus.read(directory / 'current.json', None)
    if current and current.get('source') == 'study' and current.get('study_id') == item['id']:
        current['rows'] = [dict(row, session='', context=None) for row in rows]
        current['counts'] = focus.counts(current['rows'])
        focus.finish(directory, current, slot['until'], 'study')


def command(args, config, state):
    if not config.get('study'):
        print(json.dumps({'disabled': True}, ensure_ascii=False))
        return 0
    validate(config)
    now = datetime.now().timestamp()
    if args.study_command == 'tick':
        at = focus.timestamp(args.at, config) if args.at else now
        print(json.dumps(tick(config, state, at, args.dry), ensure_ascii=False))
        return 0
    date = args.date or _date(now, config)
    item = next((row for row in config['study'] if row['id'] == getattr(args, 'id', None)), None)
    if args.study_command in ('log', 'skip') and item is None:
        raise ValueError('未知 study id: ' + args.id)
    if args.study_command == 'log':
        _log(item, date, args, state)
    elif args.study_command == 'skip':
        _skip(item, date, args.reason, config, state)
    print(json.dumps(status(config, state, date), ensure_ascii=False))
    return 0


def _log(item, date, args, state):
    directory = Path(item['dir']).expanduser()
    if not directory.is_dir():
        raise ValueError('学习目录不存在：' + str(directory))
    with _lock(state):
        _append(state / 'study' / 'log.jsonl', {'id': item['id'], 'date': date, 'title': args.title,
                                                'note': args.note, 'minutes': args.minutes})
        with (directory / 'log.md').open('a') as stream:
            stream.write(f"- {date} {args.title}" + (f" —— {args.note}" if args.note else '') + '\n')


def _skip(item, date, reason, config, state):
    with _lock(state):
        day = _load_day(state, date, config)
        if item['id'] not in day['items']:
            raise ValueError(f"{date} 没有排 {item['id']}")
        day['items'][item['id']].update(status='skip', skip_reason=reason)
        _write(_path(state, date), day)
        current = focus.read(state / 'focus' / 'current.json', None)
        if current and current.get('source') == 'study' and current.get('study_id') == item['id']:
            focus.finish(state / 'focus', current, max(current['start'], datetime.now().timestamp()), 'skip')


def status(config, state, date, at=None):
    """Read-only view; logs written after the slot still count."""
    at = at if at is not None else datetime.now().timestamp()
    day = _view(config, state, date, at)
    first = datetime.fromisoformat(date).date()
    recent = []
    for offset in range(7):
        other = (first - timedelta(days=offset)).isoformat()
        states = [entry['status'] for entry in _view(config, state, other, at)['items'].values()] \
            if _path(state, other).exists() else []
        recent.append({'date': other, 'done': states.count('done'), 'skip': states.count('skip'), 'items': len(states)})
    streak = 0
    for index, row in enumerate(recent):
        if row['items'] and row['done'] + row['skip'] == row['items']:
            streak += row['done'] > 0
        elif index:   # today may still be open
            break
    return dict(day, recent=recent[::-1], streak=streak)


def _view(config, state, date, at):
    day = _load_day(state, date, config)
    for ident, entry in day['items'].items():
        entry['logs'] = _logs(state, ident, date)
        entry['status'] = _status(entry, entry['logs'], at, config)
    return day


def day(state, start, end, config):
    """「学习」 section of the daily review: what the ledger holds for slots inside the window."""
    if not config.get('study'):
        return ''
    names = {'done': '完成', 'partial': '完成一半', 'missed': '没做', 'skip': '跳过', 'active': '进行中', 'pending': '未开始'}
    lines = []
    for date in sorted({_date(start, config), _date(end - 1, config)}):
        if not _path(state, date).exists():
            continue
        data = _view(config, state, date, datetime.now().timestamp())
        for entry in data['items'].values():
            if not start <= entry['slots'][0]['start'] < end:
                continue
            total = {kind: sum(slot[kind] for slot in entry['slots']) for kind in ('on', 'off', 'unknown')}
            line = f"- {entry['title']}：{names[entry['status']]}；离屏或在学 {total['on']} 分，偏离 {total['off']} 分，不确定 {total['unknown']} 分"
            if len(entry['slots']) > 1:
                line += '（含补做）'
            if entry['logs']:
                line += '；记录：' + '、'.join(row['title'] for row in entry['logs'])
            if entry.get('skip_reason'):
                line += '；原因：' + entry['skip_reason']
            lines.append(line)
    return '\n## 学习\n\n' + '\n'.join(lines) + '\n' if lines else ''
