# CAMO — project guide for Claude Code

CAMO is a privacy cryptocurrency: a rebranded fork of **Monero v0.18** (C++), owned by Anthony
(GitHub: thedifference7717-sys). Overview and launch checklist: `CAMO.md`. White paper: `docs/CAMO-White-Paper.pdf`.

## Ground rules
- **Never change cryptography.** CAMO's safety comes from reusing Monero's audited code unchanged.
  Changes are parameters only (names, ports, prefixes, genesis, schedule, seeds). If a task seems to need a
  crypto or consensus change, stop and explain the risk first.
- Keep Monero/CryptoNote copyright headers and `LICENSE` (BSD-3) intact.
- Merge upstream Monero security fixes from the `release-v0.18` branch promptly (`git remote add upstream https://github.com/monero-project/monero.git`).

## What differs from Monero (all CAMO edits)
| File | Change |
|---|---|
| `src/cryptonote_config.h` | name `camo`, address prefixes (mainnet 69/70/71 → addresses start with `C`), ports 19740/19741/19742 (testnet 297xx, stagenet 397xx), new network IDs, new genesis txs (burned keys) and nonces 7171/7172/7173, message-signing key `CamoMessageSignature` |
| `src/hardforks/hardforks.cpp` | fresh schedule: v1 at height 1, v16 (all current Monero rules) at height 2 |
| `src/checkpoints/checkpoints.cpp` | Monero checkpoints removed; DNS checkpoints disabled |
| `src/p2p/net_node.inl`, `net_node.h` | Monero seed IPs, DNS seeds and DNS blocklist removed (**add CAMO seed IPs in `get_ip_seed_nodes()`**) |
| `src/common/updates.cpp` | update check disabled |
| `src/blocks/checkpoints.dat` | emptied |
| CMake `OUTPUT_NAME`s | binaries `camod`, `camo-wallet-cli`, `camo-wallet-rpc`, `camo-blockchain-*` |
| `src/daemon/*`, `src/simplewallet/simplewallet.cpp` | user-facing "Monero" → "CAMO" |
| `src/version.cpp.in` | release name "CAMO Genesis" |
| `src/cryptonote_config.h` `DIFFICULTY_TARGET_V2` | **1-minute blocks** (60 s). Emission per minute is unchanged: the reward formula scales by block time, so blocks pay ~17.25 CAMO at start and the tail is 0.3 CAMO/block |

Launch plan: mainnet **Dec 15, 2026 18:00 UTC**; public stagenet from Nov 10. Roadmap doc: https://claude.ai/artifact/Afc9iNZRfzU3dqgiZ3QsDc

**Allocation (disclosed, decided Nov 2) lives in BLOCK 1, not genesis.** Block 1's coinbase is fixed by consensus to
the transaction in `src/cryptonote_core/camo_allocation.h`: 489,600 CAMO to Anthony's founder wallet, 54,400 to the
public marketing wallet, 96,000 (15%) to the provable burn address (`contrib/camo/tools/make_burn_address.py`).
Founder + marketing = 3.0% of main emission. Whoever mines block 1 gets no reward; the block template swaps in the
published outputs and tx key, and `Blockchain::validate_miner_transaction` rejects any other block-1 coinbase.
Regenerate with `python3 contrib/camo/tools/make_allocation.py --founder <addr> --marketing <addr>` (PUBLIC addresses
only, CAMO or Monero format; never ask for seed words or private keys). Genesis (block 0) stays the original
placeholder that burns 17.59 CAMO to a nothing-up-my-sleeve key. Why block 1: wallets never scan block 0, and a v1
genesis output can't be ring-signed. Verified end to end Nov 3 (`contrib/camo/allocation-spend-test.sh` with test keys):
stranger-mined block 1 still pays the allocation; a founder-style wallet restored from height 0 sees and spends it
with ring 16; marketing view-only and burn view key see their amounts.
**Wallet restore note for Anthony:** restore founder/marketing wallets with restore height **0** or 1.
The official pool's 1% fee goes to the marketing wallet (pool config, not consensus). `make_genesis.py` is no longer
used for the allocation. Keep the white paper and website in sync.

**One editor at a time.** On Nov 2 two sessions edited this repo at once and one overwrote the other. Before changing
code: run `git status` and `git log -3`; if there are uncommitted changes you didn't make, stop and ask Anthony.
Commit small, accurate commits as you go.

## Build
Linux (Ubuntu 22.04/24.04): deps are listed in `contrib/camo/deploy-seed-node.sh`, then
```
mkdir -p build/release && cd build/release
cmake -DARCH=x86-64 -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DUSE_DEVICE_TREZOR=OFF ../..
make -j$(nproc) daemon simplewallet wallet_rpc_server
```
macOS (Homebrew): `brew install cmake pkg-config boost openssl zeromq unbound libsodium expat readline hidapi protobuf libusb`
then the same cmake/make. Newer Homebrew Boost can break Monero 0.18 builds; if so, use a Linux VM/VPS or
`brew install boost@1.85` and pass `-DBOOST_ROOT=$(brew --prefix boost@1.85)`.

Full build ≈ 45–60 min on 2 cores; use `ccache` (`-DUSE_CCACHE=ON`).
Always pass `-DARCH=x86-64` (or `armv8-a` on Apple Silicon) for anything shared: the default `native` build
crashes with "invalid opcode" on other CPUs.

## Test
`bash contrib/camo/regtest-demo.sh` — starts a private regtest node, mines to wallet Alice, sends 12.345 CAMO
to Bob, and prints Bob's balance plus what the chain reveals (ring size 16, amounts hidden). Verified working on
2026-10-30 (Linux build).

## Status and next steps
- [x] Fork, rebrand, build, local mainnet-mode mining, private regtest transfer
- [x] Logo (`contrib/camo/branding/`), white paper, seed-node installer (`contrib/camo/deploy-seed-node.sh` + `camod.service`)
- [ ] Push to GitHub (`thedifference7717-sys/camo`)
- [ ] Rent 2–3 VPS seed nodes, add their IPs to `get_ip_seed_nodes()`
- [ ] Public stagenet 2–4 weeks → signed reproducible binaries (`contrib/guix`) → announced fair launch
- [x] 1-minute blocks; founder genesis tool
- [x] Founder + marketing addresses received; block-1 allocation (489,600 / 54,400 / 96,000 burn) built and tested end to end
- [ ] Explorer, pool, website
- [ ] v1.1 (Q1 2027): **Ghillie** wallet (name locked Nov 2) — desktop + mobile, fast sync, built-in "mine while idle"
      + **remote mining control** (decided Nov 3): Ghillie mobile starts/stops and monitors mining on the user's own
      computers. Phones never mine (Apple and Google Play ban on-device mining; RandomX is weak on phones).
- [ ] v1.2 (Q2 2027): built-in BTC↔CAMO atomic swaps; merchant checkout plugins
- Ghillie fee model (decided Nov 3): **no fee on sends, ever** (an extra output would fingerprint Ghillie txs);
  0.25% on built-in swaps, 1% official pool fee, optional tip off by default; all to the marketing wallet.
- Website design (tactical "night-ops" look, original, not Call of Duty branding): https://claude.ai/artifact/QB6piNbZWjL9suC5Kvfirw
- [ ] Adopt FCMP++ after it is audited and live on Monero
