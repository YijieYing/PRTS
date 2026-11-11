"""Append-only question queue. Serialize read/decide/append with an advisory lock."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import tomllib
import uuid

ROOT = Path(__file__).resolve().parents[1]
URGENCY = ('blocking', 'soon', 'whenever')
OUTCOMES = ('answered', 'deferred', 'delegated', 'rejected', 'expired_unseen', 'expired_seen', 'superseded')
VIA = ('session', 'file', 'wechat', 'claude')
HELP = '直接回复「Q12 你的答案」，或「Q12 你定」（用默认答案）、「Q12 以后」、「Q12 别问」。'


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone()


def fold(events):
    questions = {}
    for e in events:
        qid, kind = e['qid'], e['event']
        if kind == 'created':
            questions[qid] = dict(e, status='open', deliveries=[], opened=False)
        else:
            q = questions[qid]
            if kind == 'delivered':
                q['deliveries'].append(e)
            elif kind == 'opened':
                q['opened'] = True
            elif kind == 'answered':
                q.update(answer=e['answer'], via=e['via'], latency_s=e['latency_s'])
            elif kind == 'closed':
                q.update(status='closed', outcome=e['outcome'])
            elif kind == 'default_used':
                q['default_used'] = True
            elif kind == 'default_ok':
                q['default_ok'] = e['ok']
    return questions


@contextmanager
def queue():
    state = Path(os.environ.get('PRTS_REPORTER_STATE', ROOT / 'state'))
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'questions.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = state / 'questions.jsonl'
        events = []
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                events.append(json.loads(line))  # Fail closed on corruption; never discard history.
        pending = []
        yield events, pending
        if pending:
            with path.open('a', encoding='utf-8') as out:
                out.write(''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in pending))
                out.flush()
                os.fsync(out.fileno())


def quiet():
    try:
        result = subprocess.run([str(ROOT.parent / 'pulse/bin/pulse'), 'now'],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and json.loads(result.stdout).get('quiet') is True
    except (OSError, ValueError, AttributeError, subprocess.TimeoutExpired):
        return False


def ordered(questions, now):
    return sorted((q for q in questions.values() if q['status'] == 'open'
                   and (not q.get('expires') or stamp(q['expires']) > now)),
                  key=lambda q: (URGENCY.index(q['urgency']), stamp(q['t']), int(q['qid'][1:])))


def display(items):
    # Keep each question and default on one line, even for multiline input.
    lines = []
    for q in items:
        lines.extend([f"{q['qid']} · {' '.join(q['question'].split())}",
                      f"没人回答时：{' '.join(q['default'].split())}"])
    return '\n'.join(lines + [HELP]) if lines else ''


def positive(value):
    n = float(value)
    if not 0 < n < float('inf'):
        raise argparse.ArgumentTypeError('must be positive and finite')
    return n


def nonempty(value):
    if not value.strip():
        raise argparse.ArgumentTypeError('must not be empty')
    return value.strip()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('add')
    a.add_argument('question', type=nonempty)
    for key in ('why', 'default', 'source', 'dedupe'):
        a.add_argument('--' + key, required=True, type=nonempty)
    a.add_argument('--urgency', choices=URGENCY, required=True)
    a.add_argument('--expires')
    a.add_argument('--project')
    a = sub.add_parser('list')
    a.add_argument('--open', action='store_true')
    a.add_argument('--json', action='store_true')
    a = sub.add_parser('next')
    a.add_argument('--max', type=int)
    a = sub.add_parser('due')
    a.add_argument('--channel', required=True, type=nonempty)
    a.add_argument('--now')
    a = sub.add_parser('expire')
    a.add_argument('--now')
    a = sub.add_parser('answer')
    a.add_argument('qid')
    a.add_argument('answer', type=nonempty)
    a.add_argument('--via', choices=VIA, required=True)
    a = sub.add_parser('close')
    a.add_argument('qid')
    a.add_argument('outcome', choices=OUTCOMES)
    a = sub.add_parser('reply')
    a.add_argument('text')
    sub.add_parser('render')
    a = sub.add_parser('wait')
    a.add_argument('qid')
    a.add_argument('--poll', type=positive, default=30)
    for name in ('opened', 'default-used', 'default-ok'):
        a = sub.add_parser(name)
        a.add_argument('qid')
        if name == 'opened':
            a.add_argument('--channel', required=True)
        if name == 'default-ok':
            a.add_argument('ok', choices=('true', 'false'))
    return p


def execute(a):
    now = stamp(a.now) if getattr(a, 'now', None) else datetime.now().astimezone()
    with (ROOT / 'config/questions.toml').open('rb') as f:
        config = tomllib.load(f)
    cap = config['max_batch']
    limit = config['blocking_daily_limit']
    interval = config['blocking_interval_minutes']
    hour, minute = map(int, config['soon_time'].split(':'))
    if cap < 1 or limit < 0 or interval <= 0 or not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError('invalid questions.toml')
    if a.cmd == 'next' and a.max is not None and a.max < 1:
        raise ValueError('--max must be positive')
    is_quiet = quiet() if a.cmd == 'due' else False
    with queue() as (events, pending):
        qs = fold(events)
        def emit(qid, event, **fields):
            pending.append(dict(qid=qid, t=now.isoformat(), event=event, **fields))
        if a.cmd == 'add':
            if a.expires:
                stamp(a.expires)
            for q in qs.values():
                if q['status'] == 'open' and q['dedupe'] == a.dedupe:
                    return q['qid']
            qid = 'Q' + str(max((int(q[1:]) for q in qs), default=0) + 1)
            fields = {k: getattr(a, k) for k in ('question', 'why', 'default', 'urgency', 'source', 'dedupe', 'expires')}
            if a.project is not None:
                fields['project'] = a.project
            emit(qid, 'created', **fields)
            return qid
        if a.cmd == 'list':
            items = [q for q in qs.values() if not a.open or q['status'] == 'open']
            return json.dumps(items, ensure_ascii=False) if a.json else '\n'.join(
                f"{q['qid']} [{q['urgency']}/{q.get('outcome', 'open')}] {q['question']}" for q in items)
        if a.cmd in ('next', 'render', 'due'):
            items = ordered(qs, now)
            if a.cmd == 'render':
                return '# 待回答的问题\n\n' + (display(items) or '暂无待回答的问题。\n' + HELP) + '\n\n也可让 session 调用 ask answer Q12 "答案" --via file；本视图不会自动导入文件修改。'
            if a.cmd == 'next':
                return display(items[:min(cap, a.max or cap)])
            day = now.date()
            batches = {e['batch_id'] for q in qs.values() if q['urgency'] == 'blocking'
                       for e in q['deliveries'] if stamp(e['t']).date() == day}
            def due(q):
                deliveries = q['deliveries']
                if q['urgency'] == 'blocking':
                    return len(batches) < limit and (not deliveries or now - max(stamp(e['t']) for e in deliveries) >= timedelta(minutes=interval))
                return (q['urgency'] == 'soon' and not is_quiet and (now.hour, now.minute) >= (hour, minute)
                        and not any(stamp(e['t']).date() == day for e in deliveries))
            items = [q for q in items if due(q)][:cap]
            batch = uuid.uuid4().hex
            for q in items:
                emit(q['qid'], 'delivered', channel=a.channel, batch_size=len(items), batch_id=batch)
            return display(items)
        if a.cmd == 'expire':
            expired = []
            for q in qs.values():
                if q['status'] == 'open' and q.get('expires') and stamp(q['expires']) <= now:
                    emit(q['qid'], 'closed', outcome='expired_seen' if q['opened'] else 'expired_unseen')
                    expired.append(q['qid'])
            return '\n'.join(expired)
        if a.cmd == 'reply':
            match = re.fullmatch(r'\s*(Q[1-9][0-9]*)\s+(.+?)\s*', a.text, re.DOTALL)
            if not match:
                raise ValueError('请使用「Q12 你的答案」')
            a.qid, answer = match.groups()
            a.outcome = {'你定': 'delegated', '以后': 'deferred', '别问': 'rejected'}.get(answer)
            a.cmd = 'close' if a.outcome else 'answer'
            a.answer, a.via = answer, 'claude'
        if a.qid not in qs:
            raise ValueError(f'unknown question: {a.qid}')
        q = qs[a.qid]
        if a.cmd == 'wait':
            return q.get('answer', '') if q['status'] == 'closed' or 'answer' in q else None
        if a.cmd == 'answer':
            if q['status'] == 'closed' and not q.get('default_used'):
                if q.get('answer') == a.answer:
                    return a.qid
                raise ValueError('question is closed')
            if q.get('default_used'):
                emit(a.qid, 'default_ok', ok=a.answer == q['default'])
            first = min((stamp(e['t']) for e in q['deliveries']), default=None)
            emit(a.qid, 'answered', answer=a.answer, via=a.via,
                 latency_s=max(0, (now - first).total_seconds()) if first else None)
            emit(a.qid, 'closed', outcome='answered')
        elif a.cmd == 'default-ok':
            if not q.get('default_used'):
                raise ValueError('default has not been used')
            emit(a.qid, 'default_ok', ok=a.ok == 'true')
        else:
            if q['status'] == 'closed':
                if a.cmd == 'close' and q['outcome'] == a.outcome:
                    return a.qid
                raise ValueError('question is closed')
            if a.cmd == 'close':
                if a.outcome == 'answered':
                    raise ValueError('use ask answer to supply an answer')
                if a.outcome == 'delegated':
                    emit(a.qid, 'default_used', value=q['default'])
                emit(a.qid, 'closed', outcome=a.outcome)
            elif a.cmd == 'opened':
                if not q['deliveries']:
                    raise ValueError('question has not been delivered')
                emit(a.qid, 'opened', channel=a.channel)
            elif a.cmd == 'default-used':
                emit(a.qid, 'default_used', value=q['default'])
        return q['default'] if a.cmd == 'close' and a.outcome == 'delegated' else a.qid


def main():
    a = parser().parse_args()
    try:
        while True:
            result = execute(a)
            if result is not None:
                if result:
                    print(result)
                return 0
            time.sleep(a.poll)
    except (OSError, ValueError, KeyError) as exc:
        print(f'ask: {exc}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
