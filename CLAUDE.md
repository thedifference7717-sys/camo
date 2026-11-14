# CAMO — project guide for Claude Code

CAMO is a privacy cryptocurrency: a rebranded fork of **Monero v0.18** (C++), owned by Anthony
(GitHub: thedifference7717-sys). Overview and launch checklist: `CAMO.md`. White paper: `docs/CAMO-White-Paper.pdf`.

## Ground rules
- **Working with Anthony (Nov 11): ONE step at a time, for everything** (not just servers): one small action per
  message, then wait for his screenshot or "k". He doesn't want to type "done". Routine merges of our own PRs: go ahead
  (he asked for "auto"); still ask before anything that costs money, can't be undone, or posts publicly as him.
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
excluded: 1282 run, 1275 pass, 7 expected failures (~10 min): 6 DNS tests (no DNS in sandboxes) and
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
      before v1.0.0). Still to do: a second, independent builder compares hashes; signing with the release key. Version decided Nov 5: **v1.0.0** (tag `v1.0.0`; binaries say v1.0.0).
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
      `contrib/camo/deploy-services.sh --explorer [--tor] [--explorer-domain D]` (bundle from `tools/make_source_bundle.sh`). Operator rule: never run it with `--enable-mixin-guess`.
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
      (chmod -R u+w, xattr -cr). Still to do: signed builds, translations.
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
      simulator Nov 14 ("works great")** (simulator Face ID: Features > Face ID > Enrolled / Matching Face). Still to do: recovery sheet, real-device test (cable). Real iPhone not yet: he has no cable (Apple
      needs one for first pairing). Lesson: copying a command from chat overwrites the clipboard (and the simulator's);
      save addresses to a file first (`xcrun simctl pbpaste booted`). Code: PUBLIC repo `thedifference7717-sys/ghillie-mobile`
      (created Nov 13, branch `main`). Plan in its README:
      Linux dev build with real lib on regtest -> Android via contrib/depends -> iOS xcframework on macOS CI -> public
      restricted-RPC node for phones (AWS seed has the egress; Google's 1 GB/mo doesn't) -> store accounts ($99/$25) = owner's call.
- [ ] v1.2 (Q2 2027): built-in BTC↔CAMO atomic swaps; merchant checkout plugins
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
  charged", $100 credits, ends ~May 2027 or when credits run out -> plan a replacement before then). EC2 `camo-seed-2`
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
  `5F1A 8350 C748 BC43 AD19  2472 AF13 7B28 E11A 0857`, on keys.openpgp.org (verified). Secret key only on Anthony's Mac (backup file in his home folder; USB backup still to do).
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
