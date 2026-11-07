#!/bin/bash
# Reporter weekly pipeline: collect (deterministic) -> compose (one Codex run) -> deliver (email + WeChat outbox).
set -euo pipefail
R=$HOME/PRTS/reporter; L=$R/lib; S=$R/state
until=${1:-$(date +%F)}; since=$(date -j -v-6d -f %F "$until" +%F)
C=$S/out/collect-${since}_$until.json
W=$HOME/PRTS/human/reports/weekly-${since}_$until.md
X=$S/outbox/wechat-$until.txt
python3 "$L/collect.py" --since "$since" --until "$until" --out "$C"
sed -e "s#{COLLECT}#$C#" -e "s#{WEEKLY}#$W#" -e "s#{WECHAT}#$X#" \
    -e "s#{WEEKLY_TILDE}#~/PRTS/human/reports/weekly-${since}_$until.md#" "$L/compose.md" > "$S/out/compose-$until.md"
name=reporter-weekly-$until
"$HOME/PRTS/interaction/bin/dispatch" "$name" "$R" "$S/out/compose-$until.md" --add-dir "$HOME/PRTS/human"
until grep -q "\"name\":\"$name\",\"event\":\"exit\"" "$HOME/PRTS/interaction/state/registry.jsonl"; do sleep 15; done
[ -s "$W" ] && [ -s "$X" ] || { echo "compose produced no report" >&2; exit 1; }
python3 "$L/deliver.py" --weekly "$W" --wechat "$X"
