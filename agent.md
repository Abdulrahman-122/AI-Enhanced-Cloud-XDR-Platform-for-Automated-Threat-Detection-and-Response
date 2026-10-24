# on this cluster -> to connect any agent with any vm 
1. go to your vm
```
apt update
apt install neovim
```
2. go to dashboard and do the following
-<img width="866" height="853" alt="image" src="https://github.com/user-attachments/assets/5f1b2fe3-2479-4dbd-a038-9d923e97d87d" />
- <img width="1919" height="596" alt="image" src="https://github.com/user-attachments/assets/820d11bb-704a-4fcd-b1e0-d903c54fca72" />
- <img width="996" height="476" alt="image" src="https://github.com/user-attachments/assets/2f2fb0d8-1052-48b5-b199-196aab89f5eb" />

3. check the services on wazuh
  - <img width="901" height="243" alt="image" src="https://github.com/user-attachments/assets/f81b217f-e7ad-494c-ad12-445a5b9be3d5" />
  - now check the connection with wazuh on port 1515
  - <img width="807" height="170" alt="image" src="https://github.com/user-attachments/assets/97817dc0-9c82-4f55-9e2e-fb7834704190" />
  - then generate key for authentications and then it will be generated successfully
  - now: go to "/var/ossec/etc/ossec.conf"
    - change the ip to ip of wazuh-workers as it listens on port 1514
    - <img width="624" height="179" alt="image" src="https://github.com/user-attachments/assets/bfef5d6f-890d-4da6-9d52-ff1300b60d83" />
    - restart the agent again
      - <img width="483" height="45" alt="image" src="https://github.com/user-attachments/assets/df40d8a0-fbe2-4592-a64d-7ae4b9205f96" />

    -
    - once you did that now everything will work perfectly
      - <img width="1899" height="46" alt="image" src="https://github.com/user-attachments/assets/7bab4170-2eb0-442f-ba14-c8da978028ae" />

- commands you may need on wazuh-workers:
```
- restart the manager: /var/ossec/bin/wazuh-control restart
- see the status : /var/ossec/bin/wazuh-control status
#or
- kubectl rollout restart statefulset/wazuh-manager-master -n wazuh
```
  
