# Mainnet launch runbook (Dec 15, 2026, 18:00 UTC)

Written Nov 14. Companion to `STAGENET-LAUNCH.md`, `contrib/gitian/CAMO-RELEASE.md` and the launch security plan
(https://claude.ai/artifact/AHygfcMjwU5uDsKgqCKvr1). Times are UTC. Commands run from the `camo` repo root unless noted.

## Decisions for Anthony (before Dec 1)

### D1. Pre-mining guard: DONE Nov 14 (option 1, approved by Anthony)
`CAMO_LAUNCH_TIMESTAMP` in `src/cryptonote_config.h`, `Blockchain::camo_launch_time_ok`. Tested: before launch a
mainnet node refuses every block it mines; with the clock set to Dec 15 18:05 UTC it mines normally; stagenet unaffected.
Keep the original reasoning below for reviewers.

**Problem.** Nothing in the code stops anyone from mining *mainnet* before Dec 15. The source is public, so anyone can
build `camod` today, mine a private mainnet chain for weeks (difficulty adjusts to their hashrate), and publish it at
launch. Every node follows the chain with the most work, so that private chain becomes CAMO's history: the pre-miner
keeps every block reward since they started (about 17 CAMO a block, ~24,000 CAMO a day of pre-mining; a month is more
than the founder allocation). Block 1's allocation is safe (consensus fixes it), but "fair launch" would not be.
Monero never had this problem because it launched before its code was public.

**Fix options**
1. **Launch-time rule (recommended).** Mainnet only: a block at height 1 or more is invalid if its timestamp is before
   `1797357600` (Dec 15 2026 18:00 UTC). Nodes already refuse blocks dated more than 2 hours in the future, and
   difficulty is computed from timestamps, so a pre-miner's whole chain has to be dated inside the 2 hours before they
   publish it: at most ~120 blocks (~2,000 CAMO) of head start instead of weeks. About 10 lines in
   `Blockchain::check_block_timestamp`, one constant in `cryptonote_config.h`, no cryptography touched. Test plan: a
   local mainnet-mode chain (as for the checkpoint tests) must refuse a block dated before the launch time and accept one
   after it; plus the existing rehearsal, regtest demo, allocation and block-1 attack tests. Residual risk: someone who
   pre-mines with timestamps just after 18:00 and publishes at ~18:00 gets those ~2 hours; the first few hundred blocks
   may be slow while difficulty settles. Day 7 checkpoints (below) then freeze the start of the chain.
2. **Launch-day genesis.** Put an unpredictable value (e.g. the Bitcoin block hash at Dec 15 15:00) into the genesis
   transaction and build the release the same day. Stronger, but it moves the signed reproducible build (and Ghillie's
   bundled `camod`) into launch-day hours, which is risky for a one-person team.
3. Do nothing and watch with `camo_health.py`. Not recommended: detection does not undo a pre-mined chain.

### D2. Which servers become mainnet seeds: DECIDED Nov 15 (Anthony: yes)
Plan (free): switch both current stagenet seeds to mainnet on **Dec 14**: Google `34.171.218.2` and AWS
`3.134.132.214`. A 1 GB server cannot run two nodes, so public stagenet then continues only on volunteers' machines (and
Anthony's iMac if he wants). If the Oracle ARM script ever wins a server, it becomes seed 3 (and can host the explorer
and pool).

### D3. Google upload cost: DECIDED Nov 15 (`--limit-up 4` on Google; AWS carries most traffic)
Google's free tier includes 1 GB/month of upload; more costs about $0.12/GB (budget alert at $0.50 is set). A mainnet
seed with more peers uploads more than the stagenet one. Options: install the Google seed with `--limit-up 4`
(worst case ~10 GB/month, ~$1) and check billing weekly in December, or keep the Google seed on a lower cap and let the
AWS seed (free plan, no charges) carry most traffic.

### D4. Phone wallet node on mainnet: DECIDED Nov 15 (yes, AWS seed, port 19749)
Same as stagenet: `--public-rpc` on the AWS seed (port **19749**), plus an AWS security-group rule for tcp 19749.

## Timeline

### Now to Nov 30: stagenet
- [x] D1 implemented and tested (Nov 14). - [x] D2-D4 decided (Nov 15, as recommended).
- [ ] Keep stagenet mining; test Ghillie desktop + mobile against it; `bash contrib/camo/tools/check_upstream.sh` weekly.
- [ ] BitcoinTalk: 1-3 genuine replies every few days (rank).
- [x] USB backup 1 (Nov 17, encrypted stick): release signing key + revocation cert, `~/.ssh/camo-seed-2.pem`, Google SSH key. - [x] Second copy `CAMO-Keys-2` (Nov 17), kept in another place.

### ~Dec 1: announce
- [ ] Post the [ANN] thread (`contrib/camo/ANNOUNCE-DRAFT.md`; owner posts). Link the stagenet page, mining guide, FAQ.

### By Dec 5: code freeze
- [ ] Mainnet seed IPs into the code and website (parameters only):
  `python3 contrib/camo/tools/set_seed_nodes.py --mainnet 34.171.218.2 3.134.132.214` (`--dry-run` first).
- [ ] Founder/marketing outputs vs Anthony's real wallets (Nov 20: amounts 489,600/54,400/96,000 at height 1, the three
  mainnet addresses and the burn output (via its public view key) verified from the header; founder/marketing need
  their view keys): on his Mac, a local `camod --regtest --offline --fixed-difficulty 1` (regtest uses the mainnet
  allocation), `generateblocks 1`, then view-only wallets (address + view key, never the seed) for founder and
  marketing restored from height 0 must show 489,600 and 54,400.
- [ ] Final check: `src/cryptonote_core/camo_allocation.h` = the real founder/marketing addresses (not a test header);
  `src/version.cpp.in` says 1.0.0; checkpoints file empty for mainnet.
- [ ] Full test pass (unit tests, `regtest-demo.sh`, `attack_block1.py`, `allocation-spend-test.sh`, rehearsal).
  Early run Nov 18-20 on main: unit tests (only the 7 known failures), regtest demo, attack_block1 4/4, health 12+rules,
  rehearsal PASS. Re-run all at the freeze commit.
- [ ] Tag `v1.0.0` (owner, signed) and run the gitian workflow (`contrib/gitian/CAMO-RELEASE.md`). A second builder
  compares hashes.

### Dec 7: signed release
- [ ] GitHub release `v1.0.0`: Linux/Windows/macOS packages, `SHA256SUMS`, `SHA256SUMS.asc` (signed with
  `5F1A 8350 C748 BC43 AD19 2472 AF13 7B28 E11A 0857`). Website download page links them.
- [ ] Ghillie desktop 0.9 builds against v1.0.0 (bundled `camod`), uploaded next to it.

### Dec 14: seeds to mainnet (about 1 hour, one step at a time)
For each seed (Google: `ssh camo-servers@34.171.218.2`; AWS: `ssh -i ~/.ssh/camo-seed-2.pem ubuntu@3.134.132.214`),
with the v1.0.0 Linux `camod` copied over:
```bash
sudo bash deploy-seed-node.sh --binary ~/camod --limit-up 16          # AWS: add --public-rpc
sudo bash deploy-seed-node.sh --binary ~/camod --limit-up 4           # Google (see D3)
```
(No `--stagenet`: this rewrites `/etc/default/camod` for mainnet; mainnet data lives beside the stagenet data.)
- [ ] AWS security group: add tcp 19749 "CAMO phone wallets" (19740 is already open on both).
- [ ] Phone alarm: `sudo bash install-alarm.sh <ntfy topic> --mainnet` on the AWS seed.
- [ ] Check: `journalctl -u camod -f` shows the node waiting at height 1 (genesis only); `curl http://3.134.132.214:19749/get_info`
  from the Mac shows `"mainnet"` / `"restricted": true`.

### Dec 15, ~16:00 UTC: mining effectively opens (announced openly, decided Nov 16)
Blocks dated 18:00+ are accepted from about 16:00 (2-hour future limit). Anthony may start then like anyone else.

### Dec 15, 18:00 UTC: launch
- [ ] Anyone may start mining (it is a fair launch: no one gets a head start). Anthony mines like everyone else:
  `./camod --start-mining <C... address> --mining-threads 2` (mainnet = no `--stagenet`).
- [ ] Block 1 carries the allocation and pays its miner nothing. Verify on a node: `print_block 1` shows outputs
  489,600 / 54,400 / 96,000 CAMO.
- [ ] Health check every hour for the first day:
  `python3 contrib/camo/tools/camo_health.py seed1=ssh://camo-servers@34.171.218.2 seed2=ssh://ubuntu@3.134.132.214`
- [ ] Post "mainnet is live" (X, BitcoinTalk) with block 1's hash.

### Dec 15-22: first week
- [ ] Watch block times move toward 60 s, both seeds on one chain, no reorgs deeper than a few blocks.
- [ ] Founder and marketing wallets: restore with height 0; leave the founder coins untouched (people will watch).
- [ ] **Dec 22 (Day 7): checkpoints release v1.0.1**:
  `python3 contrib/camo/tools/make_checkpoints.py --write seed1=ssh://... seed2=ssh://...` (only blocks 720+ deep, all
  seeds must agree), gitian build, sign, release. Then each point release for 3 months.

## The Seals: watch team (decided Nov 19, Anthony: "k")
Watch and report only. No Seal changes servers, code or public posts by itself: Anthony decides. No Seal tries to
identify users (watching the network is fine, tracking people is not).

| Seal | Watches | How often | Where / cost |
|---|---|---|---|
| **Seal Watch** | 51% risk (one miner's share of recent blocks), deep reorgs, chain splits, stalls, odd timestamps, block-1 allocation, node down | every 2 min, phone alert at once | `camo_health.py` + ntfy alarm on both seeds; free (plain code, no AI) |
| **GitHub alarms** | known-vulnerable dependencies, leaked secrets, force-push / deletion of `main` | instant | GitHub security alerts, secret scanning, branch protection; free |
| **Seal Code** | new Monero security fixes (`check_upstream.sh`), dependency advisories, outside PRs | daily Dec 10-22, weekly after | scheduled Claude session, report to Anthony; uses plan allowance |
| **Seal Scout** | fake CAMO sites, fake Ghillie apps, impersonating accounts, fake "CAMO" tokens | daily Dec 10-22, weekly after | scheduled Claude session, report to Anthony; uses plan allowance |

- [x] Nov 20: Seal Watch mainnet checks in `camo_health.py`: hashrate surge/drop (difficulty x3 within 120 blocks;
      miner share itself can't be seen on CAMO, rewards go to one-time addresses) and future-dated blocks; reorgs,
      competing chains, splits, stalls, block 1 were already checked. Tests: `test_camo_health.sh` (rules + 12 network
      checks) ALL PASS 3/3.
- [ ] Dec 14: `install-alarm.sh --mainnet` on both seeds (pulls the new `camo_health.py`).
- [x] Nov 19: ruleset "protect main" (Active; restrict deletions, block force pushes) on the default branch of `camo`,
      `ghillie-mobile` (both verified via the API), `ghillie` (screenshot) and `camo-website` (Anthony).
- [x] Nov 19: on the same four public repos: private vulnerability reporting, Dependabot alerts, malware alerts,
      secret protection, push protection (AI Scan left off: paid credits).
- [ ] Private repos (`camo-explorer`, `camo-pool`, `camo-swap`): Dependabot alerts (secret scanning is paid on private).
- [ ] ~Dec 1: Seal Code and Seal Scout scheduled tasks (report-only prompts), daily from Dec 10.

## If something goes wrong: the panic page
**The CAMO chain cannot be paused** (by design: no one controls it, and a pause switch would be a consensus change and a
target for attackers and governments). What we can freeze fast is **our side**. Do these in order, one at a time.

**1. Warn first (minutes; this is the real brake on a 51% attack).** Exchanges and users stop on a warning.
Post the same text on the website banner, X (@CAMO_Coin) and the BitcoinTalk thread:
```
CAMO notice: we are seeing <a deep reorg / a chain split / ...> at height <N>. Please pause large transfers and deposits
and wait for 60+ confirmations until we post an all-clear. Details soon. Funds in your own wallet are safe; nothing
needs to be moved.
```
Then post facts (heights, block hashes from both seeds via `camo_health.py`), never guesses.

**2. Stop our services (one command each, on the machine that runs it).**
- Swap maker: Control+C in the `asb` window (or `pkill -f "asb --"`). Takers' swaps refund by the protocol's timelocks.
- Phone node on the AWS seed: `sudo ufw deny 19749` (phones show "can't reach node"; undo: `sudo ufw allow 19749`).
- Explorer / pool (once hosted): stop their services; show a notice instead of possibly-wrong data.

**3. Lock the code.** `main` is already protected (no force-push, no deletion). Also: GitHub, `camo` > Settings >
Actions > General > **Disable actions** (re-enable after); review recent merges; rotate any token that may have leaked.

**4. Fix and pin the honest chain.** Emergency point release with compiled-in checkpoints for the honest blocks (upgraded
nodes then reject the attacker's chain; Monero's standard response):
`python3 contrib/camo/tools/make_checkpoints.py --write seed1=ssh://camo-servers@34.171.218.2 seed2=ssh://ubuntu@3.134.132.214`
(checkpoints must be agreed by both seeds), then the signed gitian release as rehearsed Nov 19 (contrib/gitian/CAMO-RELEASE.md;
~2-3 h). Announce the version and ask exchanges, pools and node runners to upgrade. Code fixes for a software bug go the
same way (fix, test, signed release); never change cryptography or consensus in a hurry without explaining the risk.

**5. All-clear** once the honest chain is well ahead and most hashrate runs the fixed release: post it in the same three
places with the new version and the checkpoint height.
