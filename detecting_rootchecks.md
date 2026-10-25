# here i installed LKM rootkit to check whether -> our XDR will detect it or not

```yml
steps
apt install git,gcc
- clone diamorpine
git clone https://github.com/m0nad/Diamorphine.git
cd Diamorpine
- enable the rootcheck
make
- upload it as a root
sudo insmod ./diamorpine.ko
now check it
lsmod | grep diamorpine          (it starts i cogintive mode)


```
- now hide it to check whether our xdr will detect or not
- <img width="960" height="64" alt="image" src="https://github.com/user-attachments/assets/6a5c831a-70bf-4539-b3d3-74cd025f40f1" />
- if you want to hidden a process
- <img width="827" height="135" alt="image" src="https://github.com/user-attachments/assets/09b61aa9-0d27-43f5-bf6f-d495eca62a2e" />
- on our XDR
  - <img width="1882" height="40" alt="image" src="https://github.com/user-attachments/assets/2dd492b7-9e4f-4571-b6e0-a1718b3da924" />
  - <img width="1306" height="875" alt="image" src="https://github.com/user-attachments/assets/0c252f8d-25bc-4c8b-9f9a-419125b0cc18" />
