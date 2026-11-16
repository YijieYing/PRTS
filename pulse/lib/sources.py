"""Local, read-only activity collection. No browser queries outside ChatGPT."""
import glob
from contextlib import closing
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Standalone pulse entry points initially put only pulse/lib on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from interaction.lib.projects import match


def stamp(value):
    t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if t.tzinfo is None:
        raise ValueError('timestamp must include timezone')
    return t.timestamp()


def records(path, warnings):
    try:
        with path.open() as f:
            for line in f:
                try:
                    yield json.loads(line)
                except (ValueError, TypeError):
                    warnings.add('部分 JSONL 记录损坏，已跳过')
    except OSError as e:
        warnings.add(f'未读到 {path}: {e}')


def content(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n'.join(x.get('text', '') for x in value if isinstance(x, dict) and x.get('type') in ('text', 'output_text', 'input_text'))
    return ''


def project(cwd, mapping):
    if not cwd:
        return '未归属'
    path = str(Path(cwd).expanduser()).rstrip('/')
    if path == str(Path.home()).rstrip('/'):
        return '未归属'
    matched = match(cwd, mapping)
    if matched is not None:
        return matched
    return Path(path).name or '未归属'


def claude(config, start, end, mapping, warnings):
    titles = {}
    for path in Path(config['titles']).expanduser().glob('**/local_*.json'):
        try:
            item = json.loads(path.read_text())
            if item.get('cliSessionId'):
                titles[item['cliSessionId']] = item | {'local_id': path.stem}
        except (OSError, ValueError):
            warnings.add('部分 Claude 标题无法读取')
    events, seen = [], set()
    root = Path(config['claude']).expanduser()
    if not root.exists(): warnings.add('Claude 数据目录不存在')
    for path in root.glob('*/*.jsonl'):
        for r in records(path, warnings):
            if r.get('type') not in ('user', 'assistant'): continue
            sid, uid = r.get('sessionId'), r.get('uuid')
            if not sid or not uid or (sid, uid) in seen: continue
            seen.add((sid, uid))
            try: t = stamp(r['timestamp'])
            except (KeyError, ValueError, TypeError): continue
            if not start <= t < end: continue
            message = r.get('message', {})
            value = message.get('content')
            blocks = value if isinstance(value, list) else []
            tool_result = any(x.get('type') == 'tool_result' for x in blocks if isinstance(x, dict))
            meta = titles.get(sid, {})
            cwd = r.get('cwd') or meta.get('cwd', '')
            base = dict(time=t, source='claude', session=sid, uuid=uid,
                        title=meta.get('title') or sid, local_id=meta.get('local_id'),
                        cwd=cwd, project=project(cwd, mapping))
            # Tool payloads are never retained; timestamps and turn completion are evidence for held.
            if tool_result:
                events.append(base | dict(role='tool', text='', final=False))
                continue
            if r['type'] == 'user' and isinstance(value, list):
                value = [x for x in value if isinstance(x, dict) and x.get('type') == 'text'
                         and (not x.get('text', '').lstrip().startswith('<') or x.get('text', '').lstrip().startswith('<pasted_content'))]
            text = content(value).strip()
            if r['type'] == 'user':
                if not text or r.get('isMeta') or r.get('isCompactSummary') or text.startswith('This session is being continued from a previous conversation'): continue
                if text.startswith('<') and not text.startswith('<pasted_content'): continue
            events.append(base | dict(role=r['type'], text=text,
                                     final=r['type']=='assistant' and message.get('stop_reason') == 'end_turn'))
    return events


def chrome(config, start, end, warnings):
    path = Path(config['chrome']).expanduser()
    if not path.exists():
        warnings.add('Chrome History 不存在'); return []
    events, projects, visits = [], {}, []
    epoch = 11644473600
    try:
        with tempfile.TemporaryDirectory(prefix='pulse-chrome-') as tmp:
            copy = Path(tmp) / 'History'
            shutil.copyfile(path, copy)
            with closing(sqlite3.connect(copy.as_uri() + '?mode=ro', uri=True)) as db:
                # Only ChatGPT rows are read, including project titles for prefix mapping.
                rows = db.execute("SELECT urls.url, urls.title, CAST(visits.visit_time AS INTEGER), CAST(visits.visit_duration AS INTEGER) FROM visits JOIN urls ON visits.url=urls.id WHERE urls.url LIKE '%chatgpt.com%' AND CAST(visits.visit_time AS INTEGER) < ? ORDER BY CAST(visits.visit_time AS INTEGER), visits.rowid", (int((end + epoch) * 1e6),))
                for url, title, micros, duration in rows:
                    u = urlparse(url)
                    if u.hostname not in ('chatgpt.com', 'www.chatgpt.com'): continue
                    parts = u.path.split('/')
                    prefix = next((p for p in parts if p.startswith('g-p-')), None)
                    if title.startswith('ChatGPT - ') and prefix:
                        projects[prefix] = title[len('ChatGPT - '):]
                    t = micros / 1e6 - epoch
                    visits.append(t)
                    if not start <= t < end: continue
                    # Project pages supply attribution, not conversation time.
                    if title.startswith('ChatGPT - '): continue
                    if '/c/' not in u.path: continue
                    conversation = u.path.split('/c/', 1)[1].split('/')[0]
                    events.append(dict(time=t, source='chatgpt', session=conversation,
                                       role='user', text=title, title=title, url=url,
                                       prefix=prefix, project='未归属', visit_index=len(visits)-1, visit_duration=max(0, (duration or 0)/1e6)))
        for e in events:
            i = e.pop('visit_index')+1
            e['next_visit'] = visits[i] if i < len(visits) else end
            e['project'] = projects.get(e.pop('prefix'), '未归属')
    except (OSError, sqlite3.Error) as e:
        warnings.add(f'Chrome History 未读到: {e}')
    return events


def codex(config, start, end, mapping, warnings, users=None):
    outputs, activity = [], []
    root = Path(config['codex']).expanduser()
    if not root.exists(): warnings.add('Codex 数据目录不存在')
    for path in root.glob('*/*/*/*.jsonl'):
        sid, cwd, times, title = path.stem, '', [], ''
        for r in records(path, warnings):
            p = r.get('payload', {})
            if r.get('type') == 'session_meta':
                sid, cwd = p.get('id', sid), p.get('cwd', '')
            try: t = stamp(r['timestamp'])
            except (KeyError, ValueError, TypeError): continue
            if t >= end: continue
            if r.get('type') == 'event_msg' and p.get('type') == 'user_message':
                title = title or p.get('message', '')[:160]
            if not start <= t < end: continue
            times.append(t)
            if r.get('type') == 'event_msg' and p.get('type') == 'user_message':
                if users is not None:
                    users.append(dict(time=t, source='codex', session=sid, role='user',
                                      title=title, cwd=cwd))
            if r.get('type') == 'response_item' and p.get('role') == 'assistant' and p.get('type') == 'message':
                text = content(p.get('content'))
                if text: outputs.append(dict(time=t, source='codex', session=sid, project=project(cwd, mapping), text=text, cwd=cwd, verified=False, final=p.get('channel')=='final' if p.get('channel') else None))
        if times: activity.append(dict(start=min(times), end=max(times), session=sid, title=title or '未命名对话', project=project(cwd, mapping), user_seconds=0))
    return outputs, activity


def commits(config, start, end, mapping, warnings):
    outputs, seen = [], set()
    for pattern in config['repos']:
        for raw in glob.glob(str(Path(pattern).expanduser())):
            path = Path(raw)
            if not (path / '.git').exists() or str(path.resolve()) in seen: continue
            seen.add(str(path.resolve()))
            result = subprocess.run(['git', '-C', str(path), 'log', '--all', '--since=' + datetime.fromtimestamp(start, timezone.utc).isoformat(), '--until=' + datetime.fromtimestamp(end, timezone.utc).isoformat(), '--format=%H%x09%ct%x09%s'], stdin=subprocess.DEVNULL, capture_output=True, text=True)
            if result.returncode:
                warnings.add(f'git log 失败: {path}'); continue
            for line in result.stdout.splitlines():
                sha, ts, title = line.split('\t', 2)
                if start <= int(ts) < end:
                    outputs.append(dict(time=int(ts), source='git', session=sha, project=project(str(path), mapping), text=title, cwd=str(path), verified=True))
    return outputs
