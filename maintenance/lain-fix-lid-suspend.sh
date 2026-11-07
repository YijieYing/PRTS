#!/bin/bash
# lain: stop logind's lid-suspend retry loop and strip the spam from auth.log.
# Cause (2026-10-18): lid closed + HandleLidSwitch=suspend (default) + suspend.target masked
# -> logind retries every second, ~0.85G/h into /var/log/auth.log.
# Run: ssh -t lain sudo bash ~/scratch/lain-fix-lid-suspend.sh
set -euo pipefail

mkdir -p /etc/systemd/logind.conf.d
cat > /etc/systemd/logind.conf.d/90-lid-ignore.conf <<'EOF'
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
EOF
systemctl restart systemd-logind
echo "[1/3] logind: lid switch now ignored"

sleep 5
n1=$(wc -l < /var/log/auth.log); sleep 10; n2=$(wc -l < /var/log/auth.log)
echo "[2/3] auth.log grew $((n2 - n1)) lines in 10s (was ~30)"

# Keep real auth records (ssh logins etc.), drop only the suspend spam.
PAT='systemd-logind\[[0-9]+\]: (Suspending\.\.\.|Unit suspend\.target is masked|Failed to execute suspend operation)'
for f in /var/log/auth.log.1 /var/log/auth.log; do
  [ -f "$f" ] || continue
  grep -Ev "$PAT" "$f" > "$f.filtered" || true
  cat "$f.filtered" > "$f"   # in place: keeps inode/owner, rsyslog keeps writing
  rm -f "$f.filtered"
  echo "      $f -> $(du -h "$f" | cut -f1)"
done
echo "[3/3] done"; df -h /
