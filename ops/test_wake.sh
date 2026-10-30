#!/bin/bash
# Isolated functional tests; never touches real LaunchAgents, registry or sessions.
set -eu
SRC=$(cd "$(dirname "$0")" && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/ops/wakes" "$T/bin" "$T/home"
cp "$SRC/wake.sh" "$SRC/wake_run.sh" "$T/ops/"
export HOME="$T/home" CODEX_HOME="$T/home/.codex" PATH="$T/bin:$PATH"
export WAKE_GAP=0 WAKE_TRIES=2
unset WAKE_DRY
cat > "$T/bin/launchctl" <<'PY'
#!/usr/bin/env python3
import os,pathlib,plistlib,sys
root=pathlib.Path(os.environ['HOME'])
verb=sys.argv[1]
if verb=='bootstrap':
    with open(sys.argv[3],'rb') as f: p=plistlib.load(f)
    (root/p['Label']).touch()
else:
    p=root/sys.argv[2].split('/')[-1]
    if verb=='print': sys.exit(0 if p.exists() else 113)
    if verb=='bootout':
        if not p.exists(): sys.exit(113)
        p.unlink()
PY
cat > "$T/bin/codex" <<'PY'
#!/usr/bin/env python3
import json,os,pathlib,sys
p=pathlib.Path(os.environ['HOME'])
with open(p/'calls','a') as f: f.write(json.dumps(dict(args=sys.argv[1:],stdin=sys.stdin.read()))+'\n')
if (p/'capacity').exists():
    print('at capacity'); sys.exit(1)
print('pong')
PY
chmod +x "$T/bin/"*
W="$T/ops/wake.sh"
cd "$T"
# shellcheck disable=SC2016 # Literal attack text must reach Codex unchanged.
printf '%s\n' '$(touch INJECTED) `touch INJECTED` ; "quoted"' > prompt
uuid=11111111-1111-4111-8111-111111111111
future=$(python3 -c 'import datetime as d; print((d.datetime.now(d.timezone.utc)+d.timedelta(minutes=5)).isoformat())')
if "$W" add 2000-01-01T00:00+09:00 "$uuid" prompt 2>/dev/null; then exit 1; fi
if "$W" add 2027-01-01T00:00 "$uuid" prompt 2>/dev/null; then exit 1; fi
if "$W" add 25:61 "$uuid" prompt 2>/dev/null; then exit 1; fi
id=$("$W" add "$future" "$uuid" prompt --name iso)
python3 - "$id" "$future" <<'PY'
import json,pathlib,plistlib,sys,os
import datetime as dt,math
p=pathlib.Path('ops/wakes')/sys.argv[1]
s=json.loads((p/'spec.json').read_text())
assert s['mode']=='resume' and s['epoch']%60==0
assert s['epoch']==math.ceil(dt.datetime.fromisoformat(sys.argv[2]).timestamp()/60)*60
assert (p/'spec.json').stat().st_mode&0o777==0o600
assert pathlib.Path(s['plist']).stat().st_mode&0o777==0o600
with open(s['plist'],'rb') as f: job=plistlib.load(f)
assert 'StartCalendarInterval' in job and 'RunAtLoad' not in job
assert (p/'prompt.txt').read_bytes()==pathlib.Path('prompt').read_bytes()
# Name and UUID deduplicate against the same canonical session.
home=pathlib.Path(os.environ['CODEX_HOME']); home.mkdir()
import sqlite3
with sqlite3.connect(home/'state_5.sqlite') as c:
    c.execute('CREATE TABLE threads(id TEXT,name TEXT)')
    c.execute('INSERT INTO threads VALUES (?,?)',(s['target'],'test-name'))
PY
if "$W" add "$future" test-name prompt --name alias 2>/dev/null; then exit 1; fi
if "$W" add "$future" "$uuid" prompt --name duplicate 2>/dev/null; then exit 1; fi
"$W" cancel "$id"
"$W" cancel "$id"
python3 - "$id" <<'PY'
import json,pathlib,sys
s=json.loads((pathlib.Path('ops/wakes')/sys.argv[1]/'spec.json').read_text())
assert s['status']=='cancelled' and not pathlib.Path(s['plist']).exists()
PY
hhmm=$(TZ=Asia/Tokyo date +%H:%M)
id=$("$W" add "$hhmm" "$uuid" prompt --name tomorrow)
python3 - "$id" <<'PY'
import datetime as d,json,pathlib,sys
from zoneinfo import ZoneInfo
s=json.loads((pathlib.Path('ops/wakes')/sys.argv[1]/'spec.json').read_text())
assert d.datetime.fromisoformat(s['when']).date()==d.datetime.now(ZoneInfo('Asia/Tokyo')).date()+d.timedelta(days=1)
PY
"$W" cancel "$id"
# Set due time to exercise the runner without waiting for a simulated clock.
due() { python3 - "$1" <<'PY'
import json,pathlib,sys,time
p=pathlib.Path('ops/wakes')/sys.argv[1]/'spec.json'
s=json.loads(p.read_text()); s['epoch']=int(time.time())-120; p.write_text(json.dumps(s))
PY
}
id=$(WAKE_DRY=1 "$W" add "$future" "$uuid" prompt --name dry)
# Early invocation must not claim the job.
if "$T/ops/wake_run.sh" "$id"; then exit 1; fi
due "$id"
"$T/ops/wake_run.sh" "$id"
test ! -e "$HOME/calls"
test -s "ops/wakes/$id/run.log"
id=$("$W" add "$future" "$uuid" prompt --name real)
due "$id"
"$T/ops/wake_run.sh" "$id"
if "$T/ops/wake_run.sh" "$id"; then exit 1; fi
python3 - "$id" <<'PY'
import json,pathlib,sys
s=json.loads((pathlib.Path('ops/wakes')/sys.argv[1]/'spec.json').read_text())
assert s['status']=='done' and s['rc']==0 and s['delay_minutes']>=2
assert not pathlib.Path(s['plist']).exists()
calls=[json.loads(l) for l in (pathlib.Path.home()/'calls').read_text().splitlines()]
assert len(calls)==1 and calls[0]['stdin']==pathlib.Path('prompt').read_text()
assert calls[0]['args'][-1]=='-' and 'resume' in calls[0]['args']
assert not pathlib.Path('INJECTED').exists()
PY
id=$("$W" add "$future" "$uuid" prompt --name queue --mode queue)
due "$id"
"$T/ops/wake_run.sh" "$id"
python3 - <<'PY'
import pathlib,json
call=json.loads((pathlib.Path.home()/'calls').read_text().splitlines()[-1])
assert call['args'][0]=='queue' and call['args'][-1]==pathlib.Path('prompt').read_text()
assert call['stdin']==''
assert not pathlib.Path('INJECTED').exists()
PY
touch "$HOME/capacity"
id=$("$W" add "$future" "$uuid" prompt --name capacity)
due "$id"
rc=0
"$T/ops/wake_run.sh" "$id" || rc=$?
test "$rc" = 75
python3 - "$id" <<'PY'
import json,pathlib,sys
s=json.loads((pathlib.Path('ops/wakes')/sys.argv[1]/'spec.json').read_text())
assert s['status']=='failed' and s['rc']==75
assert not pathlib.Path(s['plist']).exists()
events=[json.loads(l) for l in pathlib.Path('ops/registry.jsonl').read_text().splitlines()]
assert len([e for e in events if e['event']=='wake_capacity'])==2
PY
"$W" list
printf 'PASS: time, past rejection, alias dedup, cancel, dry, delivery, injection, one-shot, capacity\n'
