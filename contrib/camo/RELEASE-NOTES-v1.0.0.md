# CAMO v1.0.0 "CAMO Genesis" (DRAFT for Dec 7, 2026)

> Draft. Fill the bracketed items when the release is built and signed. Text for the GitHub Release page and the
> website download section.

CAMO is private digital cash: the sender, the receiver and the amount of every payment are hidden, always. This is
the first release, for the mainnet launch on **December 15, 2026 at 18:00 UTC**. Mining is open to everyone from that
moment: no pre-sale, one disclosed allocation (below).

## Download and verify

| Platform | File |
| --- | --- |
| Linux x86-64 | `camo-x86_64-linux-gnu-v1.0.0.tar.bz2` |
| Linux ARM64 | `camo-aarch64-linux-gnu-v1.0.0.tar.bz2` |
| Windows 64-bit | `camo-x86_64-w64-mingw32-v1.0.0.zip` |
| macOS Intel | `camo-x86_64-apple-darwin11-v1.0.0.tar.bz2` |
| macOS Apple Silicon | `camo-aarch64-apple-darwin11-v1.0.0.tar.bz2` |

Other Linux builds (ARMv7, i686, RISC-V) and 32-bit Windows are in the same release.

1. Import the release key: fingerprint `[FINGERPRINT]`, also published on the website and at keys.openpgp.org.
2. `gpg --verify SHA256SUMS.asc` must say "Good signature" from that key.
3. `sha256sum -c SHA256SUMS --ignore-missing` must say "OK" for the file you downloaded.

These builds are reproducible: anyone can rebuild them from the `v1.0.0` tag with gitian and get identical files
(`contrib/gitian/CAMO-RELEASE.md`). Builds are not signed by Apple or Microsoft, so macOS and Windows show a warning
the first time; that does not affect the checks above.

## What's in it

- **Software:** `camod` (node), `camo-wallet-cli` (command-line wallet), `camo-wallet-rpc` (wallet for apps and
  services). Binaries report `CAMO 'CAMO Genesis' (v1.0.0-<commit>)`.
- **Code base:** Monero v0.18.5.4 (BSD-3 license, kept in full) plus later Monero bug and security fixes. CAMO keeps
  Monero's cryptography and consensus code unchanged and changes only parameters.
- **Privacy:** ring signatures with 16 members, RingCT with Bulletproofs+ (amounts hidden), one-time addresses and
  view tags, Dandelion++; optional Tor and I2P.
- **Network:** 1-minute blocks; about 17 CAMO per block at launch, falling smoothly; 18.13 million CAMO main emission,
  then a permanent 0.3 CAMO per block. RandomX proof of work (CPU-friendly). Addresses start with `C`. Ports: P2P
  19740, RPC 19741 (keep RPC private).
- **Payment links** use the `camo:` scheme (for example `camo:C...?tx_amount=1.5`). Monero `monero:` links are refused.
- **Units:** camo, millicamo, microcamo, nanocamo, picocamo (10^-12 CAMO).
- **Donations:** `donate <amount>` in the wallet sends to the public marketing wallet.

## The block 1 allocation (disclosed)

Block 1's coinbase is fixed by the consensus rules, so whoever mines it gets no reward and cannot redirect it:

| Recipient | CAMO | Address |
| --- | --- | --- |
| Founder | 489,600 | `[FOUNDER ADDRESS]` |
| Public marketing wallet | 54,400 | `Cfbe7EfJzZW4H6Li6bvsmfTvjdQE5gsGvTf1PhS9MvnnEHpQUwgxVvFJd79u6KsgibPht4u2PRyj2fU7awZCoaPc6FaAtK4` |
| Provably unspendable burn | 96,000 | `Cdqd3jC3ocP6H1BX4G2Uis8qVYj6ddShVfqGaxkvCE64YEgGgZTt5RjLZ4toVBJ3pae1HJR1AcWQxBmSRi55ePTv4dxHzs8` |

Founder plus marketing are 3.0% of the main emission. View keys to verify the amounts: `[FOUNDER VIEW KEY]`,
`[MARKETING VIEW KEY]`, burn `4846a9442b62be63ac514878acb76bc3ede0468f7f3d3b0710d191fcedf57f09`.

## Getting started

- **Run a node:** `./camod`. It finds the network through built-in seed nodes.
- **Make a wallet:** `./camo-wallet-cli --generate-new-wallet mywallet`. Write the 25 words on paper; they are the
  only way back into the wallet. Nobody from CAMO will ever ask for them.
- **Mine:** solo with `start_mining <your address> <threads>` in the wallet, or join the official pool (1% fee to the
  marketing wallet, minimum payout 0.25 CAMO): see the mining guide on the website.
- **Wait for confirmations:** in the first weeks, accept payments only after 60+ confirmations (about an hour).

## Known limitations

- Hardware wallets (Ledger, Trezor) do not support CAMO yet.
- Checkpoints for the first blocks arrive in v1.0.1 (planned about a week after launch); update when it ships.
- Ghillie, CAMO's desktop and mobile wallet, is planned for Q1 2027.

## Security

Report vulnerabilities privately to `camocoin@proton.me` (see `SECURITY.md`), not in public issues.
