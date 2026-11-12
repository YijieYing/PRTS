#!/usr/bin/env python3
"""Reporter step 3: deliver an already-written report. Only ever to the user themself.

usage: deliver.py --weekly FILE --wechat FILE [--no-email]
- email: Mail.app (the user's own iCloud account) via AppleScript; no credentials touched
- phone: notify phone sends the short summary through Bark
- wechat: optionally stage text for the existing CodexBridge /auto job
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
ROOT = os.path.dirname(HERE)  # reporter/: lib/ code, config/ settings, state/ runtime data
CFG = tomllib.load(open(os.path.join(ROOT, "config", "config.toml"), "rb"))
STATE = os.environ.get("PRTS_REPORTER_STATE", os.path.join(ROOT, "state"))
LOG = os.path.join(STATE, "out", "deliveries.jsonl")


def log(**kw):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as fh:
        fh.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), **kw}, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weekly", required=True)
    ap.add_argument("--wechat", required=True)
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--email-only", action="store_true", help="send only email (skip phone and WeChat outbox)")
    a = ap.parse_args()
    title = open(a.weekly, encoding="utf-8").readline().lstrip("# ").strip() or "PRTS 周报"

    rc = 0
    if not a.email_only and CFG.get("weekly_outbox", True):
        outbox = os.path.join(STATE, "outbox", "latest-wechat.txt") if "PRTS_REPORTER_STATE" in os.environ else os.path.expanduser(CFG["wechat_outbox"])
        os.makedirs(os.path.dirname(outbox), exist_ok=True)
        shutil.copyfile(a.wechat, outbox)
        log(channel="wechat", status="staged", file=outbox)
        print(f"wechat: staged at {outbox}")

    if not a.email_only:
        lines = [line.strip() for line in open(a.wechat, encoding="utf-8") if line.strip()]
        if not lines:
            raise ValueError("empty weekly summary")
        # Compose supplies a meaningful headline. Always attach the actual report path,
        # even for older short summaries with too many lines or a stale footer.
        body = [line for line in lines[1:] if not line.startswith("全文：")][:4]
        body.append("全文：" + os.path.abspath(os.path.expanduser(a.weekly)))
        try:
            r = subprocess.run([os.path.join(ROOT, "bin", "notify"), "phone",
                                "--title", lines[0], "--text", "\n".join(body)],
                               stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
            rc = r.returncode
            error = r.stderr.strip()[-300:]
        except (OSError, subprocess.TimeoutExpired) as e:
            rc, error = 1, str(e)
        status = "failed" if rc else "sent"
        log(channel="phone", status=status, file=a.weekly, error=error)
        print(f"phone: {status}" + (f" ({error})" if error else ""))

    if not a.no_email:
        html_path = os.path.join(STATE, "out", os.path.basename(a.weekly).replace(".md", ".html"))
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
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

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
