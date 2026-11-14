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
http://localhost:8080       (it may open if not you need to download docker first) on your vm -> go to walkthrough.md on this dirctory and you will be able to install docker.
```
# step 2 ( start AI model in order to monitor our alerts, give us some solutions for any attack on the XDR)
# AI_Triage -> is an AI that detect any attacks that happen on our XDR 
#  we have two modes on this AI dashboard
```yml
1. monitor mode
- This AI looks for indexer alerts over http  that came to the dashboard you may connect it to the alerts.json but in my case i used indexer.
2. ask for question mode
- we fine tune our model to respond to and question about technical stuff that our Security Engineers want , in general questions.
```
# How to build this feature??
```yml
- first you need to make sure you have good resources on your laptop (cpu,memory)
#step1
#python3 -m venv .ai
source .ai/bin/activate
export LLM_API_KEY="nvapi-your-new-key"
export LLM_MODEL="nvidia/nemotron-3.5-bolt-e4b"
export WAZUH_INDEXER_PASS="your-indexer-password"
#make sure you make your indexer reachable in my case i am using kubernetes and i can reach it using services
# i will run this in another terminal
k port-forward --address 0.0.0.0 svc/indexer 9200:9200
#then run on another terminal this in order to connect AI with this service
uvicorn main:app --host 127.0.0.1 --port 9000
#on your browser
http://localhost:9000 # (you will see the AI )
```
---
# output of aerocorp webapp
- 
# output of AI_Triage
-
