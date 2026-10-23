# install wazuh v.4.14.8 on our cluster 

```
- clone the repo
git clone --branch v4.14.8 --depth 1 \
  https://github.com/wazuh/wazuh-kubernetes.git \
  wazuh-kubernetes-4.14.8

cd ~/wazuh-kubernetes-4.14.8

- switch to the version of this repo
git describe --tags --exact-match
ls
ls envs/local-env/

```
```
- generate the certs
bash wazuh/certs/indexer_cluster/generate_certs.sh
bash wazuh/certs/dashboard_http/generate_certs.sh
- check that the certs are generated
ls -lh wazuh/certs/indexer_cluster/
ls -lh wazuh/certs/dashboard_http/

```
```
- check the storageclass
nano envs/local-env/storage-class.yaml
then change the contents
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: wazuh-storage

provisioner: rancher.io/local-path
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
-apply it
kubectl apply -f envs/local-env/storage-class.yaml

- save the kustomization.yaml in order to check our work whether it's work or not
kubectl kustomize envs/local-env/ > /tmp/wazuh-4.14.8.yaml
#now check the file contain the appropriate images or not
grep -n 'image:' /tmp/wazuh-4.14.8.yaml
grep -n 'kind: StorageClass' /tmp/wazuh-4.14.8.yaml
#check the nodes
kubectl get nodes
#check the storageclass
kubectl get sc
```
```
#now deploy the validations
kubectl apply -k envs/local-env/
-now install dynmic provisoning local-path in order to install controller that will watch our needs of storage and then it will provision new pv on the disk that contain the node
kubectl apply -f \
  https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.37/deploy/local-path-storage.yaml
-now check the status of this provisioner
kubectl rollout status deployment/local-path-provisioner \
  -n local-path-storage --timeout=120s
- now check 
kubectl get pods -n local-path-storage
kubectl get sc wazuh-storage
kubectl get pvc -n wazuh

- check the logs
kubectl logs -n local-path-storage \
  deployment/local-path-provisioner --tail=100

kubectl describe pvc -n wazuh wazuh-indexer-wazuh-indexer-0
 
```
- to understand how the process of our provisioning a new storage works?
-  <img width="825" height="725" alt="image" src="https://github.com/user-attachments/assets/4343fcfe-895a-4663-92cf-cdce1ff0863b" />
- the output :
  -<img width="954" height="169" alt="image" src="https://github.com/user-attachments/assets/2e185473-14a4-4b3f-8bcf-48e1323a8a02" />
  - <img width="861" height="90" alt="image" src="https://github.com/user-attachments/assets/1b5f6304-99cc-4a97-8979-01afa4b3f668" />

- note
```
- don't try to delete local-path-provisioner from your cluster as if your delete it -> your wazuh stuff can't extend the current storage (it's a dynamic storage provisioner for your pods..... )

```
- https://github.com/rancher/local-path-provisioner

```
- if you got API connection error("Error: getaddrinfo EBUSY wazuh-manager-master-0.wazuh-cluster) probably the problem due to : some configmaps,secrets that you didn't do yet
1. Check what exists

bash
kubectl -n wazuh get configmap
kubectl -n wazuh get secret

Look for wazuh-conf, indexer-certs, wazuh-authd-pass, indexer-cred, wazuh-api-cred, and wazuh-cluster-key. Your pod references all of them.

2. Create the missing configmap

The config volume mounts master.conf from wazuh-conf. Your wazuh-master-sts.yml should define this, so check whether it’s in the repo:

bash
grep -rn "wazuh-conf" ~/path/to/wazuh_managers/

If it exists in your files, apply it first:

bash
kubectl -n wazuh apply -f <file-with-configmap>.yaml

If you don’t have it, create it from your master.conf (the manager’s ossec.conf):

bash
kubectl -n wazuh create configmap wazuh-conf --from-file=master.conf=./master.conf

3. Create the indexer certificates secret

indexer-certs must contain root-ca.pem, filebeat.pem, and filebeat-key.pem. Those are the keys the pod mounts, using these exact names. If the certs were generated for the indexer earlier, reuse them:

bash
kubectl -n wazuh create secret generic indexer-certs \
  --from-file=root-ca.pem=./root-ca.pem \
  --from-file=filebeat.pem=./filebeat.pem \
  --from-file=filebeat-key.pem=./filebeat-key.pem

4. Confirm the other secrets exist

If indexer-cred, wazuh-api-cred, wazuh-cluster-key, or wazuh-authd-pass are missing, the pod will fail the same way. Create each one with kubectl create secret generic <name> --from-literal=<key>=<value>, using the key names from the describe output (username, password, key).

5. Restart the StatefulSets

bash
kubectl -n wazuh delete pod wazuh-manager-master-0 wazuh-manager-worker-1
kubectl -n wazuh get pods -w

Once the master reaches Running and 1/1 Ready, the DNS name wazuh-manager-master-0.wazuh-cluster resolves, and the dashboard’s EBUSY error should stop.
```
