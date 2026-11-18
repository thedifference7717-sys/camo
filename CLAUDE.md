# CAMO — project guide for Claude Code

CAMO is a privacy coin: a rebranded fork of **Monero v0.18.5.4** (C++), owned by Anthony (GitHub thedifference7717-sys).
Mainnet **Dec 15, 2026 18:00 UTC** (mining effectively opens ~16:00, announced). Public stagenet since Nov 11.
**Full history, decisions, server details and test results: `contrib/camo/PROJECT-LOG.md`** (read the part you need).
Runbooks: `contrib/camo/MAINNET-LAUNCH.md`, `STAGENET-LAUNCH.md`; security: `SECURITY.md`; swaps: `contrib/camo/SWAPS-PLAN.md`.

## Working with Anthony
- ONE small step per message, then wait. End each step with one short expected reply ("Reply **k** when …").
  NO AskUserQuestion boxes. Every command/URL/text he must type goes in its own code block.
- Cloud sessions can't SSH to his servers or reach non-443 ports: he runs commands on his Mac and sends screenshots.
  His Mac: Intel iMac, 8 GB RAM, **python3 = 3.7.7**, Terminal windows: top-left = stagenet miner (don't paste there).
- Merge our own PRs routinely; ask before anything that costs money, can't be undone, or posts publicly as him.
- Keep it free (no paid servers). Never commit with a personal email (camo-website / ghillie-mobile commits:
  `Anthony <camocoin@proton.me>`). Treat his name/email as private; the ntfy topic stays out of repos.
- Never ask for seed words or private keys (public addresses only).

## Hard rules
- **Never change cryptography.** Changes are parameters only. Crypto/consensus change → stop and explain the risk.
- Keep Monero/CryptoNote copyright headers and `LICENSE` (BSD-3). Cherry-picks: `-x`, original authors kept.
- Merge upstream security fixes (`bash contrib/camo/tools/check_upstream.sh`; base v0.18.5.4).
- Never commit a test allocation header or test checkpoints.
- One editor at a time: before changing code run `git status` / `git log -3`; unknown uncommitted changes → ask.

## What differs from Monero
Names/binaries (`camod`, `camo-wallet-cli`, …), address prefixes (mainnet starts with `C`, stagenet `Q`, testnet `K/L`),
ports 19740/1/2 (testnet 297xx, stagenet 397xx), network IDs, genesis, hard forks (v1 genesis, v16 from block 1),
no Monero checkpoints/seeds/DNS/update checks, `camo:` URIs, version 1.0.0 "CAMO Genesis", **60 s blocks** (same emission
per minute), **fair-launch rule** (mainnet blocks dated before 1797357600 invalid), and the **block-1 allocation**:
block 1's coinbase is fixed by consensus (`src/cryptonote_core/camo_allocation.h`): 489,600 founder, 54,400 marketing,
96,000 provably burned. Restore founder/marketing wallets from height 0. Ring size 16 (decided). FCMP++ later.

## Build and test
```
mkdir -p build/release && cd build/release
cmake -DARCH=x86-64 -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DUSE_DEVICE_TREZOR=OFF ../..
make -j$(nproc) daemon simplewallet wallet_rpc_server
```
Always `-DARCH=x86-64` (or armv8-a) for shared builds. Tests: unit tests (7 known failures: 6 DNS + portability_wallet;
`select_outputs.gamma` flaky ~1%), `contrib/camo/regtest-demo.sh`, `tools/attack_block1.py`, `allocation-spend-test.sh`,
`stagenet-rehearsal.sh`, `tools/test_camo_health.sh`, `tools/test_rig_agent.py` (RIG_PYTHON=python3.8 too).
Never pass `--allow-mismatched-daemon-version` in tests. Details: PROJECT-LOG.md "Test".

## Repos and services (details in PROJECT-LOG.md)
- `camo` (public, this repo), website `camo-website` → camocoin.org (edit `website/` here, copy there).
- Ghillie desktop `ghillie` (public, monero-gui fork, v0.9.0). Ghillie mobile `ghillie-mobile` (public, Flutter; real
  engine on iPhone; run on his iPhone with `cd ~/ghillie-mobile && git pull && ~/flutter/bin/flutter run --release -d iPhone`).
- Private: `camo-explorer`, `camo-pool`, `camo-swap` (GPL-3.0 eigenwallet fork; BTC↔CAMO swaps work on regtest).
- Stagenet seeds: Google 34.171.218.2, AWS 3.134.132.214 (phone RPC 39749, ntfy alarm). Both go mainnet Dec 14.
- Release key fingerprint `5F1A 8350 C748 BC43 AD19 2472 AF13 7B28 E11A 0857` (backups on 2 encrypted USB sticks).

## Open items (Nov 18)
- Swaps: 42/42 docker tests + first stagenet swap PASSED Nov 18 (camo-taker, iMac build); before a real maker: CAMO price
  source, outside review, lawyer.
- Ghillie mobile: words screen now closes when leaving the app (PR #2), install with the next `flutter run`.
- BitcoinTalk [ANN] ~Dec 1; marketing posts await Anthony's approval (campaign doc in PROJECT-LOG.md).
- Signed release builds (gitian second builder + release key); explorer/pool need a free server.
