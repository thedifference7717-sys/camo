#!/usr/bin/env bash
# Keep asking Oracle Cloud for an Always Free ARM server until it has capacity, then print its public IP.
# Run on your Mac after `oci setup config` works:   bash oci-retry-launch.sh [name] [ocpus] [memory_gb]
# Defaults: camo-seed-1, 2 OCPUs, 12 GB (two such servers = the whole free allowance of 4 OCPUs / 24 GB).
# Only ever creates the free VM.Standard.A1.Flex shape. Needs a VCN with a public subnet (console:
# Networking > Virtual cloud networks > Start VCN Wizard > "Create VCN with Internet Connectivity").
set -u
NAME=${1:-camo-seed-1}; OCPUS=${2:-2}; MEM=${3:-12}; WAIT=${WAIT:-90}
KEY="$HOME/.ssh/id_ed25519.pub"
command -v oci >/dev/null || { echo "oci CLI not found (install it first)"; exit 1; }
[ -f "$KEY" ] || { echo "no SSH public key at $KEY"; exit 1; }
T=$(sed -n 's/^tenancy *= *//p' "$HOME/.oci/config" | head -1)
[ -n "$T" ] || { echo "no tenancy in ~/.oci/config (run: oci setup config)"; exit 1; }

if [ -n "$(oci compute instance list --compartment-id "$T" --display-name "$NAME" --lifecycle-state RUNNING --query 'data[0].id' --raw-output 2>/dev/null)" ]; then
  echo "$NAME is already running; not creating another."; exit 0
fi
ADS=$(oci iam availability-domain list --compartment-id "$T" --query 'data[].name' --raw-output | tr -d '[]",' | xargs)
IMG=$(oci compute image list --compartment-id "$T" --operating-system "Canonical Ubuntu" --shape VM.Standard.A1.Flex \
      --sort-by TIMECREATED --sort-order DESC --all --query "data[?contains(\"display-name\",'24.04')] | [0].id" --raw-output)
SUB=$(oci network subnet list --compartment-id "$T" --query "data[?\"prohibit-public-ip-on-vnic\"==\`false\`] | [0].id" --raw-output)
[ -n "$IMG" ] && [ "$IMG" != "null" ] || { echo "no Ubuntu 24.04 ARM image found"; exit 1; }
[ -n "$SUB" ] && [ "$SUB" != "null" ] || { echo "no public subnet: run the VCN Wizard (see top of this script)"; exit 1; }
echo "Asking for $NAME ($OCPUS OCPU, $MEM GB) in: $ADS. Retrying every ${WAIT}s; leave this window open (Ctrl-C to stop)."

n=0
while true; do
  for AD in $ADS; do
    n=$((n+1))
    OUT=$(oci compute instance launch --compartment-id "$T" --availability-domain "$AD" --display-name "$NAME" \
          --shape VM.Standard.A1.Flex --shape-config "{\"ocpus\":$OCPUS,\"memoryInGBs\":$MEM}" \
          --image-id "$IMG" --subnet-id "$SUB" --assign-public-ip true --ssh-authorized-keys-file "$KEY" \
          --wait-for-state RUNNING --query 'data.id' --raw-output 2>&1)
    if echo "$OUT" | grep -q '^ocid1.instance'; then
      ID=$(echo "$OUT" | grep '^ocid1.instance' | head -1)
      IP=$(oci compute instance list-vnics --instance-id "$ID" --query 'data[0]."public-ip"' --raw-output)
      echo; echo "SUCCESS after $n tries: $NAME is running in $AD. Public IP: $IP"; exit 0
    fi
    if echo "$OUT" | grep -qi 'capacity'; then
      echo "$(date '+%H:%M') try $n: $AD out of capacity"
    else
      echo "$(date '+%H:%M') try $n: unexpected error, stopping:"; echo "$OUT" | tail -5; exit 1
    fi
  done
  sleep "$WAIT"
done
