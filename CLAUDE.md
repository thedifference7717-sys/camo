# CAMO — project guide for Claude Code

CAMO is a privacy cryptocurrency: a rebranded fork of **Monero v0.18** (C++), owned by Anthony
(GitHub: thedifference7717-sys). Overview and launch checklist: `CAMO.md`. White paper: `docs/CAMO-White-Paper.pdf`.

## Ground rules
- **Never change cryptography.** CAMO's safety comes from reusing Monero's audited code unchanged.
  Changes are parameters only (names, ports, prefixes, genesis, schedule, seeds). If a task seems to need a
  crypto or consensus change, stop and explain the risk first.
- Keep Monero/CryptoNote copyright headers and `LICENSE` (BSD-3) intact.
- Merge upstream Monero security fixes from the `release-v0.18` branch promptly (`git remote add upstream https://github.com/monero-project/monero.git`).
  Check with `bash contrib/camo/tools/check_upstream.sh` (monthly and before releases). Nov 4: CAMO = v0.18.5.4 (tip of
  release-v0.18, nothing to merge). From Monero master, 22 small fixes were cherry-picked with `-x` (original authors
  kept; never `--reset-author` on cherry-picks): RPC/HTTP hardening, db, locking, p2p, wallet. Deliberately NOT taken
  (wait for Monero's 0.18 release): `742bc14c5` and `fccaccbc8` (touch src/crypto, ringct), `a3ba0122c` (multisig kex),
  `dfc246116` (block templates, next to CAMO's block-1 code), `c1f7f0bdb` (crypto/aesb.c). Master-only fixes that need
  hand ports were not attempted (key-offset sanity check, levin data races, block template reserved offset, etc.).

## What differs from Monero (all CAMO edits)
| File | Change |
|---|---|
| `src/cryptonote_config.h` | name `camo`, address prefixes (mainnet 69/70/71 → addresses start with `C`), ports 19740/19741/19742 (testnet 297xx, stagenet 397xx), new network IDs, new genesis txs (burned keys) and nonces 7171/7172/7173, message-signing key `CamoMessageSignature` |
| `src/hardforks/hardforks.cpp` | fresh schedule: v1 for the genesis block only, v16 (all current Monero rules) from block 1 |
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
Unit tests (`-DBUILD_TESTS=ON`, `make unit_tests test_notifier`; run from the build dir): Nov 4, 1244 pass. Expected
CAMO failures: tests with hard-coded Monero addresses/files (address, uri, multisig, Serialization.portability_*,
wallet_storage), DNS tests (no DNS in sandboxes). `cryptonote_protocol_handler.race_condition` hangs (exclude it with
`--gtest_filter=-cryptonote_protocol_handler.race_condition`; also why CI's test job never finished).
`select_outputs.gamma` was adapted to 60 s blocks: wallet decoy selection matches Monero's in time terms.
`bash contrib/camo/regtest-demo.sh` — starts a private regtest node, mines to wallet Alice, sends 12.345 CAMO
to Bob, and prints Bob's balance plus what the chain reveals (ring size 16, amounts hidden). Verified working on
2026-10-30 (Linux build).
The test scripts must NOT pass `--allow-mismatched-daemon-version`: it skips the wallet's hard-fork checks and hid
the sparse-fork-table bug below until Nov 3.
`python3 contrib/camo/tools/attack_block1.py <rpc_port> <address>` against a fresh regtest node (block-1 attack test).
`bash contrib/camo/stagenet-rehearsal.sh` — launch rehearsal (3 local stagenet nodes, real difficulty, ~80 min);
exits non-zero if the miner sees no rewards, the spend fails, or the friend doesn't receive exactly 5 CAMO.

## Status and next steps
- [x] Fork, rebrand, build, local mainnet-mode mining, private regtest transfer
- [x] Logo (`contrib/camo/branding/`), white paper, hardened seed-node installer (`contrib/camo/deploy-seed-node.sh`:
      `--binary` for the private repo, `--stagenet`; firewall, SSH key-only, fail2ban, auto-updates, sandboxed service)
- [x] Security: `SECURITY.md` (threat model, key handling, Ghillie requirements, release checklist);
      `contrib/camo/tools/attack_block1.py` adversarial test passes (Nov 3)
- [x] Pushed to GitHub `thedifference7717-sys/camo` (PRIVATE, Nov 3; make public when stagenet opens Nov 10). Branch `main`;
      Monero's repo is remote `upstream`. Seed servers can't clone a private repo: copy built binaries to them instead.
- [ ] Rent 2–3 VPS seed nodes, add their IPs to `get_ip_seed_nodes()`
- [ ] Public stagenet 2–4 weeks → signed reproducible binaries (`contrib/gitian`; Monero 0.18 has no guix) → announced fair launch
- [x] 1-minute blocks; founder genesis tool
- [x] Founder + marketing addresses received; block-1 allocation (489,600 / 54,400 / 96,000 burn) built and tested end to end
- [x] Website (Nov 3): `website/` here, published from the PUBLIC repo `thedifference7717-sys/camo-website`
      (GitHub Pages, branch `main`): https://thedifference7717-sys.github.io/camo-website/ . `index.html` is the opening
      screen (living camo field, scope, hidden word CAMO; aim + click to enter), main site is `home.html`. Static, no
      third-party requests (self-hosted fonts, strict CSP). Edit in `website/` and copy to the public repo (keep in sync).
- [~] Block explorer (Nov 3): fork of onion-monero-blockchain-explorer at upstream `29593b7` (last commit by known
      contributors; the 4 later upstream commits by "Your Name <you@example.com>" are NOT used). Builds against this
      repo's `build/release`; binary `camo-explorer`; CAMO ports/wording; night-ops theme. Tested on the stagenet
      rehearsal chain: block 1 allocation, ring 16 + hidden amounts, view-key decode finds exactly 5 CAMO, Monero
      addresses rejected. Code: PRIVATE repo `thedifference7717-sys/camo-explorer` (branch `main`, full upstream
      history kept for BSD-3 attribution; see its README). Still needs a server. Operator rule: never run it with `--enable-mixin-guess`.
- [~] Mining pool (Nov 3): jtgrassie/monero-pool at `db16e73` in PRIVATE repo `thedifference7717-sys/camo-pool`
      (see its `camo/README.md`). **CAMO fix: never pay out block 1** (camod reports its 640,000 CAMO allocation as
      the block reward; unpatched, the pool would credit it to block 1's miner). 1% fee via `pool-fee-wallet` =
      marketing wallet; the pool wallet needs a small CAMO float for payout network fees; run camod with
      `--block-notify`; XMRig needs `-a rx/0`. `camo/pool-test.sh` (regtest + XMRig) PASSES: block 1 mined through the
      pool with the allocation, miner paid 99%, fee wallet 1.00%, payouts = exactly what the pool earned.
      Still needs a server, the real wallets, and a minimum payout decision.
- [ ] v1.1 (Q1 2027): **Ghillie** wallet (name locked Nov 2) — desktop + mobile, fast sync, built-in "mine while idle"
      + **remote mining control** (decided Nov 3): Ghillie mobile starts/stops and monitors mining on the user's own
      computers. Phones never mine (Apple and Google Play ban on-device mining; RandomX is weak on phones).
- [ ] v1.2 (Q2 2027): built-in BTC↔CAMO atomic swaps; merchant checkout plugins
- Ghillie fee model (decided Nov 3): **no fee on sends, ever** (an extra output would fingerprint Ghillie txs);
  0.25% on built-in swaps, 1% official pool fee, optional tip off by default; all to the marketing wallet.
- Website design (tactical "night-ops" look, original, not Call of Duty branding): https://claude.ai/artifact/QB6piNbZWjL9suC5Kvfirw
- [ ] Adopt FCMP++ after it is audited and live on Monero
- GitHub Actions (Nov 4): private-repo free minutes appear exhausted (jobs fail in ~3 s with no logs) after the heavy
  workflow's stuck test jobs ran for hours. Making the repo public (Nov 10) gives free minutes; or set a budget.
  build.yml now runs only on PRs/main/manual with a 2 h test cap; all workflows cancel superseded runs.
- Launch tooling: `contrib/camo/STAGENET-LAUNCH.md` (Nov 10 runbook), `tools/set_seed_nodes.py` (seed IPs into code +
  website in one step), `ANNOUNCE-DRAFT.md` (BitcoinTalk draft, not posted), `website/faq.html` (not yet published).
  The wallet's `donate` command is disabled (it targeted Monero's donation address) until a CAMO address is chosen.
- Ring size (decided Nov 4): **stay at 16** (Monero's audited choice). 32/64 were considered and rejected: +50%/+170%
  tx size and fees, 2x/4x verification, modest privacy gain vs. side-channel heuristics. FCMP++ is the upgrade path.

## Handoff (Nov 3, 2026, from the claude.ai cloud session)
Work moves to Claude Code from here; that session stops editing this repo.
- Docs (claude.ai artifacts, private to Anthony): white paper https://claude.ai/artifact/DWmFzRRjgYfXJ53bTX5H7d ·
  launch roadmap https://claude.ai/artifact/Afc9iNZRfzU3dqgiZ3QsDc · logo canvas https://claude.ai/artifact/RrMKu9mj5zbZPte1fEREni ·
  website design https://claude.ai/artifact/QB6piNbZWjL9suC5Kvfirw. Keep them in sync with code decisions.
- Launch rehearsal: `bash contrib/camo/stagenet-rehearsal.sh` (3 local stagenet nodes, real difficulty, ~80 min).
  **Nov 3 run 1 found a launch blocker**: wallets refused to sync ("Unexpected hard fork version v16 at height 1")
  because `wallet2.cpp` indexed the hard-fork table by version number and CAMO's table is sparse ({v1@0, v16@1}).
  Fixed in commit "Wallet: look up hard forks by version, not table index" (wallet-side checks only; no consensus
  or crypto change). **Nov 3 run 2 (with the fix, Linux x86-64 Release build): PASS.**
  - block 1 carried the stagenet allocation (489,600 / 54,400 / 96,000) on a node that didn't mine it
  - all 3 nodes on the same chain at heights 20, 35 and 87; node 2 taken offline at 20, restarted at 35, caught up in ~1 s
  - block times: first 20 avg 22 s (difficulty ramping up from the start), last 20 avg 78 s, difficulty ~28,000 with
    2 mining threads. Not yet settled at 60 s after 87 blocks; expected, since the difficulty window is 720 blocks.
    Watch this on the public stagenet.
  - miner wallet synced and saw 1,239.63 CAMO (237.74 unlocked); 5 CAMO spend sent; friend received exactly 5.0 CAMO
  - no ERROR/EXCEPTION lines in the node logs
  Same day, with the fix: `regtest-demo.sh` passed without the mismatch flag (Bob 12.345 CAMO, ring 16, amounts
  hidden, RingCT type 6) and `attack_block1.py` passed all 4 checks. `allocation-spend-test.sh` was not re-run (it
  needs a build made with the TEST allocation keys).
- Free next steps, in order: (1) ~~website~~ done Nov 3, see Status; (2) ~~block explorer~~ built and tested Nov 3 (repo `camo-explorer`), needs hosting; (3) ~~mining pool~~ built and tested Nov 3 (repo `camo-pool`), needs hosting; (4) Windows/Mac/Linux release builds via `contrib/depends`: GitHub Actions workflow `ci/gh-actions/depends` (Run workflow, or any push) uploads `camo-<platform>-<commit>` artifacts (camod, camo-wallet-cli, camo-wallet-rpc, LICENSE, SHA256SUMS) for x86_64/aarch64 Linux, Win64, Intel/Apple-Silicon Mac. Unsigned test builds; signed releases need gitian + Anthony's GPG key. (Cloud sessions can't run depends locally: the source hosts are blocked, only GitHub is reachable.);
  (5) mining guide, FAQ, BitcoinTalk announcement; (6) Ghillie mockups incl. remote mining control.
- Needs Anthony: 3 seed servers (Oracle Always Free can host 2 small ARM ones for stagenet; plan 1 paid server before
  mainnet), a security contact email for SECURITY.md, social handles, making the repo public on Nov 10.
- Building on macOS may fail with new Homebrew Boost (see Build). A Linux environment (Claude Code on the web,
  a Linux VM or a seed server) is the reliable place to build and run the tests.
