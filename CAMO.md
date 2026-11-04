# CAMO

CAMO is a privacy cryptocurrency forked from Monero v0.18. Every transaction hides the sender (CLSAG ring signatures, ring size 16), the receiver (stealth addresses, view tags) and the amount (RingCT with Bulletproofs+).

| | |
|---|---|
| Ticker | CAMO |
| Block time | 2 minutes |
| Proof of work | RandomX (CPU-friendly) |
| Supply | ~18.4M main emission, then 0.6 CAMO/block tail emission forever |
| Premine | None. The genesis reward is sent to a key nobody holds and is burned |
| Address prefix | `C...` |
| Ports | P2P 19740, RPC 19741, ZMQ 19742 (testnet 297xx, stagenet 397xx) |
| Binaries | `camod`, `camo-wallet-cli`, `camo-wallet-rpc` |

## Build

```
sudo apt install build-essential cmake pkg-config libssl-dev libzmq3-dev libunbound-dev \
  libsodium-dev libunwind8-dev liblzma-dev libreadline6-dev libexpat1-dev libpgm-dev \
  libhidapi-dev libusb-1.0-0-dev libprotobuf-dev protobuf-compiler libudev-dev libboost-all-dev
git clone --recurse-submodules <this repo> camo && cd camo
mkdir -p build/release && cd build/release
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF ../.. && make -j$(nproc) daemon simplewallet
```

## Launch checklist

### 1. Code and repo
- [ ] Push to a public GitHub repo, keeping the original Monero copyright headers and LICENSE (BSD-3 requires it).
- [ ] Run a public stagenet for 2–4 weeks before mainnet. Mine, send transactions and test the wallets.

### 2. Seed nodes (at least 2, ideally 3+ in different regions)
- [ ] Rent small VPSes (2 vCPU / 4 GB RAM / 80 GB disk, about $6–12/month each).
- [ ] On each one, run `bash contrib/camo/deploy-seed-node.sh https://github.com/<you>/camo.git`.
- [ ] Add their IPs to `get_ip_seed_nodes()` in `src/p2p/net_node.inl` (`full_addrs.insert("IP:19740");`), commit and tag the release.

### 3. Release binaries
- [ ] Build reproducibly with `contrib/gitian` so anyone can verify the binaries match the source.
- [ ] Publish signed Linux, macOS and Windows builds on GitHub Releases, with SHA256 hashes and a GPG signature.

### 4. Fair launch
- [ ] Announce the launch time and mining instructions at least a week ahead.
- [ ] Start the seed nodes when the launch time arrives. The first person to mine block 1 starts the chain.
- [ ] After launch, add the block hashes as checkpoints in `src/checkpoints/checkpoints.cpp`.

### 5. Ecosystem
- [ ] Block explorer (onion-monero-blockchain-explorer can be forked).
- [ ] Mining pool software (monero-pool or nodejs-pool) and a pool guide for XMRig.
- [ ] Website, docs, Discord/Telegram, and an announcement thread on BitcoinTalk.
- [ ] GUI wallet: fork monero-gui with the same rebrand.

### 6. Reality checks
- Privacy coins are delisted from many centralized exchanges (EU MiCA rules, Binance/Kraken/OKX in several regions). Plan for DEXs and atomic swaps instead.
- A fair launch with no premine and no token sale keeps CAMO out of most securities-law territory. Selling coins before launch changes that, so talk to a lawyer before doing it.
- A new RandomX chain with low hashrate is vulnerable to 51% attacks from Monero miners renting hashpower. Consider merge-mining or extra checkpoints in the early months.
