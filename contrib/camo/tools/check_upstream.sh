#!/usr/bin/env bash
# Check Monero upstream for fixes CAMO doesn't have yet. Run monthly and before every release.
#
#   bash contrib/camo/tools/check_upstream.sh [since-date, default 6 months ago]
#
# 1. Monero's release-v0.18 branch: every commit there that CAMO lacks should be merged
#    (git merge upstream/release-v0.18), then rebuild and run the tests in CLAUDE.md.
# 2. Monero's master: fix-looking commits since the date, each tested against CAMO's tree:
#      ALREADY PRESENT     the change is in CAMO (backported or merged)
#      MISSING, applies    candidate: read it, then `git cherry-pick -x <hash>` if it is a real fix for 0.18
#      does not apply      master-only code or needs a hand port; read it to decide
#    Never take consensus or cryptography changes this way (see CLAUDE.md ground rules).
set -uo pipefail
# The Monero release CAMO's code is based on. Update this line whenever you merge a newer release-v0.18.
BASE_TAG=v0.18.5.4
cd "$(git rev-parse --show-toplevel)"
SINCE=${1:-$(date -d '6 months ago' +%Y-%m-%d 2>/dev/null || date -v-6m +%Y-%m-%d)}
git remote get-url upstream >/dev/null 2>&1 || git remote add upstream https://github.com/monero-project/monero.git
echo "fetching monero-project/monero (release-v0.18, master)..."
git fetch -q upstream release-v0.18 master --tags || { echo "fetch failed"; exit 1; }

echo
echo "== release-v0.18"
echo "upstream tip: $(git log -1 --format='%h %ad %s' --date=short upstream/release-v0.18) ($(git describe --tags upstream/release-v0.18 2>/dev/null))"
# Compare against the recorded base release, not a merge-base: a shallow clone (cloud sessions) has no common
# commit with upstream, and the Nov 10 history rewrite changed CAMO's own commit ids.
N=$(git rev-list --count "$BASE_TAG"..upstream/release-v0.18)
echo "CAMO is based on: $BASE_TAG; upstream commits since then: $N"
[ "$N" -gt 0 ] && git log --oneline "$BASE_TAG"..upstream/release-v0.18 | head -50

echo
echo "== master fixes since $SINCE (not merged into release-v0.18)"
PATCH=$(mktemp)
git log --no-merges --since="$SINCE" --format='%h' upstream/master --not upstream/release-v0.18 \
  -i -E --grep='fix|overflow|crash|security|cve|vuln|dos|leak|exploit|harden|protect|sanit|bound|check for' |
while read -r c; do
  git show --format= "$c" > "$PATCH"
  [ -s "$PATCH" ] || continue
  if git apply --check -R "$PATCH" 2>/dev/null; then st="ALREADY PRESENT"
  elif git apply --check "$PATCH" 2>/dev/null; then st="MISSING, applies"
  else st="does not apply"; fi
  printf '%-18s %s %s\n' "$st" "$c" "$(git log -1 --format='%ad %s' --date=short "$c" | cut -c1-90)"
done | sort -s -k1,1
rm -f "$PATCH"
