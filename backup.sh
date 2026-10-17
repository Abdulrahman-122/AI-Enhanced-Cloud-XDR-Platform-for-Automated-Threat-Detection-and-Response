#!/usr/bin/env bash
# Back up every PVC (VM disks and pod volumes) plus the manifests needed to rebuild them.
#
# Usage:  ./backup.sh [backup-root]             (default: ~/xdr-backups)
# Env:    NAMESPACES="xdr-server wazuh"         namespaces to back up
#         SKIP="xdr-volume"                     PVC names to leave out (golden image can be re-uploaded)
#         IMAGE=ubuntu:24.04                    helper-pod image (must have GNU tar)
#
# Per namespace: save manifests -> stop the VMs / scale pods to 0 (consistent disks)
#                -> copy each PVC into a .tar.gz -> start everything again.
# The backup folder contains Secrets (certificates, passwords): keep it private.
#
# Tip: pre-load the helper image so the nodes never have to pull it:
#   docker pull ubuntu:24.04 && kind load docker-image ubuntu:24.04 --name kind
set -euo pipefail

ROOT=${1:-$HOME/xdr-backups}
NAMESPACES=${NAMESPACES:-"xdr-server wazuh cdi default kubevirt"}
# you can add your namespaces
SKIP=${SKIP:-"xdr-volume"}
IMAGE=${IMAGE:-ubuntu:24.04}

command -v kubectl >/dev/null || { echo "kubectl not found" >&2; exit 1; }
command -v virtctl >/dev/null || { echo "virtctl not found" >&2; exit 1; }

DEST="$ROOT/$(date +%Y-%m-%d_%H%M)"
STATE_VMS="$DEST/.vms-were-running"
STATE_SCALE="$DEST/.replicas-before"
umask 077
mkdir -p "$DEST/pvc" "$DEST/vm" "$DEST/manifests"
: > "$DEST/pvcs.txt"

# ---------------------------------------------------------------- helpers
start_workloads() {
  if [ -f "$STATE_SCALE" ]; then
    while read -r ns obj reps; do
      kubectl scale "$obj" -n "$ns" --replicas="$reps" || true
    done < "$STATE_SCALE"
    rm -f "$STATE_SCALE"
  fi
  if [ -f "$STATE_VMS" ]; then
    while read -r ns vm; do
      virtctl start "$vm" -n "$ns" || true
    done < "$STATE_VMS"
    rm -f "$STATE_VMS"
  fi
}
trap start_workloads EXIT   # also runs if the script fails halfway, so nothing stays stopped

dump_manifests() {
  local ns=$1 kind
  mkdir -p "$DEST/manifests/$ns"
  for kind in svc sts deploy cm secret pvc networkpolicy vm dv; do
    kubectl get "$kind" -n "$ns" -o yaml > "$DEST/manifests/$ns/$kind.yaml" 2>/dev/null || true
  done
}

stop_workloads() {
  local ns=$1 vm obj reps
  for vm in $(kubectl get vm -n "$ns" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true); do
    # save the VM definition BEFORE stopping (stopping changes runStrategy)
    kubectl get vm "$vm" -n "$ns" -o json > "$DEST/vm/${ns}__${vm}.json"
    if kubectl get vmi "$vm" -n "$ns" >/dev/null 2>&1; then
      echo "$ns $vm" >> "$STATE_VMS"
      echo "stopping VM $ns/$vm ..."
      virtctl stop "$vm" -n "$ns"
      kubectl wait --for=delete "vmi/$vm" -n "$ns" --timeout=300s || true
    fi
  done
  for obj in $(kubectl get sts,deploy -n "$ns" -o name 2>/dev/null || true); do
    reps=$(kubectl get "$obj" -n "$ns" -o jsonpath='{.spec.replicas}')
    echo "$ns $obj $reps" >> "$STATE_SCALE"
    echo "scaling $ns/$obj to 0 ..."
    kubectl scale "$obj" -n "$ns" --replicas=0
  done
  kubectl wait --for=delete pod --all -n "$ns" --timeout=300s >/dev/null 2>&1 || true
}

backup_pvc() {
  local ns=$1 pvc=$2 out="$DEST/pvc/${1}__${2}.tar.gz"
  kubectl delete pod pvc-backup -n "$ns" --ignore-not-found --wait >/dev/null
  kubectl apply -n "$ns" -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: pvc-backup
spec:
  restartPolicy: Never
  containers:
  - name: tar
    image: ${IMAGE}
    command: ["sleep", "86400"]
    volumeMounts:
    - {name: data, mountPath: /data, readOnly: true}
  volumes:
  - name: data
    persistentVolumeClaim: {claimName: ${pvc}, readOnly: true}
EOF
  kubectl wait --for=condition=Ready pod/pvc-backup -n "$ns" --timeout=600s || {
    echo "helper pod not ready - see: kubectl describe pod pvc-backup -n $ns" >&2; exit 1; }
  # -S keeps sparse VM disk images small; --numeric-owner keeps the qemu/wazuh uids
  kubectl exec -n "$ns" pvc-backup -- tar -C /data --numeric-owner -cSzf - . > "$out"
  gzip -t "$out"
  kubectl delete pod pvc-backup -n "$ns" --wait >/dev/null
  kubectl get pvc "$pvc" -n "$ns" -o jsonpath='{.metadata.namespace}{"|"}{.metadata.name}{"|"}{.spec.resources.requests.storage}{"|"}{.spec.storageClassName}{"|"}{.spec.accessModes[0]}{"|"}{.spec.volumeMode}{"\n"}' >> "$DEST/pvcs.txt"
  echo "saved $(du -h "$out" | cut -f1)  $out"
}

# ---------------------------------------------------------------- main
kubectl get sc -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.provisioner}{"|"}{.volumeBindingMode}{"|"}{.allowVolumeExpansion}{"\n"}{end}' > "$DEST/storageclasses.txt"

for ns in $NAMESPACES; do
  if ! kubectl get ns "$ns" >/dev/null 2>&1; then echo "skip: namespace $ns not found"; continue; fi
  echo "=== namespace $ns ==="
  dump_manifests "$ns"
  stop_workloads "$ns"
  for pvc in $(kubectl get pvc -n "$ns" -o jsonpath='{range .items[?(@.status.phase=="Bound")]}{.metadata.name}{"\n"}{end}'); do
    case " $SKIP " in *" $pvc "*) echo "skip $ns/$pvc"; continue;; esac
    echo "backing up $ns/$pvc ..."
    backup_pvc "$ns" "$pvc"
  done
  start_workloads
done

echo
echo "Backup finished: $DEST ($(du -sh "$DEST" | cut -f1))"
echo "Copy it off this machine (external disk / NAS / cloud). It contains Secrets - keep it private."
