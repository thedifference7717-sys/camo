#!/usr/bin/env bash
# Private CAMO test: mine to Alice, send 12.345 CAMO to Bob, show what the chain reveals.
# Usage: bash contrib/camo/regtest-demo.sh [path/to/bin]   (default: build/release/bin)
set -euo pipefail
B="${1:-$(cd "$(dirname "$0")/../.." && pwd)/build/release/bin}"
T="$(mktemp -d)"; DP=19900; WP=19901
cleanup(){ curl -s 127.0.0.1:$DP/stop_daemon >/dev/null 2>&1 || true; [ -f "$T/w.pid" ] && kill "$(cat "$T/w.pid")" 2>/dev/null || true; }
trap cleanup EXIT

"$B/camod" --regtest --offline --fixed-difficulty 1 --data-dir "$T/node" --non-interactive --detach \
  --pidfile "$T/d.pid" --log-file "$T/d.log" --rpc-bind-port $DP >/dev/null
"$B/camo-wallet-rpc" --wallet-dir "$T" --rpc-bind-port $WP --disable-rpc-login --daemon-address 127.0.0.1:$DP \
  --trusted-daemon --allow-mismatched-daemon-version --non-interactive --detach --pidfile "$T/w.pid" --log-file "$T/w.log" >/dev/null

w(){ curl -s 127.0.0.1:$WP/json_rpc -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"$1\",\"params\":$2}"; }
d(){ curl -s 127.0.0.1:$DP/json_rpc -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"$1\",\"params\":$2}"; }
py(){ python3 -c "import sys,json;r=json.load(sys.stdin);$1"; }
for i in $(seq 1 60); do w get_version '{}' >/dev/null 2>&1 && curl -s 127.0.0.1:$DP/get_info >/dev/null 2>&1 && break; sleep 1; done

w create_wallet '{"filename":"bob","password":"","language":"English"}' >/dev/null
BOB=$(w get_address '{"account_index":0}' | py "print(r['result']['address'])")
w close_wallet '{}' >/dev/null
w create_wallet '{"filename":"alice","password":"","language":"English"}' >/dev/null
ALICE=$(w get_address '{"account_index":0}' | py "print(r['result']['address'])")
echo "Alice: $ALICE"; echo "Bob:   $BOB"

d generateblocks "{\"amount_of_blocks\":120,\"wallet_address\":\"$ALICE\"}" >/dev/null
w refresh '{}' >/dev/null
TX=$(w transfer "{\"destinations\":[{\"amount\":12345000000000,\"address\":\"$BOB\"}],\"ring_size\":16}" | py "print(r['result']['tx_hash'])")
echo "Sent 12.345 CAMO, tx $TX"
d generateblocks "{\"amount_of_blocks\":12,\"wallet_address\":\"$ALICE\"}" >/dev/null
w close_wallet '{}' >/dev/null; w open_wallet '{"filename":"bob","password":""}' >/dev/null; w refresh '{}' >/dev/null
w get_balance '{"account_index":0}' | py "print('Bob balance:', r['result']['balance']/1e12, 'CAMO')"

curl -s 127.0.0.1:$DP/get_transactions -d "{\"txs_hashes\":[\"$TX\"],\"decode_as_json\":true}" | py "
t=json.loads(r['txs'][0]['as_json'])
print('On chain: ring size per input', [len(i['key']['key_offsets']) for i in t['vin']],
      '| visible amounts', [o['amount'] for o in t['vout']], '| RingCT type', t['rct_signatures']['type'])"
