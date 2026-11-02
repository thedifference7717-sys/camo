#!/usr/bin/env python3
"""Build a CAMO genesis transaction that pays a founder allocation to a public address.

Usage:
  python3 make_genesis.py <address> [--amount 360000] [--net mainnet|testnet|stagenet]

<address> may be a CAMO address (C...) or a standard Monero address made from the same
keys: both encode the same public spend and view keys, so a 25-word seed created in any
Monero wallet restores in camo-wallet-cli.

Only PUBLIC keys are needed. The one-time transaction key r is random and is discarded;
the owner finds the output with their view key like any other payment.

Prints the GENESIS_TX hex to paste into src/cryptonote_config.h, plus the CAMO address.
Requires: pip install pycryptodome
"""
import argparse, os, sys
from Crypto.Hash import keccak

# ---------- ed25519 ----------
q = 2**255 - 19
L = 2**252 + 27742317777372353535851937790883648493
d = (-121665 * pow(121666, q - 2, q)) % q
I = pow(2, (q - 1) // 4, q)

def inv(x): return pow(x, q - 2, q)

def xrecover(y):
    xx = (y * y - 1) * inv(d * y * y + 1)
    x = pow(xx, (q + 3) // 8, q)
    if (x * x - xx) % q: x = x * I % q
    if (x * x - xx) % q: raise ValueError("not a curve point")
    return x

By = 4 * inv(5) % q
Bx = xrecover(By)
if Bx & 1: Bx = q - Bx
G = (Bx % q, By % q, 1, Bx * By % q)  # extended coordinates

def add(P, Q):
    x1, y1, z1, t1 = P; x2, y2, z2, t2 = Q
    A = (y1 - x1) * (y2 - x2) % q; B = (y1 + x1) * (y2 + x2) % q
    C = t1 * 2 * d * t2 % q; D = z1 * 2 * z2 % q
    E, F, Gg, H = B - A, D - C, D + C, B + A
    return (E * F % q, Gg * H % q, F * Gg % q, E * H % q)

def mul(s, P):
    R = (0, 1, 1, 0)
    while s:
        if s & 1: R = add(R, P)
        P = add(P, P); s >>= 1
    return R

def enc(P):
    x, y, z, _ = P; zi = inv(z); x, y = x * zi % q, y * zi % q
    return (y | ((x & 1) << 255)).to_bytes(32, "little")

def dec(b):
    v = int.from_bytes(b, "little"); y = v & ((1 << 255) - 1); x = xrecover(y)
    if (x & 1) != (v >> 255): x = q - x
    return (x, y, 1, x * y % q)

def keccak256(b):
    h = keccak.new(digest_bits=256); h.update(b); return h.digest()

def hs(b): return int.from_bytes(keccak256(b), "little") % L

def varint(n):
    out = bytearray()
    while n >= 0x80: out.append((n & 0x7F) | 0x80); n >>= 7
    out.append(n); return bytes(out)

# ---------- Monero-style base58 ----------
ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ENC_SIZES = [0, 2, 3, 5, 6, 7, 9, 10, 11]

def b58enc(data):
    out = ""
    for i in range(0, len(data), 8):
        blk = data[i:i + 8]; n = int.from_bytes(blk, "big"); s = ""
        for _ in range(ENC_SIZES[len(blk)]): n, r = divmod(n, 58); s = ALPH[r] + s
        out += s
    return out

def b58dec(s):
    out = b""
    for i in range(0, len(s), 11):
        chunk = s[i:i + 11]; n = 0
        for c in chunk: n = n * 58 + ALPH.index(c)
        size = ENC_SIZES.index(len(chunk)); out += n.to_bytes(size, "big")
    return out

def read_varint(b):
    n = shift = i = 0
    while True:
        c = b[i]; n |= (c & 0x7F) << shift; i += 1
        if c < 0x80: return n, i
        shift += 7

PREFIX = {"mainnet": 69, "testnet": 112, "stagenet": 140}
KNOWN = {18: "Monero mainnet", 24: "Monero stagenet", 53: "Monero testnet", 69: "CAMO mainnet", 112: "CAMO testnet", 140: "CAMO stagenet"}

def parse_address(addr):
    raw = b58dec(addr)
    if keccak256(raw[:-4])[:4] != raw[-4:]: sys.exit("Address checksum is wrong: check for typos.")
    prefix, n = read_varint(raw)
    if prefix not in KNOWN: sys.exit(f"Not a standard Monero/CAMO address (prefix {prefix}). Use the primary address, not a subaddress.")
    spend, view = raw[n:n + 32], raw[n + 32:n + 64]
    return prefix, spend, view

def camo_address(spend, view, net):
    body = varint(PREFIX[net]) + spend + view
    return b58enc(body + keccak256(body)[:4])

def output_key(r, view_pub, spend_pub, index=0):
    D = mul(8, mul(r, dec(view_pub)))
    return enc(add(mul(hs(enc(D) + varint(index)), G), dec(spend_pub)))

def build(addr, amount_camo, net):
    prefix, spend, view = parse_address(addr)
    r = int.from_bytes(os.urandom(64), "little") % L
    R = enc(mul(r, G)); P = output_key(r, view, spend)
    amount = int(round(amount_camo * 10**12))
    tx = bytes([0x01, 0x3C, 0x01, 0xFF, 0x00, 0x01]) + varint(amount) + b"\x02" + P + b"\x21\x01" + R
    return tx.hex(), camo_address(spend, view, net), KNOWN[prefix]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("address"); ap.add_argument("--amount", type=float, default=360000.0)
    ap.add_argument("--net", choices=list(PREFIX), default="mainnet")
    a = ap.parse_args()
    hexs, caddr, kind = build(a.address, a.amount, a.net)
    print(f"Input address type : {kind}")
    print(f"CAMO {a.net} address: {caddr}")
    print(f"Allocation         : {a.amount:,.12f} CAMO")
    print(f"GENESIS_TX         : {hexs}")
