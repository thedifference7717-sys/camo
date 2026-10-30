#!/usr/bin/env bash
# Turn a fresh Ubuntu 22.04/24.04 VPS into a CAMO seed node.
# Usage (as root):  bash deploy-seed-node.sh https://github.com/<you>/camo.git
set -euo pipefail

REPO="${1:?pass the CAMO git repo URL}"
BRANCH="${2:-master}"

echo "==> Installing build dependencies"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git build-essential cmake pkg-config \
  libssl-dev libzmq3-dev libunbound-dev libsodium-dev libunwind8-dev liblzma-dev \
  libreadline6-dev libexpat1-dev libpgm-dev libhidapi-dev libusb-1.0-0-dev \
  libprotobuf-dev protobuf-compiler libudev-dev libboost-all-dev ufw

echo "==> Adding swap (building needs ~4 GB RAM)"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> Building CAMO"
rm -rf /opt/camo-src
git clone --recurse-submodules --branch "$BRANCH" "$REPO" /opt/camo-src
cd /opt/camo-src && mkdir -p build/release && cd build/release
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DUSE_DEVICE_TREZOR=OFF ../.. >/dev/null
make -j"$(nproc)" daemon
install -m 755 bin/camod /usr/local/bin/camod

echo "==> Creating service user and data dir"
id camo &>/dev/null || useradd --system --home /var/lib/camo --shell /usr/sbin/nologin camo
mkdir -p /var/lib/camo && chown camo:camo /var/lib/camo

install -m 644 /opt/camo-src/contrib/camo/camod.service /etc/systemd/system/camod.service
systemctl daemon-reload
systemctl enable --now camod

echo "==> Opening P2P port 19740 (RPC 19741 stays local)"
ufw allow OpenSSH >/dev/null
ufw allow 19740/tcp >/dev/null
ufw --force enable >/dev/null

echo
echo "CAMO seed node is running. Public IP: $(curl -s https://api.ipify.org || echo unknown)"
echo "Check it with:  journalctl -u camod -f    or    camod status"
