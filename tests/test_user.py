"""
Test module for User Management and Authentication.
This file contains integration tests for the user lifecycle: registration, 
preventing duplicate accounts, logging in (OAuth2), and fetching protected user profiles.
"""
import pytest
from fastapi import status
from sqlmodel import select
from app.schemas import UserOut
from sqlalchemy import func
from app.models import User

# ==========================================
# REGISTRATION & PROFILE VALIDATION
# ==========================================

def test_create_user(client):
    """
    Test standard user registration.
    
    Why use UserOut schema here?: We pass the response JSON into the UserOut Pydantic 
    model to strictly verify that the API returns the exact shape we expect.
    Crucially, we also assert that the raw password is NOT returned in the response 
    for security reasons.
    """
    payload = {"email": "bolt_api@gmail.com", "password": "password123"}
    res = client.post("/user/", json=payload)
    
    assert res.status_code == status.HTTP_201_CREATED
    
    # Validate response structure using our Pydantic schema
    new_user = UserOut(**res.json())
    assert new_user.email == payload["email"]
    
    # Security Check: Ensure sensitive data (password) is stripped from the response
    assert "password" not in res.json()

def test_create_user_duplicate(client, test_user):
    """
    Constraint Testing: Ensure the system rejects registration with an already existing email.
    
    The API must catch the database integrity error (or manual check) and return 
    a safe HTTP error rather than throwing a 500 Internal Server Error.
    """
# Attempting to use the email from the 'test_user' fixture
    payload = {"email": test_user['email'], "password": "anypassword"}
    res = client.post("/user/", json=payload)
    
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert res.json().get("detail") == "User with this email already exists"

def test_get_user_by_id(authorized_client, test_user):
    """
    Verification: Ensure an authenticated user can fetch their own profile.
    Uses 'authorized_client' to skip manual token handling.
    """
    res = authorized_client.get(f"/user/{test_user['id']}")
    assert res.status_code == status.HTTP_200_OK 
    assert res.json()['email'] == test_user['email']

def test_get_user_not_found(authorized_client, session):
    """
    Instead of guessing an ID like 9999, we find the current maximum ID in 
    the database and increment it by 1. This is mathematically guaranteed 
    to be a 'Not Found' case.
    """
    statement = select(func.max(User.id))
    max_id = session.exec(statement).first() or 0
    non_existent_id = max_id + 1
    
    res = authorized_client.get(f"/user/{non_existent_id}")
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json().get("detail") == f"User with id {non_existent_id} does not exist"

# ==========================================
# AUTHENTICATION (OAUTH2 FLOW)
# ==========================================

def test_login_user_success(client, test_user):
    """
    Test the OAuth2 Password Bearer login flow.
    
    Note: OAuth2PasswordRequestForm expects form-data (data=...), NOT a JSON body.
    Verifies that valid credentials return a JWT payload with 'access_token' and 'token_type'.
    """
    login_res = client.post(
        "/login", 
        data={"username": test_user['email'], "password": test_user['plain_password']}
    )
    
    assert login_res.status_code == status.HTTP_200_OK
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
@pytest.mark.parametrize("email, password, expected_status", [
    # 1. Non-existent email
    ("wrong_user@gmail.com", "password123", status.HTTP_403_FORBIDDEN),
    
    # 2. Correct email, incorrect password (uses placeholder to be replaced in logic)
    ("VALID_USER_EMAIL", "wrong_pass", status.HTTP_403_FORBIDDEN),
    
    # 3. Missing fields (Pydantic validation check)
    (None, "password123", status.HTTP_422_UNPROCESSABLE_CONTENT),
    ("VALID_USER_EMAIL", None, status.HTTP_422_UNPROCESSABLE_CONTENT),
    
    # 4. Empty string edge-case 
    ( "", "password123", status.HTTP_422_UNPROCESSABLE_CONTENT)
])
def test_login_user_failed(client, test_user, email, password, expected_status):
    """Comprehensive failure testing using Parametrization"""
    # Mapping placeholder to the actual email from the fixture
    login_email = test_user['email'] if email == "VALID_USER_EMAIL" else email
    res = client.post("/login", data={"username": login_email, "password": password})
    assert res.status_code == expected_status
