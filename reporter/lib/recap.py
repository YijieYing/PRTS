"""Daily delivery, with a locked per-date/channel receipt journal."""
import argparse
from datetime import date
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

MODULE = Path(__file__).resolve().parents[1]
PULSE = MODULE.parent / 'pulse/bin/pulse'


def run(args):
    return subprocess.run([str(x) for x in args], stdin=subprocess.DEVNULL,
                          text=True, capture_output=True, timeout=1800)


def head(md):
    return '\n'.join(line for line in md.splitlines()[2:]
                     if line.strip() and not line.startswith('## ')).splitlines()[:8]


def save(path, receipts):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(receipts, ensure_ascii=False, indent=2)+'\n')
    temp.replace(path)


def deliver(day, path, receipts, manual=False):
    result = run([PULSE, 'day', day])
    if result.returncode:
        raise RuntimeError('pulse day failed: '+result.stderr)
    md = result.stdout.rstrip('\n')
    name = day+' 回顾'
    receipt = {} if manual else receipts.get(day, {})
    if not receipt.get('note'):
        result = run([MODULE/'bin/notify', 'note', '--folder', 'PRTS 日报', '--title', name, '--text', md])
        receipt['note'] = result.returncode == 0
        receipts[day] = receipt; save(path, receipts)
    where = ('全文见备忘录 · PRTS 日报 · '+name if receipt['note'] else
             '备忘录写入失败，全文在 ~/PRTS/pulse/state/days/'+day+'.md')
    if not receipt.get('alert'):
        title = md.splitlines()[1] if len(md.splitlines()) > 1 else 'PRTS 每日回顾'
        result = run([MODULE/'bin/notify', 'alert', '--title', title, '--url', 'mobilenotes://',
                      '--text', '\n'.join(head(md))+'\n…\n'+where])
        receipt['alert'] = result.returncode == 0
        receipts[day] = receipt; save(path, receipts)
    # A failed note is retried next hour without repeating a successful push.
    receipt['sent'] = receipt['note'] and receipt['alert']
    save(path, receipts)
    if not receipt['alert']: raise RuntimeError('recap push failed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('date', nargs='?')
    parser.add_argument('--dry', action='store_true')
    parser.add_argument('--auto', action='store_true')
    parser.add_argument('--synced', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.auto and (args.date or args.dry): parser.error('--auto cannot combine with date/--dry')
    if args.date: date.fromisoformat(args.date)
    if args.dry:
        result = run([PULSE, 'day', *([args.date] if args.date else []), '--dry'])
        sys.stdout.write(result.stdout); sys.stderr.write(result.stderr)
        return result.returncode
    state = Path(os.environ.get('PRTS_REPORTER_STATE', MODULE/'state'))
    state.mkdir(parents=True, exist_ok=True)
    with (state/'recap.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = state/'recap-sent.json'
        receipts = json.loads(path.read_text()) if path.exists() else {}
        if not args.synced:
            sync = run([PULSE, 'ear', 'sync', '--no-notify'])
            if sync.returncode: print('warning: pulse ear sync failed: '+sync.stderr, file=sys.stderr)
        if args.auto or not args.date:
            result = run([PULSE, 'recap-status'])
            if result.returncode: raise RuntimeError(result.stderr)
            status = json.loads(result.stdout)
        if args.auto:
            # Previous completed day is unconditional; the current logical day
            # can close early only after 18 hours and verified inactivity.
            days = [status['previous']]
            if status['eligible'] and status['idle']: days.append(status['day'])
            for day in days:
                if not receipts.get(day, {}).get('sent'): deliver(day, path, receipts)
        else:
            deliver(args.date or status['day'], path, receipts, manual=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        print('recap: '+str(error), file=sys.stderr)
        sys.exit(1)
