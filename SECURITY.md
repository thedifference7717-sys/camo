# CAMO security

No coin or wallet is "hack-proof", and anyone who promises that is selling something. CAMO's goal is narrower and
achievable: be as hard to attack as the best privacy coins, and close the gaps that usually sink new ones.

## Reporting a vulnerability

Do not open a public issue. Email **[SECURITY EMAIL]** with steps to reproduce. You will get a reply within 72 hours.
Fixes ship as a point release; the reporter is credited unless they ask not to be. A bug bounty paid from the marketing
wallet is planned once CAMO has value.

## Where the risk actually is

| Layer | Risk | Status / defense |
|---|---|---|
| Cryptography (ring signatures, stealth addresses, RingCT, Bulletproofs+) | A flaw lets someone trace payments or print coins | Monero's audited code, **unchanged**. Rule: CAMO never edits cryptography (CLAUDE.md). |
| CAMO's own consensus code (block-1 allocation) | Someone redirects or inflates the allocation | Hash-pinned to the published transaction. Adversarial test `contrib/camo/tools/attack_block1.py`: forged blocks (miner keeps reward, founder output redirected, tx key swapped) are all rejected; the honest block is accepted. Re-run before every release. |
| Upstream Monero bugs | A Monero bug is also a CAMO bug | Track `upstream/release-v0.18`; merge security fixes within days. Checked Nov 3, 2026: no new commits since the fork base. |
| 51% attack in the first months | Recent payments reversed with rented RandomX hashrate | Checkpoints compiled into each point release, exchanges and merchants wait 60+ confirmations (~1 hour), monitor hashrate and reorg depth, grow miners before any listing. |
| Seed nodes | Servers taken over or knocked offline | `contrib/camo/deploy-seed-node.sh`: default-deny firewall, RPC on localhost only, SSH key-only, fail2ban, automatic security updates, sandboxed unprivileged service. 3 nodes on different providers/regions. |
| Fake downloads | Users install malware posing as CAMO | Reproducible builds (`contrib/guix`), GPG-signed SHA256 hashes, downloads only from the official site and GitHub releases. |
| Founder and marketing keys | Theft of the allocation | See below. |
| Users' own devices | Malware, phishing, seed words photographed | Ghillie rules below, plus user education on the website. |

## Founder and marketing wallets

- Seed words exist **only on paper**, in two separate secure places. Never typed into a phone, cloud note, email or chat.
- The founder wallet stays cold: day-to-day spending goes through a separate small "hot" wallet topped up as needed.
- Marketing wallet: publish its view key so spending is publicly visible. Move to multisig (e.g. 2-of-3 between Anthony
  and trusted holders) before it pays for anything significant; Monero multisig is supported in the wallet CLI.
- Public addresses and view keys can be shared; spend keys and seed words never are. Claude never needs them.

## Ghillie wallet security requirements (v1.1)

1. **Non-custodial.** Keys are generated and kept on the user's device. No server can move funds. No account, no email.
2. **Encrypted at rest** with the device keychain / secure enclave, unlocked by PIN or biometrics.
3. **No send fees, no telemetry, no analytics SDKs.** Nothing that phones home with user data.
4. **Remote mining control can never spend.** The phone↔computer link only starts/stops mining and reads stats; it uses
   an end-to-end encrypted pairing (QR code on the computer), and the miner never has access to wallet keys.
5. **Address-poisoning and clipboard defenses:** show addresses in full with a checksum chunk, warn on look-alike
   addresses, never auto-paste.
6. **Open source and reproducible**, built by CI from tagged commits, signed releases, published hashes.
7. **Independent security audit before v1.1 ships**, and again before swaps (v1.2) handle other people's BTC.
8. **Swaps stay peer-to-peer** (atomic swaps): Ghillie never holds anyone's coins.

## Before every release (checklist)

- [ ] `contrib/camo/regtest-demo.sh` passes (private transfer, ring 16, hidden amounts)
- [ ] `contrib/camo/tools/attack_block1.py` passes on a fresh regtest node
- [ ] `git log upstream/release-v0.18` checked; any security fixes merged
- [ ] Reproducible build matches across two machines; hashes signed and published
- [ ] Checkpoints updated (after launch)
