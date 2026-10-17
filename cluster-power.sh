#!/usr/bin/env bash
# Safely stop and later start a kind cluster without losing its data.
#
# Usage:  ./cluster-power.sh stop  [cluster-name]     (default cluster name: kind)
#         ./cluster-power.sh start [cluster-name]
# Env:    SCALE_NAMESPACES="wazuh"    namespaces whose pods are scaled to 0 before stopping
#
# stop : gracefully stops running VMs, scales those namespaces to 0, then stops the node containers
# start: starts the node containers, waits until the cluster is ready, scales back up, starts the VMs
#
# WARNING while stopped: never run `docker system prune` or `docker container prune`
# (they delete stopped containers = your cluster's nodes and all their data).
set -euo pipefail

ACTION=${1:?usage: $0 stop|start [cluster-name]}
CLUSTER=${2:-kind}
SCALE_NAMESPACES=${SCALE_NAMESPACES:-wazuh}
STATE="$HOME/.kind-${CLUSTER}-power-state"

NODES=$(docker ps -a --filter "label=io.x-k8s.kind.cluster=${CLUSTER}" --format '{{.Names}}')
[ -n "$NODES" ] || { echo "no kind nodes found for cluster '${CLUSTER}'" >&2; exit 1; }

case "$ACTION" in
stop)
  : > "$STATE"
  kubectl cluster-info >/dev/null 2>&1 || { echo "cluster not reachable - is it already stopped?" >&2; exit 1; }

  while read -r ns vm; do
    [ -n "$vm" ] || continue
    echo "vm $ns $vm" >> "$STATE"
    echo "stopping VM $ns/$vm ..."
    virtctl stop "$vm" -n "$ns"
    kubectl wait --for=delete "vmi/$vm" -n "$ns" --timeout=300s || true
  done < <(kubectl get vmi -A -o jsonpath='{range .items[*]}{.metadata.namespace}{" "}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)

  for ns in $SCALE_NAMESPACES; do
    kubectl get ns "$ns" >/dev/null 2>&1 || continue
    for obj in $(kubectl get sts,deploy -n "$ns" -o name 2>/dev/null || true); do
      reps=$(kubectl get "$obj" -n "$ns" -o jsonpath='{.spec.replicas}')
      echo "scale $ns $obj $reps" >> "$STATE"
      echo "scaling $ns/$obj to 0 ..."
      kubectl scale "$obj" -n "$ns" --replicas=0
    done
    kubectl wait --for=delete pod --all -n "$ns" --timeout=300s >/dev/null 2>&1 || true
  done

  echo "stopping node containers ..."
  # shellcheck disable=SC2086
  docker stop -t 120 $NODES
  echo "Cluster '${CLUSTER}' stopped. Data is kept inside the node containers."
  echo "Start it again with: $0 start ${CLUSTER}"
  ;;

start)
  echo "starting node containers (control plane first) ..."
  # shellcheck disable=SC2086
  docker start $(echo "$NODES" | grep control-plane || true)
  for n in $(echo "$NODES" | grep -v control-plane || true); do docker start "$n"; done

  # the API server's host port can change after a restart
  command -v kind >/dev/null && kind export kubeconfig --name "$CLUSTER" >/dev/null 2>&1 || true

  echo "waiting for the API server ..."
  for _ in $(seq 1 60); do kubectl get nodes >/dev/null 2>&1 && break; sleep 5; done
  kubectl wait --for=condition=Ready node --all --timeout=900s
  kubectl wait kv/kubevirt -n kubevirt --for=condition=Available --timeout=900s || true

  if [ -f "$STATE" ]; then
    while read -r kind a b c; do
      case "$kind" in
        scale) kubectl scale "$b" -n "$a" --replicas="$c" || true ;;
      esac
    done < "$STATE"
    while read -r kind a b c; do
      case "$kind" in
        vm) echo "starting VM $a/$b ..."; virtctl start "$b" -n "$a" || true ;;
      esac
    done < "$STATE"
  else
    echo "no saved state found: start VMs yourself with: virtctl start <vm> -n <namespace>"
  fi
  echo
  kubectl get nodes -o wide
  echo "Node IPs can change after a restart: re-check them before using SSH NodePorts."
  ;;

*)
  echo "usage: $0 stop|start [cluster-name]" >&2
  exit 1
  ;;
esac
