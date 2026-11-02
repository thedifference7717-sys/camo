#!/usr/bin/env python3
"""Derive CAMO's provable burn address.

Coins sent to this address can never be spent, and anyone can verify how much was burned.

  * Spend key: a curve point made by hashing a fixed public phrase onto ed25519 ("hash to point").
    Nobody knows its private key, and finding it would mean breaking the elliptic-curve
    discrete-log problem that all of CAMO's security already relies on. So the coins cannot move.
  * View key: the PRIVATE view key is published (it is just a hash of another fixed phrase).
    Anyone can open a view-only wallet with it and see every coin sent to the address.

Anyone can re-run this script and get the identical address and keys: nothing up our sleeve.
Usage: python3 make_burn_address.py [--net mainnet|testnet|stagenet]
"""
import argparse, importlib.util, os

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mg", os.path.join(_here, "make_genesis.py"))
mg = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(mg)

SPEND_PHRASE = b"CAMO provable burn address: spend key (no one knows the private key)"
VIEW_PHRASE = b"CAMO provable burn address: view key (public on purpose)"

def hash_to_point(phrase):
    """Try keccak(phrase || counter) as a y-coordinate until it is on the curve, then multiply by 8
    to land in the prime-order subgroup. Deterministic and reproducible."""
    ctr = 0
    while True:
        h = bytearray(mg.keccak256(phrase + ctr.to_bytes(4, "little")))
        sign = h[31] >> 7; h[31] &= 0x7F
        y = int.from_bytes(h, "little")
        if y < mg.q:
            try:
                x = mg.xrecover(y)
                if (x & 1) != sign: x = mg.q - x
                P = mg.mul(8, (x, y, 1, x * y % mg.q))
                if P[0] % mg.q != 0:  # not the identity
                    return mg.enc(P), ctr
            except ValueError:
                pass
        ctr += 1

def burn_keys():
    spend_pub, ctr = hash_to_point(SPEND_PHRASE)
    view_sec = mg.hs(VIEW_PHRASE)
    view_pub = mg.enc(mg.mul(view_sec, mg.G))
    return spend_pub, view_sec.to_bytes(32, "little"), view_pub, ctr

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--net", choices=list(mg.PREFIX), default="mainnet")
    a = ap.parse_args()
    spend_pub, view_sec, view_pub, ctr = burn_keys()
    print(f"CAMO {a.net} burn address : {mg.camo_address(spend_pub, view_pub, a.net)}")
    print(f"Private view key (public) : {view_sec.hex()}")
    print(f"Public spend key          : {spend_pub.hex()}  (hash-to-point, counter {ctr})")
    print(f"Public view key           : {view_pub.hex()}")
