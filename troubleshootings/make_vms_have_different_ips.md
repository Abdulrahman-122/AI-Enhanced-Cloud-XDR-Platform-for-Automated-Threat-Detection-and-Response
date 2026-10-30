# problem that i faced when i built VMS using kubevirt on k8s
- i added masquerade mode so that all Vms have the same ip however they don't conflict each other but this is not a good way for building a nework stuff
- - so i tried to find a solution 

Option 1: Bridge networking (unique IP per VM)

In the VM spec, change the interface binding from masquerade to bridge:

```yml
Option 1: Bridge networking (unique IP per VM)

In the VM spec, change the interface binding from masquerade to bridge:


kubectl -n <vm-namespace> edit vm vm4
yaml
spec:
  template:
    spec:
      domain:
        devices:
          interfaces:
          - name: default    #add this
            bridge: {}       #add this
      networks:
      - name: default
        pod: {}
```
- if the vm name vm3
```yml
stop the machine to recover the changes
kubectl patch vm vm3 --type merge -p '{"spec":{"runStrategy":"Halted"}}'
kubectl get vmi vm3 -w      # wait until the VMI is gone, then Ctrl+C

#then start it to detect the changes
kubectl patch vm vm3 --type merge -p '{"spec":{"runStrategy":"Always"}}'
kubectl get vmi vm3 -w      # wait for Running and READY True

Inside vm3:
ip a  # you will get new ip

or even:
kubectl apply -f vm-name.yml
virtctl restart vm-name
kubectl get vmi vm-name -o wide -w

#now see the result
log into the vm by ssh then see
#ip a

```
