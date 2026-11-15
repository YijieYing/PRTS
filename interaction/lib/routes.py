"""Route under event lock. Durable attempts prevent blind duplicate queue calls."""
import hashlib
import subprocess
from pathlib import Path
from .subscriptions import I, append, read, now, registry

def route(event, subscribers):
    root = registry['state']()
    ledger = root / 'routes.jsonl'
    previous = {(r['event_id'], r['subscription']): r for r in read(ledger)}
    traces = []
    pending = False
    for sub in subscribers:
        key = event['id'], sub['id']
        old = previous.get(key)
        if old:
            pending |= old['status'] != 'routed'
            traces.append(old)
            continue
        trace = dict(event_id=event['id'], subscription=sub['id'], to=sub['to'],
                     t=now(), status='attempting')
        append(ledger, trace)
        try:
            if sub['to'].startswith('claude:'):
                directory = root / 'outbox'; directory.mkdir(exist_ok=True)
                append(directory / (sub['to'][7:]+'.jsonl'), dict(event, subscription=sub['id'], to=sub['to']))
                trace.update(status='route_pending', reason='Claude session requires controller forwarding')
            else:
                directory = root / 'routes'; directory.mkdir(exist_ok=True)
                token = hashlib.sha256((':'.join(key)).encode()).hexdigest()
                prompt = directory / (token+'.txt')
                prompt.write_text(event['text'])
                result = subprocess.run([str(I/'lib/codex'), '--cwd', str(I.parent),
                    '--prompt', str(prompt), '--name', 'route_'+token, '--log', str(directory/(token+'.log')),
                    '--target', sub['to'][6:], '--tries', '1', 'queue'],
                    stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
                if result.returncode: raise RuntimeError(result.stderr or 'queue failed')
                trace.update(status='routed')
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            trace.update(status='route_pending', reason=str(exc)[-2000:])
        append(ledger, trace)
        pending |= trace['status'] != 'routed'
        traces.append(trace)
    return pending, traces
