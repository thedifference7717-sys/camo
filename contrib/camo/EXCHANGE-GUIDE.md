# Integrating CAMO: a guide for exchanges, pools and payment services

CAMO is a Monero (v0.18.5.4) fork with new parameters and no new cryptography. If you already support Monero, CAMO
works the same way: the same wallet RPC calls, subaddresses, transaction proofs and view keys. This page lists what is
different and how to stay safe in CAMO's first months, when the network's hashrate is still small.

Contact for listings and technical questions: camocoin@proton.me. Security problems: report privately (same address,
or GitHub private vulnerability reporting on thedifference7717-sys/camo).

## Quick facts

| | |
| --- | --- |
| Ticker | CAMO |
| Decimals | 12 (1 CAMO = 10^12 atomic units, like XMR) |
| Block time | 60 seconds (emission per minute equals Monero's) |
| Proof of work | RandomX (CPU) |
| Mainnet launch | Dec 15, 2026, 18:00 UTC |
| Addresses | Standard and subaddresses: 95 characters, start with `C`. Integrated: 106 characters, start with `C` or `D` |
| Ports | P2P 19740, RPC 19741, ZMQ 19742 |
| Ring size | 16 (fixed) |
| Mined coins unlock after | 60 blocks (~1 hour) |
| Received coins spendable after | 10 blocks (~10 minutes) |
| Binaries | `camod` (node), `camo-wallet-rpc`, `camo-wallet-cli` |
| URI scheme | `camo:` |

Test networks: stagenet addresses start with `Q` (ports 39740/39741/39742), testnet with `K`/`L` (29740/29741/29742).
Never let a test-network address into a mainnet deposit or withdrawal form; `validate_address` in the wallet RPC
checks the network for you.

## Run your own node and wallet

1. Download the release from GitHub (thedifference7717-sys/camo releases) and **verify it** against the signed
   `SHA256SUMS.asc` (release key fingerprint `5F1A 8350 C748 BC43 AD19 2472 AF13 7B28 E11A 0857`). Steps:
   https://camocoin.org/verify.html. The builds are reproducible, so you can also build them yourself and compare.
2. Run a node: `camod --data-dir /var/lib/camo --rpc-bind-ip 127.0.0.1 --non-interactive`. Keep the full RPC on
   localhost. Do not use a remote node for deposits.
3. Run the wallet RPC against it: `camo-wallet-rpc --daemon-address 127.0.0.1:19741 --trusted-daemon
   --wallet-dir /var/lib/camo-wallets --rpc-bind-port 19744 --rpc-login <user>:<password>`.
4. Give each user a **subaddress** (`create_address`) and match deposits with `get_transfers` / `incoming_transfers`
   (`subaddr_index`). This is the same pattern as Monero; payment IDs are not needed.

## Confirmations: start conservative

A new chain has little hashrate, so a reorganization is cheaper to buy than on an established network. Suggested
deposit confirmations:

| Period | Confirmations | Time |
| --- | --- | --- |
| First month after launch | 60 | ~1 hour |
| After that, while CAMO's hashrate is small | 30 | ~30 minutes |
| Seal Watch says CAUTION (below) | double your normal number | |
| Seal Watch says HOLD | do not credit deposits | until it clears |

Large deposits deserve more. Keep an eye on the network hashrate (`get_info`: `difficulty` / 60 is roughly hashes per
second) and on rental markets: if renting more than the network's hashrate for an hour is cheap compared with a
deposit, wait longer for that deposit.

## The Seals' status feed (pause deposits automatically)

CAMO's watch team, the Seals, runs a monitor on each seed node. It looks for double-spend attempts, chain splits, deep
reorganizations, block bursts and hashrate swings, and publishes one small JSON file per seed:

```
https://raw.githubusercontent.com/thedifference7717-sys/camo-status/main/seed1.json
https://raw.githubusercontent.com/thedifference7717-sys/camo-status/main/seed2.json
```

`status` is `OK`, `CAUTION` or `HOLD`. A HOLD (possible double-spend, split or deep reorg) lasts at least 2 hours, or
until the team has checked the network. `updated` is a unix time; a file is refreshed at least every 30 minutes, so a
file older than 45 minutes means that seed is not reporting. The GitHub file server caches for up to 5 minutes. The
format and the human page: https://github.com/thedifference7717-sys/camo-status and https://camocoin.org/status.html.

Suggested rule: if either seed says HOLD, pause crediting CAMO deposits. If either says CAUTION, or neither is fresh,
require extra confirmations. A possible double-spend names both transaction IDs in `reasons`, so you can check whether
you credited the replaced one.

Example (Python 3, standard library only):

```python
import json, time, urllib.request

FEED = "https://raw.githubusercontent.com/thedifference7717-sys/camo-status/main/{}.json"

def camo_network_status():
    """'HOLD', 'CAUTION' or 'OK' for crediting CAMO deposits."""
    fresh = []
    for seed in ("seed1", "seed2"):
        try:
            with urllib.request.urlopen(FEED.format(seed), timeout=20) as r:
                report = json.load(r)
        except (OSError, ValueError):
            continue
        if time.time() - report.get("updated", 0) < 45 * 60:
            fresh.append(report.get("status"))
    if "HOLD" in fresh:
        return "HOLD"
    if "CAUTION" in fresh or not fresh:
        return "CAUTION"
    return "OK"
```

The feed is an early warning, not a replacement for your own node and your own confirmation policy. It cannot pause,
change or reverse the chain, and nobody can. It contains only public chain data and never identifies anyone.

## Good to know

- **Block 1** pays a fixed, consensus-enforced allocation (489,600 founder, 54,400 marketing, 96,000 provably burned).
  Every block after that is mined normally. Details: `contrib/camo/ALLOCATION.md` and the white paper.
- **Fair launch:** mainnet blocks dated before Dec 15, 2026 18:00 UTC are invalid (nodes accept blocks dated up to two
  hours ahead, so mining effectively opens around 16:00 UTC).
- **Upgrades:** CAMO follows Monero's security fixes. Watch the GitHub releases (signed) and the website. There are no
  automatic update checks in the software.
- **Privacy tools you already use with Monero work the same:** view keys for audits, `get_tx_proof` / `check_tx_proof`
  for payment disputes, `get_reserve_proof` for proof of reserves.
