"""
Comprehensive Test Suite for XDR Security Platform Backend
El Shorouk Academy Graduation Project
"""
import os
import sys

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.user import User

# Use SQLite in-memory / file for testing
TEST_DATABASE_URL = "sqlite:///./test_xdr.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create test tables
Base.metadata.drop_all(bind=test_engine)
Base.metadata.create_all(bind=test_engine)

client = TestClient(app)


def run_xdr_tests():
    print(">> =================================================================")
    print(">>  EL SHOROUK ACADEMY - XDR SECURITY PLATFORM TEST SUITE")
    print(">> =================================================================\n")

    # 1. Root & Health Check
    print(">> [1/8] Testing Root & Health Endpoints...")
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["academy"] == "El Shorouk Academy"
    print("   [PASS] Root endpoint returned project metadata.")

    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
    print("   [PASS] Health check verified.")

    # 2. Authentication & JWT Token
    print("\n>> [2/8] Testing User Registration & JWT Authentication...")
    user_payload = {
        "username": "soc_analyst",
        "email": "analyst@sha.edu.eg",
        "full_name": "El Shorouk SOC Analyst",
        "password": "Password123!"
    }
    r = client.post("/api/auth/register", json=user_payload)
    assert r.status_code == 201
    print("   [PASS] Registered test user 'soc_analyst'.")

    login_payload = {
        "username_or_email": "soc_analyst",
        "password": "Password123!"
    }
    r = client.post("/api/auth/login", json=login_payload)
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token is not None
    headers = {"Authorization": f"Bearer {token}"}
    print("   [PASS] JWT login succeeded. Bearer token acquired.")

    # 3. Dashboard API
    print("\n>> [3/8] Testing XDR Dashboard API (GET /api/dashboard)...")
    r = client.get("/api/dashboard", headers=headers)
    assert r.status_code == 200, f"Dashboard failed: {r.text}"
    dash = r.json()
    assert "total_agents" in dash
    assert "active_agents" in dash
    assert "total_alerts" in dash
    assert "alerts_over_time" in dash
    assert "alerts_by_severity" in dash
    assert "top_rules" in dash
    assert "wazuh_status" in dash
    print(f"   [PASS] Dashboard data verified (Agents: {dash['total_agents']}, Alerts: {dash['total_alerts']}).")

    # 4. Agents API
    print("\n>> [4/8] Testing Agents Endpoints (GET /api/agents, GET /api/agents/{id})...")
    r = client.get("/api/agents", headers=headers)
    assert r.status_code == 200
    agents_data = r.json()
    assert agents_data["total"] > 0
    first_agent_id = agents_data["items"][0]["id"]
    print(f"   [PASS] Agents list returned {agents_data['total']} endpoints.")

    r = client.get(f"/api/agents/{first_agent_id}", headers=headers)
    assert r.status_code == 200
    agent_detail = r.json()
    assert agent_detail["id"] == first_agent_id
    print(f"   [PASS] Agent detail retrieved for '{agent_detail['name']}' (ID: {first_agent_id}).")

    # 5. Alerts API
    print("\n>> [5/8] Testing Security Alerts Endpoints (GET /api/alerts, GET /api/alerts/{id})...")
    r = client.get("/api/alerts?severity=critical", headers=headers)
    assert r.status_code == 200
    alerts_data = r.json()
    assert len(alerts_data["items"]) > 0
    first_alert_id = alerts_data["items"][0]["id"]
    print(f"   [PASS] Filtered critical alerts returned {len(alerts_data['items'])} items.")

    r = client.get(f"/api/alerts/{first_alert_id}", headers=headers)
    assert r.status_code == 200
    alert_detail = r.json()
    assert alert_detail["id"] == first_alert_id
    print(f"   [PASS] Alert detail fetched for '{first_alert_id}' - Level {alert_detail['rule_level']}.")

    # 6. Threat Detection & MITRE ATT&CK
    print("\n>> [6/8] Testing Threat Detection API (GET /api/threats)...")
    r = client.get("/api/threats", headers=headers)
    assert r.status_code == 200
    threats = r.json()
    assert "mitre_tactics" in threats
    assert "fim_events" in threats
    assert "vulnerabilities" in threats
    print(f"   [PASS] Threat intelligence matrix loaded ({len(threats['mitre_tactics'])} MITRE tactics, {len(threats['fim_events'])} FIM events).")

    # 7. Reports & CSV Export
    print("\n>> [7/8] Testing Reports & CSV Export (GET /api/reports/summary, /export/alerts.csv)...")
    r = client.get("/api/reports/summary", headers=headers)
    assert r.status_code == 200
    rep = r.json()
    assert rep["organization"] == "El Shorouk Academy"
    print(f"   [PASS] Report summary generated for {rep['organization']}.")

    r = client.get("/api/reports/export/alerts.csv", headers=headers)
    assert r.status_code == 200
    assert "Alert ID,Timestamp (UTC)" in r.text
    print("   [PASS] CSV export generated valid tabular alerts spreadsheet.")

    # 8. Settings & Diagnostics
    print("\n>> [8/8] Testing Settings & Diagnostics (GET /api/settings/diagnostics)...")
    r = client.get("/api/settings/diagnostics", headers=headers)
    assert r.status_code == 200
    diag = r.json()
    assert "wazuh_endpoint" in diag
    assert "database_status" in diag
    print(f"   [PASS] Diagnostics validated (Wazuh Status: {diag['status_message']}).")

    print("\n>> =================================================================")
    print(">>  ALL 8/8 XDR PLATFORM API TEST SUITES PASSED WITH 100% SUCCESS! 🚀")
    print(">> =================================================================\n")


if __name__ == "__main__":
    run_xdr_tests()
