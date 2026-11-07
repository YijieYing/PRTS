#!/usr/bin/env python3
"""Keep only the first K turns of a Codex thread, using official app-server calls.

usage: codex_trim.py <thread_id> <keep_turns> --name NAME [--provider P] [--archive-original] [--dry-run]
Paginated threads reject `thread/rollback`, so this forks through turn K (`thread/fork` + lastTurnId),
names the fork (`thread/name/set`), and optionally archives the original (`codex archive`, reversible).
Refuses while another process holds the original's writer lock; backs up its rollout first.
"""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time

HOME = os.path.expanduser("~")


def rpc(proc, msg_id, method, params):
    proc.stdin.write(json.dumps({"id": msg_id, "method": method, "params": params}) + "\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError(f"app-server closed while waiting for {method}: {proc.stderr.read()[-500:]}")
        msg = json.loads(line)
        if msg.get("id") == msg_id:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg.get("result")


def turn_ids(thread_id):
    con = sqlite3.connect(f"file:{HOME}/.codex/thread_history_1.sqlite?mode=ro", uri=True)
    return [r[0] for r in con.execute("select turn_id from thread_turns where thread_id = ? order by rollout_ordinal",
                                      (thread_id,))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("thread_id")
    ap.add_argument("keep_turns", type=int)
    ap.add_argument("--name", required=True)
    ap.add_argument("--provider", help="model provider for the fork, e.g. jinchi (app-server rejects --profile)")
    ap.add_argument("--archive-original", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    lock = f"{HOME}/.codex/thread-writer-locks/{a.thread_id}.lock"
    holder = subprocess.run(["lsof", "-w", "-t", lock], capture_output=True, text=True).stdout.strip()
    if holder:
        sys.exit(f"thread is open in pid {holder}; close it first")
    con = sqlite3.connect(f"file:{HOME}/.codex/state_5.sqlite?mode=ro", uri=True)
    row = con.execute("select rollout_path from threads where id = ?", (a.thread_id,)).fetchone()
    if not row:
        sys.exit("unknown thread")
    ids = turn_ids(a.thread_id)
    print(f"turns: {len(ids)}; keeping 1..{a.keep_turns} (through {ids[a.keep_turns - 1]})")
    if not 1 <= a.keep_turns < len(ids):
        sys.exit("keep_turns must be between 1 and turns-1")
    if a.dry_run:
        return
    backup = f"{HOME}/PRTS/maintenance/backups/{a.thread_id}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    os.makedirs(os.path.dirname(backup), exist_ok=True)
    shutil.copy2(row[0], backup)
    print(f"original rollout backed up to {backup}")

    cmd = ["codex", "app-server"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        rpc(proc, 1, "initialize", {"clientInfo": {"name": "prts-trim", "version": "0.1"}})
        proc.stdin.write(json.dumps({"method": "initialized"}) + "\n")
        proc.stdin.flush()
        fork = rpc(proc, 2, "thread/fork", {"threadId": a.thread_id, "lastTurnId": ids[a.keep_turns - 1],
                                            **({"modelProvider": a.provider} if a.provider else {})})
        new_id = fork["thread"]["id"]
        rpc(proc, 3, "thread/name/set", {"threadId": new_id, "name": a.name})
    finally:
        proc.stdin.close()
        proc.terminate()
        proc.wait(timeout=10)
    time.sleep(1)
    print(f"new thread {new_id} '{a.name}': {len(turn_ids(new_id))} turns")
    if a.archive_original:
        subprocess.run(["codex", "archive", a.thread_id], check=True)
        print(f"original {a.thread_id} archived (codex unarchive {a.thread_id} to restore)")


if __name__ == "__main__":
    main()
