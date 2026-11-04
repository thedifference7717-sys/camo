#!/usr/bin/env bash
# Pack CAMO (with submodules), the block explorer and the mining pool into one tarball for a server.
# Needed while the repos are private (servers can't clone them); once public, deploy-services.sh can take git URLs.
#
#   bash contrib/camo/tools/make_source_bundle.sh [--explorer ../camo-explorer] [--pool ../camo-pool] [-o out.tar.gz]
#
# Packs the committed state (HEAD) of each repo, not uncommitted edits. Then:
#   scp camo-bundle-*.tar.gz contrib/camo/deploy-services.sh root@<server>:/root/
set -euo pipefail
CAMO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
EXPLORER="$CAMO/../camo-explorer"; POOL="$CAMO/../camo-pool"; OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --explorer) EXPLORER="$2"; shift 2 ;;
    --pool) POOL="$2"; shift 2 ;;
    -o) OUT="$2"; shift 2 ;;
    *) echo "unknown option $1"; exit 1 ;;
  esac
done
REV=$(git -C "$CAMO" rev-parse --short HEAD)
OUT=${OUT:-$PWD/camo-bundle-$REV.tar.gz}
STAGE=$(mktemp -d); trap 'rm -rf "$STAGE"' EXIT

pack(){ # repo-dir name: committed tree plus initialized submodules
  local dir=$1 name=$2
  git -C "$dir" archive --format=tar --prefix="$name/" HEAD | tar -x -C "$STAGE"
  git -C "$dir" submodule status --recursive 2>/dev/null | awk '{print $2}' | while read -r sub; do
    [ -n "$sub" ] || continue
    git -C "$dir/$sub" archive --format=tar --prefix="$name/$sub/" HEAD | tar -x -C "$STAGE"
  done
  echo "$name $(git -C "$dir" rev-parse HEAD)" >> "$STAGE/VERSIONS"
}

pack "$CAMO" camo
[ -d "$EXPLORER/.git" ] && pack "$EXPLORER" camo-explorer || echo "note: no explorer at $EXPLORER (skipped)"
[ -d "$POOL/.git" ] && pack "$POOL" camo-pool || echo "note: no pool at $POOL (skipped)"
tar -C "$STAGE" -czf "$OUT" .
echo "wrote $OUT ($(du -h "$OUT" | cut -f1))"; cat "$STAGE/VERSIONS"
echo "sha256 $(sha256sum "$OUT" | cut -d' ' -f1)"
