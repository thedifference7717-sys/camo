#!/usr/bin/env bash
# Copyright (c) 2026, The CAMO Project. BSD-3-Clause, see LICENSE.
# End-to-end test of camo_health.py's double-spend watch on a private regtest chain: one coin is spent twice
# (to Bob and to Carol), each spend is confirmed on a different side of a network split, the sides reconnect, the
# longer side wins and Bob's payment vanishes. The watch must report CRIT "POSSIBLE DOUBLE-SPEND" naming both txs.
#   bash contrib/camo/tools/test_double_spend.sh [build/release/bin]
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
BIN=${1:-$HERE/../../../build/release/bin}
T=$(mktemp -d); PA=28281; PB=28291; WP=28299
log(){ echo "[$(date -u +%H:%M:%S)] $*"; }
cleanup(){ for p in "$T"/*.pid; do [ -f "$p" ] && kill "$(cat "$p")" 2>/dev/null; done; sleep 2; rm -rf "$T"; }
trap cleanup EXIT
start(){ # name rpcport p2pport peer-p2pport [--offline: alone, so it can mine without peers]
  "$BIN/camod" --regtest --fixed-difficulty 1 --data-dir "$T/$1" --rpc-bind-ip 127.0.0.1 --rpc-bind-port "$2" \
    --p2p-bind-ip 127.0.0.1 --p2p-bind-port "$3" --zmq-rpc-bind-port $(($2+2)) --no-igd --allow-local-ip \
    --keep-fakechain --add-exclusive-node "127.0.0.1:$4" --non-interactive --detach --pidfile "$T/$1.pid" \
    --log-file "$T/$1.log" ${5:-} >/dev/null
  for i in $(seq 60); do curl -s "127.0.0.1:$2/get_info" | grep -q height && return; sleep 1; done
  log "FAIL: $1 did not start"; exit 1
}
stop(){ kill "$(cat "$T/$1.pid")"; for i in $(seq 30); do kill -0 "$(cat "$T/$1.pid")" 2>/dev/null || break; sleep 1; done; rm -f "$T/$1.pid"; }
d(){ curl -s "127.0.0.1:$1/json_rpc" -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"$2\",\"params\":${3:-{\}}}"; }
w(){ curl -s "127.0.0.1:$WP/json_rpc" -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"$1\",\"params\":${2:-{\}}}"; }
py(){ python3 -c "import sys,json;r=json.load(sys.stdin);$1"; }
height(){ curl -s "127.0.0.1:$1/get_info" | py "print(r['height'])"; }
top(){ d "$1" get_last_block_header | py "print(r['result']['block_header']['hash'])"; }
health(){ python3 "$HERE/camo_health.py" --regtest --min-peers 0 --state "$T/state.json" --status-file "$T/status.json" \
  --status-name a "$@" "a=http://127.0.0.1:$PA"; }
feed(){ python3 -c "import json;d=json.load(open('$T/status.json'));print(d['status'], ' | '.join(d['reasons']))"; }

start a $PA 28280 28290; start b $PB 28290 28280
"$BIN/camo-wallet-rpc" --wallet-dir "$T" --rpc-bind-port $WP --disable-rpc-login --daemon-address "127.0.0.1:$PA" \
  --trusted-daemon --non-interactive --detach --pidfile "$T/w.pid" --log-file "$T/w.log" >/dev/null
for i in $(seq 60); do w get_version >/dev/null 2>&1 && break; sleep 1; done
addr(){ w create_wallet "{\"filename\":\"$1\",\"password\":\"\",\"language\":\"English\"}" >/dev/null
        w get_address '{"account_index":0}' | py "print(r['result']['address'])"; w close_wallet >/dev/null; }
BOB=$(addr bob); CAROL=$(addr carol); ALICE=$(addr alice)
w open_wallet '{"filename":"alice","password":""}' >/dev/null

d $PA generateblocks "{\"amount_of_blocks\":80,\"wallet_address\":\"$ALICE\"}" >/dev/null
for i in $(seq 60); do [ "$(height $PB)" = "$(height $PA)" ] && break; sleep 1; done
w refresh >/dev/null
KI=$(w incoming_transfers '{"transfer_type":"available"}' | py "
t=[x for x in r['result']['transfers'] if x.get('unlocked')]; print(t[0]['key_image'])")
spend(){ w sweep_single "{\"address\":\"$1\",\"key_image\":\"$KI\",\"ring_size\":16,\"do_not_relay\":true,\"get_tx_hex\":true}"; }
S1=$(spend "$BOB"); S2=$(spend "$CAROL")
TX1=$(echo "$S1" | py "print(r['result']['tx_hash'])"); TX2=$(echo "$S2" | py "print(r['result']['tx_hash'])")
[ -n "$TX1" ] && [ -n "$TX2" ] && [ "$TX1" != "$TX2" ] || { log "FAIL: could not build the two spends"; echo "$S1 $S2"; exit 1; }
log "same coin spent twice: to Bob $TX1, to Carol $TX2"
health >/dev/null   # first run: remember the chain

stop b                                   # split: side A confirms the payment to Bob
curl -s "127.0.0.1:$PA/send_raw_transaction" -d "{\"tx_as_hex\":\"$(echo "$S1" | py "print(r['result']['tx_blob'])")\"}" >/dev/null
d $PA generateblocks "{\"amount_of_blocks\":1,\"wallet_address\":\"$ALICE\"}" >/dev/null
health > "$T/before" ; log "side A confirmed Bob's payment at height $(( $(height $PA) - 1 ))"
stop a; start b $PB 28290 28280 --offline # side B confirms the payment to Carol and grows longer
curl -s "127.0.0.1:$PB/send_raw_transaction" -d "{\"tx_as_hex\":\"$(echo "$S2" | py "print(r['result']['tx_blob'])")\"}" >/dev/null
d $PB generateblocks "{\"amount_of_blocks\":3,\"wallet_address\":\"$ALICE\"}" | grep -q '"status": "OK"' \
  || { log "FAIL: side B could not mine"; exit 1; }
log "side B confirmed Carol's payment and is at height $(height $PB)"
stop b; start b $PB 28290 28280
start a $PA 28280 28290                   # reconnect: A switches to the longer chain
for i in $(seq 90); do [ "$(top $PA)" = "$(top $PB)" ] && break; sleep 1; done
[ "$(top $PA)" = "$(top $PB)" ] || { log "FAIL: nodes did not converge"; exit 1; }
log "reconnected: both at height $(height $PA), Bob's payment gone"

health > "$T/after"; RC=$?
if [ $RC = 2 ] && grep -q "POSSIBLE DOUBLE-SPEND: tx $TX1" "$T/after" && grep -q "$TX2" "$T/after"; then
  log "PASS: double-spend reported as CRIT"; sed -n '/DOUBLE-SPEND/p' "$T/after" | sed 's/^/    /'
else
  log "FAIL: expected CRIT naming both txs (exit $RC)"; sed 's/^/    /' "$T/after"; exit 1
fi
# The public status feed turns HOLD, stays HOLD on the next quiet run, and clears only by hand (or after 2 hours)
F=0
feed | grep -q "^HOLD .*$TX1" && log "PASS: status feed says HOLD, naming the tx" || { log "FAIL: feed: $(feed)"; F=1; }
health >/dev/null; feed | grep -q "^HOLD" && log "PASS: HOLD stays on the next run" || { log "FAIL: feed: $(feed)"; F=1; }
touch "$T/clear-hold"; health --clear-hold-file "$T/clear-hold" > "$T/cleared"
feed | grep -q "^OK" && grep -q "cleared by hand" "$T/cleared" && [ ! -e "$T/clear-hold" ] \
  && log "PASS: touching the clear-hold file clears it" || { log "FAIL: feed: $(feed)"; F=1; }
exit $F
