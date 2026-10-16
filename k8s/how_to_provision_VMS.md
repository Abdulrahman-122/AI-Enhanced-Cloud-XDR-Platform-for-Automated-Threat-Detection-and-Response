# How to create VMs on k8s cluster using Kubevirt???
- <img width="866" height="1016" alt="image" src="https://github.com/user-attachments/assets/7bcc7a0c-90e9-45bc-9edd-c027f4195ce0" />
- <img width="1166" height="876" alt="image" src="https://github.com/user-attachments/assets/c85e71b5-4d4c-4960-84da-708f4f540dbd" />

- create the cluster: kind-config.yaml
```
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
  extraMounts:
  - hostPath: /home/YOU/kind-data      # real folder on your machine
    containerPath: /var/lib/csi-hostpath-data

---
mkdir -p ~/kind-data
#run the cluster
kind create cluster --name lab --config kind-config.yaml
#install CRDs+controller,CSI driver
git clone https://github.com/kubernetes-csi/external-snapshotter.git
cd external-snapshotter
kubectl kustomize client/config/crd | kubectl create -f -
kubectl -n kube-system kustomize deploy/kubernetes/snapshot-controller | kubectl create -f -
cd ..

# the CSI driver
git clone https://github.com/kubernetes-csi/csi-driver-host-path.git
cd csi-driver-host-path
./deploy/kubernetes-latest/deploy.sh
kubectl apply -f examples/csi-storageclass.yaml       # creates csi-hostpath-sc
#install CDI(containerized data importer)
export VERSION=$(basename $(curl -s -w %{redirect_url} https://github.com/kubevirt/containerized-data-importer/releases/latest))
kubectl apply -f https://github.com/kubevirt/containerized-data-importer/releases/download/$VERSION/cdi-operator.yaml
kubectl apply -f https://github.com/kubevirt/containerized-data-importer/releases/download/$VERSION/cdi-cr.yaml
kubectl get cdi -n cdi        # wait for Deployed
#or go here and build it
https://kubevirt.io/labs/kubernetes/lab2.html
#create the kubevirt crd
export VERSION=$(curl -s https://storage.googleapis.com/kubevirt-prow/release/kubevirt/kubevirt/stable.txt)
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/${VERSION}/kubevirt-operator.yaml
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/${VERSION}/kubevirt-cr.yaml
kubectl -n kubevirt wait kv kubevirt --for condition=Available --timeout=15m

---
. Get the Ubuntu image once and reuse it (“golden image”)

Option A: import from URL (easiest).

yaml
# nano ubuntu-base.yaml
apiVersion: cdi.kubevirt.io/v1beta1
kind: DataVolume
metadata:
  name: ubuntu-2204-base
spec:
  source:
    http:
      url: https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img
  storage:
    storageClassName: csi-hostpath-sc
    resources:
      requests:
        storage: 10Gi

---
kubectl apply -f ubuntu-base.yaml
kubectl get dv -w            # until Succeeded

Option B: upload a local file.
- to know the size of the image in order to append to it's pvc enough storage
qemu-img info /home/abdo/studying/Grad_projects/The_Full_Project/k8s/images/ubuntu/ubuntu-24.04-server-cloudimg-amd64.img | grep -i "virtual size"
output: virtual size: 3.5 GiB (3758096384 bytes)

3. Make sure the proxy forward is running

--uploadproxy-url=https://127.0.0.1:18443 needs a live port-forward, and your earlier background job may have died:


kubectl port-forward -n cdi svc/cdi-uploadproxy 18443:443 &
4. Corrected upload

virtctl image-upload dv xdr-volume -n xdr-server \
  --image-path="/home/abdo/studying/Grad_projects/The_Full_Project/k8s/images/ubuntu/ubuntu-24.04-server-cloudimg-amd64.img" \
  --size=5Gi \
  --storage-class=csi-hostpath-sc \
  --access-mode=ReadWriteOnce \
  --volume-mode=filesystem \
  --uploadproxy-url=https://127.0.0.1:18443 \
  --insecure
5. Use it for new VMs
bash
BASE=xdr-volume ./new-vm.sh vm3 1 1 8 2            #new-vm.sh (under the first vm1)

```
- this is what we need:
- <img width="742" height="68" alt="image" src="https://github.com/user-attachments/assets/e4d4fe2e-e1e1-44c0-ae64-3de33b3d084d" />
- <img width="922" height="154" alt="image" src="https://github.com/user-attachments/assets/5e2a68f2-1a9f-4be0-b53c-d64c3a5108c0" />

---
# Writing your first VM
```
Since you know YAML, here is every block with its purpose:

yaml
# vm1.yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: wazuh
  namespace: xdr-server
spec:
  runStrategy: Always
  dataVolumeTemplates:
  - metadata:
      name: wazuh-root
    spec:
      storage:
        storageClassName: csi-hostpath-sc
        accessModes: ["ReadWriteOnce"]
        volumeMode: Filesystem
        resources:
          requests:
            storage: 12Gi          # must be >= the golden image PVC (xdr-volume, 5Gi); Wazuh packages need room
      source:
        pvc:                       # clone the golden Ubuntu image
          name: xdr-volume
          namespace: xdr-server
  - metadata:
      name: wazuh-data
    spec:
      storage:
        storageClassName: csi-hostpath-sc
        accessModes: ["ReadWriteOnce"]
        volumeMode: Filesystem
        resources:
          requests:
            storage: 20Gi          # Wazuh indexer data grows; 3Gi fills up fast
      source:
        blank: {}
  template:
    metadata:
      labels:
        app: wazuh
    spec:
      domain:
        cpu:
          cores: 2
        memory:
          guest: 4Gi
        resources:
          requests:
            cpu: "1"
            memory: 4500Mi         # guest 4Gi + ~400Mi QEMU overhead
          limits:
            cpu: "2"
            memory: 4500Mi
        devices:
          disks:
          - name: rootdisk
            disk: {bus: virtio}
          - name: datadisk
            serial: appdata01
            disk: {bus: virtio}
          - name: cloudinit
            disk: {bus: virtio}
          interfaces:
          - name: default
            masquerade: {}
      networks:
      - name: default
        pod: {}
      volumes:
      - name: rootdisk
        dataVolume: {name: wazuh-root}
      - name: datadisk
        dataVolume: {name: wazuh-data}
      - name: cloudinit
        cloudInitNoCloud:
          networkData: |
            version: 2
            ethernets:
              all-en:
                match:
                  name: "en*"
                dhcp4: true
          userData: |
            #cloud-config
            hostname: wazuh
            user: adam
            password: adam
            chpasswd: {expire: false}
            ssh_pwauth: true
            packages:
              - qemu-guest-agent
            runcmd:
              - systemctl enable --now qemu-guest-agent
              - blkid /dev/disk/by-id/virtio-appdata01 || mkfs.ext4 -L appdata /dev/disk/by-id/virtio-appdata01
              - mkdir -p /data
              - echo 'LABEL=appdata /data ext4 defaults,nofail 0 2' >> /etc/fstab
              - mount -a
---
apiVersion: v1
kind: Service
metadata:
  name: wazuh-ssh
  namespace: xdr-server
spec:
  type: NodePort
  selector:
    app: wazuh
  ports:
  - name: ssh
    port: 22
    targetPort: 22
    nodePort: 30024
---
apiVersion: v1
kind: Service
metadata:
  name: wazuh
  namespace: xdr-server
spec:
  selector:
    app: wazuh
  ports:
  - {name: events, port: 1514, targetPort: 1514}
  - {name: enroll, port: 1515, targetPort: 1515}
  - {name: api, port: 55000, targetPort: 55000}
  - {name: dashboard, port: 443, targetPort: 443}
---
kubectl apply -f vm1.yaml
kubectl get vm,vmi,dv,pvc
virtctl console vm1          # exit with Ctrl+]
virtctl ssh ubuntu@vm1       # or use the pod IP from `kubectl get vmi`

---
virtctl stop vm1
virtctl start vm1
virtctl restart vm1



```

- Commands you should know
```
k get sc       #find the storageclass
kubectl get vm,vmi,dv,pvc         #vmi->virtual machine instance,dv ->data volume
kubectl get vm,dv,pvc -A | grep -E 'vm1|NAME'                #search for specific name in vm,dv,pvc->persistent volume claim
kubectl describe dv  name  -n xdr-server
kubectl get events -n xdr-server --sort-by=.lastTimestamp | tail -20
kubectl delete vm name-of-virtualmachine -n default
#in case you found a problem related to accessMode,volumeMode in the sci driver plugin do
kubectl patch storageprofile csi-hostpath-sc --type=merge \
  -p '{"spec":{"claimPropertySets":[{"accessModes":["ReadWriteOnce"],"volumeMode":"Filesystem"}]}}'

kubectl get storageprofile csi-hostpath-sc -o yaml | grep -A4 claimPropertySets

#find specific pods from the whole pods
kubectl get pods -A | grep -E 'csi|snapshot'
#to describe a specific plugin,see it's logs..
kubectl describe pod csi-hostpathplugin-0 -n <ns> | tail -20
kubectl logs csi-hostpathplugin-0 -n <ns> -c hostpath --tail=40
kubectl logs csi-hostpathplugin-0 -n <ns> -c csi-provisioner --tail=40

#to see the volumessnapshot,...(related to snapshots)
kubectl get volumesnapshot,volumesnapshotcontent -A
#to ssh into a vm (the best choice)
1. Give the VM a permanent SSH endpoint

This Service selects the VM’s pod through its app: vm1 label, and fixes the port so it never changes:

yaml
# vm1-ssh-svc.yaml
apiVersion: v1
kind: Service
metadata:
  name: vm1-ssh
  namespace: xdr-server
spec:
  type: NodePort
  selector:
    app: vm1
  ports:
  - name: ssh
    port: 22
    targetPort: 22
    nodePort: 30022
bash
kubectl apply -f vm1-ssh-svc.yaml
kubectl get nodes -o wide        # note an INTERNAL-IP, e.g. 172.18.0.3

Kind nodes are Docker containers, and on Linux your Arch host can reach their IPs directly, so this works with no cluster rebuild:

bash
ssh -p 30022 adam@172.18.0.3     # use your node's INTERNAL-IP
2. Switch to SSH keys

Passwords on a reachable port are a bad idea (adam/adam especially).

bash
ssh-keygen -t ed25519 -f ~/.ssh/vm_ed25519
ssh-copy-id -i ~/.ssh/vm_ed25519.pub -p 30022 adam@172.18.0.3

Then, inside the VM, turn off passwords. Ubuntu reads the sshd_config.d files in order and uses the first value it finds, so a 10- file beats the cloud-init one:

bash
echo 'PasswordAuthentication no' | sudo tee /etc/ssh/sshd_config.d/10-keys-only.conf
sudo systemctl restart ssh

Test a new key login from a second terminal before closing your current session. Then add a shortcut in ~/.ssh/config on Arch:

Host vm1
  HostName 172.18.0.3
  Port 30022
  User adam
  IdentityFile ~/.ssh/vm_ed25519
```
#script for provisioning a new vm
```
#!/usr/bin/env bash
# Usage: ./new-vm.sh <name> [cpu] [mem_gi] [root_gi] [data_gi]
# Example: ./new-vm.sh vm3 4 4 30 10
# Generates <name>.yaml (kept so you can edit/re-apply later) and applies it.
set -euo pipefail

NAME=${1:?usage: ./new-vm.sh <name> [cpu] [mem_gi] [root_gi] [data_gi]}
CPU=${2:-2}
MEM_GI=${3:-2}
ROOT_GI=${4:-20}
DATA_GI=${5:-5}

NS=${NS:-xdr-server}
BASE=${BASE:-vm1}                 # golden image PVC (change to ubuntu-2404-base if you rename it)
SC=${SC:-csi-hostpath-sc}
MEM_REQ=$((MEM_GI * 1024 + 300))Mi   # guest RAM + QEMU overhead

cat > "${NAME}.yaml" <<EOF
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: ${NAME}
  namespace: ${NS}
spec:
  runStrategy: Always
  dataVolumeTemplates:
  - metadata:
      name: ${NAME}-root
    spec:
      storage:
        storageClassName: ${SC}
        accessModes: ["ReadWriteOnce"]
        volumeMode: Filesystem
        resources:
          requests:
            storage: ${ROOT_GI}Gi
      source:
        pvc:
          name: ${BASE}
          namespace: ${NS}
  - metadata:
      name: ${NAME}-data
    spec:
      storage:
        storageClassName: ${SC}
        accessModes: ["ReadWriteOnce"]
        volumeMode: Filesystem
        resources:
          requests:
            storage: ${DATA_GI}Gi
      source:
        blank: {}
  template:
    metadata:
      labels:
        app: ${NAME}
    spec:
      domain:
        cpu:
          cores: ${CPU}
        memory:
          guest: ${MEM_GI}Gi
        resources:
          requests:
            cpu: "${CPU}"
            memory: ${MEM_REQ}
          limits:
            cpu: "${CPU}"
            memory: ${MEM_REQ}
        devices:
          disks:
          - name: rootdisk
            disk: {bus: virtio}
          - name: datadisk
            serial: appdata01
            disk: {bus: virtio}
          - name: cloudinit
            disk: {bus: virtio}
          interfaces:
          - name: default
            masquerade: {}
      networks:
      - name: default
        pod: {}
      volumes:
      - name: rootdisk
        dataVolume: {name: ${NAME}-root}
      - name: datadisk
        dataVolume: {name: ${NAME}-data}
      - name: cloudinit
        cloudInitNoCloud:
          userData: |
            #cloud-config
            hostname: ${NAME}
            user: adam
            password: adam
            chpasswd: {expire: false}
            ssh_pwauth: true
            packages:
              - qemu-guest-agent
            runcmd:
              - systemctl enable --now qemu-guest-agent
              - blkid /dev/disk/by-id/virtio-appdata01 || mkfs.ext4 -L appdata /dev/disk/by-id/virtio-appdata01
              - mkdir -p /data
              - echo 'LABEL=appdata /data ext4 defaults,nofail 0 2' >> /etc/fstab
              - mount -a
EOF

kubectl apply -f "${NAME}.yaml"
echo
echo "Watch:   kubectl get vm,vmi,dv,pvc -n ${NS} -w"
echo "Console: virtctl console ${NAME} -n ${NS}   (login adam/adam, exit Ctrl+])"
```

---
# some debugging for some ideas
```
rootdisk -> this is the / device that contain all of the system (it hold /etc,/var...)
datadisk -> contain data related to data of the systems that doesn't belong to rootdisk
cloudinit -> it's a tool used to build vm from cloud image
chpasswd: {expire: false}      => this will assumes that the password isn't used for registration
ssh_pwauth: true =>authenticate over ssh
#start qemu-guest-agent(in order to provision the vm from the pod look at here ;https://kubevirt.io/user-guide/architecture/architecture/
#build a Filesystem for disks, and mount them
- systemctl enable --now qemu-guest-agent
- blkid /dev/disk/by-id/virtio-appdata01 || mkfs.ext4 -L appdata /dev/disk/by-id/virtio-appdata01
- mkdir -p /data
- echo 'LABEL=appdata /data ext4 defaults,nofail 0 2' >> /etc/fstab
- mount -a
---
if you wanted to increase the resources over a vm

# does the storage class allow it?
kubectl get sc csi-hostpath-sc -o jsonpath='{.allowVolumeExpansion}{"\n"}'

kubectl patch pvc vm1-data -n xdr-server --type=merge \
  -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'

virtctl restart vm1 -n xdr-server
# inside the VM:
lsblk
sudo resize2fs /dev/disk/by-id/virtio-appdata01        #this will build new filesystem for that incremented storage
df -h /data
```
  ## Backup vs snapshots
- <img width="785" height="251" alt="image" src="https://github.com/user-attachments/assets/e3422262-bb90-46a7-af77-2904cec96df6" />
```
#how to backup a vm on your system
virtctl vmexport download vm1-export -n xdr-server \
  --snapshot=vm1-snap1 --output=vm1-snap1.img.gz --port-forward
for snapshots:
- create snapshot from the vm
---

kubectl apply -f - <<EOF
apiVersion: snapshot.kubevirt.io/v1beta1
kind: VirtualMachineSnapshot
metadata:
  name: vm1-snap-test
  namespace: xdr-server
spec:
  failureDeadline: 1h
  source:
    apiGroup: kubevirt.io
    kind: VirtualMachine
    name: vm1
EOF

kubectl get vmsnapshot,volumesnapshot,volumesnapshotcontent -n xdr-server -w
```
- take care
  - <img width="758" height="201" alt="image" src="https://github.com/user-attachments/assets/290bc6d9-d7df-4fa1-beb6-938a30a5cb9c" />

# if you got a failed response when you want to get a snapshot out of vm do the following to solve the problem

```
#make sure that you closed the machine
virtctl stop vm -n namespace
Add the line in two containers in that block, csi-provisioner and csi-snapshotter. Under args: of each, add - --timeout=30m:

yaml
      - args:
        - -v=5
        - --csi-address=/csi/csi.sock
        - --feature-gates=Topology=true
        - --timeout=30m                      # add this
        image: registry.k8s.io/sig-storage/csi-provisioner:v6.3.0
        imagePullPolicy: IfNotPresent
        name: csi-provisioner
yaml
      - args:
        - -v=5
        - --csi-address=/csi/csi.sock
        - --timeout=30m                      # add this
        image: registry.k8s.io/sig-storage/csi-snapshotter:v8.6.0
        imagePullPolicy: IfNotPresent
        name: csi-snapshotter

Leave csi-attacher and csi-resizer alone.

#then delete the snapshot that you created and then
kubectl delete vmsnapshot vm1-snap -n xdr-server
#and provision it again
kubectl apply -f - <<EOF
apiVersion: snapshot.kubevirt.io/v1beta1
kind: VirtualMachineSnapshot
metadata:
  name: vm1-snap-test
  namespace: xdr-server
spec:
  failureDeadline: 1h
  source:
    apiGroup: kubevirt.io
    kind: VirtualMachine
    name: vm1
EOF

#if you wanted to provision a volumesnapshot and the deletiion hangs up
kubectl patch volumesnapshot vmsnapshot-f7a534d2-c8d6-4f5b-83df-1ab6350c5da4-volume-rootdisk \
  -n xdr-server --type=merge -p '{"metadata":{"finalizers":null}}'
#then delete it
kubectl delete vmsnapshot vm1-snap -n xdr-server
kubectl delete pod csi-hostpathplugin-0 -n default

--
to restore the snapshot on your system from the snapshot that you created
kubectl get vmrestore -n xdr-server -w      # wait for COMPLETE=true
kubectl get pvc -n xdr-server
#to delete an old pvc  (first check it's dv is removed first then do this job)
kubectl delete pvc restore-1ed9c1dd-fcc4-4fd7-9628-50a2afe49404-rootdisk \
                   restore-1ed9c1dd-fcc4-4fd7-9628-50a2afe49404-datadisk -n xdr-server

```
#for ssh problem (can't reach host(vm)
```
#go to vm and see the ip if you didn't see any ip for  it then this is a problem
virtctl console vm-name

ip a

#check some things in order to see the problem from where
ip link show enp1s0                 # note the MAC: c6:ce:79:1e:10:63
cat /etc/netplan/*.yaml             # look for a "macaddress:" line
networkctl
cloud-init status --long
journalctl -u systemd-networkd -b --no-pager | tail -20
If the macaddress: in the netplan file is different from the one ip link shows, that is the cause.
cat > /etc/netplan/50-cloud-init.yaml <<'EOF'
network:
  version: 2
  ethernets:
    all-en:
      match:
        name: "en*"
      dhcp4: true
EOF
chmod 600 /etc/netplan/50-cloud-init.yaml
netplan apply
ip a show enp1s0
#now you must see an ip
#you can even make that ip permenant by disable cloud-init from rewriting it
echo 'network: {config: disabled}' > /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg

#Done
```
---
# How to install xdr
```
1. Install Wazuh inside the VM

ssh -p 30024 adam@172.19.0.6        # your node IP; or: virtctl console wazuh -n xdr-server

Wazuh’s quickstart installs the server, indexer and dashboard on one host with its installation assistant, using the 4.14 script. 
wazuh


curl -sO https://packages.wazuh.com/4.14/wazuh-install.sh
sudo bash ./wazuh-install.sh -a 2>&1 | tee ~/wazuh-install.log

Use the 4.14 line. Wazuh 5.0 appears only as beta and release-candidate builds in the docs I found, so I wouldn’t use it for a project you need to be stable. It can take 10+ minutes. Watch free -h in a second session, and if a service fails to start, sudo journalctl -u wazuh-indexer -b | tail -30 shows whether it ran out of memory.

At the end, the installer prints the credentials and confirms success, and the passwords for the indexer and API users are in a file inside wazuh-install-files.tar. 
wazuh


sudo tar -O -xvf wazuh-install-files.tar wazuh-install-files/wazuh-passwords.txt
sudo systemctl status wazuh-manager wazuh-indexer wazuh-dashboard filebeat --no-pager

Copy wazuh-install-files.tar out of the VM and keep it. It holds the certificates and passwords, and you need them later:


sudo cp ~/wazuh-install-files.tar /tmp/ && sudo chmod 644 /tmp/wazuh-install-files.tar
scp -P 30024 adam@172.19.0.6:/tmp/wazuh-install-files.tar .
2. Right after install
Stop accidental upgrades. Wazuh recommends disabling its package repositories after installation so updates don’t break the setup. On Ubuntu: sudo sed -i 's/^deb/#deb/' /etc/apt/sources.list.d/wazuh.list && sudo apt update. 
wazuh
Cap the indexer’s memory. Check /etc/wazuh-indexer/jvm.options for -Xms and -Xmx. With a 4Gi VM, 1g to 2g each is right (never more than half the RAM), then sudo systemctl restart wazuh-indexer.
Move the indexer data to /data while it’s still small, so growth lands on the 20Gi disk instead of the root disk:

  sudo systemctl stop wazuh-dashboard filebeat wazuh-manager wazuh-indexer
  sudo mkdir -p /data/wazuh-indexer
  sudo rsync -a /var/lib/wazuh-indexer/ /data/wazuh-indexer/
  echo '/data/wazuh-indexer /var/lib/wazuh-indexer none bind,nofail,x-systemd.requires-mounts-for=/data 0 0' | sudo tee -a /etc/fstab
  sudo mount /var/lib/wazuh-indexer
  sudo systemctl start wazuh-indexer wazuh-manager filebeat wazuh-dashboard

Check findmnt /var/lib/wazuh-indexer, and that the owner is still wazuh-indexer.

3. Open the dashboard

From your Arch machine, tunnel to it through the API, which doesn’t depend on node IPs:


virtctl port-forward vm/wazuh 8443:443 -n xdr-server

Then open https://localhost:8443. Your browser will warn about the self-signed certificate, which is expected. The user is admin, and the password comes from the passwords file above.
```
