#!/usr/bin/env bash
# Turn a fresh Ubuntu 22.04/24.04 VPS into a hardened CAMO seed node.
#
# Usage (as root):
#   bash deploy-seed-node.sh --binary /root/camod [--stagenet]          # copy a prebuilt camod first (private repo)
#   bash deploy-seed-node.sh --repo https://github.com/<you>/camo.git [--branch main] [--stagenet]   # build from source
#
# Security defaults: firewall (only SSH + CAMO P2P open), RPC bound to localhost, SSH key-only login (only if a key
# is already installed, so you can't lock yourself out), fail2ban, automatic security updates, camod runs as an
# unprivileged sandboxed user.
set -euo pipefail

BINARY=""; REPO=""; BRANCH="main"; NET="mainnet"
while [ $# -gt 0 ]; do
  case "$1" in
    --binary) BINARY="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --stagenet) NET="stagenet"; shift ;;
    *) echo "unknown option $1"; exit 1 ;;
  esac
done
[ -n "$BINARY" ] || [ -n "$REPO" ] || { echo "pass --binary <path-to-camod> or --repo <git-url>"; exit 1; }
if [ "$NET" = "stagenet" ]; then P2P=39740; RPC=39741; NETFLAG="--stagenet"; else P2P=19740; RPC=19741; NETFLAG=""; fi

echo "==> System updates and security tools"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ufw fail2ban unattended-upgrades curl
dpkg-reconfigure -f noninteractive unattended-upgrades
systemctl enable --now fail2ban

if [ -n "$REPO" ]; then
  echo "==> Building CAMO from $REPO ($BRANCH)"
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git build-essential cmake pkg-config \
    libssl-dev libzmq3-dev libunbound-dev libsodium-dev libunwind8-dev liblzma-dev \
    libreadline6-dev libexpat1-dev libpgm-dev libhidapi-dev libusb-1.0-0-dev \
    libprotobuf-dev protobuf-compiler libudev-dev libboost-all-dev
  if ! swapon --show | grep -q /swapfile; then
    fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
  rm -rf /opt/camo-src
  git clone --recurse-submodules --branch "$BRANCH" "$REPO" /opt/camo-src
  cd /opt/camo-src && mkdir -p build/release && cd build/release
  # portable CPU target for this machine's architecture (Oracle Always Free servers are ARM)
  case "$(uname -m)" in aarch64|arm64) CPU_ARCH=armv8-a ;; *) CPU_ARCH=x86-64 ;; esac
  cmake -DARCH="$CPU_ARCH" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DUSE_DEVICE_TREZOR=OFF ../.. >/dev/null
  make -j"$(nproc)" daemon
  BINARY=/opt/camo-src/build/release/bin/camod
else
  echo "==> Installing prebuilt camod and its runtime libraries"
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libssl3 libzmq5 libunbound8 libsodium23 libunwind8 \
    liblzma5 libreadline8 libexpat1 libpgm-5.3-0 libhidapi-libusb0 libusb-1.0-0 libprotobuf-dev libudev1 \
    libboost-chrono-dev libboost-date-time-dev libboost-filesystem-dev libboost-locale-dev \
    libboost-program-options-dev libboost-regex-dev libboost-serialization-dev libboost-system-dev \
    libboost-thread-dev || true
fi
install -m 755 "$BINARY" /usr/local/bin/camod
/usr/local/bin/camod --version

echo "==> Service user and data dir"
id camo &>/dev/null || useradd --system --home /var/lib/camo --shell /usr/sbin/nologin camo
mkdir -p /var/lib/camo && chown camo:camo /var/lib/camo && chmod 700 /var/lib/camo
cat > /etc/default/camod <<EOF
CAMOD_ARGS="$NETFLAG --p2p-bind-port $P2P --rpc-bind-ip 127.0.0.1 --rpc-bind-port $RPC"
EOF
cat > /etc/systemd/system/camod.service <<'EOF'
[Unit]
Description=CAMO full node (seed)
After=network-online.target
Wants=network-online.target

[Service]
User=camo
Group=camo
Type=simple
EnvironmentFile=/etc/default/camod
ExecStart=/usr/local/bin/camod --non-interactive --data-dir /var/lib/camo --p2p-bind-ip 0.0.0.0 \
  --out-peers 64 --in-peers 128 --log-level 0 $CAMOD_ARGS
Restart=always
RestartSec=10
LimitNOFILE=65536
# Sandboxing: camod can only write its own data dir and cannot gain privileges
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/camo
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now camod

echo "==> Firewall: only SSH and CAMO P2P ($P2P) are reachable; RPC ($RPC) stays local"
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow OpenSSH >/dev/null
ufw limit OpenSSH >/dev/null
ufw allow "$P2P"/tcp >/dev/null
ufw --force enable >/dev/null
# Oracle Cloud's Ubuntu images ship their own iptables rules that REJECT everything but SSH before ufw's chains are
# reached, so the P2P port would stay closed. Open it there too, ahead of that REJECT, and keep it across reboots.
if iptables -C INPUT -j REJECT --reject-with icmp-host-prohibited 2>/dev/null; then
  iptables -C INPUT -p tcp --dport "$P2P" -m state --state NEW -j ACCEPT 2>/dev/null || \
    iptables -I INPUT "$(iptables -L INPUT --line-numbers | awk '/REJECT/ {print $1; exit}')" -p tcp --dport "$P2P" -m state --state NEW -j ACCEPT
  command -v netfilter-persistent >/dev/null && netfilter-persistent save >/dev/null 2>&1 || true
  echo "    Oracle Cloud firewall rules found: opened $P2P there as well (also open it in the cloud console's security list)"
fi

echo "==> SSH hardening"
# a key counts if root has one or the account that ran sudo has one (Oracle and many clouds log in as "ubuntu")
KEYFILE_USER=""
[ -n "${SUDO_USER:-}" ] && KEYFILE_USER="$(getent passwd "$SUDO_USER" | cut -d: -f6)/.ssh/authorized_keys"
if [ -s /root/.ssh/authorized_keys ] || { [ -n "$KEYFILE_USER" ] && [ -s "$KEYFILE_USER" ]; }; then
  mkdir -p /etc/ssh/sshd_config.d
  cat > /etc/ssh/sshd_config.d/99-camo-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
MaxAuthTries 3
EOF
  systemctl reload ssh 2>/dev/null || systemctl reload sshd
  echo "    password logins disabled (SSH key only)"
else
  echo "    WARNING: no SSH key installed (for root or ${SUDO_USER:-the sudo user}), so password login was left ON to avoid"
  echo "    locking you out. Add your key to ~/.ssh/authorized_keys and re-run this script to finish hardening."
fi

echo
echo "CAMO $NET seed node is running. Public IP: $(curl -s https://api.ipify.org || echo unknown), P2P port $P2P"
echo "Check it with:  journalctl -u camod -f"
