#!/bin/zsh
# post_hook of the backup plugin: never pushes. If a PRTS repo has committed-but-unpushed work older than
# 2 days, add one event per day to the review queue so the user can ask the console to push.
event="$(cd "$(dirname "$0")/.." && pwd)/interaction/bin/event"; today=$(date +%F)
for repo in "$HOME/PRTS" "$HOME/research/PRTS"; do
  n=$(git -C "$repo" rev-list --count @{u}..HEAD 2>/dev/null) || continue
  [ "$n" -gt 0 ] || continue
  oldest=$(git -C "$repo" log @{u}..HEAD --reverse --format=%ct | head -1)
  age=$(( ($(date +%s) - oldest) / 86400 ))
  [ "$age" -ge 2 ] || continue
  name=${repo/#$HOME/~}
  "$event" list | python3 -c 'import json,sys; day,repo=sys.argv[1:]; sys.exit(0 if any(r.get("source")=="unpushed_reminder" and r.get("text", "").startswith(day+" "+repo+" 有 ") for r in map(json.loads,sys.stdin)) else 1)' "$today" "$name" && continue
  "$event" add L1 unpushed_reminder "$today $name 有 $n 个已提交但未推送到 GitHub 的提交（最早的已 $age 天）。需要时对总控说“推 github”。"
  echo "reminded: $name $n commits, $age days"
done
