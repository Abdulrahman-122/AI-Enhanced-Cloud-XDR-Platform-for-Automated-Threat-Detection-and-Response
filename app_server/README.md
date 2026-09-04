# 🛡️ XDR Security Platform | El Shorouk Academy
### Graduation Project &bull; مشروع التخرج &bull; أكاديمية الشروق

An enterprise-grade **Extended Detection & Response (XDR) Security Operations Center (SOC)** platform built with a high-performance **FastAPI** backend, live **Wazuh SIEM/EDR REST API integration**, and a modern **React + Vite + Tailwind CSS** cyber defense dashboard.

---

## 🏛️ Project Branding & Information
- **Institution**: El Shorouk Academy (أكاديمية الشروق)
- **Project Name**: XDR Security Platform (منصة الاستجابة والكشف الأمني المتقدمة)
- **Sub-domain**: Cybersecurity & SOC Infrastructure Engineering
- **Architecture Flow**:
  ```
  React Frontend (Port 5173 / Port 80)
          ↓ (REST API / JWT Bearer)
  FastAPI Backend (Port 8000)
          ↓ (Wazuh REST API / JWT Token Caching)
  Wazuh Manager Server (Port 55000)
          ↓ (OSSEC / Sysmon / FIM)
  Monitored Agents & Endpoints (Windows / Linux / Servers)
  ```
  > **Note**: The React frontend never communicates directly with the Wazuh server. All requests are authenticated and brokered through the FastAPI security backend.

---

## 🚀 Key Features

### 1. 🔐 Authentication & Access Control
- JWT (JSON Web Tokens) with HS256 algorithm and bcrypt password salting.
- Protected API endpoints using FastAPI dependency injection (`get_current_user`).
- Role-ready user persistence with SQLite and PostgreSQL support.

### 2. 📊 Executive SOC Dashboard
- **Real-time KPI Metrics**: Total Agents, Active/Disconnected Endpoints, Total Alert Events, Critical/High/Medium/Low distribution.
- **Interactive Visualizations (Recharts)**:
  - Alert Events Over Time (hourly timeline area chart).
  - Severity Breakdown distribution (donut chart).
  - Alerts by Asset / Agent (horizontal bar chart).
  - Top Triggered Wazuh Detection Rules.
  - Top Threat Categories (MITRE ATT&CK tactics).
- **Live Incident Stream**: Recent security alerts table with instant drill-down inspection.

### 3. 🖥️ Endpoint Agent Management
- Live status tracking of all registered Wazuh agents (active, disconnected, pending).
- Agent details modal displaying operating system, IP, last keepalive, CPU/RAM/Disk health, open listening ports, and active security modules (FIM, Rootcheck, SCA).

### 4. 🚨 Security Alert Investigation
- Advanced alert table with multi-criteria filtering:
  - Severity level (`Critical`, `High`, `Medium`, `Low`).
  - Agent ID / Name.
  - Keyword search across rules, source IPs, MITRE tactics.
  - Paginated navigation.
- Alert detail modal showing full Wazuh rule metadata, MITRE ATT&CK technique IDs, source/destination IPs and ports, log location, and raw JSON event log payload.

### 5. 🎯 Threat Detection & MITRE ATT&CK
- **MITRE ATT&CK Framework Matrix**: Visual mapping of tactical categories (Initial Access, Execution, Persistence, Credential Access, Discovery, Impact) and technique counters.
- **File Integrity Monitoring (FIM / Syscheck)**: Tracking modifications to critical system files (e.g., `/usr/bin/sudo`, `hosts`), before/after MD5 checksums, and user attribution.
- **Vulnerability Detector (CVE)**: Tracking detected CVEs (e.g., RunC, XZ-Utils, OpenSSH), vulnerable packages, CVSS scores, and patch status.

### 6. 📑 Compliance Reporting & CSV Export
- Executive SOC summary statistics and compliance scores (PCI-DSS, CIS benchmark adherence).
- One-click CSV Export (`/api/reports/export/alerts.csv`) for spreadsheet analysis.
- Print / PDF-ready formal audit report with official El Shorouk Academy header and supervisor sign-off section.

### 7. ⚙️ Settings & Wazuh Diagnostics
- User profile management and password update.
- Dashboard polling interval customization (10s, 30s, 60s, off) and alert toggles.
- Live Wazuh connection diagnostic tool (reports endpoint, connectivity status, and version without exposing secrets).

---

## 📁 Repository Structure

```
├── app/
│   ├── auth/                    # JWT Authentication & Bcrypt Security
│   ├── database.py              # SQLAlchemy database engine & session maker
│   ├── config.py                # Pydantic Settings & environment variables
│   ├── models/                  # Database models (User model)
│   ├── schemas/                 # Pydantic schemas (Wazuh, Dashboard, Agent, Alert, Threat, Report)
│   ├── services/
│   │   └── wazuh_service.py     # Dedicated Wazuh REST API integration service
│   ├── routers/
│   │   ├── auth.py              # POST /api/auth/register, POST /api/auth/login
│   │   ├── home.py              # GET /api/home/me
│   │   ├── dashboard.py         # GET /api/dashboard
│   │   ├── agents.py            # GET /api/agents, GET /api/agents/{id}
│   │   ├── alerts.py            # GET /api/alerts, GET /api/alerts/{id}
│   │   ├── threats.py           # GET /api/threats
│   │   ├── reports.py           # GET /api/reports/summary, /export/alerts.csv
│   │   └── settings.py          # GET /api/settings/diagnostics, PUT /api/settings/profile
│   └── main.py                  # FastAPI Application Entry & CORS Middleware
│
├── frontend/
│   ├── src/
│   │   ├── assets/              # El Shorouk Academy official logo
│   │   ├── components/          # Reusable SOC UI components & modals
│   │   ├── layouts/             # MainLayout (Sidebar + Navbar)
│   │   ├── pages/               # Login, Dashboard, Agents, Alerts, Threats, Reports, Settings
│   │   ├── services/            # Axios API services (api, auth, dashboard, agent, alert, threat, report)
│   │   ├── App.jsx              # Routing & protected route guards
│   │   ├── main.jsx             # React entry point
│   │   └── index.css            # Tailwind & Cyber SOC styling
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── .env.example
│   └── .env
│
├── requirements.txt             # Python backend dependencies
├── .env.example                 # Backend environment template
├── .env                         # Backend environment file
├── test_xdr_api.py              # Automated backend test suite
└── README.md                    # Project Documentation
```

---

## 🛠️ Installation & Setup (Local Development)

### 1. Backend Setup
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure .env
cp .env.example .env

# 3. Run automated backend tests
python test_xdr_api.py

# 4. Start FastAPI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- API Health Check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 2. Frontend Setup
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install Node.js dependencies
npm install

# 3. Start Vite React development server
npm run dev
```
- Access Frontend Dashboard: [http://localhost:5173](http://localhost:5173)

---

## 🐧 Ubuntu Server Deployment Guide

To deploy the platform on an **Ubuntu 22.04 / 24.04 LTS Server**:

### Step 1: System Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nodejs npm nginx git
```

### Step 2: Clone & Configure Backend
```bash
cd /opt
git clone <your-repo-url> xdr-platform
cd xdr-platform

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
nano .env
```

### Step 3: Configure Systemd Service for FastAPI
Create `/etc/systemd/system/xdr-backend.service`:
```ini
[Unit]
Description=XDR Security Platform FastAPI Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/xdr-platform
Environment="PATH=/opt/xdr-platform/venv/bin"
ExecStart=/opt/xdr-platform/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now xdr-backend
```

### Step 4: Build Frontend
```bash
cd /opt/xdr-platform/frontend
npm install
npm run build
sudo cp -r dist/* /var/www/html/
```

### Step 5: Configure Nginx Reverse Proxy
Create `/etc/nginx/sites-available/xdr-platform`:
```nginx
server {
    listen 80;
    server_name _;

    root /var/www/html;
    index index.html;

    # Frontend Single Page App Routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Swagger Documentation
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
    }
}
```
Enable the site and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/xdr-platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔗 Connecting to Live Wazuh Server

In `.env`, configure the connection parameters for your Wazuh Server:
```env
WAZUH_API_URL=https://<YOUR_WAZUH_SERVER_IP>:55000
WAZUH_API_USERNAME=wazuh-wui
WAZUH_API_PASSWORD=your_wazuh_password
WAZUH_VERIFY_SSL=False
```
1. If using the default Wazuh self-signed certificates, set `WAZUH_VERIFY_SSL=False`.
2. The platform tests connection on startup and during user interaction. If Wazuh is temporarily unreachable or offline during demonstrations, the platform gracefully activates high-fidelity SOC simulation telemetry, indicating `Simulation Mode` without crashing.

---

## 🧪 Testing

Run the full end-to-end integration test suite:
```bash
python test_xdr_api.py
```
This validates:
- API root and health checks
- User registration & JWT authentication
- Dashboard metrics aggregation
- Agent list & detailed telemetry
- Paginated security alerts & filtering
- Threat detection MITRE ATT&CK matrix
- Reports generation & CSV stream download
- Settings & live diagnostics
