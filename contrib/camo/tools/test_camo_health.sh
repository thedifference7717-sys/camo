#!/usr/bin/env bash
# Self-test for camo_health.py: three local regtest nodes, then a forced chain split, a reorg, a stall, the wrong
# network, a dead node, and the SSH transport (through a stand-in ssh that runs the command locally).
#   bash contrib/camo/tools/test_camo_health.sh [build/release/bin]
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
BIN=${1:-$HERE/../../../build/release/bin}
H="python3 $HERE/camo_health.py --regtest"
T=$(mktemp -d); FAILS=0
log(){ echo "[$(date -u +%H:%M:%S)] $*"; }
pass(){ log "PASS: $*"; }
fail(){ log "FAIL: $*"; FAILS=$((FAILS+1)); }
cleanup(){ for p in "$T"/*.pid; do [ -f "$p" ] && kill "$(cat "$p")" 2>/dev/null; done; sleep 2; rm -rf "$T"; }
trap cleanup EXIT

rpc(){ curl -s "127.0.0.1:$1/json_rpc" -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"$2\",\"params\":${3:-{\}}}"; }
height(){ curl -s "127.0.0.1:$1/get_info" | python3 -c 'import sys,json;print(json.load(sys.stdin)["height"])'; }
start(){ # name rpcport p2pport [extra camod args...]
  local n=$1 r=$2 p=$3; shift 3
  "$BIN/camod" --regtest --fixed-difficulty 1 --data-dir "$T/$n" --rpc-bind-ip 127.0.0.1 --rpc-bind-port "$r" \
    --p2p-bind-ip 127.0.0.1 --p2p-bind-port "$p" --zmq-rpc-bind-port $((r+2)) --no-igd --allow-local-ip --keep-fakechain \
    --non-interactive --detach --pidfile "$T/$n.pid" --log-file "$T/$n.log" "$@" >/dev/null
  for i in $(seq 60); do curl -s "127.0.0.1:$r/get_info" | grep -q height && return; sleep 1; done
  fail "$n did not start"; exit 1
}
stop(){ kill "$(cat "$T/$1.pid")"; for i in $(seq 30); do kill -0 "$(cat "$T/$1.pid")" 2>/dev/null || break; sleep 1; done; rm -f "$T/$1.pid"; }
mine(){ rpc "$1" generateblocks "{\"amount_of_blocks\":$2,\"wallet_address\":\"$ADDR\"}" >/dev/null; }
wait_h(){ for i in $(seq 60); do [ "$(height "$1")" -ge "$2" ] && return; sleep 1; done; }
run(){ $H --state "$T/state-$1.json" "${@:2}" > "$T/out" 2>&1; echo $? > "$T/rc"; }
expect(){ # description exit-code grep-pattern
  local rc; rc=$(cat "$T/rc")
  if [ "$rc" = "$2" ] && grep -qE "$3" "$T/out"; then pass "$1"; else fail "$1 (exit $rc)"; sed 's/^/    /' "$T/out"; fi
}

echo exit | "$BIN/camo-wallet-cli" --generate-new-wallet "$T/w" --password "" --mnemonic-language English --offline >/dev/null 2>&1
ADDR=$("$BIN/camo-wallet-cli" --wallet-file "$T/w" --password "" --offline --command address 2>/dev/null | grep -oE 'C[1-9A-HJ-NP-Za-km-z]{94}' | head -1)
[ -n "$ADDR" ] || { fail "no wallet address"; exit 1; }

A="--add-exclusive-node 127.0.0.1"
start a 28081 28080 $A:28090 $A:28100
start b 28091 28090 $A:28080 $A:28100
start c 28101 28100 $A:28080 $A:28090
NODES="a=http://127.0.0.1:28081 b=http://127.0.0.1:28091 c=http://127.0.0.1:28101"
sleep 5; mine 28081 20; wait_h 28091 21; wait_h 28101 21
log "3 nodes at heights $(height 28081)/$(height 28091)/$(height 28101)"

run all $NODES;                            expect "healthy network is OK" 0 "health: OK"
grep -q "block 1 pays" "$T/out" && fail "block 1 allocation flagged" || pass "block 1 carries the 640,000 allocation"
run all --json $NODES;                     expect "JSON output" 0 '"status": "OK"'
run all --stall-warn 0.001 --stall-crit 1000 $NODES; expect "stall is reported" 1 "WARN: no new block"
python3 "$HERE/camo_health.py" --stagenet --state "$T/state-x.json" $NODES > "$T/out" 2>&1; echo $? > "$T/rc"
expect "wrong network is CRIT" 2 "expected stagenet"

# SSH transport through a stand-in ssh (drops the options and host, runs the remote command here)
mkdir -p "$T/fakebin"; printf '#!/bin/sh\nfor a; do last=$a; done\nexec sh -c "$last"\n' > "$T/fakebin/ssh"; chmod +x "$T/fakebin/ssh"
PATH="$T/fakebin:$PATH" run ssh seed=ssh://root@example.invalid:28081; expect "ssh:// transport" 0 "seed +height"

# Chain split: isolate c, mine on both sides
stop c; start c 28101 28100 --offline
mine 28101 3; mine 28081 5; wait_h 28091 26
run c c=http://127.0.0.1:28101               # remember c's own 3 blocks in its state file
for h in 21 22 23; do rpc 28101 get_block "{\"height\":$h}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["blob"])' >> "$T/cblobs"; done
run all $NODES;                            expect "chain split is CRIT" 2 "CHAIN SPLIT"
grep -q "running with --offline" "$T/out" && pass "offline node noticed" || fail "offline node not noticed"

# Reconnect c: it reorganizes onto the longer chain (3 blocks replaced)
stop c; start c 28101 28100 $A:28080 $A:28090; wait_h 28101 26; sleep 3
run c c=http://127.0.0.1:28101;            expect "3-block reorg is WARN" 1 "reorganization since last run: 3 block"
run all $NODES
grep -q "CHAIN SPLIT" "$T/out" && fail "split still reported after reorg" || pass "no split after reconnect"
# c's discarded blocks, handed to a: a now holds a 3-block competing chain
while read -r b; do rpc 28081 submitblock "[\"$b\"]" >/dev/null; done < "$T/cblobs"
run all $NODES;                            expect "competing chain is WARN" 1 "a: competing chain 3 blocks"

# Dead node
stop b
run all $NODES;                            expect "dead node is CRIT" 2 "b: not answering"

[ $FAILS = 0 ] && log "ALL PASS" || log "$FAILS FAILED"
exit $FAILS
