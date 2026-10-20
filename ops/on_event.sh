#!/bin/bash
# AgentConsole event handler (PRTS policy). stdin: one JSON event.
# L0: log only (default) | L1: list in ~/PRTS/human/inbox.md | L2: macOS notification + inbox.
# LLM work is deferred: a finished headless job only gets flagged for the console to verify.
ev=$(cat)
get() { python3 -c "import json,sys;print(json.loads(sys.argv[1]).get('$1',''))" "$ev"; }
kind=$(get event); to=$(get to); title=$(get title | cut -c1-60); cwd=$(get cwd)
inbox=$HOME/PRTS/human/inbox.md
line() { echo "- $(date '+%m-%d %H:%M') $1" >> "$inbox"; }
case "$kind" in
  state)
    if [ "$to" = "dormant" ] && grep -q "\"cwd\":\"$cwd\"" "$HOME/PRTS/ops/registry.jsonl" 2>/dev/null; then
      line "派发任务结束，待总控验收：$title（$cwd）"          # L1
    fi ;;
  idle_long) line "空闲很久的进程，可以关掉：$title（pid $(get pid)）" ;;   # L1
  stale) line "$(get host) 上有 $(get count) 个 session 超过 $(get days) 天没用，可以在 AgentConsole 里归档" ;;  # L1, at most daily
  host_down)                                                            # L2
    line "主机不可达：$(get host)"
    osascript -e "display notification \"$(get host) 不可达\" with title \"AgentConsole\"" ;;
esac
exit 0
