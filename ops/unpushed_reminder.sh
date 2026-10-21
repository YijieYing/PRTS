#!/bin/zsh
# post_hook of the backup plugin: never pushes. If a PRTS repo has committed-but-unpushed work older than
# 2 days, add one line per day to the human inbox so the user can ask the console to push.
inbox=$HOME/PRTS/human/inbox.md; today=$(date +%F)
for repo in "$HOME/PRTS" "$HOME/research/PRTS"; do
  n=$(git -C "$repo" rev-list --count @{u}..HEAD 2>/dev/null) || continue
  [ "$n" -gt 0 ] || continue
  oldest=$(git -C "$repo" log @{u}..HEAD --reverse --format=%ct | head -1)
  age=$(( ($(date +%s) - oldest) / 86400 ))
  [ "$age" -ge 2 ] || continue
  name=${repo/#$HOME/~}
  grep -q "$today.*未推送.*$name" "$inbox" 2>/dev/null && continue
  echo "- $today $name 有 $n 个已提交但未推送到 GitHub 的提交（最早的已 $age 天）。需要时对总控说“推 github”。" >> "$inbox"
  echo "reminded: $name $n commits, $age days"
done
