#!/bin/bash
# Take over Codex thread $THREAD headlessly after its interactive TUI finishes the current turn.
set -u
THREAD=01a1532a-c005-7360-a2e8-859f9de0843a
TUI_PID=54978
ROLLOUT=$HOME/.codex/sessions/2026/10/19/rollout-2026-10-19T16-57-53-01a1532a-c005-7360-a2e8-859f9de0843a.jsonl
REPO=$HOME/Projects/aquant
OPS=$HOME/PRTS/ops/aquant-overnight; LOG=$OPS/logs; EVENTS=$LOG/events.log
STOP_NY=1620; ROUND_MAX=2100
ev() { echo "$(date '+%F %T %Z') | NY $(TZ=America/New_York date +%H:%M) | $*" | tee -a "$EVENTS"; }

ev "resume-supervisor start pid=$$; waiting for TUI turn to finish"
base=$(grep -c '"type":"task_complete"' "$ROLLOUT")
until [ "$(grep -c '"type":"task_complete"' "$ROLLOUT")" -gt "$base" ] || ! kill -0 $TUI_PID 2>/dev/null; do sleep 20; done
sleep 10
if kill -0 $TUI_PID 2>/dev/null; then kill -TERM $TUI_PID; ev "TUI turn complete -> terminated TUI pid $TUI_PID"; else ev "TUI already exited"; fi
sleep 5

run() { # $1=name $2=prompt
  ( cd "$REPO" && codex exec resume "$THREAD" \
      -c sandbox_mode='"workspace-write"' -c sandbox_workspace_write.network_access=true \
      -c approval_policy='"never"' -o "$LOG/$1.last.md" "$2" ) > "$LOG/$1.log" 2>&1 &
  local pid=$! w=0
  while kill -0 $pid 2>/dev/null; do sleep 15; w=$((w+15)); [ $w -ge $ROUND_MAX ] && { kill $pid; ev "$1 TIMEOUT"; break; }; done
  wait $pid; local rc=$?; ev "$1 exit=$rc branch=$(git -C "$REPO" branch --show-current)"; return $rc
}
n=0; fails=0
while [ "$(TZ=America/New_York date +%H%M)" -lt $STOP_NY ]; do
  n=$((n+1))
  p=$(sed -e "s/{ROUND}/$n/" -e "s/{NY_TIME}/$(TZ=America/New_York date +%H:%M)/" "$OPS/resume-round.md")
  if run "r$n" "$p"; then fails=0; else fails=$((fails+1)); fi
  [ $fails -ge 3 ] && { ev "3 consecutive failures -> stop (L2)"; break; }
  sleep 30
done
run rfinal "$(cat "$OPS/resume-final.md")"
ev "resume-supervisor done rounds=$n"
