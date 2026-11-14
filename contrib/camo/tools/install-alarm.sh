#!/usr/bin/env bash
# Install the CAMO network alarm on a seed node: camo_health.py watches the local node every 2 minutes and sends a
# phone notification through ntfy.sh when something goes wrong (no new blocks, node behind, few peers, wrong chain,
# reorg) and again when it recovers.
#
#   sudo bash install-alarm.sh <ntfy-topic> [--stagenet|--mainnet]
#
# The topic name works like a private channel name: keep it to yourself. Read-only: the alarm only queries the
# node's local RPC (127.0.0.1), it opens no ports.
set -euo pipefail
TOPIC=${1:?usage: install-alarm.sh <ntfy-topic> [--stagenet|--mainnet]}
NET=${2:---stagenet}
case "$NET" in --stagenet) PORT=39741 ;; --mainnet) PORT=19741 ;; *) echo "unknown network $NET"; exit 1 ;; esac
[[ "$TOPIC" =~ ^[A-Za-z0-9_-]{8,64}$ ]] || { echo "topic: 8-64 letters, digits, - or _"; exit 1; }
SRC=https://raw.githubusercontent.com/thedifference7717-sys/camo/main/contrib/camo/tools/camo_health.py
curl -fsSL -o /usr/local/bin/camo_health.py "$SRC"
chmod 755 /usr/local/bin/camo_health.py
NAME="$(hostname)"
cat > /etc/systemd/system/camo-alarm.service <<EOF
[Unit]
Description=CAMO network alarm (camo_health.py -> ntfy.sh/$TOPIC)
After=network-online.target camod.service
Wants=network-online.target

[Service]
DynamicUser=yes
StateDirectory=camo-alarm
ExecStart=/usr/bin/python3 /usr/local/bin/camo_health.py ${NET} --min-peers 1 --watch 120 --state /var/lib/camo-alarm/state.json --alert-cmd "curl -s -H 'Title: CAMO alarm ($NAME)' -d @- https://ntfy.sh/$TOPIC" $NAME=http://127.0.0.1:$PORT
Restart=always
RestartSec=30
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now camo-alarm
curl -s -H "Title: CAMO alarm ($NAME)" -d "Alarm installed: watching the ${NET#--} node every 2 minutes." "https://ntfy.sh/$TOPIC" >/dev/null
sleep 3
systemctl --no-pager --lines=5 status camo-alarm | head -12
echo "==> CAMO alarm running. Logs: journalctl -u camo-alarm -f"
