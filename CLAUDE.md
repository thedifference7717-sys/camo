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

**Genesis allocation (disclosed, decided Nov 2):** the mainnet genesis tx creates **640,000 CAMO**:
489,600 to Anthony's founder wallet, 54,400 to a public marketing wallet, 96,000 (15%) to the provable burn
address (`contrib/camo/tools/make_burn_address.py`). Founder + marketing = 3.0% of main emission. Generate with
`python3 contrib/camo/tools/make_genesis.py <founder-addr> --amount 640000 --burn-pct 15 --extra <marketing-addr>:54400`
(needs only PUBLIC addresses — CAMO or Monero addresses from the same seeds; never ask for seed words or private
keys) and paste the `GENESIS_TX` hex into `config::GENESIS_TX`. The official mining pool's 1% fee is paid to the
marketing wallet (pool config, not consensus). The current mainnet genesis (hash `9b1db372…`) is a placeholder that
burns 17.59 CAMO and must be replaced before launch. Keep the white paper and website in sync with the allocation.

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
- [x] Founder + marketing addresses received; real genesis committed (640,000 CAMO: 489,600 / 54,400 / 96,000 burn)
- [x] Genesis exempted from the block-reward check (`Blockchain::validate_miner_transaction`, height 0 only)
- [ ] **BLOCKER (next session):** genesis coins are not usable yet. (1) wallet2 never scans block 0 (it seeds
      `m_blockchain` with the genesis hash and starts at height 1); (2) the genesis tx is version 1, so its outputs
      are indexed by exact amount and can't form a 16-member ring. Fix: make the genesis tx version 2 with RCT type
      null (outputs indexed under amount 0, like modern coinbases) and have wallet2 process block 0's miner tx.
      Verify end to end: a test wallet receives a genesis output, sees it after unlock, and spends it with ring 16.
- [ ] Explorer, pool, website
- [ ] v1.1 (Q1 2027): **Ghillie** wallet (name locked Nov 2) — desktop + mobile, fast sync, built-in "mine while idle"
- [ ] v1.2 (Q2 2027): built-in BTC↔CAMO atomic swaps; merchant checkout plugins
- [ ] Adopt FCMP++ after it is audited and live on Monero
