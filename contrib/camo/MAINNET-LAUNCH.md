# Mainnet launch runbook (Dec 15, 2026, 18:00 UTC)

Written Nov 14. Companion to `STAGENET-LAUNCH.md`, `contrib/gitian/CAMO-RELEASE.md` and the launch security plan
(https://claude.ai/artifact/AHygfcMjwU5uDsKgqCKvr1). Times are UTC. Commands run from the `camo` repo root unless noted.

## Decisions for Anthony (before Dec 1)

### D1. Pre-mining guard (IMPORTANT, consensus change: needs your OK)
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

### D2. Which servers become mainnet seeds
Plan (free): switch both current stagenet seeds to mainnet on **Dec 14**: Google `34.171.218.2` and AWS
`3.134.132.214`. A 1 GB server cannot run two nodes, so public stagenet then continues only on volunteers' machines (and
Anthony's iMac if he wants). If the Oracle ARM script ever wins a server, it becomes seed 3 (and can host the explorer
and pool).

### D3. Google upload cost
Google's free tier includes 1 GB/month of upload; more costs about $0.12/GB (budget alert at $0.50 is set). A mainnet
seed with more peers uploads more than the stagenet one. Options: install the Google seed with `--limit-up 4`
(worst case ~10 GB/month, ~$1) and check billing weekly in December, or keep the Google seed on a lower cap and let the
AWS seed (free plan, no charges) carry most traffic.

### D4. Phone wallet node on mainnet
Same as stagenet: `--public-rpc` on the AWS seed (port **19749**), plus an AWS security-group rule for tcp 19749.

## Timeline

### Now to Nov 30: stagenet
- [ ] Decide D1-D4. If D1 = option 1: implement, test, merge (Claude), well before the code freeze.
- [ ] Keep stagenet mining; test Ghillie desktop + mobile against it; `bash contrib/camo/tools/check_upstream.sh` weekly.
- [ ] BitcoinTalk: 1-3 genuine replies every few days (rank).
- [ ] USB backups (offline, two copies): release signing key, `~/.ssh/camo-seed-2.pem`, Google SSH key.

### ~Dec 1: announce
- [ ] Post the [ANN] thread (`contrib/camo/ANNOUNCE-DRAFT.md`; owner posts). Link the stagenet page, mining guide, FAQ.

### By Dec 5: code freeze
- [ ] Mainnet seed IPs into the code and website (parameters only):
  `python3 contrib/camo/tools/set_seed_nodes.py --mainnet 34.171.218.2 3.134.132.214` (`--dry-run` first).
- [ ] Final check: `src/cryptonote_core/camo_allocation.h` = the real founder/marketing addresses (not a test header);
  `src/version.cpp.in` says 1.0.0; checkpoints file empty for mainnet.
- [ ] Full test pass (unit tests, `regtest-demo.sh`, `attack_block1.py`, `allocation-spend-test.sh`, rehearsal).
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

## If something goes wrong
The incident table is in the launch security plan. The short version: a chain split or deep reorg means stop announcing,
compare both seeds with `camo_health.py`, and post facts (heights, hashes) before opinions.
