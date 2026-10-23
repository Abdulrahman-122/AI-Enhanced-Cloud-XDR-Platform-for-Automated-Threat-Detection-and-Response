# to start (you must have a cluster that is running on your machine)
## we need to install wazuh on kubernetes 
 - <img width="990" height="634" alt="image" src="https://github.com/user-attachments/assets/27f3b75b-8d7e-4696-8c51-47f11602b388" />


### steps
- the whole workflow 

```yml
1.check the cluster first
kubectl cluster-info
kubectl get nodes -o wide
kubectl get storageclass
kubectl get pods -A
2.check your resources
kubectl top nodes
free -h
df -h

```

```yml
3.clone the official repo with version v5.0.0 or any recent versions
mkdir -p ~/projects/security
cd ~/projects/security
#check tags and choose any version
git fetch --tags 

git clone --depth 1 --branch v5.0.0 \
  https://github.com/wazuh/wazuh-kubernetes.git
#you can even switch to any version later by doing this
git checkout v.*.*

cd wazuh-kubernetes

#describe tags
git describe --tags
```

```yml
#check whether github is accessable
curl -fIL \
  https://raw.githubusercontent.com/wazuh/wazuh-installation-assistant/main/builder.sh
#clone wazuh-installation-assistent in order to build the certificate for the project
cd ~/projects/security

git clone https://github.com/wazuh/wazuh-installation-assistant.git
cd wazuh-installation-assistant

git tag -l '*5.0.0*'

#check the supported options
bash builder.sh -c
```

```yml
#build the certificate and the password tools
cd ~/projects/security/wazuh-installation-assistant

git status --short
git log -1 --oneline
git branch --show-current

bash builder.sh --cert-tool
bash builder.sh --passwords-tool

find . -type f \( \
  -name 'wazuh-certs-tool.sh' -o \
  -name 'wazuh-passwords-tool.sh' \
\) -print

#find the matching between wazuh-kubernets,wazuh-installation
cd ~/projects/security

printf '\n=== CERTIFICATE CONFIG TEMPLATES ===\n'
find wazuh-installation-assistant wazuh-kubernetes \
  -type f \( -name 'config.yml' -o -name '*config*.yml' \) \
  -print

printf '\n=== CREDENTIALS LIBRARY ===\n'
find wazuh-installation-assistant \
  -type f \( -name 'wazuh-credentials.sh' -o -name '*credentials*' \) \
  -print

printf '\n=== KUBERNETES NODE NAMES ===\n'
grep -RInE 'name:|image:' wazuh-kubernetes/wazuh \
  --include='*.yaml' --include='*.yml' | head -100

#if wazuh-certs-tools.sh is found inside wazuh-installation...
cp ./wazuh-certs-tool.sh \
  ../wazuh-kubernetes/wazuh/wazuh-certs-tool.sh

chmod +x ../wazuh-kubernetes/wazuh/wazuh-certs-tool.sh

#check the helper output 
bash wazuh-certs-tool.sh -h
#check whether the credentials library  matches
head -40 wazuh/wazuh-certs-tool.sh
head -40 ../wazuh-installation-assistant/credentials_lib/wazuh-credentials.sh
#find the configurations,credential instructions
grep -RInE \
  'certificates-conf|credentials-conf|wazuh-certs-tool|WAZUH_CREDENTIALS_LIB' \
  README.md docs envs tools
```
```yml
#create config.yaml inside : wazuh/config.yaml

cat << 'EOF' > config.yaml
nodes:
  indexer:
    - name: indexer
      ip: "127.0.0.1"
      dns:
        - "indexer"
        - "indexer.wazuh.svc"
        - "indexer.wazuh.svc.cluster.local"
        - "wazuh-indexer"
        - "wazuh-indexer.wazuh.svc"
        - "wazuh-indexer.wazuh.svc.cluster.local"

  manager:
    - name: manager
      ip: "127.0.0.1"
      dns:
        - "manager"
        - "wazuh-api"
        - "wazuh-api.wazuh.svc"
        - "wazuh-api.wazuh.svc.cluster.local"
        - "wazuh-cluster"
        - "wazuh-cluster.wazuh.svc"
        - "wazuh-cluster.wazuh.svc.cluster.local"

  dashboard:
    - name: dashboard
      ip: "127.0.0.1"
      dns:
        - "dashboard"
        - "dashboard.wazuh.svc"
        - "dashboard.wazuh.svc.cluster.local"
EOF


```

```yml
#generate and copy the certificates

cd wazuh

sudo bash ../tools/utils/deployment/certificates-conf.sh \
  --cert --copy --priv

-
for f in \
  config/indexer/certs/admin-key.pem \
  config/indexer/certs/admin.pem \
  config/indexer/certs/indexer-key.pem \
  config/indexer/certs/indexer.pem \
  config/dashboard/certs/dashboard-key.pem \
  config/dashboard/certs/dashboard.pem \
  config/manager/certs/manager-key.pem \
  config/manager/certs/manager.pem \
  config/manager/certs/manager-remoted-key.pem \
  config/manager/certs/manager-remoted.pem \
  config/manager/certs/manager-apid-key.pem \
  config/manager/certs/manager-apid.pem \
  config/root-ca/certs/root-ca.pem
do
  if [ -s "$f" ]; then
    printf 'OK      %s\n' "$f"
  else
    printf 'MISSING %s\n' "$f"
  fi
done
-
# Verify the credentials library exists
LIB="$(realpath ../../wazuh-installation-assistant/credentials_lib/wazuh-credentials.sh)"
printf 'Library: %s\n' "$LIB"
test -r "$LIB" || { echo "Library not readable"; exit 1; }

# Run with sudo while explicitly passing the environment variable
sudo env WAZUH_CREDENTIALS_LIB="$LIB" \
  bash ../tools/utils/deployment/credentials-conf.sh

-
sudo find config/credentials -maxdepth 1 -type f -printf '%f\n'
sudo ls -l config/credentials


You should see these files:
- indexer.env
- manager.env
- dashboard.env
- cluster.key

-
#render the files and test them
cd ..
kubectl kustomize envs/local-env/ > /tmp/wazuh-rendered.yaml


Check whether rendering succeeded:
test -s /tmp/wazuh-rendered.yaml \
  && echo "Kustomize rendering succeeded" \
  || echo "Rendering failed"
  

 ```

```yml
#now check images on your docker images
for image in \
  wazuh/wazuh-manager:5.0.0 \
  wazuh/wazuh-indexer:5.0.0 \
  wazuh/wazuh-dashboard:5.0.0
do
  printf '\nChecking %s\n' "$image"
  if docker manifest inspect "$image" >/dev/null 2>&1; then
    echo "AVAILABLE"
  else
    echo "NOT AVAILABLE (or registry access failed)"
  fi
done

-
#if the images not found pull them
docker pull wazuh/wazuh-manager:5.0.0-beta5
docker pull wazuh/wazuh-indexer:5.0.0-beta5
docker pull wazuh/wazuh-dashboard:5.0.0-beta5
#wait untill successfully pulled

-
#fetch the release that corresponding to these images
git fetch origin tag v5.0.0-beta5
git show --no-patch --oneline v5.0.0-beta5
#checking the type of releases that manifests on  wazuh-kubernets uses
git show v5.0.0-beta5:wazuh/wazuh_managers/wazuh-master-sts.yaml \
  | grep 'image:'

git show v5.0.0-beta5:wazuh/indexer_stack/wazuh-indexer/cluster/indexer-sts.yaml \
  | grep 'image:'

git show v5.0.0-beta5:wazuh/indexer_stack/wazuh-dashboard/dashboard-deploy.yaml \
  | grep 'image:'
  #they must have  : 5.0.0-beta5
#now switch git to the release that like on manifist
# Back up your custom storage configuration
cp envs/local-env/storage-class.yaml /tmp/wazuh-storage-class.yaml.backup

# Preserve the tracked change, then switch to the matching release
git stash push -m "local Wazuh storage class" -- envs/local-env/storage-class.yaml
git switch --detach v5.0.0-beta5

# Restore your local storage configuration
cp /tmp/wazuh-storage-class.yaml.backup envs/local-env/storage-class.yaml

# Confirm the release and storage configuration
cat VERSION.json
git status --short
-
#Render again and check
kubectl kustomize envs/local-env/ > /tmp/wazuh-rendered.yaml &&
  echo "Rendering succeeded"

grep 'image:' /tmp/wazuh-rendered.yaml | sort -u

-
#Now deploy wazuh
kubectl apply -k envs/local-env/
#check pvc,..
kubectl get pods,pvc,svc -n wazuh -w
kubectl get pods -n wazuh -o wide
kubectl get pvc -n wazuh
kubectl get events -n wazuh --sort-by=.lastTimestamp | tail -30

-
#now in order to access the dashboard you must build an ingress as no ingrss is built for or using port-forward + convert the svc of the dash to be NodePort

nvim wazuh/indexer_stack/wazuh-dashboard/dashboard-svc.yaml
make these changes;
spec:
  type: NodePort
  ports:
    - name: dashboard
      port: 443
      targetPort: 443
      nodePort: 30443

-
add the network policy ingress

kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dashboard-ingress
  namespace: wazuh
spec:
  podSelector:
    matchLabels:
      app: wazuh-dashboard
  policyTypes:
    - Ingress
  ingress:
    - ports:
        - protocol: TCP
          port: 443
EOF
apply again the whole manifests: kubectl apply -k envs/local-env/

```
- this is the output
- <img width="629" height="528" alt="image" src="https://github.com/user-attachments/assets/a1b4deea-0031-44bf-9880-133e10080093" />
- <img width="604" height="235" alt="image" src="https://github.com/user-attachments/assets/cd616586-2eca-4fc7-a4ac-038c2ac1cf42" />
- in my case to access dashboard:  https;//Node_IP_of_the_cluster:30443
  - <img width="1723" height="889" alt="image" src="https://github.com/user-attachments/assets/451c8c13-da86-4b21-9e63-50a3a0bfd22a" />

