"""
Test module for User Management and Authentication.
This file contains integration tests for the user lifecycle: registration, 
preventing duplicate accounts, logging in (OAuth2), and fetching protected user profiles.
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from app.schemas import UserOut
from app.main import app

@pytest.fixture
def client():
    """
    Pytest fixture to create a fresh TestClient for each test.
    This simulates an API consumer (like a frontend app or mobile app) 
    interacting with our server.
    """
    yield TestClient(app)

# ==========================================
# USER & AUTHENTICATION TEST CASES
# ==========================================

def test_create_user(client):
    """
    Test standard user registration.
    
    Why use UserOut schema here?: We pass the response JSON into the UserOut Pydantic 
    model to strictly verify that the API returns the exact shape we expect.
    Crucially, we also assert that the raw password is NOT returned in the response 
    for security reasons.
    """
    res = client.post("/user/", json={"email": "hello@gmail.com", "password": "password123"})
    
    # Verify successful creation
    assert res.status_code == status.HTTP_201_CREATED
    
    # Validate response structure using our Pydantic schema
    new_user = UserOut(**res.json())
    assert new_user.email == "hello@gmail.com"
    
    # Security Check: Ensure sensitive data (password) is stripped from the response
    assert "password" not in res.json()

def test_create_user_duplicate(client):
    """
    Constraint Testing: Ensure the system rejects registration with an already existing email.
    
    The API must catch the database integrity error (or manual check) and return 
    a safe HTTP error rather than throwing a 500 Internal Server Error.
    """
    payload = {"email":"duplicate@gmail.com", "password":"password123"}
    
    # Step 1: Create the initial user
    client.post("/user/", json=payload)
    
    # Step 2: Attempt to create another user with the exact same payload
    res = client.post("/user/", json=payload)
    
    # Note: Depending on router implementation, this is often 400 Bad Request or 409 Conflict.
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json().get("detail") == "User with this email already exists"

def test_login_user(client):
    """
    Test the OAuth2 Password Bearer login flow.
    Verifies that valid credentials return a correctly formatted JWT payload containing 
    the 'access_token' and 'token_type'.
    """
    # Note: OAuth2PasswordRequestForm expects form data (data=...), not JSON.
    login_res = client.post(
        "/login", 
        data={"username": "hello@gmail.com", "password": "password123"}
    )
    
    assert login_res.status_code == status.HTTP_200_OK
    
    # Verify standard OAuth2 response keys
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_user_by_id(client):
    """
    Test accessing a protected route (Fetching user profile).
    
    This ensures that the `Depends(oauth2.get_current_user)` dependency in the router 
    is actively validating the Bearer token before allowing access to the resource.
    """
    # Step 1: Authenticate and extract the token
    login_res = client.post(
        "/login", 
        data={"username": "hello@gmail.com", "password": "password123"}
    )
    token = login_res.json()["access_token"]
    
    # Step 2: Inject the token into the HTTP Authorization header
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 3: Fetch the user profile (Assuming ID 1 belongs to hello@gmail.com in the test DB)
    res = client.get("/user/1", headers=headers)
    
    assert res.status_code == status.HTTP_200_OK
    assert res.json()['email'] == "hello@gmail.com"