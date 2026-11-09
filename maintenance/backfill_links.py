#!/usr/bin/env python3
"""One-off (2026-11-09): give tasks dispatched before callers were recorded a caller and a thread.

Evidence only, no guessing:
- thread: the "session id: <uuid>" line in the task's run.log (Codex prints it at start);
- caller: the Claude session (the record's own sessionId, so fork copies don't count) that ran a
  dispatch/resume command naming this task; `for i in ...` loops are expanded.
  A task named by more than one session's transcript is skipped.
Appends `caller` and `thread` events through interaction's registry; never rewrites history.
usage: backfill_links.py [--apply]   (default: dry run, print what would be appended)
"""
import glob, json, os, re, subprocess, sys
HOME = os.path.expanduser("~")
I = os.path.join(HOME, "PRTS", "interaction")
TASKS = os.path.join(I, "state", "tasks")
apply = sys.argv[1:] == ["--apply"]

rows = [json.loads(l) for l in subprocess.run([os.path.join(I, "bin", "status")], capture_output=True, text=True).stdout.splitlines()]
have = {r["name"] for r in rows if r.get("event") in ("caller",) or (r.get("event") == "start" and r.get("caller"))}
threads = {r["name"] for r in rows if r.get("event") == "thread"}
tasks = sorted(d for d in os.listdir(TASKS) if os.path.isdir(os.path.join(TASKS, d)))

callers = {t: set() for t in tasks}
pat = re.compile(r"(dispatch(?:\.sh)?|retry_resume\.sh|bin/resume)\s+['\"]?([A-Za-z0-9_-]+)")
loop = re.compile(r"for (\w+) in ([^;]+);")
def variants(cmd):  # expand `for i in 1 2 3; do ... name-w$i ...` into one command per value
    out = [cmd]
    for var, vals in loop.findall(cmd):
        out = [c.replace("$" + var, v).replace("${" + var + "}", v) for c in out for v in vals.split()]
    return out
# A forked transcript copies its parent's history, but every record keeps its original sessionId:
# credit each tool call to that session, not to the file it was found in.
for path in glob.glob(os.path.join(HOME, ".claude", "projects", "*", "*.jsonl")):
    for line in open(path, errors="ignore"):
        if '"tool_use"' not in line or ("dispatch" not in line and "resume" not in line):
            continue
        try: rec = json.loads(line)
        except ValueError: continue
        sid = rec.get("sessionId") or os.path.basename(path)[:-6]
        for b in (rec.get("message") or {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Bash":
                for cmd in variants(b.get("input", {}).get("command", "")):
                    for m in pat.finditer(cmd):
                        if m.group(2) in callers: callers[m.group(2)].add(sid)

out = []
for t in tasks:
    log = os.path.join(TASKS, t, "run.log")
    if t not in threads and os.path.exists(log):
        m = re.search(r"session id: ([0-9a-f-]{36})", open(log, errors="ignore").read(4000))
        if m: out.append({"name": t, "event": "thread", "thread": m.group(1), "backfill": "run.log"})
    if t not in have and len(callers[t]) == 1:
        out.append({"name": t, "event": "caller", "caller": {"kind": "claude", "id": next(iter(callers[t]))}, "backfill": "transcript"})
for r in out:
    print(json.dumps(r, ensure_ascii=False))
    if apply: subprocess.run([os.path.join(I, "lib", "registry"), "append", json.dumps(r, ensure_ascii=False)], check=True)
print(f"{'appended' if apply else 'would append'} {len(out)} events; ambiguous callers skipped: "
      + ", ".join(t for t in tasks if len(callers[t]) > 1), file=sys.stderr)
