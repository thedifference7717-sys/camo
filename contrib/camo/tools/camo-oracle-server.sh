#!/usr/bin/env bash
# Keep asking Oracle Cloud for an Always Free ARM server until it has capacity, then print its public IP.
# Run on your Mac after `oci setup config` works:   bash camo-oracle-server.sh [name] [ocpus] [memory_gb]
# Defaults: camo-seed-1, 2 OCPUs, 12 GB (two such servers = the whole free allowance of 4 OCPUs / 24 GB).
# Backup when ARM capacity never frees up:          bash camo-oracle-server.sh camo-seed-1 micro
#   asks for the Always Free AMD VM.Standard.E2.1.Micro (1 GB RAM, x86-64; 2 per account) instead. Too small to build
#   CAMO on: install it with deploy-seed-node.sh --binary and the prebuilt x86_64 Linux camod.
# Only ever creates these two free shapes. If the account has no public subnet yet, it first creates one
# (VCN camo-vcn 10.0.0.0/16, internet gateway, default route, subnet camo-public 10.0.0.0/24) and opens TCP 22 (SSH),
# 39740 (stagenet P2P) and 19740 (mainnet P2P) in its security list. All of that is free.
set -u
NAME=${1:-camo-seed-1}; OCPUS=${2:-2}; MEM=${3:-12}; WAIT=${WAIT:-180}
if [ "$OCPUS" = "micro" ]; then
  # Oracle recommends Ubuntu Minimal for the 1 GB micro server (the full image was refused with NotAuthorizedOrNotFound)
  SHAPE=VM.Standard.E2.1.Micro; SHAPECFG=""; DESC="free AMD micro server, 1 GB"; IMGMATCH="24.04-Minimal"
else
  SHAPE=VM.Standard.A1.Flex; SHAPECFG="{\"ocpus\":$OCPUS,\"memoryInGBs\":$MEM}"; DESC="$OCPUS OCPU, $MEM GB"; IMGMATCH="24.04"
fi
KEY="$HOME/.ssh/id_ed25519.pub"
command -v oci >/dev/null || { echo "oci CLI not found (install it first)"; exit 1; }
[ -f "$KEY" ] || { echo "no SSH public key at $KEY"; exit 1; }
T=$(sed -n 's/^tenancy *= *//p' "$HOME/.oci/config" | head -1)
[ -n "$T" ] || { echo "no tenancy in ~/.oci/config (run: oci setup config)"; exit 1; }

if [ -n "$(oci compute instance list --compartment-id "$T" --display-name "$NAME" --lifecycle-state RUNNING --query 'data[0].id' --raw-output 2>/dev/null)" ]; then
  echo "$NAME is already running; not creating another."; exit 0
fi
ADS=$(oci iam availability-domain list --compartment-id "$T" --query 'data[].name' --raw-output | tr -d '[]",' | xargs)
IMG=$(oci compute image list --compartment-id "$T" --operating-system "Canonical Ubuntu" --shape "$SHAPE" \
      --sort-by TIMECREATED --sort-order DESC --all --query "data[?contains(\"display-name\",'$IMGMATCH')] | [0].id" --raw-output)
[ -n "$IMG" ] && [ "$IMG" != "null" ] || { echo "no Ubuntu 24.04 image found for $SHAPE"; exit 1; }
SUB=$(oci network subnet list --compartment-id "$T" --query "data[?\"prohibit-public-ip-on-vnic\"==\`false\`] | [0].id" --raw-output)
if [ -z "$SUB" ] || [ "$SUB" = "null" ]; then
  echo "Creating the network (one time): VCN, internet gateway, public subnet, firewall rules for SSH and CAMO..."
  VCN=$(oci network vcn create --compartment-id "$T" --cidr-blocks '["10.0.0.0/16"]' --display-name camo-vcn \
        --dns-label camovcn --wait-for-state AVAILABLE --query 'data.id' --raw-output) || { echo "VCN create failed"; exit 1; }
  RT=$(oci network vcn get --vcn-id "$VCN" --query 'data."default-route-table-id"' --raw-output)
  SL=$(oci network vcn get --vcn-id "$VCN" --query 'data."default-security-list-id"' --raw-output)
  IGW=$(oci network internet-gateway create --compartment-id "$T" --vcn-id "$VCN" --is-enabled true \
        --display-name camo-igw --wait-for-state AVAILABLE --query 'data.id' --raw-output) || { echo "gateway create failed"; exit 1; }
  oci network route-table update --rt-id "$RT" --force \
    --route-rules "[{\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"networkEntityId\":\"$IGW\"}]" >/dev/null \
    || { echo "route update failed"; exit 1; }
  RULES='[{"source":"0.0.0.0/0","protocol":"6","tcpOptions":{"destinationPortRange":{"min":22,"max":22}}},
          {"source":"0.0.0.0/0","protocol":"6","tcpOptions":{"destinationPortRange":{"min":39740,"max":39740}}},
          {"source":"0.0.0.0/0","protocol":"6","tcpOptions":{"destinationPortRange":{"min":19740,"max":19740}}},
          {"source":"0.0.0.0/0","protocol":"1","icmpOptions":{"type":3,"code":4}},
          {"source":"10.0.0.0/16","protocol":"1","icmpOptions":{"type":3}}]'
  oci network security-list update --security-list-id "$SL" --force --ingress-security-rules "$RULES" >/dev/null \
    || { echo "firewall rule update failed"; exit 1; }
  SUB=$(oci network subnet create --compartment-id "$T" --vcn-id "$VCN" --cidr-block 10.0.0.0/24 --display-name camo-public \
        --dns-label public --wait-for-state AVAILABLE --query 'data.id' --raw-output) || { echo "subnet create failed"; exit 1; }
  echo "Network ready."
fi
echo "Image: $(oci compute image get --image-id "$IMG" --query 'data."display-name"' --raw-output 2>/dev/null)"
echo "Asking for $NAME ($DESC) in: $ADS. Retrying every ${WAIT}s; leave this window open (Ctrl-C to stop)."

n=0; NOSHAPE=""
while true; do
  tried=0; skipped=0
  for AD in $ADS; do
    case " $NOSHAPE " in *" $AD "*) continue ;; esac
    n=$((n+1)); tried=$((tried+1))
    set -- --shape "$SHAPE"; [ -n "$SHAPECFG" ] && set -- "$@" --shape-config "$SHAPECFG"
    OUT=$(oci compute instance launch --compartment-id "$T" --availability-domain "$AD" --display-name "$NAME" "$@" \
          --image-id "$IMG" --subnet-id "$SUB" --assign-public-ip true --ssh-authorized-keys-file "$KEY" \
          --wait-for-state RUNNING --query 'data.id' --raw-output 2>&1)
    if echo "$OUT" | grep -q '^ocid1.instance'; then
      ID=$(echo "$OUT" | grep '^ocid1.instance' | head -1)
      IP=$(oci compute instance list-vnics --instance-id "$ID" --query 'data[0]."public-ip"' --raw-output)
      echo; echo "SUCCESS after $n tries: $NAME is running in $AD. Public IP: $IP"; exit 0
    fi
    if echo "$OUT" | grep -qi 'capacity'; then
      echo "$(date '+%H:%M') try $n: $AD out of capacity"
    elif [ "$SHAPE" = VM.Standard.E2.1.Micro ] && echo "$OUT" | grep -q '"status": 400'; then
      echo "$(date '+%H:%M') try $n: $AD refused the micro server; skipping it from now on. Oracle said:"
      echo "$OUT" | grep -E '"(code|message)"' | sed 's/^ */    /'
      NOSHAPE="$NOSHAPE $AD"; skipped=$((skipped+1))
    elif echo "$OUT" | grep -qE '"status": 429|TooManyRequests'; then
      echo "$(date '+%H:%M') try $n: Oracle says slow down; pausing 5 minutes"; sleep 300
    else
      echo "$(date '+%H:%M') try $n: unexpected error, stopping. Oracle said:"
      echo "$OUT" | grep -E '"(code|message|status)"' | sed 's/^ */    /'; exit 1
    fi
  done
  [ "$tried" -eq "$skipped" ] && { echo "No availability domain offers $SHAPE here."; exit 1; }
  sleep "$WAIT"
done
