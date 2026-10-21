#!/bin/zsh
# PRTS-local post_hook for the AgentConsole backup plugin: push already-committed PRTS *repos*
# (memory, reports, scripts; NOT the backup data, which is gitignored) to GitHub.
# Never commits anything; no interactive prompts; each push gives up after 60s.
export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never
# launchd jobs do not inherit the shell's HTTPS_PROXY; GitHub is only reachable through it on this network.
# Follow the macOS system proxy setting (Clash) so the job matches what the desktop uses.
if scutil --proxy | grep -q "HTTPSEnable : 1"; then
  host=$(scutil --proxy | awk '/HTTPSProxy :/{print $3}'); port=$(scutil --proxy | awk '/HTTPSPort :/{print $3}')
  export HTTPS_PROXY="http://$host:$port" https_proxy="http://$host:$port"
fi
for repo in "$HOME/PRTS" "$HOME/research/PRTS"; do
  if perl -e 'alarm 60; exec @ARGV' git -C "$repo" push -q origin HEAD 2>&1; then
    echo "pushed $repo"
  else
    echo "push failed or timed out: $repo"
  fi
done
