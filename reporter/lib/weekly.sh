#!/bin/bash
# Reporter weekly pipeline: collect (deterministic) -> compose (one Codex run) -> deliver (email + WeChat outbox).
set -euo pipefail
R=$(cd "$(dirname "$0")/.." && pwd); L=$R/lib; S=${PRTS_REPORTER_STATE:-$R/state}
I=$(dirname "$R")/interaction/bin
mkdir -p "$S/out" "$S/outbox"
until=${1:-$(date +%F)}; since=$(date -j -v-6d -f %F "$until" +%F)
C=$S/out/collect-${since}_$until.json
W=$HOME/PRTS/human/reports/weekly-${since}_$until.md
X=$S/outbox/wechat-$until.txt
python3 "$L/collect.py" --since "$since" --until "$until" --out "$C"
sed -e "s#{COLLECT}#$C#" -e "s#{WEEKLY}#$W#" -e "s#{WECHAT}#$X#" \
    -e "s#{WEEKLY_TILDE}#~/PRTS/human/reports/weekly-${since}_$until.md#" "$L/compose.md" > "$S/out/compose-$until.md"
name=reporter-weekly-$until
"$I/dispatch" "$name" "$R" "$S/out/compose-$until.md" --add-dir "$HOME/PRTS/human"
until "$I/status" "$name" | python3 -c 'import json,sys; rows=list(map(json.loads,sys.stdin)); sys.exit(0 if rows and rows[-1].get("event") in ("exit","gave_up") else 1)'; do sleep 15; done
"$I/status" "$name" | python3 -c 'import json,sys; row=list(map(json.loads,sys.stdin))[-1]; sys.exit(row.get("rc",75))'
[ -s "$W" ] && [ -s "$X" ] || { echo "compose produced no report" >&2; exit 1; }
python3 "$L/deliver.py" --weekly "$W" --wechat "$X"
