#!/usr/bin/env bash
# Restore PVC data and VM definitions from a backup made by backup.sh.
#
# Usage:  ./restore.sh <backup-dir>
# Env:    RUN=Halted|Always       VM start mode (default Halted: start them one by one, RAM is limited)
#         SC_OVERRIDE=<class>     use this StorageClass instead of the one recorded in the backup
#         IMAGE=ubuntu:24.04      helper-pod image (must have GNU tar)
#
# Run it on a cluster that already has: the storage driver, KubeVirt and CDI.
# It recreates the namespaces and PVCs (same names), unpacks the data, and re-creates each VM
# pointing straight at its restored PVCs. Pod workloads (Wazuh) are re-applied by you afterwards.
set -euo pipefail

BK=${1:?usage: $0 <backup-dir>}
RUN=${RUN:-Halted}
IMAGE=${IMAGE:-ubuntu:24.04}

[ -f "$BK/pvcs.txt" ] || { echo "not a backup folder: $BK" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is needed to rewrite the VM definitions" >&2; exit 1; }

ensure_sc() {
  local sc=$1 line prov bind exp
  kubectl get sc "$sc" >/dev/null 2>&1 && return 0
  line=$(awk -F'|' -v n="$sc" '$1==n' "$BK/storageclasses.txt")
  if [ -z "$line" ]; then
    echo "StorageClass '$sc' is missing and not recorded in the backup: create it or set SC_OVERRIDE" >&2
    return 1
  fi
  IFS='|' read -r _ prov bind exp <<< "$line"
  echo "creating StorageClass $sc ($prov)"
  kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ${sc}
provisioner: ${prov}
volumeBindingMode: ${bind:-WaitForFirstConsumer}
allowVolumeExpansion: ${exp:-false}
EOF
}

# ---- namespaces
for ns in $(cut -d'|' -f1 "$BK/pvcs.txt" | sort -u); do
  kubectl create ns "$ns" --dry-run=client -o yaml | kubectl apply -f -
done

# ---- PVCs + data
while IFS='|' read -r ns name size sc mode vmode <&3; do
  file="$BK/pvc/${ns}__${name}.tar.gz"
  [ -f "$file" ] || { echo "missing $file - skipping"; continue; }
  sc=${SC_OVERRIDE:-$sc}
  ensure_sc "$sc"
  echo "=== restoring $ns/$name ($size, $sc) ==="
  kubectl apply -n "$ns" -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${name}
spec:
  accessModes: ["${mode}"]
  volumeMode: ${vmode:-Filesystem}
  storageClassName: ${sc}
  resources:
    requests:
      storage: ${size}
EOF
  kubectl delete pod pvc-restore -n "$ns" --ignore-not-found --wait >/dev/null
  kubectl apply -n "$ns" -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: pvc-restore
spec:
  restartPolicy: Never
  containers:
  - name: tar
    image: ${IMAGE}
    command: ["sleep", "86400"]
    volumeMounts:
    - {name: data, mountPath: /data}
  volumes:
  - name: data
    persistentVolumeClaim: {claimName: ${name}}
EOF
  kubectl wait --for=condition=Ready pod/pvc-restore -n "$ns" --timeout=600s || {
    echo "helper pod not ready - see: kubectl describe pod pvc-restore -n $ns  (storage driver installed?)" >&2; exit 1; }
  kubectl exec -i -n "$ns" pvc-restore -- tar -C /data --numeric-owner -xzf - < "$file"
  kubectl exec -n "$ns" pvc-restore -- sync || true
  kubectl delete pod pvc-restore -n "$ns" --wait >/dev/null
done 3< "$BK/pvcs.txt"

# ---- VMs: same spec, but disks point at the restored PVCs instead of DataVolume templates
for f in "$BK"/vm/*.json; do
  [ -e "$f" ] || continue
  echo "=== recreating VM from $(basename "$f") (runStrategy: $RUN) ==="
  python3 - "$f" "$RUN" <<'PY' | kubectl apply -f -
import json, sys
vm = json.load(open(sys.argv[1]))
md = vm["metadata"]
vm["metadata"] = {"name": md["name"], "namespace": md["namespace"]}
vm.pop("status", None)
spec = vm["spec"]
spec.pop("dataVolumeTemplates", None)
spec.pop("running", None)
spec["runStrategy"] = sys.argv[2]
for v in spec["template"]["spec"]["volumes"]:
    if "dataVolume" in v:
        v["persistentVolumeClaim"] = {"claimName": v.pop("dataVolume")["name"]}
print(json.dumps(vm))
PY
done

cat <<'MSG'

Restore finished. Next:
  * VMs:    kubectl get vm -A ; start them one by one:  virtctl start <vm> -n <namespace>
  * Services for the VMs (SSH NodePorts) are not restored here: re-apply your own YAML files.
  * Wazuh (pods): from your wazuh-kubernetes clone (with its generated certs) run
        kubectl apply -k envs/local-env/
    The StatefulSets reuse the restored PVCs because the names match.
    If it complains about the StorageClass, delete it first (bound PVCs are not affected):
        kubectl delete sc <name-from-error>
  * The golden image (xdr-volume) is not in the backup: re-upload it with virtctl image-upload
    when you want to create NEW VMs.
MSG
