# Aerocorp web app 
- is a web application that we build in order to attack our XDR(Wazuh) through it then see our XDR will see that attack or not
- after you start this web application
  - the logs of web app , nginx on : logs/
  - these logs we will use later to fine tune our model.
# step 1 (start the web application)
```yml
- How to start this project
# docker compose up --build -d
- after that you will have 3 containers (db,backend,nginx(frontend)
```
```yml
- to test the connection :
#curl http://localhost:8080
- on your browser
http://localhost:8080       (it may open if not you need to download docker first) on your vm
```
# step 2 ( start AI model in order to monitor our alerts, give us some solutions for any attack on the XDR)

