# Important commands on k8s 
- how to send data to a vm on k8s
```
virtctl scp ./file-name  user@vm/vm-name/namespace-that-contain-vm:/home/anydestination

```
- if you wanted to access vms on your host machine
```
ssh -p 30026(portnumber) -N -L port-to-access-on-host:127.0.0.1:port-on-vm username@ip-to-vm
```
