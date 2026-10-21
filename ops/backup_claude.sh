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
rows.sort()
with open(os.path.join(dest, "INDEX.tsv"), "w") as out:
    out.write("created\tcwd\ttitle\tstate\ttranscript\n")
    for r in rows:
        out.write("\t".join(r) + "\n")
print(f"indexed {len(rows)} desktop sessions")
PY

date -u +%FT%TZ > "$DEST/.last-backup"
du -sh "$DEST"
