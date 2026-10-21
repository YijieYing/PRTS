#!/bin/zsh
# 备份 Claude Code / Claude 桌面端的本地对话与记忆，供日后（含 Codex 总控）查阅。
# 只增不删：rsync 不带 --delete，源端被清理后备份里仍保留。
# 用法：ops/backup_claude.sh [目标目录]，默认 ~/PRTS/ops/backups/claude（已被 .gitignore 忽略）
set -euo pipefail

DEST="${1:-$HOME/PRTS/ops/backups/claude}"
APP="$HOME/Library/Application Support/Claude"
mkdir -p "$DEST"

# 1. 对话转录（*.jsonl）、子代理记录、各项目的自动 memory
rsync -a "$HOME/.claude/projects/" "$DEST/projects/"
# 2. CLI 设置与文件编辑快照
rsync -a "$HOME/.claude/settings.json" "$DEST/"
rsync -a "$HOME/.claude/file-history/" "$DEST/file-history/"
# 3. 桌面端会话元数据（标题、cwd、归档状态、定时任务）与 cowork 会话
rsync -a "$APP/claude-code-sessions/" "$DEST/desktop-sessions/"
rsync -a "$APP/local-agent-mode-sessions/" "$DEST/local-agent-mode-sessions/"
rsync -a "$APP/claude_desktop_config.json" "$DEST/"

# 4. 生成索引：一行一个会话，方便 grep 找到对应的 jsonl
python3 -I - "$DEST" <<'PY'
import json, sys, glob, os, datetime
dest = sys.argv[1]
rows = []
for f in glob.glob(os.path.join(dest, "desktop-sessions", "**", "local_*.json"), recursive=True):
    try:
        d = json.load(open(f))
    except Exception:
        continue
    sid = d.get("cliSessionId") or ""
    hits = glob.glob(os.path.join(dest, "projects", "*", sid + ".jsonl")) if sid else []
    ts = d.get("createdAt") or 0
    rows.append((
        datetime.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M") if ts else "",
        d.get("cwd", ""),
        (d.get("title") or "").replace("\t", " "),
        "archived" if d.get("isArchived") else "active",
        os.path.relpath(hits[0], dest) if hits else "(no transcript)",
    ))
# 一个桌面会话可能跨多个 jsonl（续接时换了 CLI 会话 id），把没被直接引用的也列出来
listed = {r[4] for r in rows}
meta = {f: open(f).read() for f in glob.glob(os.path.join(dest, "desktop-sessions", "**", "local_*.json"), recursive=True)}
for j in glob.glob(os.path.join(dest, "projects", "*", "*.jsonl")):
    rel = os.path.relpath(j, dest)
    if rel in listed:
        continue
    sid = os.path.basename(j)[:-6]
    title = ""
    try:
        title = json.load(open(j[:-6] + "/custom-title.json")).get("customTitle", "")
    except Exception:
        pass
    owner = next((json.loads(t).get("title", "") for f, t in meta.items() if sid in t), None)
    first = ""
    with open(j) as fh:
        for line in fh:
            if '"timestamp"' in line:
                first = json.loads(line).get("timestamp", "")[:16].replace("T", " ")
                break
    state = f"earlier part of: {owner}" if owner is not None else "no desktop session"
    rows.append((first, "", title, state, rel))
rows.sort()
with open(os.path.join(dest, "INDEX.tsv"), "w") as out:
    out.write("created\tcwd\ttitle\tstate\ttranscript\n")
    for r in rows:
        out.write("\t".join(r) + "\n")
print(f"indexed {len(rows)} desktop sessions")
PY

# 5. 把已提交的内容推到 GitHub（私有库）；不自动 commit，推送失败不影响本地备份
for repo in "$HOME/PRTS" "$HOME/research/PRTS"; do
  git -C "$repo" push -q origin HEAD 2>&1 && echo "pushed $repo" || echo "push failed: $repo"
done

date -u +%FT%TZ > "$DEST/.last-backup"
du -sh "$DEST"
