#!/bin/bash
# Dispatch a Codex job headlessly and record it in the registry.
# usage: [CODEX_TOP=--search] dispatch.sh <name> <workdir> <prompt-file> [extra codex exec args...]
# Lessons baked in: stdin closed (codex exec otherwise waits on stdin forever),
# startup verified (attempted != verified), every job registered (no duplicate workers).
set -u
name=$1; wd=$2; prompt=$3; shift 3
OPS=$HOME/PRTS/ops; LOG=$OPS/jobs/$name; REG=$OPS/registry.jsonl
mkdir -p "$LOG"
# workspace-write keeps the repo's own .git read-only; grant it so workers can commit.
gitdir=$(git -C "$wd" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) && set -- --add-dir "$gitdir" "$@"
( cd "$wd" && caffeinate -i codex ${CODEX_TOP:-} exec -C "$wd" -s workspace-write "$@" \
    -o "$LOG/last.md" "$(cat "$prompt")" < /dev/null > "$LOG/run.log" 2>&1
  rc=$?
  printf '{"t":"%s","name":"%s","event":"exit","rc":%d}\n' "$(date -u +%FT%TZ)" "$name" $rc >> "$REG" ) &
pid=$!
printf '{"t":"%s","name":"%s","event":"start","pid":%d,"cwd":"%s","prompt":"%s"}\n' \
  "$(date -u +%FT%TZ)" "$name" $pid "$wd" "$prompt" >> "$REG"
for _ in $(seq 1 30); do   # up to 60s: wait for real activity, not just the banner
  sleep 2
  if ! kill -0 $pid 2>/dev/null; then echo "DIED early:"; tail -5 "$LOG/run.log"; exit 1; fi
  [ "$(grep -cvE '^(Reading additional input from stdin|\s*)$' "$LOG/run.log")" -gt 8 ] && { echo "OK $name pid=$pid log=$LOG/run.log"; exit 0; }
done
echo "SUSPECT $name: no activity after 60s"; tail -5 "$LOG/run.log"; exit 2
