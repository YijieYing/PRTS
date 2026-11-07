#!/bin/bash
# Reporter weekly pipeline: collect (deterministic) -> compose (one Codex run) -> deliver (email + WeChat outbox).
set -euo pipefail
R=$HOME/PRTS/reporter
until=${1:-$(date +%F)}; since=$(date -j -v-6d -f %F "$until" +%F)
C=$R/out/collect-${since}_$until.json
W=$HOME/PRTS/human/reports/weekly-${since}_$until.md
X=$R/outbox/wechat-$until.txt
python3 "$R/collect.py" --since "$since" --until "$until" --out "$C"
sed -e "s#{COLLECT}#$C#" -e "s#{WEEKLY}#$W#" -e "s#{WECHAT}#$X#" \
    -e "s#{WEEKLY_TILDE}#~/PRTS/human/reports/weekly-${since}_$until.md#" "$R/compose.md" > "$R/out/compose-$until.md"
name=reporter-weekly-$until
"$HOME/PRTS/ops/dispatch.sh" "$name" "$R" "$R/out/compose-$until.md" --add-dir "$HOME/PRTS/human"
until grep -q "\"name\":\"$name\",\"event\":\"exit\"" "$HOME/PRTS/ops/registry.jsonl"; do sleep 15; done
[ -s "$W" ] && [ -s "$X" ] || { echo "compose produced no report" >&2; exit 1; }
python3 "$R/deliver.py" --weekly "$W" --wechat "$X"
