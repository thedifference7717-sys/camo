#!/usr/bin/env python3
"""Adversarial test of CAMO's block-1 allocation rule (run against a fresh regtest node).

Builds block-1 candidates from the node's own template and submits them:
  A. control: the template unchanged                                  -> must be ACCEPTED (proves the method works)
  B. miner keeps the reward: allocation outputs replaced by one output -> must be REJECTED
  C. theft: founder output key swapped for an attacker's key           -> must be REJECTED
  D. key swap: allocation outputs intact but a different tx public key -> must be REJECTED
Each bad block is submitted first; the control is submitted last (a valid block 1 ends the test).

Usage: python3 attack_block1.py <rpc_port> <any_wallet_address>
"""
import json, os, sys, urllib.request

PORT, ADDR = sys.argv[1], sys.argv[2]

def rpc(method, params):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json_rpc",
        data=json.dumps({"jsonrpc": "2.0", "id": 0, "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))

def rd_varint(b, i):
    n = s = 0
    while True:
        c = b[i]; n |= (c & 0x7F) << s; i += 1
        if c < 0x80: return n, i
        s += 7

def varint(n):
    o = bytearray()
    while n >= 0x80: o.append((n & 0x7F) | 0x80); n >>= 7
    o.append(n); return bytes(o)

def parse(blob):
    """Split a block blob into header, miner-tx fields and the trailing tx-hash list."""
    i = 0
    for _ in range(3): _, i = rd_varint(blob, i)       # major, minor, timestamp
    i += 32 + 4                                          # prev_id, nonce
    header = blob[:i]
    tx_start = i
    version, i = rd_varint(blob, i); unlock, i = rd_varint(blob, i)
    nin, i = rd_varint(blob, i); assert nin == 1 and blob[i] == 0xFF; i += 1
    height, i = rd_varint(blob, i)
    pre_out = blob[tx_start:i]
    nout, i = rd_varint(blob, i); outs = []
    for _ in range(nout):
        amt, i = rd_varint(blob, i); tag = blob[i]; i += 1
        key = blob[i:i + 32]; i += 32
        vt = b""
        if tag == 0x03: vt = blob[i:i + 1]; i += 1
        outs.append([amt, tag, key, vt])
    elen, i = rd_varint(blob, i); extra = bytearray(blob[i:i + elen]); i += elen
    rct = blob[i:i + 1]; i += 1
    return header, pre_out, outs, extra, rct, blob[i:], height

def build(header, pre_out, outs, extra, rct, tail):
    body = pre_out + varint(len(outs)) + b"".join(varint(a) + bytes([t]) + k + v for a, t, k, v in outs)
    return header + body + varint(len(extra)) + bytes(extra) + rct + tail

def submit(name, blob, expect_ok):
    r = rpc("submit_block", [blob.hex()])
    ok = "result" in r and r["result"].get("status") == "OK"
    verdict = "PASS" if ok == expect_ok else "FAIL"
    print(f"{verdict}  {name}: {'accepted' if ok else 'rejected'} (expected {'accept' if expect_ok else 'reject'})")
    return verdict == "PASS"

t = rpc("get_block_template", {"wallet_address": ADDR, "reserve_size": 8})["result"]
assert t["height"] == 1, f"node must be at height 1 (fresh chain), got {t['height']}"
blob = bytes.fromhex(t["blocktemplate_blob"])
header, pre_out, outs, extra, rct, tail, h = parse(blob)
print(f"template for height {h}: outputs {[o[0] / 1e12 for o in outs]}")
rand = lambda: os.urandom(32)
results = []

# B: one output paying the miner the normal block reward
reward = 16_981_834_481_915
results.append(submit("B miner keeps the reward", build(header, pre_out, [[reward, 0x03, rand(), b"\x00"]], extra, rct, tail), False))
# C: founder output redirected to an attacker key
stolen = [list(o) for o in outs]; stolen[0][2] = rand()
results.append(submit("C founder output redirected", build(header, pre_out, stolen, extra, rct, tail), False))
# D: same outputs, different tx public key in extra
ex2 = bytearray(extra); assert ex2[0] == 0x01; ex2[1:33] = rand()
results.append(submit("D tx public key swapped", build(header, pre_out, outs, ex2, rct, tail), False))
# A: control (the honest template)
results.append(submit("A honest template (control)", blob, True))

print("ALL PASS" if all(results) else "SOME CHECKS FAILED")
sys.exit(0 if all(results) else 1)
