#!/usr/bin/env bash
# Copyright (c) 2026, The CAMO Project. BSD-3-Clause, see LICENSE.
# Publish this seed's Seal Watch status feed (OK / CAUTION / HOLD) to the public camo-status repository, where
# exchanges, pools and swap makers poll it. Run every minute by the camo-status-publish timer (install-alarm.sh
# --status NAME). Pushes when the status or its reasons change, and every 30 minutes as a heartbeat (so a stale
# file means this seed's watch has stopped). The deploy key can write only to camo-status, never to camo or the
# website, so a compromised seed cannot touch code or download links.
#   publish_status.sh <status.json> <seed name> [repo dir]
set -euo pipefail
SRC=${1:?usage: publish_status.sh <status.json> <seed name> [repo dir]}
NAME=${2:?seed name}
DIR=${3:-$HOME/camo-status}
REPO=${CAMO_STATUS_REPO:-git@github.com:thedifference7717-sys/camo-status.git}
KEY=${CAMO_STATUS_KEY:-$HOME/.ssh/camo-status}
HEARTBEAT=${CAMO_STATUS_HEARTBEAT:-1800}
[[ "$NAME" =~ ^[a-z0-9-]{1,32}$ ]] || { echo "seed name: 1-32 lowercase letters, digits or -" >&2; exit 1; }
[ -s "$SRC" ] || exit 0                               # the watch hasn't written its first status yet
export GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
[ -d "$DIR/.git" ] || git clone -q "$REPO" "$DIR"
cd "$DIR"
git config user.name "Seal Watch ($NAME)"; git config user.email camocoin@proton.me
git pull -q --rebase
# what matters for change detection: status + reasons + until (not the timestamp)
key(){ [ -f "$1" ] && python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['status'],d.get('until'),d['reasons'])" "$1" || echo none; }
OUT="$NAME.json"
changed=0; [ "$(key "$SRC")" != "$(key "$OUT")" ] && changed=1
last=$(git log -1 --format=%ct -- "$OUT" 2>/dev/null || true)
age=$(( $(date +%s) - ${last:-0} ))
[ $changed = 1 ] || [ $age -ge "$HEARTBEAT" ] || exit 0
cp "$SRC" "$OUT"
git add "$OUT"
git diff --cached --quiet && exit 0
STATUS=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$OUT")
git commit -q -m "$NAME: $STATUS"
for i in 1 2 3 4; do
  git push -q origin HEAD && exit 0
  sleep $((i * 3)); git pull -q --rebase
done
echo "push failed" >&2; exit 1
