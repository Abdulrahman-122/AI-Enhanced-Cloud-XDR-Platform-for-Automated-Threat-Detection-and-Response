# solve the connection between wazuh on k8s,agent on another Vm
- by default "Wazuh-kubernetes" doesn't contain 
  - service for accessing 1517 through agents
  - network policy to allow this happens as by default it contains: default-deny network policy


```
- configure service on kubernetes-manager
nvim allow-wazuh-agent-ingress.yaml
apiVersion: v1
kind: Service
metadata:
  name: wazuh-agent-endpoint
  namespace: wazuh
spec:
  type: ClusterIP
  selector:
    app: wazuh-manager
    node-type: master
  ports:
    - name: agent-endpoint
      protocol: TCP
      port: 1517
      targetPort: 1517

----
- configure network policy to allow any agents to access that manager

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-wazuh-agent-ingress
  namespace: wazuh
spec:
  podSelector:
    matchLabels:
      app: wazuh-manager
      node-type: master
  policyTypes:
    - Ingress
  ingress:
    - ports:
        - protocol: TCP
          port: 1517
---
kubectl apply -f allow-wazuh-agent-ingress.yaml

- now bring the ip of the  service above in order to test it from the vm that contain the agent
nc -zv ip-of-svc 1517   (you should get)
Connection to ip-of-svc 1517 port [tcp/*] succeeded!
- now check  the logs of that agent whether it's connected to the manager
sudo cat /var/ossec/var/run/wazuh-agentd.state
sudo tail -n 40 /var/ossec/logs/ossec.log
#if you got a failure then do the following 
tep 1 — Update the agent endpoint
Inside vm2, edit the configuration:
nano /var/ossec/etc/ossec.conf
Find the manager endpoint inside the <agent> section and change it to:
<manager>
  <endpoint>ip-of-svc:1517</endpoint>
</manager>
sudo tail -n 40 /var/ossec/logs/ossec.log (it must be connected)
```
- output:
- <img width="930" height="176" alt="image" src="https://github.com/user-attachments/assets/feafe4fa-6145-4def-8e77-8d884a7d9046" />

- if you want to delete the agant from your system (ubuntu)
```
dpkg --remove --force-remove-reinstreq --force-depends wazuh-agent
#if that fails do the following
- disable the removal broken script
if [ -f /var/lib/dpkg/info/wazuh-agent.prerm ]; then
    mv /var/lib/dpkg/info/wazuh-agent.prerm \
       /var/lib/dpkg/info/wazuh-agent.prerm.disabled
fi
- then delete
dpkg --purge --force-all wazuh-agent
- then remove the remaining files
systemctl disable --now wazuh-agent 2>/dev/null || true

rm -rf /var/ossec

rm -f /etc/systemd/system/wazuh-agent.service
rm -f /etc/systemd/system/multi-user.target.wants/wazuh-agent.service

systemctl daemon-reload
systemctl reset-failed
- now check
dpkg-query -W wazuh-agent 2>/dev/null || echo "Wazuh package removed"
test ! -e /var/ossec && echo "Wazuh files removed"
```
- if you got more critical vulnerability on wazuh from thee image do the following
```
- check your installed kernel image
cat /etc/os-release

uname -r

dpkg-query -W -f='${binary:Package}\t${Version}\t${source:Package}\n' \
  'linux-image*' 2>/dev/null

apt-cache policy linux-generic linux-image-generic
```
- <img width="784" height="110" alt="image" src="https://github.com/user-attachments/assets/fba22bc4-8fb5-4479-82b2-508a1ac16fc6" />
- now update the kernel to higher one
```
sudo apt update
sudo apt full-upgrade
sudo reboot
uname -r (in my case the new one is 6.8.0-147-generic)
# now remove the old kernel version
sudo apt remove linux-image-6.8.0-142-generic
sudo apt autoremove
#then restart your agent
sudo systemctl restart wazuh-agent
```
