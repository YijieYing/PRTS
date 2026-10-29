#!/bin/bash
# Push a message to the user's WeChat via the running CodexBridge service.
# usage: wechat-notify.sh [--title T] (--file PATH | --text TEXT)   (<= 4000 chars)
# If the WeChat context token has expired (>24h since the user's last message), it is held
# and delivered right after the user's next message. Status: add "outbox" as the only argument.
NODE=/Users/prts/.local/share/fnm/node-versions/v24.21.0/installation/bin/node
cd /Users/prts/Projects/CodexBridge/app || exit 1
if [ "$1" = "outbox" ]; then exec "$NODE" --import tsx src/cli.ts weixin outbox --state-dir "$HOME/.codexbridge"; fi
exec "$NODE" --import tsx src/cli.ts weixin notify --state-dir "$HOME/.codexbridge" "$@"
