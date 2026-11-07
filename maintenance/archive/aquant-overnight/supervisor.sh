#!/bin/bash
# PRTS supervisor: runs bounded Codex rounds on the aquant worktree until US close, then a final report round.
# Deterministic shell = control plane; Codex = worker; Claude reads logs/STATE when notified.
set -u
OPS=$HOME/PRTS/ops/aquant-overnight
WT=$HOME/Projects/aquant-overnight
LOG=$OPS/logs
EVENTS=$LOG/events.log
STOP_NY=1620          # last round must start before 16:20 ET
ROUND_MAX=2100        # kill a round after 35 min
export AQUANT_DATA_ROOT=$HOME/Projects/aquant/data
export AQUANT_OUTPUT_DIR=$WT/outputs
mkdir -p "$LOG"
ev() { echo "$(date '+%F %T %Z') | NY $(TZ=America/New_York date +%H:%M) | $*" | tee -a "$EVENTS"; }

run_codex() { # $1=name $2=prompt
  codex exec -C "$WT" -s workspace-write \
    -c sandbox_workspace_write.network_access=true \
    --add-dir "$HOME/Projects/aquant/.git" --add-dir "$HOME/Projects/aquant/data" \
    -o "$LOG/$1.last.md" "$2" > "$LOG/$1.log" 2>&1 &
  local pid=$! waited=0
  while kill -0 $pid 2>/dev/null; do
    sleep 15; waited=$((waited+15))
    if [ $waited -ge $ROUND_MAX ]; then kill $pid; ev "$1 TIMEOUT killed"; break; fi
  done
  wait $pid; local rc=$?
  ev "$1 exit=$rc commits=$(git -C "$WT" rev-list --count main..HEAD)"
  return $rc
}

ev "supervisor start pid=$$"
n=0; fails=0
while [ "$(TZ=America/New_York date +%H%M)" -lt $STOP_NY ]; do
  n=$((n+1))
  p=$(sed -e "s/{ROUND}/$n/" -e "s/{NY_TIME}/$(TZ=America/New_York date +%H:%M)/" "$OPS/round.md")
  if run_codex "round-$n" "$p"; then fails=0; else fails=$((fails+1)); fi
  if [ $fails -ge 3 ]; then ev "3 consecutive failures -> stop rounds (L2 for human)"; break; fi
  sleep 30
done
run_codex final "$(cat "$OPS/final.md")"
ev "supervisor done rounds=$n"
