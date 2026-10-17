"""
End-to-End REST API Backend Verification Test
"""
import os
import sys

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure current directory is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.user import User

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite:///./test_api.db"
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


def test_full_flow():
    print(">> [1/6] Testing Root & Health Check Endpoints...")
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert root_resp.json()["status"] == "online"
    assert "endpoints" in root_resp.json()
    print("   [OK] Root endpoint '/' returned API overview JSON.")

    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"
    print("   [OK] Health check passed:", health_resp.json())

    print("\n>> [2/6] Testing Swagger UI & OpenAPI Specification...")
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    assert "/api/auth/register" in openapi_resp.json()["paths"]
    assert "/api/auth/login" in openapi_resp.json()["paths"]
    assert "/api/home/me" in openapi_resp.json()["paths"]
    print("   [OK] Swagger UI & OpenAPI schema generated successfully.")

    print("\n>> [3/6] Testing API 1: User Registration (POST /api/auth/register)...")
    user_payload = {
        "username": "fouad_dev",
        "email": "fouad@example.com",
        "full_name": "Fouad Engineer",
        "password": "SecurePassword123!"
    }
    reg_resp = client.post("/api/auth/register", json=user_payload)
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    reg_data = reg_resp.json()
    assert reg_data["username"] == "fouad_dev"
    assert reg_data["email"] == "fouad@example.com"
    assert "id" in reg_data
    print("   [OK] API 1 Registration succeeded for user:", reg_data["username"], f"(ID: {reg_data['id']})")

    # Test Duplicate Registration rejection
    dup_resp = client.post("/api/auth/register", json=user_payload)
    assert dup_resp.status_code == 400
    print("   [OK] Duplicate registration properly rejected (400 Bad Request).")

    print("\n>> [4/6] Testing API 2: User Login (POST /api/auth/login)...")
    # Test Login with Username
    login_payload = {
        "username_or_email": "fouad_dev",
        "password": "SecurePassword123!"
    }
    login_resp = client.post("/api/auth/login", json=login_payload)
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    token = login_data["access_token"]
    print("   [OK] API 2 Login succeeded! JWT Token generated:", token[:30] + "...")

    # Test Login with Email
    login_email_payload = {
        "username_or_email": "fouad@example.com",
        "password": "SecurePassword123!"
    }
    login_email_resp = client.post("/api/auth/login", json=login_email_payload)
    assert login_email_resp.status_code == 200
    print("   [OK] Login using Email address succeeded!")

    # Test Invalid Password
    bad_login = client.post("/api/auth/login", json={"username_or_email": "fouad_dev", "password": "WrongPassword"})
    assert bad_login.status_code == 401
    print("   [OK] Invalid credentials properly rejected (401 Unauthorized).")

    print("\n>> [5/6] Testing API 3: Protected User Profile (GET /api/home/me)...")
    # Request without token -> should fail with 401
    unauth_resp = client.get("/api/home/me")
    assert unauth_resp.status_code == 401
    print("   [OK] Unauthorized access without token correctly rejected (401 Unauthorized).")

    # Request with valid Bearer token -> should succeed with 200
    auth_headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/home/me", headers=auth_headers)
    assert me_resp.status_code == 200, f"Protected API failed: {me_resp.text}"
    me_data = me_resp.json()
    assert me_data["status"] == "authenticated"
    assert me_data["user"]["username"] == "fouad_dev"
    assert me_data["user"]["full_name"] == "Fouad Engineer"
    print("   [OK] API 3 Protected User Data retrieved successfully:")
    print("       Message:", me_data["message"])
    print("       User Details:", me_data["user"])

    print("\n>> [6/6] All backend REST API test suites passed with 100% success! 🎉")


if __name__ == "__main__":
    test_full_flow()
