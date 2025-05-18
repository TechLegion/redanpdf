# Tests for API endpoints will be implemented here. 

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_register_and_login():
    # Register a new user
    email = "testuser@example.com"
    password = "testpassword"
    reg_response = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert reg_response.status_code == 200 or reg_response.status_code == 400  # 400 if already registered

    # Login
    login_response = client.post("/api/v1/auth/token", data={"username": email, "password": password})
    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer" 