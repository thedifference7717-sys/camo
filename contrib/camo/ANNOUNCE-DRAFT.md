<!-- DRAFT for Anthony to review. BBCode to paste: contrib/camo/ANNOUNCE-BBCODE.txt (regenerate with tools/ann_to_bbcode.py). Not posted anywhere. Numbers match CLAUDE.md, ALLOCATION.md and the website.
     Placeholders filled Nov 13; progress section updated Nov 23; re-check numbers and links before posting. BitcoinTalk uses BBCode; this is plain text with light formatting
     that pastes cleanly, convert headings to [b]...[/b] if you like. -->

![CAMO|160](https://camocoin.org/assets/camo-logo-512.png)

# [ANN][CAMO] CAMO: private digital cash | RandomX CPU | Fair launch Dec 15, 2026

**Fair launch: Dec 15, 2026, 18:00 UTC. Public stagenet open now.**

**Hidden in plain sight.** CAMO is digital cash that hides the sender, the receiver and the amount of every
payment, with no opt-in and no exceptions. It runs Monero's audited privacy technology, unchanged.

## Why another coin?
CAMO is a deliberately conservative Monero fork: the cryptography and consensus code are Monero's v0.18, kept as-is.
What changes is parameters (name, ports, addresses, genesis, 1-minute blocks) and a launch done in the open: a public
stagenet first, one disclosed allocation, and its own desktop wallet, Ghillie, ready on launch day.

## Specs
| | |
|---|---|
| Ticker | CAMO |
| Proof of work | RandomX (CPU), XMRig: `-a rx/0` |
| Block time | 60 seconds |
| Main emission | 18.13M CAMO over ~8 years, ~17 CAMO per block at launch |
| Tail emission | 0.3 CAMO per block, forever (miners are always paid) |
| Privacy | Ring signatures (ring size 16, CLSAG), stealth addresses, RingCT + Bulletproofs+, Dandelion++, Tor/I2P support |
| Addresses | mainnet start with `C`, stagenet with `Q` |
| Ports | P2P 19740, RPC 19741 (stagenet 39740/39741) |
| Code base | Monero v0.18.5.4 (BSD-3), plus Monero's later bug and security fixes |

## Allocation: disclosed, fixed by consensus, partly burned
There is no pre-sale. Block 1 (the first mined block) carries a single allocation, enforced by consensus so it cannot
be changed or added to:

| | Amount | Share of main emission |
|---|---|---|
| Founder | 489,600 CAMO | 2.7% |
| Marketing (public wallet) | 54,400 CAMO | 0.3% |
| Burned (provably unspendable) | 96,000 CAMO | |

Whoever mines block 1 receives nothing for it; every block after pays the miner in full. The burn address and its
public view key are published so anyone can audit it: `Cdqd3jC3ocP6H1BX4G2Uis8qVYj6ddShVfqGaxkvCE64YEgGgZTt5RjLZ4toVBJ3pae1HJR1AcWQxBmSRi55ePTv4dxHzs8`,
view key `4846a9442b62be63ac514878acb76bc3ede0468f7f3d3b0710d191fcedf57f09`. Founder and marketing view keys are
published at launch.

## Tested before launch (on the public stagenet and in the open)
- **Reproducible releases**: two independent builders produced byte-identical binaries for Linux, Windows and macOS,
  and the hash list is signed with the release key below. Anyone can rebuild and compare.
- **Launch rehearsals**: block 1 allocation, nodes going offline and catching up, block times settling toward 60 s,
  private sends, and an attack test that tries to change block 1 (every attempt rejected).
- **BTC to CAMO atomic swaps**: the full swap suite passes, and a real swap ran on the stagenet against Bitcoin testnet.
  Not live for real coins until an outside review.
- **Ghillie for phones**: the real wallet runs on iPhone in testing (send, receive, Face ID, recovery sheet).
- **The Seals' HOLD flag**: a live drill on the stagenet raised the alarm and turned the public status page to HOLD
  within minutes, then cleared. A double-spend attempt is caught the same way in tests on a split network.

## Roadmap
- **Nov 10, 2026**: public stagenet opens (test network, worthless coins). Please help test.
- **Dec 7, 2026**: signed release binaries and their hashes.
- **Dec 15, 2026, 18:00 UTC**: mainnet. Anyone can mine from the first block. Every block must be dated 18:00 UTC or
  later; nodes accept blocks dated up to 2 hours ahead, so in practice mining opens at about **16:00 UTC**. We say it here
  so nobody has an insider head start.
- **Dec 15, 2026**: Ghillie desktop wallet (Mac, Windows, Linux) ships with the launch downloads.
- **Q1 2027**: Ghillie for phones, "mine while idle", control mining on your own computers from your phone.
- **Q2 2027**: BTC to CAMO atomic swaps in Ghillie, merchant checkout plugins.
- **Later**: FCMP++ (every spend hidden among every coin on the chain) once it is audited and live on Monero.

## Mining
Any modern CPU. Solo with your own node or Ghillie, solo with XMRig, or the official pool once it is online (1% fee to the
public marketing wallet, PPLNS; link posted here). Mining needs free memory: close heavy apps if your hash rate drops to 0. Guide: https://camocoin.org/mine.html

## Join the stagenet
Build from source or use the test binaries, start a node, make a test wallet, mine, send: https://camocoin.org/stagenet.html
Seed nodes: 34.171.218.2:39740 and 3.134.132.214:39740 (both built into the software)

## Security
![The Seals: Watch, Code and Scout|800](https://camocoin.org/assets/seals/seals-banner.png)

Releases are reproducible and signed (two independent builders matched byte for byte). The Seals, CAMO's watch team,
monitor the network around the clock for double-spend attempts, splits, deep reorgs, block bursts and hashrate swings,
and track Monero's security fixes. On a possible attack they raise a public HOLD flag within minutes:
https://camocoin.org/status.html, with a JSON feed exchanges and pools can poll to pause deposits automatically. The
Seals watch and warn; nobody can pause or reverse the chain.

Release signing key: `CAMO release signing <camocoin@proton.me>`, fingerprint
`5F1A 8350 C748 BC43 AD19 2472 AF13 7B28 E11A 0857` (https://camocoin.org/assets/camo-release.asc, keys.openpgp.org).
How to check a download: https://camocoin.org/verify.html

Report problems privately: camocoin@proton.me or GitHub private vulnerability reporting.

## Links
- Website: https://camocoin.org
- Source: https://github.com/thedifference7717-sys/camo
- White paper: https://camocoin.org/assets/CAMO-White-Paper.pdf
- Network status (the Seals): https://camocoin.org/status.html
- Block explorer and official pool: links posted here when their servers are live
- Community: X https://x.com/CAMO_Coin (@CAMO_Coin), BitcoinTalk CAMO_Coin; more channels to follow
- Security reports (private): camocoin@proton.me

## Credits
CAMO is built on the work of the Monero Project and the CryptoNote developers. Their copyright notices and
BSD-3 license are kept in full. Mistakes in CAMO are ours, not theirs.

*Not an offer to sell anything and not investment advice. Follow the laws where you live.*
