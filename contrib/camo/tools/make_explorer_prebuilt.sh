#!/usr/bin/env bash
# Copyright (c) 2026, The CAMO Project. BSD-3-Clause, see LICENSE.
# Build the CAMO block explorer here and pack it for deploy-services.sh --explorer-prebuilt (so a small server
# doesn't have to compile). Build on the SAME Ubuntu release as the server (Ubuntu 24.04 for the seeds).
#   bash contrib/camo/tools/make_explorer_prebuilt.sh <camo-explorer source dir> [camo build dir] [out dir]
# Needs a CAMO build (build/release with daemon + wallet libs) and: apt install libasio-dev libminiupnpc-dev
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); CAMO=$(cd "$HERE/../../.." && pwd)
EXP=$(cd "${1:?camo-explorer source dir}" && pwd); BUILD=$(cd "${2:-$CAMO/build/release}" && pwd); OUT=$(mkdir -p "${3:-.}" && cd "${3:-.}" && pwd)
UPNP=$(find /usr/lib /usr/lib64 -name 'libminiupnpc.so' 2>/dev/null | head -1)
[ -n "$UPNP" ] || { echo "apt install libminiupnpc-dev libasio-dev"; exit 1; }
mkdir -p "$EXP/build"
(cd "$EXP/build" && cmake -DMONERO_DIR="$CAMO" -DMONERO_BUILD_DIR="$BUILD/" -DCMAKE_BUILD_TYPE=Release \
   -DXmr_MINIUPNPC_LIBRARY="$UPNP" .. >/dev/null && make -j"$(nproc)" >/dev/null)
REV="camo-$(git -C "$CAMO" rev-parse --short=9 HEAD)_explorer-$(git -C "$EXP" rev-parse --short=7 HEAD)"
. /etc/os-release
STAGE=$(mktemp -d); trap 'rm -rf "$STAGE"' EXIT
cp "$EXP/build/camo-explorer" "$STAGE/"; cp -a "$EXP/build/templates" "$STAGE/"
printf '%s\nbuilt on %s\n' "$REV" "$PRETTY_NAME" > "$STAGE/VERSION"
TAR="$OUT/camo-explorer-$REV.tar.gz"
tar -czf "$TAR" -C "$STAGE" camo-explorer templates VERSION
sha256sum "$TAR"
