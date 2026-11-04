#!/usr/bin/env bash
# Add the CAMO block explorer and/or the official mining pool to a server that already runs camod
# (set up with deploy-seed-node.sh). Builds everything on the server, so it works on x86-64 and ARM.
#
# Usage (as root, on the server):
#   bash deploy-services.sh --bundle /root/camo-bundle-<rev>.tar.gz --explorer [--tor] [--explorer-domain explorer.example.org]
#   bash deploy-services.sh --bundle /root/camo-bundle-<rev>.tar.gz --pool --pool-fee-wallet <marketing address> \
#        [--pool-min-payout 0.2] [--pool-domain pool.example.org]
#   add --stagenet for the stagenet node. Both --explorer and --pool can be given at once. Safe to re-run.
#   The bundle comes from contrib/camo/tools/make_source_bundle.sh (repos private); once the repos are public you can
#   pass --camo-src/--explorer-src/--pool-src git URLs instead. --camo-build DIR reuses an existing CAMO build.
#
# Security layout:
#   camod, the explorer and the pool run as user `camo` (no keys). The pool's hot wallet runs in camo-wallet-rpc as
#   its own user `camo-wallet`; only that user can read the wallet. All RPC/web ports bind to 127.0.0.1; only P2P,
#   stratum (4242) and, with a domain, 80/443 are opened. Caddy serves HTTPS and keeps NO access logs (the explorer
#   receives view keys in requests). This script never creates or shows wallet seeds: it prints the command for you.
#
# --stage DIR: build and write every file under DIR without touching the system (no apt, users, systemd, firewall).
set -euo pipefail

NET=mainnet; DO_EXPLORER=0; DO_POOL=0; TOR=0; EXPLORER_DOMAIN=""; POOL_DOMAIN=""; FEE_WALLET=""; MIN_PAYOUT=0.2
BUNDLE=""; CAMO_SRC=""; EXPLORER_SRC=""; POOL_SRC=""; CAMO_BUILD=""; ROOT=""; STAGE=0; JOBS=$(nproc)
while [ $# -gt 0 ]; do
  case "$1" in
    --explorer) DO_EXPLORER=1; shift ;;
    --pool) DO_POOL=1; shift ;;
    --stagenet) NET=stagenet; shift ;;
    --tor) TOR=1; shift ;;
    --explorer-domain) EXPLORER_DOMAIN="$2"; shift 2 ;;
    --pool-domain) POOL_DOMAIN="$2"; shift 2 ;;
    --pool-fee-wallet) FEE_WALLET="$2"; shift 2 ;;
    --pool-min-payout) MIN_PAYOUT="$2"; shift 2 ;;
    --bundle) BUNDLE="$2"; shift 2 ;;
    --camo-src) CAMO_SRC="$2"; shift 2 ;;
    --explorer-src) EXPLORER_SRC="$2"; shift 2 ;;
    --pool-src) POOL_SRC="$2"; shift 2 ;;
    --camo-build) CAMO_BUILD="$2"; shift 2 ;;
    --stage) ROOT="$(mkdir -p "$2" && cd "$2" && pwd)"; STAGE=1; shift 2 ;;
    --jobs) JOBS="$2"; shift 2 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "unknown option $1"; exit 1 ;;
  esac
done
die(){ echo "ERROR: $*" >&2; exit 1; }
say(){ echo "==> $*"; }
run(){ if [ $STAGE = 1 ]; then echo "    [stage] skip: $*"; else "$@"; fi; }
[ $DO_EXPLORER = 1 ] || [ $DO_POOL = 1 ] || die "pass --explorer and/or --pool"
[ $STAGE = 1 ] || [ "$(id -u)" = 0 ] || die "run as root (or use --stage DIR to try it without changing the system)"
if [ $DO_POOL = 1 ]; then
  [ -n "$FEE_WALLET" ] || die "--pool-fee-wallet <public marketing wallet address> is required for the pool"
  # must match the network: the pool silently ignores an invalid fee wallet and keeps the fee
  case "$NET:$FEE_WALLET" in mainnet:C*|stagenet:Q*) ;; *) die "fee wallet must be a $NET address (mainnet C..., stagenet Q...)" ;; esac
  python3 -c "import sys; v=float(sys.argv[1]); assert 0 < v < 1000" "$MIN_PAYOUT" 2>/dev/null || die "bad --pool-min-payout"
fi

if [ "$NET" = stagenet ]; then RPC=39741; NETFLAG=--stagenet; LMDB=/var/lib/camo/stagenet/lmdb; EXFLAG=-s
else RPC=19741; NETFLAG=""; LMDB=/var/lib/camo/lmdb; EXFLAG=""; fi
WALLET_RPC=19744; EXPLORER_PORT=8081; STRATUM=4242; POOL_WEB=4243
SRC=$ROOT/opt/camo-build-src
case "$(uname -m)" in x86_64) ARCH=x86-64 ;; aarch64|arm64) ARCH=armv8-a ;; *) ARCH=default ;; esac

# ---------------------------------------------------------------- packages
if [ $STAGE = 0 ]; then
  say "Build dependencies"
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git build-essential cmake pkg-config ccache \
    libssl-dev libzmq3-dev libunbound-dev libsodium-dev libunwind8-dev liblzma-dev libreadline-dev libexpat1-dev \
    libpgm-dev libhidapi-dev libusb-1.0-0-dev libprotobuf-dev protobuf-compiler libudev-dev libboost-all-dev \
    libasio-dev libminiupnpc-dev libcurl4-openssl-dev liblmdb-dev libevent-dev libjson-c-dev uuid-dev xxd
  [ $TOR = 1 ] && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq tor
  if [ -n "$EXPLORER_DOMAIN$POOL_DOMAIN" ]; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq caddy ||
      die "caddy isn't in this Ubuntu's archive; install it from https://caddyserver.com/docs/install, then re-run"
  fi
  if [ "$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)" -lt 3500 ] && ! swapon --show | grep -q /swapfile; then
    say "Adding 4 GB swap for the build"; fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
  id camo &>/dev/null || die "user camo not found: set up the node with deploy-seed-node.sh first"
fi

# ---------------------------------------------------------------- sources
say "Sources"
mkdir -p "$SRC"
if [ -n "$BUNDLE" ]; then
  rm -rf "$SRC"/*; tar -xzf "$BUNDLE" -C "$SRC"; cat "$SRC/VERSIONS"
fi
fetch(){ # url-or-dir dest
  [ -z "$1" ] && return 0
  rm -rf "$2"
  if [ -d "$1" ]; then cp -a "$1" "$2"; else git clone -q --recurse-submodules "$1" "$2"; fi
}
fetch "$CAMO_SRC" "$SRC/camo"; fetch "$EXPLORER_SRC" "$SRC/camo-explorer"; fetch "$POOL_SRC" "$SRC/camo-pool"

# ---------------------------------------------------------------- build CAMO libraries + wallet RPC
if [ -n "$CAMO_BUILD" ]; then
  CAMO_DIR=$(cd "$CAMO_BUILD/../.." && pwd); CAMO_BUILD=$(cd "$CAMO_BUILD" && pwd)
  say "Reusing CAMO build at $CAMO_BUILD"
else
  [ -d "$SRC/camo" ] || die "no CAMO source (use --bundle or --camo-src)"
  CAMO_DIR=$SRC/camo; CAMO_BUILD=$SRC/camo/build/release
  say "Building CAMO ($ARCH, $JOBS jobs; 45-90 min on a small server)"
  mkdir -p "$CAMO_BUILD"
  (cd "$CAMO_BUILD" && cmake -DARCH=$ARCH -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DUSE_DEVICE_TREZOR=OFF \
     -DUSE_CCACHE=ON ../.. >/dev/null && make -j"$JOBS" daemon simplewallet wallet_rpc_server >/dev/null)
fi
install -D -m 755 "$CAMO_BUILD/bin/camo-wallet-rpc" "$ROOT/usr/local/bin/camo-wallet-rpc"
install -D -m 755 "$CAMO_BUILD/bin/camo-wallet-cli" "$ROOT/usr/local/bin/camo-wallet-cli"

# ---------------------------------------------------------------- explorer
if [ $DO_EXPLORER = 1 ]; then
  [ -d "$SRC/camo-explorer" ] || die "no explorer source (bundle or --explorer-src)"
  say "Building the block explorer"
  UPNP=$(find /usr/lib /usr/lib64 -name 'libminiupnpc.so' 2>/dev/null | head -1)
  [ -n "$UPNP" ] || die "libminiupnpc.so not found (apt install libminiupnpc-dev)"
  mkdir -p "$SRC/camo-explorer/build"
  (cd "$SRC/camo-explorer/build" && cmake -DMONERO_DIR="$CAMO_DIR" -DMONERO_BUILD_DIR="$CAMO_BUILD/" \
     -DCMAKE_BUILD_TYPE=Release -DXmr_MINIUPNPC_LIBRARY="$UPNP" .. >/dev/null && make -j"$JOBS" >/dev/null)
  rm -rf "$ROOT/opt/camo-explorer"; mkdir -p "$ROOT/opt/camo-explorer"
  install -m 755 "$SRC/camo-explorer/build/camo-explorer" "$ROOT/opt/camo-explorer/"
  cp -a "$SRC/camo-explorer/build/templates" "$ROOT/opt/camo-explorer/"
  mkdir -p "$ROOT/etc/systemd/system"
  # Never add --enable-mixin-guess (guesses real ring members) or the key/tx upload checkers.
  cat > "$ROOT/etc/systemd/system/camo-explorer.service" <<EOF
[Unit]
Description=CAMO block explorer ($NET)
After=camod.service
Requires=camod.service

[Service]
User=camo
Group=camo
WorkingDirectory=/opt/camo-explorer
ExecStart=/opt/camo-explorer/camo-explorer $EXFLAG -b $LMDB -d 127.0.0.1:$RPC -x 127.0.0.1 -p $EXPLORER_PORT --enable-json-api
Restart=always
RestartSec=10
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
fi

# ---------------------------------------------------------------- pool
if [ $DO_POOL = 1 ]; then
  [ -d "$SRC/camo-pool" ] || die "no pool source (bundle or --pool-src)"
  say "Building the mining pool"
  (cd "$SRC/camo-pool" && MONERO_ROOT="$CAMO_DIR" MONERO_BUILD_ROOT="$CAMO_BUILD" make release -j"$JOBS" >/dev/null)
  rm -rf "$ROOT/opt/camo-pool"; mkdir -p "$ROOT/opt/camo-pool"
  install -m 755 "$SRC/camo-pool/build/release/monero-pool" "$ROOT/opt/camo-pool/"
  mkdir -p "$ROOT/etc/camo-pool" "$ROOT/etc/camo-wallet" "$ROOT/etc/systemd/system" "$ROOT/usr/local/bin"

  # camod tells the pool about each new block at once (pool and camod both run as user camo)
  cat > "$ROOT/usr/local/bin/camo-notify-pool" <<'EOF'
#!/bin/sh
exec /usr/bin/pkill -USR1 -x monero-pool
EOF
  chmod 755 "$ROOT/usr/local/bin/camo-notify-pool"

  # hot wallet: password file readable only by camo-wallet; the seed is created by the operator, never by this script
  W=/var/lib/camo-wallet/pool; PASS=/etc/camo-wallet/pool.pass
  if [ $STAGE = 0 ]; then
    id camo-wallet &>/dev/null || useradd --system --home /var/lib/camo-wallet --shell /usr/sbin/nologin camo-wallet
    mkdir -p /var/lib/camo-wallet /var/lib/camo-pool
    chown camo-wallet:camo-wallet /var/lib/camo-wallet; chmod 700 /var/lib/camo-wallet
    chown camo:camo /var/lib/camo-pool; chmod 700 /var/lib/camo-pool
    if [ ! -s "$PASS" ]; then head -c 32 /dev/urandom | base64 | tr -d '/+=' > "$PASS"; fi
    chown camo-wallet:camo-wallet "$PASS"; chmod 400 "$PASS"
  fi

  cat > "$ROOT/etc/systemd/system/camo-pool-wallet.service" <<EOF
[Unit]
Description=CAMO pool hot wallet (camo-wallet-rpc, localhost only)
After=camod.service
Requires=camod.service

[Service]
User=camo-wallet
Group=camo-wallet
ExecStart=/usr/local/bin/camo-wallet-rpc $NETFLAG --wallet-file $W --password-file $PASS --rpc-bind-ip 127.0.0.1 \\
  --rpc-bind-port $WALLET_RPC --disable-rpc-login --daemon-address 127.0.0.1:$RPC --trusted-daemon --non-interactive \\
  --log-file /var/lib/camo-wallet/wallet-rpc.log
Restart=always
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/camo-wallet
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

  cat > "$ROOT/etc/systemd/system/camo-pool.service" <<EOF
[Unit]
Description=CAMO mining pool
After=camod.service camo-pool-wallet.service
Requires=camod.service camo-pool-wallet.service

[Service]
User=camo
Group=camo
WorkingDirectory=/var/lib/camo-pool
ExecStart=/opt/camo-pool/monero-pool --config-file /etc/camo-pool/pool.conf
Restart=always
RestartSec=10
LimitNOFILE=65536
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/camo-pool
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

  write_pool_conf(){ # pool-wallet-address
    sed -e "s/^pool-listen = .*/pool-listen = 0.0.0.0/" -e "s/^pool-port = .*/pool-port = $STRATUM/" \
        -e "s/^webui-listen = .*/webui-listen = 127.0.0.1/" -e "s/^webui-port = .*/webui-port = $POOL_WEB/" \
        -e "s/^rpc-port = .*/rpc-port = $RPC/" -e "s/^wallet-rpc-port = .*/wallet-rpc-port = $WALLET_RPC/" \
        -e "s/^pool-wallet = .*/pool-wallet = $1/" -e "s/^pool-fee-wallet = .*/pool-fee-wallet = $FEE_WALLET/" \
        -e "s/^pool-fee = .*/pool-fee = 0.01/" -e "s/^payment-threshold = .*/payment-threshold = $MIN_PAYOUT/" \
        -e "s#^data-dir = .*#data-dir = /var/lib/camo-pool#" -e "s#^log-file =.*#log-file = /var/lib/camo-pool/pool.log#" \
        -e "s/^log-level = .*/log-level = 3/" -e "s/^block-notified = .*/block-notified = 1/" \
        "$SRC/camo-pool/pool.conf" > "$ROOT/etc/camo-pool/pool.conf"
    grep -qx "pool-fee-wallet = $FEE_WALLET" "$ROOT/etc/camo-pool/pool.conf" || die "could not set pool-fee-wallet in pool.conf"
  }
fi

if [ $STAGE = 1 ]; then
  [ $DO_POOL = 1 ] && write_pool_conf "<pool wallet address>"
  say "Staged under $ROOT (nothing on this system was changed)"; find "$ROOT" -path "$SRC" -prune -o -type f -print | sed "s#^$ROOT##" | sort
  exit 0
fi

# ---------------------------------------------------------------- activate
systemctl daemon-reload
if [ $DO_EXPLORER = 1 ]; then
  say "Starting the explorer (127.0.0.1:$EXPLORER_PORT)"; systemctl enable --now camo-explorer
fi

if [ $DO_POOL = 1 ]; then
  if ! grep -q -- "--block-notify" /etc/default/camod; then
    say "camod: notify the pool of new blocks"
    sed -i 's#^CAMOD_ARGS="\(.*\)"#CAMOD_ARGS="\1 --block-notify /usr/local/bin/camo-notify-pool"#' /etc/default/camod
    systemctl restart camod
  fi
  if [ ! -f "$W.keys" ]; then
    cat <<EOF

==> ONE MANUAL STEP: create the pool's hot wallet (you will see its 25-word seed; write it down OFFLINE):

    sudo -u camo-wallet /usr/local/bin/camo-wallet-cli $NETFLAG --generate-new-wallet $W \\
      --password-file $PASS --mnemonic-language English --daemon-address 127.0.0.1:$RPC

    Type "exit" when it has printed the seed, then re-run this same command to finish the pool setup.
    Before opening the pool, send a few CAMO to it as a float for payout network fees (see camo-pool camo/README.md).
EOF
    exit 0
  fi
  systemctl enable --now camo-pool-wallet
  for i in $(seq 60); do
    ADDR=$(curl -s 127.0.0.1:$WALLET_RPC/json_rpc -d '{"jsonrpc":"2.0","id":0,"method":"get_address","params":{"account_index":0}}' |
           python3 -c "import sys,json;print(json.load(sys.stdin)['result']['address'])" 2>/dev/null) && break; sleep 2
  done
  [ -n "${ADDR:-}" ] || die "pool wallet RPC did not answer (journalctl -u camo-pool-wallet)"
  [ "$ADDR" != "$FEE_WALLET" ] || die "the fee wallet must differ from the pool wallet"
  write_pool_conf "$ADDR"; chown root:camo /etc/camo-pool/pool.conf; chmod 640 /etc/camo-pool/pool.conf
  say "Starting the pool (stratum :$STRATUM, stats 127.0.0.1:$POOL_WEB)"; systemctl enable --now camo-pool
  systemctl restart camo-pool
  ufw allow "$STRATUM"/tcp >/dev/null
fi

if [ -n "$EXPLORER_DOMAIN$POOL_DOMAIN" ]; then
  say "HTTPS with Caddy (no access logs)"
  {
    echo "# managed by deploy-services.sh; no 'log' directive on purpose: no access logs"
    [ -n "$EXPLORER_DOMAIN" ] && printf '%s {\n\treverse_proxy 127.0.0.1:%s\n}\n' "$EXPLORER_DOMAIN" "$EXPLORER_PORT"
    [ -n "$POOL_DOMAIN" ] && printf '%s {\n\treverse_proxy 127.0.0.1:%s\n}\n' "$POOL_DOMAIN" "$POOL_WEB"
  } > /etc/caddy/Caddyfile
  ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
  systemctl enable caddy >/dev/null; systemctl reload caddy || systemctl restart caddy
fi

if [ $TOR = 1 ] && [ $DO_EXPLORER = 1 ]; then
  say "Tor onion service for the explorer"
  if ! grep -q "camo-explorer" /etc/tor/torrc; then
    printf '\n# camo-explorer\nHiddenServiceDir /var/lib/tor/camo-explorer/\nHiddenServicePort 80 127.0.0.1:%s\n' "$EXPLORER_PORT" >> /etc/tor/torrc
  fi
  systemctl restart tor; sleep 5
  ONION=$(cat /var/lib/tor/camo-explorer/hostname 2>/dev/null || echo "(not ready yet: cat /var/lib/tor/camo-explorer/hostname)")
fi

echo
echo "Done ($NET)."
[ $DO_EXPLORER = 1 ] && echo "  Explorer: ${EXPLORER_DOMAIN:+https://$EXPLORER_DOMAIN }(local 127.0.0.1:$EXPLORER_PORT)${ONION:+  Tor: http://$ONION}"
[ $DO_POOL = 1 ] && echo "  Pool: stratum $(curl -s https://api.ipify.org || echo '<server IP>'):$STRATUM  stats ${POOL_DOMAIN:+https://$POOL_DOMAIN }(local 127.0.0.1:$POOL_WEB)  fee 1% -> ${FEE_WALLET:0:12}...  min payout $MIN_PAYOUT"
echo "  Logs: journalctl -u camo-explorer / camo-pool / camo-pool-wallet -f"
