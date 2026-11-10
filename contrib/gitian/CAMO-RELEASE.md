# Signed, reproducible CAMO releases (gitian)

Goal for **Dec 7, 2026**: anyone can rebuild the release from the tagged source, get byte-identical files,
and check that Anthony's GPG key signed the same hashes. This file is the CAMO-specific checklist; the
generic tool docs are [DOCKRUN.md](DOCKRUN.md) (Docker, recommended) and [README.md](README.md) (LXC/KVM).

What's already set up in this repo:
- The build recipes (`gitian-linux.yml`, `gitian-win.yml`, `gitian-osx.yml`, plus `android`/`freebsd`, which
  aren't built by default) fetch `thedifference7717-sys/camo` and produce `camo-<host>-<version>` archives.
- `gitian-build.py` and `dockrun.sh` use CAMO's repos. By default they build Linux (x86_64, aarch64, armv7,
  i686, riscv64), Windows (64- and 32-bit) and macOS (Intel and Apple Silicon).
- GitHub Actions workflow `ci/gh-actions/gitian` runs the same build on every `v*` tag and on demand
  (Actions -> ci/gh-actions/gitian -> Run workflow). Its hashes appear in the run summary. It serves as an
  independent second builder to compare against.

Monero's own release tags (`v0.18.x`) are still in this repo. **Never build or sign those as CAMO.**

## One-time setup (Anthony)

**Done Nov 10:** release key `CAMO release signing <camocoin@proton.me>`, ed25519, fingerprint
`5F1A 8350 C748 BC43 AD19  2472 AF13 7B28 E11A 0857`, expires 2030-11-10, published on keys.openpgp.org (email verified). Created with GPG Suite on Anthony's Mac.
Still to do: offline backup of the secret key on a USB stick (before Dec 7), and the signatures repo (step 2).

1. **GPG key** (on your own computer; the private key never leaves it and is never shared with anyone,
   including Claude):
   ```bash
   gpg --quick-gen-key "Anthony (CAMO release signing) <your-release-email>" ed25519 sign 2y
   gpg --armor --export <fingerprint> > thedifference7717-sys.asc
   ```
   Back the key up offline (e.g. `gpg --export-secret-keys --armor` onto a USB stick kept somewhere safe).
   Publish the **public** key and its fingerprint in three places: the website, keys.openpgp.org, and
   the signatures repo (step 2).
2. **Signatures repo**: create a PUBLIC GitHub repo `thedifference7717-sys/camo-gitian.sigs` (branch `main`)
   with `gitian-pubkeys/thedifference7717-sys.asc` (your public key) and a short README. Each release adds a
   folder per platform with every builder's signed `.assert` file.
3. **Build machine**: an Ubuntu 22.04/24.04 **x86-64** machine with Docker: at least 4 cores, 8 GB RAM and
   60 GB disk. A VPS rented by the hour works; delete it afterwards. Apple Silicon Macs are not suitable
   (the builder needs amd64). Expect 3-5 hours for all three platforms the first time.
   ```bash
   sudo apt-get install -y docker.io apt-cacher-ng git && sudo usermod -aG docker $USER && su - $USER
   ```
   The GPG key does **not** go on this machine; see step 3 of the release below.

## Each release

1. **Freeze and tag.** The code is final (mainnet seed IPs set, tests and the stagenet rehearsal pass). Tag the
   commit and push the tag. A signed tag is preferable: on your computer, run
   `git tag -s v1.0.0 -m "CAMO v1.0.0"` and then `git push origin v1.0.0`. Pushing the tag starts the
   gitian workflow on GitHub.
2. **Build** on the build machine:
   ```bash
   git clone https://github.com/thedifference7717-sys/camo.git && cd camo/contrib/gitian
   GH_USER=thedifference7717-sys OPT="-j 4" ./dockrun.sh v1.0.0
   ```
   It prints the SHA-256 of every archive. **Compare them with the hashes in the GitHub workflow's summary.
   They must be identical.** If anything differs: STOP. Don't sign, and find out why first.
   At the "type sign" prompt press Ctrl-C (the key isn't on this machine). Then copy the results out:
   ```bash
   docker cp gitrun:/home/ubuntu/out/v1.0.0 ./out-v1.0.0
   docker cp gitrun:/home/ubuntu/sigs ./sigs-v1.0.0
   ```
3. **Sign** on your own computer. Download `out-v1.0.0/` and the `.assert` files from
   `sigs-v1.0.0/v1.0.0-*/thedifference7717-sys/`, then run:
   ```bash
   for f in v1.0.0-*/thedifference7717-sys/*.assert; do gpg --detach-sign "$f"; done   # -> .assert.sig
   cd out-v1.0.0 && sha256sum camo-* > SHA256SUMS && gpg --clearsign SHA256SUMS          # -> SHA256SUMS.asc
   ```
   Commit the `v1.0.0-*` folders (each `.assert` plus its `.assert.sig`) to `camo-gitian.sigs`.
4. **Publish.** Create a GitHub Release for the tag on `camo` with the archives and `SHA256SUMS.asc`. Then
   update the website's download links and hashes, and post the hashes with the announcement.
5. **Anyone can verify.** They run `gpg --verify SHA256SUMS.asc`, then `sha256sum -c SHA256SUMS`. To check the
   build itself, they run `dockrun.sh v1.0.0` and compare the hashes with yours.

## Version number (decided Nov 5)

The first release is **v1.0.0**: tag `v1.0.0`, and binaries report `CAMO 'CAMO Genesis' (v1.0.0-<commit>)`
(`src/version.cpp.in`). The code base is Monero v0.18.5.4 plus later fixes; say so in release notes. When merging a
Monero "build: prepare v0.18.x" commit, keep CAMO's own version line.

## Notes

- The release recipes depend on `contrib/depends`, which downloads pinned, hash-checked source tarballs (and
  Monero's mirror as fallback). The macOS SDK comes from a pinned GitHub download, so no Apple account is needed.
- The archives are unsigned at the OS level. Mac users will see a Gatekeeper warning, and Windows users a
  SmartScreen warning. An Apple developer account ($99/yr) or a Windows code-signing certificate would remove
  those later; they don't affect reproducibility.
- Not yet run end to end: cloud sessions can't reach the depends source hosts, and GitHub Actions minutes for
  the private repo are used up. The first full run happens when the repo is public (Nov 10). Run the workflow by
  hand then, well before Dec 7, so there is time to fix anything.
