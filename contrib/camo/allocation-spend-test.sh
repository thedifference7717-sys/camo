#!/usr/bin/env bash
# End-to-end: a wallet restored from height 0 finds its genesis allocation, waits for unlock, and spends it privately.
set -uo pipefail
S="${CAMO_TEST_KEYS_DIR:?set CAMO_TEST_KEYS_DIR to the folder holding test_genesis_wallets.json (only for a build made with make_allocation.py from those TEST wallets)}"
B=${CAMO_BIN:-$(cd "$(dirname "$0")/../.." && pwd)/build/release/bin}; T=$(mktemp -d); DP=19990; WP=19991
K="$S/test_genesis_wallets.json"
key(){ python3 -c "import json;print(json.load(open('$K'))['$1']['$2'])"; }
exec > >(tee "$T/out.txt") 2>&1   # the checks at the end read the printed results
$B/camod --regtest --offline --fixed-difficulty 1 --data-dir $T/n --non-interactive --detach --pidfile $T/d.pid --log-file $T/d.log --rpc-bind-port $DP --p2p-bind-port 19992 --zmq-rpc-bind-port 19993 >/dev/null
$B/camo-wallet-rpc --wallet-dir $T --rpc-bind-port $WP --disable-rpc-login --daemon-address 127.0.0.1:$DP --trusted-daemon --non-interactive --detach --pidfile $T/w.pid --log-file $T/w.log >/dev/null
w(){ curl -s 127.0.0.1:$WP/json_rpc -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"$1\",\"params\":$2}"; }
d(){ curl -s 127.0.0.1:$DP/json_rpc -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"$1\",\"params\":$2}"; }
j(){ python3 -c "import sys,json;r=json.load(sys.stdin);print($1)"; }
for i in $(seq 1 60); do w get_version '{}' | grep -q result && d get_info '{}' | grep -q result && break; timeout 1 tail -f /dev/null; done

# a separate miner wallet to advance the chain
w create_wallet '{"filename":"miner","password":"","language":"English"}' >/dev/null
MINER=$(w get_address '{"account_index":0}' | j "r['result']['address']"); w close_wallet '{}' >/dev/null
d generateblocks "{\"amount_of_blocks\":80,\"wallet_address\":\"$MINER\"}" >/dev/null
echo "== Blocks 0-2 on chain (block 1 must carry the allocation even though a stranger mined it)"
for h in 0 1 2; do d get_block "{\"height\":$h}" | j "'block $h: v'+str(r['result']['block_header']['major_version']), [o['amount']/1e12 for o in json.loads(r['result']['json'])['miner_tx']['vout']]"; done

echo "== Founder-style wallet restored from height 0"
w generate_from_keys "{\"filename\":\"founder\",\"address\":\"$(key founder address)\",\"spendkey\":\"$(key founder spendkey)\",\"viewkey\":\"$(key founder viewkey)\",\"password\":\"\",\"restore_height\":0}" | j "r.get('result',{}).get('info') or r"
w refresh '{"start_height":0}' >/dev/null
w get_balance '{"account_index":0}' | j "'balance', r['result']['balance']/1e12, 'unlocked', r['result']['unlocked_balance']/1e12"

echo "== Spend 1,000 CAMO from the genesis output with ring size 16"
BOB=$MINER
w transfer "{\"destinations\":[{\"amount\":1000000000000000,\"address\":\"$BOB\"}],\"ring_size\":16}" > $T/tx.json
j "r.get('error') or ('sent', r['result']['tx_hash'], 'fee', r['result']['fee']/1e12)" < $T/tx.json
TX=$(python3 -c "import json;print(json.load(open('$T/tx.json')).get('result',{}).get('tx_hash',''))")
d generateblocks "{\"amount_of_blocks\":12,\"wallet_address\":\"$MINER\"}" >/dev/null
w refresh '{}' >/dev/null
w get_balance '{"account_index":0}' | j "'founder balance after spend', r['result']['balance']/1e12"
[ -n "$TX" ] && curl -s 127.0.0.1:$DP/get_transactions -d "{\"txs_hashes\":[\"$TX\"],\"decode_as_json\":true}" | j "'on chain: ring size', [len(i['key']['key_offsets']) for i in json.loads(r['txs'][0]['as_json'])['vin']], 'amounts visible', [o['amount'] for o in json.loads(r['txs'][0]['as_json'])['vout']], 'in block', r['txs'][0].get('block_height')"
w close_wallet '{}' >/dev/null

echo "== Marketing-style wallet (view-only) and burn wallet (public view key)"
w generate_from_keys "{\"filename\":\"mkt\",\"address\":\"$(key marketing address)\",\"viewkey\":\"$(key marketing viewkey)\",\"password\":\"\",\"restore_height\":0}" >/dev/null
w refresh '{"start_height":0}' >/dev/null; w get_balance '{"account_index":0}' | j "'marketing sees', r['result']['balance']/1e12"; w close_wallet '{}' >/dev/null
w generate_from_keys '{"filename":"burn","address":"Cdqd3jC3ocP6H1BX4G2Uis8qVYj6ddShVfqGaxkvCE64YEgGgZTt5RjLZ4toVBJ3pae1HJR1AcWQxBmSRi55ePTv4dxHzs8","viewkey":"4846a9442b62be63ac514878acb76bc3ede0468f7f3d3b0710d191fcedf57f09","password":"","restore_height":0}' >/dev/null
w refresh '{"start_height":0}' >/dev/null; w get_balance '{"account_index":0}' | j "'burn address holds', r['result']['balance']/1e12"

curl -s 127.0.0.1:$DP/stop_daemon >/dev/null; kill $(cat $T/w.pid) 2>/dev/null

echo "== Checks"
F=0; chk(){ if grep -qF "$2" "$T/out.txt"; then echo "PASS: $1"; else echo "FAIL: $1 (expected: $2)"; F=1; fi; }
chk "block 1 pays the allocation" "block 1: v16 [489600.0, 54400.0, 96000.0]"
chk "founder wallet sees 489,600 unlocked" "balance 489600.0 unlocked 489600.0"
chk "spend accepted" "('sent', "
chk "ring size 16, amounts hidden, mined" "on chain: ring size [16] amounts visible [0, 0] in block"
chk "marketing view-only wallet sees 54,400" "marketing sees 54400.0"
chk "burn view key shows 96,000" "burn address holds 96000.0"
exit $F
