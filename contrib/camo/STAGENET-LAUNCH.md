# Stagenet launch runbook (target: Nov 10, 2026)

Everything that can be prepared ahead is done; this is the order of operations once servers exist.
Times are rough. Commands run from the `camo` repo root unless noted.

## 0. Decide (Anthony)
- [ ] Servers: 2-3 Ubuntu 22.04/24.04 VPSes (Oracle Always Free ARM is fine for stagenet). Note each public IPv4.
- [ ] Security contact email (SECURITY.md, website stagenet page).
- [ ] Pool minimum payout (suggested 0.1-0.5 CAMO) if the pool runs on stagenet.
- [ ] Merge the open PR into `main` (release builds + upstream fixes).

## 1. Seed IPs into the code (10 min)
```bash
python3 contrib/camo/tools/set_seed_nodes.py --stagenet <IP1> <IP2> [<IP3>] --dry-run   # check
python3 contrib/camo/tools/set_seed_nodes.py --stagenet <IP1> <IP2> [<IP3>]
```
This writes `get_ip_seed_nodes()` in `src/p2p/net_node.inl` and the example in `website/stagenet.html`.
Commit, push, open/merge the PR. CI (`ci/gh-actions/depends`) builds the release packages and smoke-tests Linux.

## 2. Binaries (5 min after the push)
Download from the workflow run's Artifacts: `camo-x86_64-unknown-linux-gnu-<commit>` (Intel/AMD servers) or
`camo-aarch64-linux-gnu-<commit>` (ARM / Oracle Always Free). Check `SHA256SUMS`. The binaries are static apart
from libc, so they run on any current Linux.

## 3. Seed nodes (15 min each)
Copy `camod` and the installer to each server, then as root:
```bash
scp camod contrib/camo/deploy-seed-node.sh root@<IP>:/root/
ssh root@<IP> 'bash /root/deploy-seed-node.sh --binary /root/camod --stagenet'
```
Make sure your SSH key is in `/root/.ssh/authorized_keys` first (the script then disables password logins).
Check: `ssh root@<IP> journalctl -u camod -f` shows peers and, once someone mines, new blocks.

## 3b. Explorer and pool (on one of the seed nodes; 1-1.5 h, mostly the build)
While the repos are private, bundle the sources on a machine that has all three repos checked out:
```bash
bash contrib/camo/tools/make_source_bundle.sh --explorer ../camo-explorer --pool ../camo-pool
scp camo-bundle-*.tar.gz contrib/camo/deploy-services.sh root@<IP>:/root/
ssh root@<IP> 'bash /root/deploy-services.sh --bundle /root/camo-bundle-*.tar.gz --stagenet --explorer --tor \
  --pool --pool-fee-wallet QRF1BeCDpUdPvpDqSpe97KKWEphrXL7zadjcaYVD2hcb4ELRHabLjPi2QbxE1Hqignia4B5sW7D8kUkRUXKVBWF62QG274FjV \
  --pool-min-payout <decided amount>'
```
`QRF1BeCD...` is the public marketing wallet's stagenet address (same keys as `Cfbe7EfJ...`; derived with
`make_genesis.py`'s `parse_address` / `camo_address`). To see these stagenet funds, restore the marketing seed in a wallet started with `--stagenet`.
Add `--explorer-domain` / `--pool-domain` once DNS points at the server (Caddy gets HTTPS certificates; no access logs).
The first run stops after the build and prints one command to create the pool's hot wallet: run it on the server,
write the 25 words down offline, then re-run the same deploy command. Send a few CAMO to the pool wallet as a float
for payout network fees. `--stage DIR` builds and writes everything into DIR without touching the system (dry run).

## 4. First blocks (whoever goes first)
Stagenet has its own genesis and block 1 (stagenet allocation, same amounts as mainnet, test coins).
Mine from any machine: `./camod --stagenet` then `start_mining <stagenet address> 2` in a stagenet wallet, or
XMRig `-a rx/0 --daemon -o 127.0.0.1:39741 -u <stagenet address>`. Block 1 pays the miner nothing (allocation);
block 2 onward pays normally.

## 5. Website (10 min)
```bash
cp website/* ../camo-website/   # plus any changed assets
cd ../camo-website && git add -A && git commit -m "Stagenet open: seed nodes" && git push
```
Remaining placeholders to fill: stagenet explorer link, pool address/stats link, min payout, security email.

## 6. Make the code public
GitHub -> camo -> Settings -> General -> Danger zone -> Change visibility -> Public. The website's GitHub link and
the stagenet page's build-from-source steps start working. Keep `camo-explorer` and `camo-pool` private until
reviewed, or publish them too (both are BSD-3 forks; licenses already kept).

## 7. Announce
Post the stagenet thread (draft: `contrib/camo/ANNOUNCE-DRAFT.md`), linking the stagenet page and mining guide.

## 8. Watch (daily, 2-4 weeks)
- Block times trend toward 60 s (difficulty window is 720 blocks, about 12 hours of stagenet blocks).
- Seed nodes stay in sync (`curl -s 127.0.0.1:39741/get_info` on each: same height and top hash).
- Testers' wallets sync and send (the hard-fork-table wallet bug fixed Nov 3 would show up here).
- `bash contrib/camo/tools/check_upstream.sh` weekly; merge Monero `release-v0.18` fixes promptly.

## Before mainnet (Dec 15)
Mainnet seed IPs (`set_seed_nodes.py --mainnet ...`), signed reproducible builds by Dec 7 (`contrib/gitian/CAMO-RELEASE.md`;
run the `ci/gh-actions/gitian` workflow by hand once the repo is public, well before then),
explorer and pool hosted, checkpoints after launch (`src/checkpoints/checkpoints.cpp`).
