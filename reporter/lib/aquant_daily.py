#!/usr/bin/env python3
"""Reporter channel: aquant daily report -> WeChat outbox (and optionally email).

Contract with aquant (2026-10-21): after each US close aquant writes
  ~/Projects/aquant/outputs/daily/latest-wechat.txt  (first line "aquant 日报 YYYY-MM-DD", <= 900 chars)
  ~/Projects/aquant/outputs/daily/YYYY-MM-DD.md       (full version)
This script validates the short version and stages it at state/outbox/aquant-daily.txt, which a user-created
CodexBridge /auto job forwards at 07:30 JST. Triggered by launchd WatchPaths, plus a morning fallback run.
Only Reporter sends anything outward, and only to the user.
"""
import json
import os
import re
import subprocess
import sys
import time
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # reporter/: lib/ code, config/ settings, state/ runtime data
CFG = tomllib.load(open(os.path.join(ROOT, "config", "config.toml"), "rb"))
SRC_DIR = os.path.expanduser(CFG.get("aquant_daily_dir", "~/Projects/aquant/outputs/daily"))
STATE = os.environ.get("PRTS_REPORTER_STATE", os.path.join(ROOT, "state"))
OUT = os.path.join(STATE, "outbox", "aquant-daily.txt")
LOG = os.path.join(STATE, "out", "deliveries.jsonl")
EVENT = os.path.join(os.path.dirname(ROOT), "interaction", "bin", "event")
SECRET = re.compile(r"(PK[A-Z0-9]{16,}|AK[A-Z0-9]{16,}|sk-[A-Za-z0-9]{20,}|APCA_API_(KEY_ID|SECRET_KEY)\s*=\s*\S+)")


def log(**kw):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as fh:
        fh.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "channel": "aquant-daily", **kw},
                            ensure_ascii=False) + "\n")


def reject(reason):
    log(status="rejected", reason=reason)
    subprocess.run([EVENT, "add", "L1", "aquant_daily", f"aquant 日报没有转发：{reason}"], check=True)
    print("rejected:", reason)
    return 1


def main():
    src = os.path.join(SRC_DIR, "latest-wechat.txt")
    if not os.path.exists(src):
        print("no daily report yet")
        return 0
    text = open(src, encoding="utf-8").read().strip()
    m = re.match(r"aquant 日报 (\d{4}-\d{2}-\d{2})", text.splitlines()[0] if text else "")
    if not m:
        return reject("首行不是“aquant 日报 YYYY-MM-DD”")
    day = m.group(1)
    if os.path.exists(OUT) and open(OUT, encoding="utf-8").read().strip() == text:
        print("unchanged", day)
        return 0
    if len(text) > 900:
        return reject(f"{day} 的微信短版有 {len(text)} 字，超过 900 字")
    if SECRET.search(text):
        return reject(f"{day} 的微信短版里有疑似 key 的字符串")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    os.replace(tmp, OUT)  # atomic: the 07:30 /auto job never reads a half-written file
    log(status="staged", day=day, chars=len(text), file=OUT)
    print("staged", day, len(text), "chars")

    full = os.path.join(SRC_DIR, f"{day}.md")
    if CFG.get("aquant_daily_email", False) and os.path.exists(full):
        r = subprocess.run([sys.executable, os.path.join(HERE, "deliver.py"), "--weekly", full,
                            "--wechat", OUT, "--email-only"], capture_output=True, text=True)
        log(status="email-" + ("ok" if r.returncode == 0 else "failed"), day=day)
    return 0


if __name__ == "__main__":
    sys.exit(main())
