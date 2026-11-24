#!/usr/bin/env bash
# Install the CAMO network alarm on a seed node: camo_health.py watches the local node every 2 minutes and sends a
# phone notification through ntfy.sh when something goes wrong (no new blocks, node behind, few peers, wrong chain,
# reorg) and again when it recovers.
#
#   sudo bash install-alarm.sh <ntfy-topic> [--stagenet|--mainnet] [--status SEEDNAME]
#
# --status SEEDNAME also publishes this seed's public status feed (OK / CAUTION / HOLD, see camo_health.py) to the
# camo-status repository each minute it changes (heartbeat every 30 minutes). It creates a deploy key and prints
# the public half: add it to github.com/thedifference7717-sys/camo-status > Settings > Deploy keys, with write
# access. That key can write to camo-status only.
#
# The topic name works like a private channel name: keep it to yourself. Read-only: the alarm only queries the
# node's local RPC (127.0.0.1), it opens no ports.
set -euo pipefail
TOPIC=${1:?usage: install-alarm.sh <ntfy-topic> [--stagenet|--mainnet]}
NET=${2:---stagenet}
STATUS_NAME=""
[ "${3:-}" = "--status" ] && STATUS_NAME=${4:?--status needs a seed name, like seed1}
[ -z "$STATUS_NAME" ] || [[ "$STATUS_NAME" =~ ^[a-z0-9-]{1,32}$ ]] || { echo "seed name: lowercase letters, digits or -"; exit 1; }
case "$NET" in --stagenet) PORT=39741 ;; --mainnet) PORT=19741 ;; *) echo "unknown network $NET"; exit 1 ;; esac
[[ "$TOPIC" =~ ^[A-Za-z0-9_-]{8,64}$ ]] || { echo "topic: 8-64 letters, digits, - or _"; exit 1; }
RAW=https://raw.githubusercontent.com/thedifference7717-sys/camo/main/contrib/camo/tools
curl -fsSL -o /usr/local/bin/camo_health.py "$RAW/camo_health.py"
chmod 755 /usr/local/bin/camo_health.py
NAME="$(hostname)"
FEED=""
[ -z "$STATUS_NAME" ] || FEED="--status-file /run/camo-status/status.json --status-name $STATUS_NAME --clear-hold-file /run/camo-status/clear-hold"
cat > /etc/systemd/system/camo-alarm.service <<EOF
[Unit]
Description=CAMO network alarm (camo_health.py -> ntfy.sh/$TOPIC)
After=network-online.target camod.service
Wants=network-online.target

[Service]
DynamicUser=yes
StateDirectory=camo-alarm
ExecStart=/usr/bin/python3 /usr/local/bin/camo_health.py ${NET} --min-peers 1 --watch 120 --state /var/lib/camo-alarm/state.json --alert-cmd "curl -s -H 'Title: CAMO alarm ($NAME)' -d @- https://ntfy.sh/$TOPIC" $FEED $NAME=http://127.0.0.1:$PORT
RuntimeDirectory=camo-status
RuntimeDirectoryMode=0755
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
systemctl enable camo-alarm
systemctl restart camo-alarm   # restart, so a re-install takes the new settings
curl -s -H "Title: CAMO alarm ($NAME)" -d "Alarm installed: watching the ${NET#--} node every 2 minutes." "https://ntfy.sh/$TOPIC" >/dev/null
sleep 3
systemctl --no-pager --lines=5 status camo-alarm | head -12
echo "==> CAMO alarm running. Logs: journalctl -u camo-alarm -f"
[ -n "$STATUS_NAME" ] || exit 0

# Public status feed publisher: its own system user and deploy key, a timer every minute.
command -v git >/dev/null || { apt-get update -qq && apt-get install -y -qq git; }
id camo-status >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/camo-status --shell /usr/sbin/nologin camo-status
curl -fsSL -o /usr/local/bin/publish_status.sh "$RAW/publish_status.sh"
chmod 755 /usr/local/bin/publish_status.sh
KEY=/var/lib/camo-status/.ssh/camo-status
if [ ! -f "$KEY" ]; then
  install -d -m 700 -o camo-status -g camo-status /var/lib/camo-status/.ssh
  sudo -u camo-status ssh-keygen -q -t ed25519 -N "" -C "seal-watch-$STATUS_NAME" -f "$KEY"
fi
cat > /etc/systemd/system/camo-status-publish.service <<UNIT
[Unit]
Description=Publish the CAMO Seal Watch status feed ($STATUS_NAME)
After=network-online.target camo-alarm.service

[Service]
Type=oneshot
User=camo-status
Environment=HOME=/var/lib/camo-status
ExecStart=/usr/local/bin/publish_status.sh /run/camo-status/status.json $STATUS_NAME
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=/var/lib/camo-status
PrivateTmp=yes
UNIT
cat > /etc/systemd/system/camo-status-publish.timer <<UNIT
[Unit]
Description=Publish the CAMO Seal Watch status feed every minute

[Timer]
OnBootSec=2min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now camo-status-publish.timer
echo
echo "==> Status feed publisher installed as $STATUS_NAME. Add this deploy key to"
echo "    github.com/thedifference7717-sys/camo-status > Settings > Deploy keys > Add deploy key"
echo "    (title: seal-watch-$STATUS_NAME, tick 'Allow write access'):"
echo
cat "$KEY.pub"
echo
echo "    Logs: journalctl -u camo-status-publish -f"
echo "    After checking the network, clear a HOLD with: sudo touch /run/camo-status/clear-hold (takes effect within 2 minutes)"
