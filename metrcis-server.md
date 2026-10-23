Step 1: Check the cluster
```yml
kind get clusters
kubectl config current-context
kubectl get nodes -o wide
```
The context should look like kind-<cluster-name>. Your node names (xdr-cluster-worker, xdr-cluster-worker2) suggest the cluster is named xdr-cluster.

Step 2: Install the Metrics Server
```yml
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```
This creates a Deployment in kube-system, a ServiceAccount, RBAC rules, and an APIService named v1beta1.metrics.k8s.io.

It will probably not work yet. On kind, the kubelets use self-signed certificates, so the Metrics Server can’t verify them. You need one flag.

Step 3: Patch it for kind

Check the current arguments first so you don’t add a duplicate flag, which can stop the container from starting:

```yml
kubectl -n kube-system get deployment metrics-server \
  -o jsonpath='{.spec.template.spec.containers[0].args}{"\n"}'
```
If --kubelet-insecure-tls isn’t in the output, add it:

```yml
kubectl -n kube-system patch deployment metrics-server --type=json -p='[
  {"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}
]'
```
Optionally, tell it to use node IPs, which avoids DNS lookups for node names:
```yml
kubectl -n kube-system patch deployment metrics-server --type=json -p='[
  {"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname"}
]'
```
--kubelet-insecure-tls skips certificate verification, which is fine for a local lab. Don’t use it in production.

Wait for the rollout:

```yml
kubectl -n kube-system rollout status deployment/metrics-server
```
Step 4: Verify

Give it about a minute to collect its first scrape, then run:

```yml
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl top pods -A
```
AVAILABLE should be True on the APIService, and kubectl top should show CPU and memory values. If kubectl top says “metrics not available yet,” wait another minute.

Step 5: Troubleshoot if needed
```yml
kubectl -n kube-system logs deployment/metrics-server
kubectl describe apiservice v1beta1.metrics.k8s.io
```
Common errors:
```yml
Error in logs	Fix
x509: certificate signed by unknown authority	Add --kubelet-insecure-tls (Step 3)
no such host for a node name	Add --kubelet-preferred-address-types=InternalIP
Failed to scrape node ... connection refused	Check that the kubelets are healthy with kubectl get nodes
APIService AVAILABLE: False	Usually a delay of a minute or two, or one of the errors above
```
Step 6: Prove it works with autoscaling

This test shows the metrics are real, because the autoscaler uses them to make decisions.
```yml
Create a deployment with CPU requests (HPA needs them):

bash
kubectl create deployment php-apache --image=registry.k8s.io/hpa-example --port=80
kubectl set resources deployment php-apache --requests=cpu=200m --limits=cpu=500m
kubectl expose deployment php-apache --port=80
kubectl autoscale deployment php-apache --cpu-percent=50 --min=1 --max=5
kubectl get hpa -w

In a second terminal, generate load:

bash
kubectl run load-generator --rm -it --image=busybox:1.36 --restart=Never -- \
  /bin/sh -c "while true; do wget -q -O- http://php-apache; done"

Watch the HPA’s TARGETS column rise, and the replica count increase. Stop the load with Ctrl+C, and the replicas will drop back after a few minutes.

Clean up:

bash
kubectl delete hpa php-apache
kubectl delete svc php-apache
kubectl delete deployment php-apache
```
link: https://artifacthub.io/packages/helm/metrics-server/metrics-server
