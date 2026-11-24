# CAMO project log (full history; moved out of CLAUDE.md on Nov 17, 2026 to save context)

CAMO is a privacy cryptocurrency: a rebranded fork of **Monero v0.18** (C++), owned by Anthony
(GitHub: thedifference7717-sys). Overview and launch checklist: `CAMO.md`. White paper: `docs/CAMO-White-Paper.pdf`.

## Ground rules
- **Working with Anthony (Nov 11): ONE step at a time, for everything** (not just servers): one small action per
  message, then wait for his screenshot or "k". He doesn't want to type "done". Routine merges of our own PRs: go ahead
  (he asked for "auto"); still ask before anything that costs money, can't be undone, or posts publicly as him.
  **Replies (Nov 16): NO AskUserQuestion choice boxes** (he dislikes them). He wants the Claude app's suggested replies in
  the message box: end each step with one short expected reply (e.g. "Reply **k** when you see X") so the app can offer it.
  **Make everything copyable:** every URL, command, name, email or text he must type goes in its own code block.
- **Never change cryptography.** CAMO's safety comes from reusing Monero's audited code unchanged.
  Changes are parameters only (names, ports, prefixes, genesis, schedule, seeds). If a task seems to need a
  crypto or consensus change, stop and explain the risk first.
- Keep Monero/CryptoNote copyright headers and `LICENSE` (BSD-3) intact.
- Merge upstream Monero security fixes from the `release-v0.18` branch promptly (`git remote add upstream https://github.com/monero-project/monero.git`).
  Check with `bash contrib/camo/tools/check_upstream.sh` (monthly and before releases; it compares against `BASE_TAG` in the
  script, so bump that when merging a newer release). Nov 4 and Nov 13: CAMO = v0.18.5.4 (tip of release-v0.18, nothing to
  merge). Nov 13: master's `b5f7330e0` (tx_pool use-after-free) checked: master-only bug, CAMO's 0.18 code already copies txid. From Monero master, 22 small fixes were cherry-picked with `-x` (original authors
  kept; never `--reset-author` on cherry-picks): RPC/HTTP hardening, db, locking, p2p, wallet. Deliberately NOT taken
  (wait for Monero's 0.18 release): `742bc14c5` and `fccaccbc8` (touch src/crypto, ringct), `a3ba0122c` (multisig kex),
  `dfc246116` (block templates, next to CAMO's block-1 code), `c1f7f0bdb` (crypto/aesb.c). Master-only fixes that need
  hand ports were not attempted (key-offset sanity check, levin data races, block template reserved offset, etc.).
  **Nov 15: 12 more master fixes taken** (`-x`, original authors kept): tx_pool double-spend flag (4d2a0da33), banned hosts
  dropped from startup peer lists (c85fb9b27), epee rejects nested arrays (d0788a876, C++14 static_assert follow-up),
  command args out of debug logs (a56d2d9bd), zero full-reward-zone guard (96b1cea20, numeric-priority follow-up), and
  source-only (their test hunks conflict with CAMO-adapted tests): 7672a71d4, 8a1cb7bc5, bb5c3c6cf, 090d6d828,
  e69fd7fde (reject unverifiable message signatures), d5a187b83, 36b87ef80. Skipped: 35b2b6ed2 (Polyseed-era rewrite; CAMO's
  0.18 print_seed already bypasses logs), 0216b7458/22bd3f073 (linenoise rewrite), features (i2p, tx-proxy, RPC queries),
  DNS/update-check fixes (both disabled in CAMO), 1b02df82e (crypto build flags), FCMP++. release-v0.18: nothing new.
  Tested: unit tests 1276 pass + the 7 known failures; regtest-demo and attack_block1.py pass; stagenet rehearsal PASS
  (Nov 15, before these picks: block 1 allocation, 3 nodes in sync at 20/35/86, last-20 avg 62 s, friend got exactly 5.0).
  **Nov 16: `allocation-spend-test.sh` PASS 6/6 on main after the picks** (throwaway test wallets; test header reverted and
  verified identical to the committed one, then rebuilt).

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
| `src/version.cpp.in` | release name "CAMO Genesis"; version **1.0.0** (Nov 5; code base Monero 0.18.5.4). Keep it when merging Monero version bumps |
| `src/wallet/wallet2.cpp`, `src/simplewallet/simplewallet.cpp` | payment URI scheme `camo:` (Nov 4); `monero:` links are rejected |
| `src/cryptonote_config.h` `DIFFICULTY_TARGET_V2` | **1-minute blocks** (60 s). Emission per minute is unchanged: the reward formula scales by block time, so blocks pay ~17.25 CAMO at start and the tail is 0.3 CAMO/block |
| `src/cryptonote_config.h` `CAMO_LAUNCH_TIMESTAMP`, `blockchain.cpp` `camo_launch_time_ok` | **Fair-launch rule (Nov 14, Anthony approved):** on MAINNET, blocks above genesis dated before 1797357600 (Dec 15 2026 18:00 UTC) are invalid (main and alt chains). With the 2 h future limit, nobody can pre-mine before launch. Testnet/stagenet/regtest unaffected |

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
Unit tests (`-DBUILD_TESTS=ON`, `make unit_tests test_notifier`; run from the build dir): Nov 4, full suite with nothing
excluded: 1282 run, 1275 pass, 7 expected failures (~10 min; re-checked Nov 14 after the fair-launch rule: same 7, plus
`rpc.is_version_string_valid`, fixed the same day: its regex wanted Monero's 4-part versions, so `camod`'s `version` command
said "not available" for 1.0.0): 6 DNS tests (no DNS in sandboxes) and
`Serialization.portability_wallet` (its fixture is a real Monero testnet wallet with Monero chain history; CAMO wallets
rightly refuse it: genesis mismatch). The address-based tests (uri, multisig, base58 address, portability tx) use the
same keys re-encoded with CAMO prefixes (`contrib/camo/tools/make_genesis.py` helpers), and the wallet_storage fixture's
cache was re-saved on CAMO's chain (keys file unchanged). `select_outputs.gamma` fails ~1% of runs (median just under
1.3 days): Monero's own test does the same; a simulation of the picker gave mean medians 1.330 d (120 s) vs 1.332 d (60 s),
1% below the bound for both, so CAMO's decoy ages match Monero's. Don't widen its bounds; just re-run.
Fixed Nov 4: `race_condition` no longer hangs (its test chain used pre-v15 coinbase outputs, which CAMO's v16-from-block-1
rules reject; test-only fix), and `http_server.response_soft_limit` / `ban.subnet` (new-Boost test bugs) via upstream
cherry-picks `665316708` and `108857032`. `select_outputs.gamma` was adapted to 60 s blocks: wallet decoy selection
matches Monero's in time terms. The wallet_storage tests' scratch wallets in `tests/data/` are git-ignored.
`bash contrib/camo/regtest-demo.sh` — starts a private regtest node, mines to wallet Alice, sends 12.345 CAMO
to Bob, and prints Bob's balance plus what the chain reveals (ring size 16, amounts hidden). Verified working on
2026-10-30 (Linux build).
The test scripts must NOT pass `--allow-mismatched-daemon-version`: it skips the wallet's hard-fork checks and hid
the sparse-fork-table bug below until Nov 3.
`python3 contrib/camo/tools/attack_block1.py <rpc_port> <address>` against a fresh regtest node (block-1 attack test).
`python3 contrib/camo/tools/camo_health.py --stagenet ssh://root@<IP> ...` — network health check (Nov 4): nodes up, peers,
right genesis + block-1 allocation, all on one chain, block times, stalls, competing chains, reorgs; exit 0/1/2;
`--watch N --alert-cmd CMD` for phone alerts. `bash contrib/camo/tools/test_camo_health.sh` (3 regtest nodes; forced split,
reorg, stall, wrong network, dead node, ssh transport) passes 12/12. Regtest nodes need `--keep-fakechain` to survive restarts.
`python3 contrib/camo/tools/make_checkpoints.py [--write] NODES...` — compiled-in checkpoints for the Day 7/weekly releases
(Nov 4): all nodes must agree, 720+ blocks deep, existing lines re-verified and append-only. camod enforces compiled-in
checkpoints on MAINNET only (as Monero; stagenet/testnet sections are wallet-only). Tested on a local mainnet-mode chain:
syncing node "CHECKPOINT PASSED" at each height; a node mining its own chain refused at block 1. Never commit test checkpoints.
`bash contrib/camo/stagenet-rehearsal.sh` — launch rehearsal (3 local stagenet nodes, real difficulty, ~80 min);
exits non-zero if the miner sees no rewards, the spend fails, or the friend doesn't receive exactly 5 CAMO.

## Status and next steps
- [x] Fork, rebrand, build, local mainnet-mode mining, private regtest transfer
- [x] Logo (`contrib/camo/branding/`), white paper, hardened seed-node installer (`contrib/camo/deploy-seed-node.sh`:
      `--binary` for the private repo, `--stagenet`; firewall, SSH key-only, fail2ban, auto-updates, sandboxed service)
- [x] Security: `SECURITY.md` (threat model, key handling, Ghillie requirements, release checklist);
      `contrib/camo/tools/attack_block1.py` adversarial test passes (Nov 3)
- [x] Pushed to GitHub `thedifference7717-sys/camo` (PUBLIC since Nov 10; secrets scan of all CAMO commits clean first). Branch `main`;
      Monero's repo is remote `upstream`. Seed servers can't clone a private repo: copy built binaries to them instead.
- [ ] Rent 2–3 VPS seed nodes, add their IPs to `get_ip_seed_nodes()`
      Server setup guide for Anthony (Nov 4): https://claude.ai/artifact/Bo8C3gMDsscMF5ETi9d3Cb (SSH key, Oracle free ARM or
      Hetzner, port 39740/19740, send IPs only). **Cloud sessions cannot SSH to servers** (outbound SSH blocked): Anthony runs
      the commands from his Mac and pastes output back. On Nov 10, after the repo is public, each server installs with
      `deploy-seed-node.sh --repo https://github.com/thedifference7717-sys/camo.git --stagenet` (builds on the server;
      picks armv8-a on ARM; opens Oracle's own iptables REJECT rule for the P2P port; Oracle logs in as `ubuntu` + sudo).
      **Anthony asked (Nov 4) to be walked through server setup ONE STEP AT A TIME** when he says he's ready: give one step
      (what to do, the exact command, what he should see), wait for "done" + output, check it, then the next step.
- [ ] Public stagenet 2–4 weeks → signed reproducible binaries (`contrib/gitian`; Monero 0.18 has no guix) → announced fair launch
      Gitian is set up for CAMO (Nov 4): recipes and scripts build `camo-<host>-<tag>` from this repo, sigs repo
      `thedifference7717-sys/camo-gitian.sigs` (created Nov 12: README + release public key), workflow `ci/gh-actions/gitian` on `v*` tags + manual
      (Linux/Win/Mac). Checklist: `contrib/gitian/CAMO-RELEASE.md`. **First full run PASSED Nov 10** (workflow on branch,
      commit 4d156bee4: Linux 1h35, Win 43 min, Mac 47 min) after the recipes got `git describe --always` (repo has no tags
      before v1.0.0). **Nov 18 rehearsal on main `a9371c3b42c013a36a220f79ca3c3b5d1f513d5d`** (run 44367910575: Linux 1h16,
      Win 26 min, Mac 1h03, all PASS). Second builder = Anthony's Intel iMac (Docker Desktop 19.03, 6 CPUs / 6 GB,
      `dockrun.sh` with OPT="-c -j 6 -m 5000"; started Nov 18 ~19:30 UTC). GitHub's hashes to compare:
      ```
      20e6c9ab5bc8bf5b2dc9a24052a93cf28a8b3c0346a321c0e31ce8f83e47196d  camo-aarch64-linux-gnu-a9371c3b4.tar.bz2
      08cd71dd1d8808c8c74273a65500f4ee7438005ccacb191b1ed32715cb8457d4  camo-arm-linux-gnueabihf-a9371c3b4.tar.bz2
      8cef1a582a46b374192dd949033fe9807f9248a0cee46c261d6e2c5b2b099786  camo-i686-linux-gnu-a9371c3b4.tar.bz2
      356e59dbcb46c9fb1bad9208fe41c2c61f7fd22da0a4be90c9e7fb51442c1080  camo-riscv64-linux-gnu-a9371c3b4.tar.bz2
      6f2c756ce7400cb329414fefab64f41c5a824afdaebe1b0d516ba7018406ffb5  camo-x86_64-linux-gnu-a9371c3b4.tar.bz2
      48d73ba73eaec7d5159fd9510f45d1a79fb65c4f66977f994ea647801e9dac5d  camo-i686-w64-mingw32-a9371c3b4.zip
      5eddc74ca1b296374f0093279074cdbecd24f4146db94f110262ccbdc1c46884  camo-x86_64-w64-mingw32-a9371c3b4.zip
      bfa1f17c168224de85519fcf9301e6b16db23ed97aa9891f4e7cdc06cdf63f5a  camo-aarch64-apple-darwin11-a9371c3b4.tar.bz2
      fdd5b18653f67ae40cf1a41f026ae0f5c51854cdc8ec1c37113d51bd98dd3a4b  camo-x86_64-apple-darwin11-a9371c3b4.tar.bz2
      ```
      **Nov 19: ALL 9 MATCH on the iMac (second, independent builder): CAMO builds are reproducible.** Mac lessons:
      `-j 6` with 6 GB ran out of memory (cc1plus Killed); `-j 2` works (Linux overnight, Win+Mac ~2 h with `-o wm`);
      his network couldn't fetch the mingw packages from archive.ubuntu.com, so the target image was switched to
      mirrors.edge.kernel.org (same packages, same hashes). Don't click Docker's "Install and Relaunch" mid-build.
      Also Nov 18: full unit tests on main 6ce783a: 1283 run, 1276 pass, the 7 known failures only.
      **Nov 19: practice signing PASSED** on the iMac (test files only, nothing published): `shasum -a 256 camo-* >
      SHA256SUMS`, `gpg --local-user 5F1A8350C748BC43AD192472AF137B28E11A0857 --clearsign SHA256SUMS`, `gpg --verify` =
      Good signature (EDDSA, [ultimate]), `shasum -c` 9 OK. The release chain (two builders + signing) is rehearsed. Version decided Nov 5: **v1.0.0** (tag `v1.0.0`; binaries say v1.0.0).
- [x] 1-minute blocks; founder genesis tool
- [x] Founder + marketing addresses received; block-1 allocation (489,600 / 54,400 / 96,000 burn) built and tested end to end
- [x] Website (Nov 3): `website/` here, published from the PUBLIC repo `thedifference7717-sys/camo-website`
      (GitHub Pages, branch `main`): **https://camocoin.org** (custom domain since Nov 11; old URL redirects). `index.html` is the opening
      screen (living camo field, scope, hidden word CAMO; aim + click to enter), main site is `home.html`. Static, no
      third-party requests (self-hosted fonts, strict CSP). Edit in `website/` and copy to the public repo (keep in sync).
- [~] Block explorer (Nov 3): fork of onion-monero-blockchain-explorer at upstream `29593b7` (last commit by known
      contributors; the 4 later upstream commits by "Your Name <you@example.com>" are NOT used). Builds against this
      repo's `build/release`; binary `camo-explorer`; CAMO ports/wording; night-ops theme. Tested on the stagenet
      rehearsal chain: block 1 allocation, ring 16 + hidden amounts, view-key decode finds exactly 5 CAMO, Monero
      addresses rejected. Code: PRIVATE repo `thedifference7717-sys/camo-explorer` (branch `main`, full upstream
      history kept for BSD-3 attribution; see its README). Still needs a server: deploy with
      `contrib/camo/deploy-services.sh --explorer [--tor] [--explorer-domain D]` (bundle from `tools/make_source_bundle.sh`). **Nov 20 plan (Anthony: k): host it on the AWS seed** (only free
      server with real egress; the mainnet chain starts small). Built HERE (same Ubuntu 24.04) with
      `tools/make_explorer_prebuilt.sh` (needs libasio-dev, libminiupnpc-dev) and installed with
      `deploy-services.sh --explorer --explorer-prebuilt <tar.gz> --explorer-domain explorer.camocoin.org` (no compiling,
      no swap on the server; Caddy HTTPS, no access logs). Tested locally: page, JSON API, address search. Stagenet first;
      rebuild against v1.0.0 and switch to mainnet with the seed on Dec 14. Pool stays off this 1 GB server. Operator rule: never run it with `--enable-mixin-guess`.
- [~] Mining pool (Nov 3): jtgrassie/monero-pool at `db16e73` in PRIVATE repo `thedifference7717-sys/camo-pool`
      (see its `camo/README.md`). **CAMO fix: never pay out block 1** (camod reports its 640,000 CAMO allocation as
      the block reward; unpatched, the pool would credit it to block 1's miner). 1% fee via `pool-fee-wallet` =
      marketing wallet; the pool wallet needs a small CAMO float for payout network fees; run camod with
      `--block-notify`; XMRig needs `-a rx/0`. `camo/pool-test.sh` (regtest + XMRig) PASSES: block 1 mined through the
      pool with the allocation, miner paid 99%, fee wallet 1.00%, payouts = exactly what the pool earned.
      Still needs a server and the real wallets. Minimum payout: **0.25 CAMO** (decided Nov 5). Deploy with `deploy-services.sh --pool
      --pool-fee-wallet <addr> --pool-min-payout <x>` (STAGENET-LAUNCH.md step 3b). Stagenet fee wallet = the marketing
      wallet's stagenet address `QRF1BeCD...` (same keys). Note: stagenet addresses are 97 chars (prefix 140 is a 2-byte
      varint); mainnet addresses are 95. The pool silently ignores an invalid fee wallet (fee then stays in the pool wallet).
- [ ] v1.1 (Q1 2027): **Ghillie** wallet (name locked Nov 2) — desktop + mobile, fast sync, built-in "mine while idle"
      + **remote mining control** (decided Nov 3): Ghillie mobile starts/stops and monitors mining on the user's own
      computers. Phones never mine (Apple and Google Play ban on-device mining; RandomX is weak on phones).
      **Mockups (Nov 4):** https://claude.ai/artifact/RfFeusuAaxrHQnLayoFgVM (design canvas; opens on the phone home
      screen, tap-through prototype). Screens: mobile wallet home, send, receive, remote mining (start/stop per rig),
      pair a computer; desktop wallet + "mine while idle". Look decided by Anthony: **retro but very readable**. VT323
      pixel font (smoothing off) for headings, labels, big numbers, addresses and pixel buttons; Inter for body text;
      **notched 4 px corners** on cards/buttons/inputs (no drop shadows); dark pixel-camo texture on key cards; colors
      from the website. **The Ghillie logo stays clean and smooth** (`website/assets/ghillie-icon-512.png`, never
      pixelated). Rejected Nov 4: pixel icons + pixel body text (less readable), Pixelify/Silkscreen/Press Start 2P.
      UX decisions in the mockups: "Ghillie fee: 0 · never" shown on send; fresh address per payer; `camo:` payment
      links; pairing by QR or pairing words, end to end encrypted, phone can start/stop/cap CPU/watch but never spend,
      see keys or change payout; mine-while-idle defaults: 5 min idle, 75% CPU cap, never on battery; no fiat prices.
- [~] **Ghillie desktop v0.9 for launch (decided Nov 11)**: PUBLIC repo `thedifference7717-sys/ghillie` = fork of Monero's
      desktop wallet monero-gui `v0.18.5.4` (full history kept), rebranded/restyled; wallet logic untouched (libwallet
      from this repo). Plan + status: `GHILLIE.md` in that repo. Nov 11: CAMO text/ports/URIs, no price lookups, no
      update checks, no P2Pool (not compiled yet). Nov 12: plumbing done (submodule -> camo, starts camod, CI builds incl.
      Intel Mac); **first test PASSED on Anthony's Intel Mac** (friend-stagenet, 5.0 CAMO). Network-from-address bug fixed
      (Q = stagenet, K/L = testnet). **Nov 12 later: v0.9.0 feature-complete** (see GHILLIE.md): name Ghillie
      (Ghillie.app / ghillie / ghillie.exe), Ghillie icons, mockup look (website palette, amber, Inter/JetBrains Mono,
      VT323 headings + balance, pixel-camo card), "Ghillie fee: 0 · never", Monero text -> CAMO, Donate -> marketing
      wallet, Windows installer (Ghillie.iss: Ghillie + camod, camo:/camoseed:), Ghillie recovery-sheet PDF. Hidden: Simple
      mode (needs public CAMO wallet RPC nodes; our seed has none) and hardware wallets. Mac CI pins OpenSSL 3 (Monero
      0.18 net_ssl.cpp fails with Homebrew's OpenSSL 4). Tested on Linux/regtest: 15/15 QML tests; sent 5 CAMO from
      Ghillie, received exactly 5.0. **Caution (same as Monero GUI):** a wallet made by camo-wallet-cli and never synced
      is treated as new when first opened in Ghillie and skips existing blocks; fix: Settings > Info > restore height 0.
      Applies to the founder/marketing wallets. **Nov 12: CI all green** (Intel + Apple-silicon Mac bundles, Windows,
      Linux, QML tests); **v0.9.0 tested on Anthony's Intel Mac**: friend-stagenet opened without picking the network
      (address-prefix fix confirmed), 5.0 CAMO on the pixel-camo card, "Ghillie fee: 0 · never" shown, synced at 2085.
      Mac test builds: CI artifact `macos-bundle-intel` -> `~/Downloads/Ghillie.tar` -> unpack to `~/ghillie-new`
      (chmod -R u+w, xattr -cr). **Nov 16: rebuilt on camo main 03be81d92 (12 upstream fixes), CI all green (run 43804499227);
      tested on Anthony's Intel Mac**: friend-stagenet opened (empty password), 5.0 CAMO, synced at 7163, "Connected + Mining"
      via his running camod. Still to do: signed builds, translations.
- [~] **Ghillie mobile groundwork (Nov 13-14)**: Flutter app (iOS/iPadOS/Android from one codebase), approved mockup
      screens on DEMO data (home, send w/ review + "Ghillie fee: 0 · never", receive w/ QR + camo: links + fresh subaddress
      per payer, rigs preview, settings), opening screen = the camocoin.org scope (hidden CAMO, aim + tap, Skip), CamoAmount
      (BigInt, 12 decimals), address hints (C/Q/K-L, Monero refused), 11 tests, CI (tests, Android demo APK, unsigned iOS).
      C bridge `native/camo_wallet_ffi.{h,cpp}` over wallet2_api.h (glue only; mixin 0 = library default ring 16;
      remote nodes untrusted). **Nov 14: bridge PASSES end to end** against the real library on regtest
      (`native/test/run-regtest-smoke.sh <camo src> <build dir>`): 5 CAMO to a new labelled subaddress, fee 0.00123462
      ("Normal" = library's automatic priority), txid returned, receiver exactly 5.0. Lesson: a wallet opened while the
      chain is <=1 block tall counts as new on every open (library rule; irrelevant on real chains). **Nov 14 later: the app's Dart wallet (`lib/wallet/ffi_wallet.dart`) runs on the real library too**
      (`native/test/run-regtest-dart.sh`: 5 CAMO sent, receiver exactly 5); demo data stays the default unless `CAMO_WALLET_LIB` etc. are set.
      Same day: setup screens (create: password 8+, 25 words shown once, 3 checked; restore with height; unlock; node
      field on phones), tested on the real library (wrong password refused, restore gives the same address). Phones use
      the real wallet when the engine is bundled (stagenet for now), else demo. CI builds the engine for Android
      (`android-lib.yml`, contrib/depends NDK r17b) and iOS (`ios-lib.yml`, `native/ios/build-ios-lib.sh`, pinned
      checksummed sources, Boost 1.84). **Phone node:** `deploy-seed-node.sh --public-rpc` (Nov 14) adds a restricted
      view-only RPC on 19749 / stagenet 39749 (4 conns per IP, 64 total; full RPC stays local); tested on regtest with
      the app syncing and sending through it. **Nov 14 (Anthony approved): ENABLED on seed 2** (AWS security group rule
      tcp 39749 0.0.0.0/0 "CAMO stagenet phone wallets"; flags appended to /etc/default/camod; ufw allow 39749). Verified
      from his Mac: `curl http://3.134.132.214:39749/get_info` -> stagenet, restricted true; survives reboot (seed rebooted
      for pending updates). The app suggests `3.134.132.214:39749` as the stagenet node. Cloud sessions can't reach it
      (non-443 ports blocked); test from his Mac.
      **Nov 14 night: both phone engines BUILD.** Android `libcamo_wallet.so` (arm64, 17.7 MB, 33 functions); the CI APK
      `ghillie-android-stagenet` bundles it. iOS `libcamo_wallet.a` (arm64, iOS 15+, 81 MB static) on macos-15 from pinned
      checksummed sources; iPhone link check passes. iOS needs a build-only patch applied to the CI's copy of camo
      (`native/ios/camo-ios-miner.patch`: miner.cpp's macOS battery API) and `ios_shims.c` (`__clear_cache` for
      RandomX's JIT, unused by wallets); camo itself unchanged. Settings > Node switches nodes on a live wallet; sends run
      on a background isolate and broadcast exactly the reviewed tx. **Nov 14 ~11:08 local: FIRST REAL iOS RUN PASSED** on
      Anthony's Intel iMac in the iOS simulator (iPhone 17, iOS 26.5; Xcode 26.5 runs on his Intel Mac despite the App
      Store's "not compatible" banner; Flutter 3.50.0 in ~/flutter, Swift Package Manager on instead of CocoaPods; app in
      ~/ghillie-mobile; engines in ios/Engine (device) and ios/Engine/sim (x86_64 sim build, `ios-lib.yml` matrix target
      sim-x86_64) wired by the git-ignored ios/Flutter/Engine.xcconfig with [sdk=iphoneos*]/[sdk=iphonesimulator*] lines):
      created a wallet (25 words from the real library, 3 checked), synced via 3.134.132.214:39749 to block 4,200, miner
      sent 5 CAMO (fee 0.00124), Ghillie showed +5.00, 1 of 10 confirmations. ~11:25: after unlocking, **Ghillie SENT 1 CAMO back** to
      the miner (review screen: real fee 0.00086355, Ghillie fee 0; balance 3.99 with change unlocking): both directions work.
      Later Nov 14 (CI green on Android + iOS): seed screens protected (Android FLAG_SECURE via MainActivity channel,
      words covered whenever the app leaves the foreground) and QR scanning on Send (mobile_scanner, on-device; camera
      text in Info.plist). **Face ID / fingerprint unlock (Anthony chose it, Nov 14; CI green):** opt-in checkbox when typing
      the password; flutter_secure_storage 11 (Swift Package Manager OK; biometric_storage was rejected: no SPM, would force
      CocoaPods): iOS Keychain biometryCurrentSet + passcode-only + this device; Android Keystore, strong biometrics per read
      (MainActivity is a FlutterFragmentActivity); refusal falls back to the password; a stale saved password is deleted;
      Settings turns it off. Linux dev builds need libsecret-1-dev. Settings also has LOCK WALLET and "turn on" for Face ID (the
      password typed once proves it). Bug found by Anthony and fixed: after Lock, Face ID auto-prompted and reopened the
      wallet instantly; now auto-prompt only at app start, after Lock it waits for a tap. **Verified by Anthony in the
      simulator Nov 14 ("works great")** (simulator Face ID: Features > Face ID > Enrolled / Matching Face). **Nov 16: REAL iPhone PASSED** (iPhone 15 Pro, iOS 27.2, Xcode 26.5 on the Intel iMac, free Personal Team signing, Developer Mode, `flutter run --release -d iPhone`): wallet created with the real engine, synced via 3.134.132.214:39749 to 7,207, **Face ID unlock works on hardware**. Release builds needed `ios/Flutter/Release.xcconfig`: DEAD_CODE_STRIPPING = NO + STRIP_STYLE = non-global (else the static engine is stripped and the app silently falls back to DEMO; check with `nm -gU build/ios/iphoneos/Runner.app/Runner | grep -c _camo_` = 33). App icons = Ghillie logo (were Flutter default). Free-team installs expire after 7 days (re-run flutter run). Nov 17 on the real iPhone: received 5 CAMO from the miner (fee 0.00124773), sent 1 CAMO back: both directions work. Added Nov 17: iOS screenshot warning + cover while recording on the words screen; **auto-lock after 7 min 17 s** idle or in background (Anthony; was 13 min); **Subscriptions** (Anthony): saved monthly payments (name, address, amount, monthly day) in the Keychain per wallet, shown as due on their day, paid with one tap through the normal Send review (first date picked on a calendar, any day 1-31, 29-31 = last day of shorter months; **verified on the real iPhone Nov 17**: test 1 CAMO paid, then "Next: Dec 17 · paid this month"): NEVER automatic (would need keys unlocked in the background). Declined (advised Nov 17): storing Kalshi/Hyperliquid API keys in the wallet. USDC swap: v1.2 idea via non-custodial atomic swaps only, after a lawyer (custodial swaps = money transmission). Nov 17 later: **payment reminders** (flutter_local_notifications 23: one notification at 9:00 on the due day, no name/amount on the lock screen; iOS permission asked when the first subscription is saved; Android compileSdk 37 + desugaring; CI green) and **Saved addresses** (Anthony; home tile + Settings + "Saved" on Send; types Exchange/Person/Shop/Other; exchanges typed in, NONE pre-loaded until one lists CAMO; deposit-address-may-change warning; verified on the real iPhone). **Payment requests** (Nov 17, verified on the real iPhone): Receive has amount + note (tx_description) + "Share request" (share_plus); the shared text is "Please pay 2 CAMO · gift" + `https://camocoin.org/pay#<camo: link>` (iMessage shows a clean "CAMO payment request" card; `website/pay.html` + `pay.js` show amount/note/address + OPEN IN GHILLIE; the request stays after `#`, never sent to the server, no network requests); Ghillie registers the `camo:` URL scheme (iOS CFBundleURLTypes + FlutterDeepLinkingEnabled false, Android VIEW intent filter, app_links) and opens Send filled in with "For: <note>" after unlock; monero: links ignored. **Recovery sheet + print (Nov 17, verified on the real iPhone)**: camocoin.org/recovery has blank sheets
      (letter/A4 PDFs); Ghillie has PRINT RECOVERY SHEET on the words screen and on Settings > Recovery words (password
      typed again, or Face ID; only a salted hash of the password is kept in memory while unlocked): one page with the
      words, date made and restore height filled in, built in memory and sent to the system print dialog (pdf/printing
      packages), warning first (own printer, never Save as PDF). New wallets record date + chain height - 720 at
      creation; older wallets fill both in once. Declined (advised): an editable/pasteable seed file (files leak; trains
      the phishing habit). **Rigs (Nov 17)**: `contrib/camo/tools/ghillie-rig-agent.py` (setup/pair/run; TLS with a
      self-signed cert pinned by SHA-256 in the pairing code, 256-bit secret, 5-strike lockout; phone can only
      status/start (threads capped)/stop; payout fixed on the computer; camod RPC on 127.0.0.1 only;
      `test_rig_agent.py` 15/15 on regtest) + Ghillie Rigs screen (pair by paste/QR, pinned HttpClient with no trusted
      roots; real-helper test via CAMO_RIG_AGENT); guide: camocoin.org/mine#rigs. **Verified Nov 17 on Anthony's iMac + iPhone**: paired (Universal Clipboard
      paste; macOS asked Python for local-network access: Allow), card showed MINING 1139 H/s 2 of 9 threads, thread
      change from the phone works. Bugs found and fixed that day: his Mac's python3 is **3.7.7** (no removeprefix /
      dict |; the helper is now 3.7+ and test_rig_agent.py takes RIG_PYTHON), Dart sent chunked bodies the helper
      didn't read (started 9 threads instead of 3; helper now reads chunked and refuses a missing count; phone sends
      Content-Length). **iOS screenshots of the 25-words screens come out black** (window drawn in a secure text
      field layer; verified on the iPhone; other screens screenshot normally). **Nov 18: restore height from the engine** (ghillie-mobile PR #1):
      bridge `camo_wallet_restore_height()` (wallet2_api getRefreshFromBlockHeight = the library's scan start; for app-made
      wallets the library resets it to the node's exact height on first connect, so it is never too high). Wallets made
      before Ghillie recorded it fill the sheet in automatically; the date is estimated on the phone from the block count
      (60 s) and printed "about <date>" (asking the node for that block would tell it roughly when the wallet was made).
      flutter test 46 pass; native regtest smoke passes with the new check. New engine on the iPhone Nov 18 (nm check = 1).
      **Nov 18 (Anthony found it): leaving the app closes Settings > Recovery words** (ghillie-mobile PR #2; Sensitive
      onLeave on hidden/paused, not inactive; covered until gone; 47 tests). **Verified on his iPhone Nov 18** (words gone after
      leaving and reopening).
      **Nov 22: iPhone not found over Wi-Fi** ("unable to connect after 30 seconds"; Xcode Devices: "Disconnected",
      "Browsing on the local area network"). Cause: the iPhone had auto-updated to iOS 27.2.1 and the Mac had restarted.
      Fix: cable once, Xcode > Window > Devices and Simulators until "Copying shared cache symbols" finishes; then
      Wi-Fi works again (`flutter run` shows "(wireless)"). Restarting the iPhone or checking Local Network didn't help.
      Mac cleanup same day (8 GB, it ran out of memory): Docker removed from login items (start by hand for gitian
      builds), MacKeeper uninstalled, XQuartz background item off, desktop Stacks. Grass (bandwidth sharing) kept by choice.
      The new-wallet setup words screen still only covers itself.
      Nov 17: Anthony's stagenet test wallet's words were shown in a chat screenshot: test only, never for real coins.
      Lesson: copying a command from chat overwrites the clipboard (and the simulator's);
      save addresses to a file first (`xcrun simctl pbpaste booted`). Code: PUBLIC repo `thedifference7717-sys/ghillie-mobile`
      (created Nov 13, branch `main`). Plan in its README:
      Linux dev build with real lib on regtest -> Android via contrib/depends -> iOS xcframework on macOS CI -> public
      restricted-RPC node for phones (AWS seed has the egress; Google's 1 GB/mo doesn't) -> store accounts ($99/$25) = owner's call.
- [ ] v1.2 (Q2 2027): built-in BTC↔CAMO atomic swaps; merchant checkout plugins. **Swap plan: `contrib/camo/SWAPS-PLAN.md`**
      (Nov 17): fork eigenwallet/core (GPL-3.0, keep it a separate process from Ghillie); change prefixes, wallet lib -> camo,
      and **monero-oxide's decoy BLOCK_TIME 120 s -> 60 s (privacy-critical)**; regtest -> stagenet -> outside review;
      lawyer before Anthony runs a maker. USDC later via AthanorLabs/atomic-swap (LGPL-3.0).
      **Nov 17: prototype BUILT and the first BTC<->CAMO swap PASSED** (`happy_path`, regtest, 191 s) in PRIVATE repo
      `thedifference7717-sys/camo-swap` (branch `main`; setup + status in its `CAMO.md`). Build here with
      `CAMO_SWAP_SYSTEM_DEPS=1` (system libs; depends hosts are blocked) and `CARGO_PROFILE_DEV_DEBUG=0` (debug target was
      18 GB and filled the disk). monero-oxide fix: address prefix written as a varint (CAMO stagenet 140+ needs 2 bytes).
      Docker works in cloud sessions after starting `dockerd`; bitcoin/bitcoin:28.1 + vulpemventures/electrs pulled
      (Docker Hub rate-limits: retry or use mirror.gcr.io); CAMO image `camo-local/camo:dev` = camod + camo-wallet-rpc
      from build/release with ldd libs, FROM scratch, EXPOSE 18080-18083 18089. Nov 17: the 7 tests that failed on Monero test addresses all PASS after the CAMO-address fix; the other 32 docker tests (refund, punish, restarts, concurrent) were started in the cloud session. **Nov 18: all 42 of 42 docker tests PASS** (last one, happy_path_hermes_disabled, 187 s).
      **Nov 18: FIRST STAGENET SWAP PASSED** on Anthony's Intel iMac (camo-swap CAMO.md has details): `camo-taker`
      (new headless buyer, PR #1, stagenet/regtest only; docker test camo_headless_taker PASS) bought 0.1206 CAMO for
      0.001 testnet3 BTC (coinfaucet.eu) from an `asb` on his local stagenet camod, ~22 min. iMac build 79 min (Homebrew
      cmake/autotools after fresh CLT for macOS 26, rustup 1.92, monero-depends submodule, no fat LTO); fixed the
      build script re-applying patches (PR #3). GitHub Actions minutes for private repos used up Nov 18 (2 s, no log);
      camo-swap's upstream workflows are now manual-only. Gaps before a real maker: a CAMO price source (asb uses
      XMR/BTC feeds), per-swap Tor wormhole services always on (review/lawyer). Next: outside review, lawyer.
- Ghillie fee model (decided Nov 3): **no fee on sends, ever** (an extra output would fingerprint Ghillie txs);
  0.25% on built-in swaps, 1% official pool fee, optional tip off by default; all to the marketing wallet.
- Website design (tactical "night-ops" look, original, not Call of Duty branding): https://claude.ai/artifact/QB6piNbZWjL9suC5Kvfirw
- [ ] Adopt FCMP++ after it is audited and live on Monero
- GitHub Actions (Nov 4): private-repo free minutes appear exhausted (jobs fail in ~3 s with no logs) after the heavy
  workflow's stuck test jobs ran for hours. Making the repo public (Nov 10) gives free minutes; or set a budget.
  build.yml now runs only on PRs/main/manual with a 2 h test cap; all workflows cancel superseded runs.
- Nov 10: history of `camo` and `camo-website` rewritten (git filter-repo, files unchanged) so commits show
  `Anthony <camocoin@proton.me>` instead of the personal Gmail; old commit IDs in older notes are gone. GitHub: keep email
  private + block pushes exposing it, 2FA (authenticator + passkey). Never commit with a personal email.
- Oracle (Nov 10): free ARM (A1) servers out of capacity in Chicago for 24 h+; `tools/camo-oracle-server.sh` keeps retrying
  (run on Anthony's Mac). The free AMD micro is NOT obtainable on his account: CLI gave LimitExceeded (AD-1/2) and
  NotAuthorizedOrNotFound (AD-3, any image) and the console lists no E2.1.Micro in any AD. Anthony will not pay
  (no Pay As You Go upgrade). Free fallback if ARM never frees: Google Cloud always-free e2-micro.
  **Nov 11 decision: stay 100% free** (no paid servers, incl. no $5-7 Hetzner box); keep the Oracle ARM script running.
  Consequence: explorer + pool + 2nd/3rd seed wait for an Oracle ARM server (or a community-run seed node).
  camocoin.org HTTPS enforced Nov 11.
- Google Cloud (Nov 11): free-tier VM **camo-seed-1**, e2-micro, us-central1-f, Ubuntu 24.04 amd64, 30 GB standard disk,
  no snapshots, **static** external IP **34.171.218.2** (`camo-seed-1-ip`), firewall rule `camo-p2p` (tcp 39740,19740). Billing:
  free trial ($300/90 d), budget alert camo-1-dollar-alert ($0.50/$0.90/$1). **Billing checked Nov 12 (SKU report):
  total $0.00, trial credit untouched**: External IP on a standard VM $0.00 (28.5 h), e2-micro core/RAM fully offset by
  "free tier discount" lines, 30 GB standard PD $0.00. Re-check monthly and after the trial ends (~Feb 9, 2027). 1 GB/mo free egress: cap camod upload. 1 GB RAM: install
  the prebuilt binary (deploy-seed-node.sh --binary), don't build on it.
  **Nov 11: stagenet seed node RUNNING** (`deploy-seed-node.sh --binary ~/camod --stagenet --limit-up 16`, camod
  v1.0.0-845a54633 from the depends CI artifact, copied via scp from Anthony's Mac). Login: `ssh camo-servers@34.171.218.2`
  (key camo-servers, passphrase). Port 39740 reachable from the internet (nc test). Seed IP in `get_ip_seed_nodes()`.
  **Nov 11 ~20:05 UTC: public stagenet chain STARTED.** Anthony mines from his Intel iMac (`~/camo`, Mac depends build
  845a54633, `camod --stagenet --add-priority-node 34.171.218.2:39740 --start-mining <Q...> --mining-threads 2`, wallet
  `~/camo/miner-stagenet`, empty password, stagenet only). Height 7 after 3 min, ~944 H/s, 1 outbound peer (the seed).
  Live checks Nov 11: block 1 vout = 489,600 / 54,400 / 96,000 CAMO, unlock_time 61 (`print_block 1`); blocks ~1/min by
  height 20 (difficulty ~33k-45k); miner 2,207.50 CAMO at height 131 (1,205.67 unlocked, ~16.98/block); **first public
  stagenet transaction**: 5 CAMO miner -> `~/camo/friend-stagenet`, fee 0.0012 CAMO, received exactly 5.0.
  **Nov 12 ~01:35-03:48 UTC: stagenet stalled at height 359** (only miner = Anthony's Mac). Cause: Mac memory full (8 GB,
  ~5.5 GB of Safari/Claude WebKit pages, 96 MB free, heavy swap); camod showed `mining at 0 H/s`, state "stuck" in `top`.
  Not a CAMO bug (sync_info clean; stop/start_mining and a camod restart didn't help). Fixed by a Mac restart: blocks
  resumed at once. Mining guide must say: mining needs free RAM; check `status` H/s. Until more miners join, any stall on
  his Mac stalls stagenet. **Nov 13: seed #2 RUNNING on AWS** (account `camo-seed`, project email; FREE PLAN: "does not get
  charged", $100 credits, ends ~May 2027 or when credits run out -> plan a replacement before then).
  **Nov 20: AWS console login not working**: the account's root email is NOT camocoin@proton.me ("no account"), and
  the other address Anthony found is a general Amazon/Builder login, not this account. Seed unaffected. Needed before
  Dec 14 (security group: tcp 19749, 80/443 for the explorer): recover via AWS account support (free, no sign-in).
  Never record the email here. Safari can't do AWS sign-in ("Bad request"); use Chrome. EC2 `camo-seed-2`
  (i-056784d10469d8eac), us-east-2 Ohio, t3.micro, Ubuntu 24.04, 30 GB gp3, security group `camo-seed` (22, 39740, 19740),
  **Elastic IP 3.134.132.214**. Login `ssh -i ~/.ssh/camo-seed-2.pem ubuntu@3.134.132.214`. Installed with
  `deploy-seed-node.sh --binary ~/camod --stagenet --limit-up 16` (camod v1.0.0-fe86eb95c from the depends artifact);
  synced 2138 blocks in 23 s. Both stagenet seeds in `get_ip_seed_nodes()` and website/stagenet.html.
  **Nov 14: phone alarm RUNNING on seed 2** (`contrib/camo/tools/install-alarm.sh <topic> --stagenet`: systemd
  `camo-alarm`, camo_health.py --watch 120 on the local node, ntfy.sh topic in Anthony's ntfy app (private; not
  recorded here), alerts on WARN/CRIT + recovery). Tested: notifications reach his phone (iOS notifications had to be
  allowed for ntfy). Re-run with --mainnet on mainnet seeds.
  Restart: `~/camo/camod --stagenet --add-priority-node 34.171.218.2:39740 --start-mining
  <miner Q... address> --mining-threads 2` (address in `~/camo/miner-stagenet.address.txt`). Oracle script restarted.
- Release signing key (Nov 10): `CAMO release signing <camocoin@proton.me>`, ed25519, fingerprint
  `5F1A 8350 C748 BC43 AD19  2472 AF13 7B28 E11A 0857`, on keys.openpgp.org (verified). Secret key on Anthony's Mac; **USB backup DONE Nov 17**: encrypted stick `CAMO-Keys` (APFS Encrypted, FileVault: Yes, password on paper kept apart) holds `camo/`: release-signing-SECRET.asc (passphrase-locked) + public.asc, revocation cert (.rev), AWS `camo-seed-2.pem`, Google seed key `id_ed25519`(+.pub; the Google login user is camo-servers). **Second copy DONE same day**: `CAMO-Keys-2` (same files, same password), to be kept in another place. Both sticks also hold `github-recovery-codes.txt` (removed from his Downloads) and `repos/` with source snapshots of the private camo-explorer and camo-pool repos (Nov 17).
- Project email (Nov 9): **camocoin@proton.me** (Proton Mail, 2FA on; security contact on the site and in SECURITY.md).
- X account (Nov 10): **@CAMO_Coin** (https://x.com/CAMO_Coin), signed up with the project email, 2FA by authenticator app,
  launch post pinned. Profile photo = app icon crop, header 1500x500 (camo field, wordmark, mainnet date). Linked in the
  website footers and the FAQ "official accounts" list.
- Domain (Nov 11): **camocoin.org** at Porkbun (account `camocoin`, passkey login, project email; WHOIS privacy, transfer
  lock, auto-renew $11.84/yr; expires 2027-11-11). DNS: 4 A records 185.199.108-111.153 (GitHub Pages) + CNAME www ->
  thedifference7717-sys.github.io. `CNAME` file in camo-website (and website/). camocoin.com is taken by someone else.
- BitcoinTalk (Nov 11): account **CAMO_Coin** registered with the project email (email hidden). Newbie rank: activity grows
  per 14-day period with posts, so post a few genuine replies each period before the [ANN] thread (~Dec 1).
  Nov 13: first 2 posts (Altcoin Discussion: free-tier VPS advice; how XMR tracing happens in practice), no CAMO mentions
  (shilling in others' threads risks flags). New accounts: 6 min between posts; a blocked post is saved as a draft. Keep it
  to 1-3 genuine replies every few days.
- **Mainnet runbook (Nov 14): `contrib/camo/MAINNET-LAUNCH.md`** (decisions D1-D4, dated timeline to Dec 22). **D1 OPEN,
  IMPORTANT (was): nothing stopped pre-mining mainnet before Dec 15** (public code; a private chain mined for weeks would win at
  launch). **D1 DONE Nov 14 (Anthony: "fix that asap")**: mainnet-only launch-time rule, see the table above. Tested on a
  local mainnet node: before launch every mined block is refused ("is dated before the CAMO launch time"); with the clock
  faked to Dec 15 18:05 (`faketime`) the same node mined 11 blocks; stagenet mines normally today; regtest-demo and
  attack_block1.py pass; unit tests unchanged (the `race_condition` test now runs on testnet: it dated blocks at genesis
  time, mainnet refused them, and it hung). PR #47 merged. Residual: up to ~2 h head start for someone who dates blocks just after 18:00.
  **D2-D4 decided Nov 15 (Anthony: "yes to all three")**: both seeds (Google 34.171.218.2, AWS 3.134.132.214) switch to
  mainnet on Dec 14 (stagenet then only on volunteers' machines); Google seed `--limit-up 4`; AWS seed `--public-rpc` on 19749.
  **Nov 16 (Anthony: "yes, announce 16:00")**: website (home, mine, FAQ), ANNOUNCE-DRAFT and the runbook say openly that
  mining effectively opens ~16:00 UTC (blocks dated 18:00+ accepted up to 2 h early), so nobody has an insider edge.
- Launch tooling: `contrib/camo/STAGENET-LAUNCH.md` (Nov 10 runbook), `tools/set_seed_nodes.py` (seed IPs into code +
  website in one step), `ANNOUNCE-DRAFT.md` (BitcoinTalk draft, not posted), `website/faq.html` (published Nov 5).
  The wallet's `donate` command pays the public marketing wallet (`Cfbe7EfJ...aAtK4`, decided Nov 5). Wallet units are
  camo / millicamo / microcamo / nanocamo / picocamo (were Monero's names; display only).
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
  **Nov 20 run on main (binaries from 01fc355; src unchanged since): PASS.** Block 1 allocation; 3 nodes in sync at 20;
  node 2 offline 15 min, caught up at 35 in ~1 s; block times first 20 avg 27 s, last 20 avg 76 s (difficulty 40,676);
  miner saw 1,239.63 CAMO; 5 CAMO spent, friend received 5.0; all 3 nodes on one chain at 88. Same day: test_camo_health.sh
  (with the new Seal Watch rules) ALL PASS 3/3; block-1 header checked (amounts, three mainnet addresses, burn output
  proven with its public view key).
  **Nov 23: Seal Watch double-spend watch** (camo_health.py remembers the last 60 blocks' txs and key images; after a
  reorg a removed tx whose coins a different tx now spends is CRIT). Rule tests 17/17; test_double_spend.sh (real regtest
  split: one coin paid to Bob on side A, to Carol on longer side B, reconnect) PASS with CRIT naming both txs;
  test_camo_health.sh ALL PASS.
  **Nov 24: Seal Watch block-burst (selfish-mining) alarm**: blocks arriving between runs far faster than chance
  (Poisson odds below 1 in 10,000, at least 6 blocks; with --watch 120 about 10 blocks in 2 min) is WARN; off on regtest.
  Rule tests 27/27; test_camo_health.sh ALL PASS (new live 20-block burst case); test_double_spend.sh PASS.
  White paper: Seals section added (Security model), PDF re-exported to docs/ and the website.
  **Nov 4 run 3 (with the 22 upstream fixes): PASS.** Block 1 allocation on a non-mining node; 3 nodes in sync at 20/35/86;
  node 2 caught up in ~1 s; block times first 20 avg 28 s, last 20 avg 65 s; miner saw 1,239.63 CAMO; 5 CAMO arrived.
  Same day, with the fix: `regtest-demo.sh` passed without the mismatch flag (Bob 12.345 CAMO, ring 16, amounts
  hidden, RingCT type 6) and `attack_block1.py` passed all 4 checks. **Nov 4, `allocation-spend-test.sh` re-run on current
  `main` (after the upstream fixes, camo: URIs): PASS 6/6** (block 1 allocation, founder wallet sees 489,600 unlocked, 1,000
  CAMO spent with ring 16 and hidden amounts, marketing view-only 54,400, burn view key 96,000). How: fresh throwaway test
  wallets, `make_allocation.py` into the header temporarily, rebuild (~30 s), run with `CAMO_TEST_KEYS_DIR`, then
  `git checkout` the header and rebuild; the script now exits non-zero on any failed check (against the real build it
  correctly fails the wallet checks). Never commit a test allocation header.
- Free next steps, in order: (1) ~~website~~ done Nov 3, see Status; (2) ~~block explorer~~ built and tested Nov 3 (repo `camo-explorer`), needs hosting; (3) ~~mining pool~~ built and tested Nov 3 (repo `camo-pool`), needs hosting; (4) Windows/Mac/Linux release builds via `contrib/depends`: GitHub Actions workflow `ci/gh-actions/depends` (Run workflow, or any push) uploads `camo-<platform>-<commit>` artifacts (camod, camo-wallet-cli, camo-wallet-rpc, LICENSE, SHA256SUMS) for x86_64/aarch64 Linux, Win64, Intel/Apple-Silicon Mac. Unsigned test builds; signed releases need gitian + Anthony's GPG key. (Cloud sessions can't run depends locally: the source hosts are blocked, only GitHub is reachable.);
  (5) mining guide, FAQ, BitcoinTalk announcement; (6) Ghillie mockups incl. remote mining control.
- Needs Anthony: 3 seed servers (Oracle Always Free can host 2 small ARM ones for stagenet; plan 1 paid server before
  mainnet), making the repo public on Nov 10.
- Building on macOS may fail with new Homebrew Boost (see Build). A Linux environment (Claude Code on the web,
  a Linux VM or a seed server) is the reliable place to build and run the tests.
