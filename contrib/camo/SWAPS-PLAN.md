# BTC ↔ CAMO atomic swaps: plan (v1.2, Q2 2027)

Written Nov 17, 2026. Status: **research done, nothing built yet.** Mainnet launch (Dec 15) comes first.

## What an atomic swap is
Two people trade BTC for CAMO directly. The protocol ensures that either both payments go through or both
are refunded. Nobody holds anyone else's coins: no exchange, no custody, no account.

## Starting point: eigenwallet (formerly UnstoppableSwap / COMIT xmr-btc-swap)
- `https://github.com/eigenwallet/core`: the working BTC ↔ XMR swap, in use since 2021, maintained (commits Nov 17, 2026).
  Rust. Maker = `asb` (offers a price, holds both coins), taker = `swap` CLI / GUI.
- **License: GPL-3.0.** A fork must stay GPL-3.0 (fine for a separate swap tool). Linking it into Ghillie would make
  Ghillie GPL too, so keep it a separate process / app that Ghillie talks to.
- The CAMO side of the protocol uses only standard Monero keys and transactions (a shared address from two key halves).
  **CAMO's consensus and cryptography do not change.** The BTC side uses adaptor signatures on Bitcoin.
- Their AI policy (`AI_POLICY.md`) welcomes AI as a tool, not as an autopilot: a fork is ours, but any fix we send
  upstream must be human-reviewed.

## What a CAMO fork has to change (parameters, plus one privacy-critical item)
1. **Wallet library:** `monero-sys` builds Monero's `wallet2` from a Monero fork; point it at the `camo` repo (same
   wallet2_api.h we already use for Ghillie mobile).
2. **monero-oxide** (`kayabaNerve/monero-oxide`, used for building transactions): address prefixes
   (`MONERO_MAINNET_BYTES = 18, 19, 42, 70` → CAMO's 69/70/71 + stagenet/testnet).
3. **PRIVACY-CRITICAL: block time.** monero-oxide's decoy selection (`wallet/src/decoys.rs`) uses `BLOCK_TIME` (Monero's
   120 s) to model output ages. CAMO has 60 s blocks. Unchanged, swap transactions would pick decoys with a different age
   distribution from normal CAMO wallets and stand out on chain. It must use 60 s, matching what we did for wallet2's
   `select_outputs.gamma` test on Nov 4. Also `swap-env`: `monero_avg_block_time: 2 min` → 1 min, finality/lock
   confirmations re-checked for 60 s blocks.
4. Network: CAMO daemon ports, our seed/remote nodes, rendezvous points for makers, the BTC network unchanged.
5. Names, wording, no Monero defaults left (no XMR nodes, no XMR price feeds).

## USDC
`https://github.com/AthanorLabs/atomic-swap` (XMR ↔ ETH and ERC-20 tokens such as USDC, Go, LGPL-3.0). Same idea,
same changes (prefixes, 60 s blocks). Do it after BTC works. Note: USDC can be frozen by its issuer; BTC cannot.

## Order of work
1. Fork eigenwallet → `camo-swap` (private at first). Change 1-5. Build.
2. Full swap on **regtest** (BTC regtest + CAMO regtest), both maker and taker local; then refund paths
   (taker vanishes, maker vanishes, timelocks expire).
3. **Stagenet + BTC testnet** swap in public, with a test maker.
4. **Outside security review** of our changes (especially the decoy block-time change).
5. Ghillie integration: Ghillie runs or talks to the taker; "0.25% Ghillie fee on swaps" (decided Nov 3) needs care:
   a fee output must not fingerprint swap transactions, the same reason sends have no fee.
6. Makers: someone must offer liquidity. **Talk to a crypto lawyer before Anthony runs a maker** (trading with the
   public at posted prices). Custodial swaps (holding users' coins) are out: that is money transmission in the US.

## Not doing
- No custodial swaps or exchange accounts inside Ghillie.
- No third-party exchange API keys in the wallet (declined Nov 17).
