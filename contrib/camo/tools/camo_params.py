"""Find base58 prefixes that make CAMO addresses start with a chosen letter,
and derive nothing-up-my-sleeve genesis keys (burned: nobody knows the private key)."""
import os, hashlib, uuid

ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
FULL_BLOCK, ENC_SIZES = 8, [0, 2, 3, 5, 6, 7, 9, 10, 11]

def enc_block(b):
    n = int.from_bytes(b, "big"); size = ENC_SIZES[len(b)]; out = []
    for _ in range(size):
        n, r = divmod(n, 58); out.append(ALPH[r])
    return "".join(reversed(out))

def b58(data):
    return "".join(enc_block(data[i:i+8]) for i in range(0, len(data), 8))

def varint(n):
    out = bytearray()
    while n >= 0x80: out.append((n & 0x7f) | 0x80); n >>= 7
    out.append(n); return bytes(out)

def first_chars(prefix, extra=0, trials=300):
    seen = set()
    for _ in range(trials):
        seen.add(b58(varint(prefix) + os.urandom(64 + extra + 4))[:2])
    return seen

def find(letter_pairs):
    hits = {}
    for p in range(1, 0x4000):
        s = first_chars(p)
        firsts = {x[0] for x in s}
        if len(firsts) == 1:
            hits[p] = sorted(s)
    return hits

# --- ed25519 point helpers (for valid curve points) ---
q = 2**255 - 19
d = (-121665 * pow(121666, q - 2, q)) % q
I = pow(2, (q - 1) // 4, q)

def xrecover(y):
    xx = (y*y - 1) * pow(d*y*y + 1, q - 2, q) % q
    x = pow(xx, (q + 3) // 8, q)
    if (x*x - xx) % q: x = x * I % q
    if (x*x - xx) % q: return None
    return x

def add(P, Q):
    x1, y1 = P; x2, y2 = Q
    x3 = (x1*y2 + x2*y1) * pow(1 + d*x1*x2*y1*y2, q - 2, q)
    y3 = (y1*y2 + x1*x2) * pow(1 - d*x1*x2*y1*y2, q - 2, q)
    return (x3 % q, y3 % q)

def enc_point(P):
    x, y = P
    v = y | ((x & 1) << 255)
    return v.to_bytes(32, "little")

def hash_to_point(label):
    ctr = 0
    while True:
        h = bytearray(hashlib.sha256(f"{label}:{ctr}".encode()).digest())
        sign = h[31] >> 7; h[31] &= 0x7f
        y = int.from_bytes(h, "little")
        if y < q:
            x = xrecover(y)
            if x is not None:
                if (x & 1) != sign: x = q - x
                P = (x, y)
                for _ in range(3): P = add(P, P)  # *8 -> prime-order subgroup
                return enc_point(P), ctr
        ctr += 1

if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["prefixes"]:
        for p, s in find(None).items():
            if s[0][0] == "C": print(p, s)
    else:
        for net in ("mainnet", "testnet", "stagenet"):
            out_key, c1 = hash_to_point(f"CAMO genesis output key {net}")
            tx_key, c2 = hash_to_point(f"CAMO genesis tx pubkey {net}")
            amount = varint((2**64 - 1) >> 20)
            tx = (bytes([0x01, 0x3c, 0x01, 0xff, 0x00, 0x01]) + amount + bytes([0x02]) + out_key
                  + bytes([0x21, 0x01]) + tx_key)
            u = uuid.uuid4().bytes
            print(net, tx.hex())
            print(net, "uuid", ", ".join(f"0x{b:02X}" for b in u))
