#!/usr/bin/env python3
"""Reporter step 3: deliver an already-written report. Only ever to the user themself.

usage: deliver.py --weekly FILE --wechat FILE [--no-email]
- email: Mail.app (the user's own iCloud account) via AppleScript; no credentials touched
- wechat: (written before CodexBridge had `weixin notify`; ~/PRTS/ops/wechat-notify.sh can now push directly) we only
  stage the text at a fixed path that a user-created CodexBridge `/auto` job reads and forwards
"""
import argparse
import json
import os
import shutil
import subprocess
import time
import tomllib

from render import render

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = tomllib.load(open(os.path.join(HERE, "config.toml"), "rb"))
LOG = os.path.join(HERE, "out", "deliveries.jsonl")


def log(**kw):
    with open(LOG, "a") as fh:
        fh.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), **kw}, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weekly", required=True)
    ap.add_argument("--wechat", required=True)
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--email-only", action="store_true", help="skip staging the WeChat outbox")
    a = ap.parse_args()
    title = open(a.weekly, encoding="utf-8").readline().lstrip("# ").strip() or "PRTS 周报"

    if not a.email_only:
        outbox = os.path.expanduser(CFG["wechat_outbox"])
        shutil.copyfile(a.wechat, outbox)
        log(channel="wechat", status="staged", file=outbox)
        print(f"wechat: staged at {outbox}")

    if not a.no_email:
        html_path = os.path.join(HERE, "out", os.path.basename(a.weekly).replace(".md", ".html"))
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(render(open(a.weekly, encoding="utf-8").read()))
        r = subprocess.run(["osascript", os.path.join(HERE, "send_mail.applescript"), title, a.weekly, CFG["email_to"], html_path],
                           capture_output=True, text=True, timeout=120)
        status = "failed"
        if r.returncode == 0:  # "send" only queues it; confirm it left the Outbox and reached Sent
            q = f'tell application "Mail" to return count of (messages of sent mailbox whose subject is "{title}")'
            status = "queued"
            for _ in range(24):
                time.sleep(5)
                n = subprocess.run(["osascript", "-e", q], capture_output=True, text=True).stdout.strip()
                if n.isdigit() and int(n) > 0:
                    status = "sent"
                    break
        log(channel="email", status=status, to=CFG["email_to"], subject=title, error=r.stderr.strip()[-300:])
        print(f"email: {status} -> {CFG['email_to']} {r.stderr.strip()[-200:]}")


if __name__ == "__main__":
    main()
