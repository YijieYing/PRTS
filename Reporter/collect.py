#!/usr/bin/env python3
"""Reporter step 1: deterministic weekly diff of everything that happened on the machines. No LLM.

usage: collect.py [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--out FILE]
Sources: git commits (local + lain), agent sessions active in the window (via AgentConsole),
new human-facing reports, PRTS progress-log rows. Every item is tagged with a project from
~/PRTS/human/projects.toml so the writer can split 工程 / 学术 / 课程.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import tomllib
import urllib.request

HOME = os.path.expanduser("~")
PRTS = os.path.join(HOME, "PRTS")
CONSOLE = "http://127.0.0.1:7788"
LOCAL_REPOS = ["~/PRTS", "~/PRTS/AgentConsole", "~/CodexBridge", "~/research/*", "~/Projects/*"]
LAIN_REPOS = ["~/Undergrad_3_Autumn/*/*", "~/projects/*", "~/repos/*"]


def registry():
    with open(os.path.join(PRTS, "human", "projects.toml"), "rb") as fh:
        projects = tomllib.load(fh)["project"]
    for p in projects:
        p["prefix"] = p["path"].replace("~", HOME, 1) if p["path"].startswith("~") else p["path"]
    return sorted(projects, key=lambda p: -len(p["prefix"]))


def classify(path, projects):
    for p in projects:
        if path == p["prefix"] or (not p.get("exact") and path.startswith(p["prefix"].rstrip("/") + "/")):
            return p["name"], p["category"]
    return os.path.basename(path.rstrip("/")) or path, "其他"


def git_log(repo, since, until, host="local"):
    fmt = "%h%x1f%ad%x1f%s"
    cmd = ["git", "-C", repo, "log", "--all", "--no-merges", f"--since={since}", f"--until={until}",
           "--date=format:%m-%d %H:%M", f"--pretty=format:{fmt}", "--shortstat"]
    if host != "local":
        cmd = ["ssh", "-o", "BatchMode=yes", host, " ".join(f"'{c}'" if " " in c or "%" in c else c for c in cmd)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
    commits, cur = [], None
    for line in out.splitlines():
        if "\x1f" in line:
            h, when, subject = line.split("\x1f", 2)
            cur = {"hash": h, "when": when, "subject": subject, "files": 0}
            commits.append(cur)
        elif cur and "changed" in line:
            m = re.search(r"(\d+) files? changed", line)
            cur["files"] = int(m.group(1)) if m else 0
    return commits


def repos():
    local = [d for pat in LOCAL_REPOS for d in glob.glob(os.path.expanduser(pat)) if os.path.isdir(os.path.join(d, ".git"))]
    script = "for d in " + " ".join(LAIN_REPOS) + '; do [ -d "$d/.git" ] && echo "$d"; done'
    lain = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "lain", script],
                          capture_output=True, text=True, timeout=30).stdout.split()
    return [("local", d) for d in sorted(set(local))] + [("lain", d) for d in lain]


def get(path):
    with urllib.request.urlopen(CONSOLE + path, timeout=60) as r:
        return json.load(r)


def sessions(since_ms, until_ms, projects):
    out = []
    for host in get("/api/state")["hosts"]:
        for a in host["agents"]:
            if a["kind"] == "error" or not since_ms <= (a.get("updated_ms") or 0) <= until_ms:
                continue
            d = get(f"/api/agent?host={host['label']}&id={a['id']}")
            path = a["cwd"] if host["label"] == "local" else f"{host['label']}:{a['cwd']}"
            wt = a.get("worktree") or {}
            name, cat = classify(wt.get("main") or path, projects)
            out.append({"host": host["label"], "kind": a["kind"], "title": a["title"], "project": name,
                        "category": cat, "cwd": a["cwd"], "state": a["state"], "source": a.get("source"),
                        "updated": dt.datetime.fromtimestamp(a["updated_ms"] / 1000).strftime("%m-%d %H:%M"),
                        "last_prompt": ((d.get("last_user") or {}).get("text") or "")[:600],
                        "recap": ((d.get("recap") or {}).get("text") or "")[:1500]})
    return out


def reports(since_ts, projects):
    pats = ["~/PRTS/human/reports/*.md", "~/Projects/*/human/*.md", "~/Projects/*/docs/overnight/REPORT-*.md",
            "~/research/*/notes/*.md"]
    out = []
    for pat in pats:
        for f in glob.glob(os.path.expanduser(pat)):
            if os.path.getmtime(f) >= since_ts and not f.endswith("notes.md"):
                name, cat = classify(os.path.dirname(f), projects)
                out.append({"path": f.replace(HOME, "~"), "project": name, "category": cat,
                            "modified": dt.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%m-%d %H:%M")})
    return out


def progress_rows(since, until):
    rows = []
    for line in open(os.path.join(PRTS, "memory", "prts.md"), encoding="utf-8"):
        m = re.match(r"\| (\d{4}-\d{2}-\d{2}) \| (.*) \|$", line.strip())
        if m and since <= m.group(1) <= until:
            rows.append({"date": m.group(1), "text": m.group(2)[:800]})
    return rows


def main():
    today = dt.date.today()
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=str(today - dt.timedelta(days=6)))
    ap.add_argument("--until", default=str(today))
    ap.add_argument("--out")
    a = ap.parse_args()
    since_dt = dt.datetime.fromisoformat(a.since)
    until_dt = dt.datetime.fromisoformat(a.until) + dt.timedelta(days=1)
    projects = registry()

    commits = []
    for host, repo in repos():
        try:
            log = git_log(repo, a.since, until_dt.strftime("%Y-%m-%d"), host)
        except (subprocess.TimeoutExpired, OSError):
            continue
        if log:
            path = repo if host == "local" else f"{host}:{repo}"
            name, cat = classify(path, projects)
            commits.append({"repo": path.replace(HOME, "~"), "project": name, "category": cat,
                            "count": len(log), "commits": log[:40]})

    data = {"window": [a.since, a.until], "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "git": commits,
            "sessions": sessions(since_dt.timestamp() * 1000, until_dt.timestamp() * 1000, projects),
            "reports": reports(since_dt.timestamp(), projects),
            "prts_log": progress_rows(a.since, a.until)}
    out = a.out or os.path.join(PRTS, "Reporter", "out", f"collect-{a.since}_{a.until}.json")
    with open(out, "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print(out, {k: len(v) for k, v in data.items() if isinstance(v, list)})


if __name__ == "__main__":
    main()
