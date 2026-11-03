#!/usr/bin/env bash
# Launch rehearsal: three CAMO stagenet nodes on one machine, real mining difficulty, no fixed difficulty.
# Checks: block 1 carries the stagenet allocation; nodes stay in sync; a node that goes offline catches up;
# block times trend toward 60 s; a mined reward can be spent privately once unlocked.
# Usage: bash contrib/camo/stagenet-rehearsal.sh [blocks_before_spend=75]
set -uo pipefail
B="$(cd "$(dirname "$0")/../.." && pwd)/build/release/bin"
N=${1:-75}
T=$(mktemp -d); echo "workdir $T"
P=(41001 41002 41003); R=(41101 41102 41103); Z=(41201 41202 41203); WP=41301
start_node(){ # idx, extra args
  local i=$1; shift
  local peers=""; for j in 0 1 2; do [ $j != $i ] && peers="$peers --add-exclusive-node 127.0.0.1:${P[$j]}"; done
  $B/camod --stagenet --data-dir $T/n$i --p2p-bind-ip 127.0.0.1 --p2p-bind-port ${P[$i]} --rpc-bind-port ${R[$i]} \
    --zmq-rpc-bind-port ${Z[$i]} --allow-local-ip --no-igd --disable-dns-checkpoints $peers \
    --non-interactive --detach --pidfile $T/n$i.pid --log-file $T/n$i.log "$@" >/dev/null
}
rpc(){ curl -s 127.0.0.1:$1/json_rpc -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"$2\",\"params\":${3:-{\}}}"; }
w(){ curl -s 127.0.0.1:$WP/json_rpc -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"$1\",\"params\":${2:-{\}}}"; }
info(){ curl -s 127.0.0.1:$1/get_info | python3 -c "import sys,json;r=json.load(sys.stdin);print(r['height'],r['top_block_hash'][:12],r['outgoing_connections_count']+r['incoming_connections_count'])"; }
wait_up(){ for k in $(seq 1 90); do curl -s 127.0.0.1:$1/get_info | grep -q height && return 0; timeout 1 tail -f /dev/null; done; return 1; }
log(){ echo "[$(date -u +%H:%M:%S)] $*"; }

for i in 0 1 2; do start_node $i; done
for i in 0 1 2; do wait_up ${R[$i]} || { log "node $i failed to start"; tail -5 $T/n$i.log; exit 1; }; done
$B/camo-wallet-rpc --stagenet --wallet-dir $T --rpc-bind-port $WP --disable-rpc-login --daemon-address 127.0.0.1:${R[0]} \
  --trusted-daemon --non-interactive --detach --pidfile $T/w.pid --log-file $T/w.log >/dev/null
for k in $(seq 1 90); do w get_version | grep -q result && break; timeout 1 tail -f /dev/null; done
w create_wallet '{"filename":"miner","password":"","language":"English"}' >/dev/null
MINER=$(w get_address '{"account_index":0}' | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['address'])")
w create_wallet '{"filename":"friend","password":"","language":"English"}' >/dev/null
FRIEND=$(w get_address '{"account_index":0}' | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['address'])")
w close_wallet >/dev/null; w open_wallet '{"filename":"miner","password":""}' >/dev/null
log "3 nodes up; miner ${MINER:0:12}…  connections: $(for i in 0 1 2; do info ${R[$i]} | awk '{print $3}'; done | tr '\n' ' ')"
curl -s 127.0.0.1:${R[0]}/start_mining -d "{\"miner_address\":\"$MINER\",\"threads_count\":2,\"do_background_mining\":false,\"ignore_battery\":true}" >/dev/null
log "mining started on node 0 (real difficulty)"

height(){ curl -s 127.0.0.1:$1/get_info | python3 -c "import sys,json;print(json.load(sys.stdin)['height'])"; }
until [ "$(height ${R[0]})" -ge 3 ]; do timeout 5 tail -f /dev/null; done
rpc ${R[1]} get_block '{"height":1}' | python3 -c "import sys,json;r=json.load(sys.stdin)['result'];print('['+__import__('time').strftime('%H:%M:%S',__import__('time').gmtime())+'] block 1 on node 1:', [o['amount']/1e12 for o in json.loads(r['json'])['miner_tx']['vout']])"

until [ "$(height ${R[0]})" -ge 20 ]; do timeout 10 tail -f /dev/null; done
log "height 20: $(for i in 0 1 2; do echo -n "n$i=$(info ${R[$i]}) | "; done)"
log "taking node 2 offline"; curl -s 127.0.0.1:${R[2]}/stop_daemon >/dev/null
until [ "$(height ${R[0]})" -ge 35 ]; do timeout 10 tail -f /dev/null; done
log "restarting node 2 at network height $(height ${R[0]})"; start_node 2; wait_up ${R[2]}
for k in $(seq 1 60); do [ "$(height ${R[2]})" -ge "$(height ${R[0]})" ] && break; timeout 5 tail -f /dev/null; done
log "after resync: $(for i in 0 1 2; do echo -n "n$i=$(info ${R[$i]}) | "; done)"

until [ "$(height ${R[0]})" -ge "$N" ]; do timeout 15 tail -f /dev/null; done
python3 - ${R[0]} <<'EOF'
import json, sys, urllib.request
port = sys.argv[1]
def rpc(m, p):
    r = urllib.request.Request(f"http://127.0.0.1:{port}/json_rpc", data=json.dumps({"jsonrpc":"2.0","id":0,"method":m,"params":p}).encode())
    return json.load(urllib.request.urlopen(r))["result"]
top = rpc("get_last_block_header", {})["block_header"]["height"]
hs = rpc("get_block_headers_range", {"start_height": 2, "end_height": top})["headers"]
gaps = [b["timestamp"] - a["timestamp"] for a, b in zip(hs, hs[1:])]
last = gaps[-20:]
print(f"block times: first 20 avg {sum(gaps[:20])/20:.0f}s, last 20 avg {sum(last)/len(last):.0f}s, difficulty now {hs[-1]['difficulty']}")
EOF
w refresh >/dev/null
w get_balance '{"account_index":0}' | python3 -c "import sys,json;r=json.load(sys.stdin)['result'];print('miner balance', r['balance']/1e12, 'unlocked', r['unlocked_balance']/1e12)"
w transfer "{\"destinations\":[{\"amount\":5000000000000,\"address\":\"$FRIEND\"}]}" | python3 -c "import sys,json;r=json.load(sys.stdin);print('spend 5 CAMO:', r.get('error') or ('sent', r['result']['tx_hash'][:16]))"
H0=$(height ${R[0]}); until [ "$(height ${R[0]})" -ge $((H0 + 11)) ]; do timeout 15 tail -f /dev/null; done
w close_wallet >/dev/null; w open_wallet '{"filename":"friend","password":""}' >/dev/null; w refresh >/dev/null
w get_balance '{"account_index":0}' | python3 -c "import sys,json;print('friend received', json.load(sys.stdin)['result']['balance']/1e12, 'CAMO')"
log "final: $(for i in 0 1 2; do echo -n "n$i=$(info ${R[$i]}) | "; done)"
grep -hE "ERROR|EXCEPTION" $T/n*.log | grep -vE "log categories|Failed to connect to" | sort | uniq -c | sort -rn | head -8
curl -s 127.0.0.1:${R[0]}/stop_mining >/dev/null
for i in 0 1 2; do curl -s 127.0.0.1:${R[$i]}/stop_daemon >/dev/null; done; kill $(cat $T/w.pid) 2>/dev/null
log "rehearsal done"
